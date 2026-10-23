#!/usr/bin/env python3
"""Stage125 private paired 120,000-frame tenth-C experiment; integrity metadata only."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import json, os, signal, subprocess, sys
from pathlib import Path
from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_archive_gate import verify_private_stage124_archive
from tools.saturn_private_archived_pair_audit import audit_archived_stage124_pair
from tools.saturn_private_capture_session import PINNED, _fingerprint, _not_in_checkout
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_first_battle_window import _equal_frame
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import MAX_SECONDS, SHA256, FRAME_STATS, SH2_LINE, VIDEO_LINE, _frame
from tools.saturn_private_start_ab import MAX_PNG_BYTES, _count_canonical_fads
from tools.saturn_private_prologue_continue_ninth_c import (
    TERM108, STATE108, NONA_EVENTS, NONA_STATE,
)

FRAME_COUNT=120000
CONFIRM10_PRESS=108000
CONFIRM10_RELEASE=108006
CHECKPOINTS=tuple(range(120,FRAME_COUNT+1,120))
PRE_TENTH_CHECKPOINTS=tuple(range(120,CONFIRM10_PRESS,120))
POST_TENTH_CHECKPOINTS=tuple(f for f in CHECKPOINTS if f>CONFIRM10_PRESS)
POST_TENTH_BY_109200=tuple(range(CONFIRM10_PRESS+120,109200+1,120))
TERM120=f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
STATE120=f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
NONA_EVENTS_120=NONA_EVENTS.replace(TERM108,TERM120)
NONA_STATE_120=NONA_STATE.replace(STATE108,STATE120)
DECA_EVENTS=NONA_EVENTS_120.replace(TERM120,(f"VH_PAD frame={CONFIRM10_PRESS} button=C action=PRESS\n"
    f"VH_PAD frame={CONFIRM10_RELEASE} button=C action=RELEASE\n").encode("ascii")+TERM120)
DECA_STATE=NONA_STATE_120.replace(STATE120,(f"VH_PADSTATE frame={CONFIRM10_PRESS} button=C active_low_bit=0\n"
    f"VH_PADSTATE frame={CONFIRM10_RELEASE} button=C active_low_bit=1\n").encode("ascii")+STATE120)

def _require_stage124_drive_readback_receipt(receipt:Path,readback_archive:Path)->tuple[int,str,tuple[int,...]]:
    """Require an owner-only private attestation before any new capture is launched."""
    if (not readback_archive.is_absolute() or readback_archive.is_symlink()
            or readback_archive.resolve()==receipt.resolve()):
        raise ValueError("distinct absolute private Stage124 Drive-downloaded archive required")
    _not_in_checkout(readback_archive)
    if not receipt.is_absolute() or receipt.is_symlink():
        raise ValueError("absolute private Stage124 Drive readback receipt required")
    _not_in_checkout(receipt)
    try:
        evidence=json.loads(_private_regular(receipt,16384).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Stage124 Drive readback receipt unreadable") from exc
    if not isinstance(evidence,dict) or type(evidence.get("stage")) is not int or evidence["stage"]!=124:
        raise ValueError("wrong previous archive stage")
    if (evidence.get("owner_only") is not True or evidence.get("readback_verified") is not True
            or not isinstance(evidence.get("drive_file_id"),str)
            or not evidence["drive_file_id"].strip()
            or type(evidence.get("archive_size_bytes")) is not int
            or evidence["archive_size_bytes"]<=0):
        raise ValueError("Stage124 archive Drive readback not attested")
    archive_hash=evidence.get("archive_sha256")
    readback_hash=evidence.get("drive_readback_sha256")
    if (not isinstance(archive_hash,str) or not SHA256.fullmatch(archive_hash)
            or not isinstance(readback_hash,str) or readback_hash!=archive_hash):
        raise ValueError("Stage124 archive hash readback not attested")
    try:
        archived=_fingerprint(readback_archive)
    except OSError as exc:
        raise ValueError("Stage124 Drive-downloaded archive unavailable") from exc
    if archived[0]!=evidence["archive_size_bytes"] or archived[1]!=archive_hash:
        raise ValueError("Stage124 Drive-downloaded archive differs from private receipt")
    return archived

def _pair_shape(a:Path,b:Path)->None:
    a,b=a.resolve(),b.resolve()
    if a.parent!=b.parent or len(str(a))!=len(str(b)):raise ValueError("Stage125 paired paths must be equal-shape siblings")

def _check_frames(d:Path)->tuple[int,tuple[int,int]]:
    pngs={f"frame-{n}.png" for n in CHECKPOINTS}
    expected=pngs|{"pre.png","post.png","frames.stats","fad.vhcdlog","pad-events.txt","pad-state.txt","sh2-window.txt","video-state.txt"}
    if {p.name for p in d.iterdir()}!=expected:raise ValueError("Stage125 output file set mismatch")
    dims=None
    for n in CHECKPOINTS:
        size,_=_frame(d,n)
        if not (64<=size[0]<=704 and 64<=size[1]<=512):raise ValueError("Stage125 PNG geometry invalid")
        if dims is None:dims=size
        elif dims!=size:raise ValueError("Stage125 PNG geometry changed")
    pre=validate_png_file(_private_regular(d/"pre.png",MAX_PNG_BYTES))
    post=validate_png_file(_private_regular(d/"post.png",MAX_PNG_BYTES))
    if dims is None or not (64<=pre[0]<=704 and 64<=pre[1]<=512) or post!=dims:raise ValueError("Stage125 pre/post geometry invalid")
    m=FRAME_STATS.fullmatch(_private_regular(d/"frames.stats",256))
    if not m:raise ValueError("Stage125 frame stats malformed")
    completed,pc0,pc1,w,h=map(int,m.groups())
    if completed!=FRAME_COUNT or pc0>0xffffffff or pc1>0xffffffff or (w,h)!=dims:raise ValueError("Stage125 frame stats mismatch")
    samples=[0]+list(CHECKPOINTS)+[FRAME_COUNT]
    for name,pattern in (("sh2-window.txt",SH2_LINE),("video-state.txt",VIDEO_LINE)):
        raw=_private_regular(d/name,1024*1024)
        if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:raise ValueError("Stage125 noncanonical diagnostics")
        lines=raw.splitlines()
        if len(lines)!=len(samples):raise ValueError("Stage125 diagnostic sample count mismatch")
        seen=[]
        for line in lines:
            m=pattern.fullmatch(line)
            if not m:raise ValueError("Stage125 diagnostic record malformed")
            seen.append(int(m.group(1)))
        if seen!=samples:raise ValueError("Stage125 diagnostic sequence mismatch")
    _count_canonical_fads(d)
    return len(CHECKPOINTS),dims

def audit_private_prologue_continue_tenth_c(control:Path,enabled:Path)->dict:
    if not control.is_absolute() or not enabled.is_absolute() or control.resolve()==enabled.resolve():raise ValueError("two distinct absolute Stage125 paths required")
    _pair_shape(control,enabled);_private_directory(control);_private_directory(enabled)
    if _private_regular(control/"pad-events.txt",2048)!=NONA_EVENTS_120:raise ValueError("Stage125 nine-C control receipt mismatch")
    if _private_regular(control/"pad-state.txt",2048)!=NONA_STATE_120:raise ValueError("Stage125 nine-C control active-low receipt mismatch")
    if _private_regular(enabled/"pad-events.txt",2048)!=DECA_EVENTS:raise ValueError("Stage125 tenth-C event receipt mismatch")
    if _private_regular(enabled/"pad-state.txt",2048)!=DECA_STATE:raise ValueError("Stage125 tenth-C active-low receipt mismatch")
    a=_private_regular(control/"pre.png",MAX_PNG_BYTES);b=_private_regular(enabled/"pre.png",MAX_PNG_BYTES)
    if validate_png_file(a)!=validate_png_file(b) or a!=b:raise ValueError("Stage125 cold boots differ before START")
    ca,da=_check_frames(control);cb,db=_check_frames(enabled)
    if ca!=1000 or cb!=1000 or da!=db:raise ValueError("Stage125 checkpoint count/dimensions mismatch")
    equal=sum(_equal_frame(control,enabled,f) for f in PRE_TENTH_CHECKPOINTS)
    if equal!=len(PRE_TENTH_CHECKPOINTS):raise ValueError("Stage125 diverged before tenth C")
    changes=[f for f in POST_TENTH_CHECKPOINTS if not _equal_frame(control,enabled,f)]
    early=[f for f in POST_TENTH_BY_109200 if not _equal_frame(control,enabled,f)]
    if not early:raise ValueError("Stage125 tenth C had no framebuffer effect by frame 109200")
    cc,ch=_count_canonical_fads(control);ec,eh=_count_canonical_fads(enabled)
    return {"schema_version":1,"kind":"STAGE125_PRIVATE_PROLOGUE_CONTINUE_INTEGRITY_ONLY",
        "frames_per_process":FRAME_COUNT,"paired_cold_boot_processes":2,"checkpoint_png_count_per_process":1000,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified":True,"same_dimensions_across_runs":True,
        "tenth_C_press_frame":CONFIRM10_PRESS,"tenth_C_release_frame":CONFIRM10_RELEASE,
        "pre_tenth_checkpoint_equal_count":equal,"pre_tenth_checkpoint_total":len(PRE_TENTH_CHECKPOINTS),
        "first_post_tenth_framebuffer_divergence_by_109200":min(early),
        "first_post_tenth_framebuffer_divergence_through_120000":min(changes),
        "frame_120000_differs":not _equal_frame(control,enabled,FRAME_COUNT),
        "nine_C_control_cd_event_count":cc,"ten_C_intervention_cd_event_count":ec,
        "cd_logs_differ":ch!=eh,"first_battle_or_player_control_verified":False,
        "requires_private_visual_review_of_dialogue_and_battle_state":True,"original_media_or_frame_hashes_exported":False}

def _run_one(exe:Path,cue:Path,d:Path,*,tenth:bool,seconds:int)->None:
    env={"HOME":str(d),"TMPDIR":str(d),"PATH":os.defpath,"LANG":"C","LC_ALL":"C","TZ":"UTC",
      "VH_SATURN_CAPTURE_GATE":str(d/"gate"),"VH_SATURN_FAD_LOG":str(d/"fad.vhcdlog"),
      "VH_SATURN_PRIVATE_FRAMES_DIR":str(d),"VH_SATURN_START_AT_FRAME":"12060",
      "VH_SATURN_CONFIRM_AT_FRAME":"12240","VH_SATURN_CONFIRM_BUTTON":"C",
      "VH_SATURN_CONFIRM_AT_FRAME2":"31200","VH_SATURN_CONFIRM2_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME3":"36000","VH_SATURN_CONFIRM3_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME4":"42000","VH_SATURN_CONFIRM4_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME5":"48000","VH_SATURN_CONFIRM5_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME6":"60000","VH_SATURN_CONFIRM6_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME7":"72000","VH_SATURN_CONFIRM7_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME8":"84000","VH_SATURN_CONFIRM8_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME9":"96000","VH_SATURN_CONFIRM9_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME10":str(CONFIRM10_PRESS),"VH_SATURN_CONFIRM10_ENABLED":"1" if tenth else "0"}
    p=subprocess.Popen([str(exe),"vh-private-frame-boot",str(cue),str(FRAME_COUNT)],cwd=d,env=env,
      stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,umask=0o077)
    try:status=p.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.wait();raise ValueError("Stage125 private process timed out") from exc
    if status!=0:raise ValueError("Stage125 Yabause process failed")
    if (d/"gate").exists() or (d/"gate").is_symlink():raise ValueError("Stage125 CD gate remained open")

def _enforce_stage124_capture_archive_integrity(readback_archive:Path, fingerprint:tuple)->dict:
    """Stage128: verify the FULL previous capture before admitting any emulator run.

    A matching local receipt and file digest alone cannot establish valid
    900+900-frame evidence, or independently authenticate Google Drive access.
    """
    if (not isinstance(fingerprint,tuple) or len(fingerprint)<2
            or type(fingerprint[0]) is not int or fingerprint[0]<=0
            or not isinstance(fingerprint[1],str) or not SHA256.fullmatch(fingerprint[1])):
        raise ValueError("previous archive fingerprint unavailable")
    result=verify_private_stage124_archive(readback_archive,
        expected_size=fingerprint[0],expected_sha256=fingerprint[1])
    if (result.get("stage")!=124 or result.get("checkpoint_pngs")!=1800
            or result.get("cohorts")!=2 or result.get("regular_members",0)<1816
            or result.get("archive_matches_supplied_fingerprint") is not True):
        raise ValueError("Stage124 readback archive integrity gate incomplete")
    return result

def run_private_prologue_continue_tenth_c(cue:Path,track1:Path,track2:Path,executable:Path,
    expected_runner_sha256:str,control:Path,enabled:Path,stage124_drive_receipt:Path,
    stage124_drive_readback_archive:Path,*,seconds:int=14400,pins:dict=PINNED)->dict:
    readback_before=_require_stage124_drive_readback_receipt(stage124_drive_receipt,stage124_drive_readback_archive)
    _enforce_stage124_capture_archive_integrity(stage124_drive_readback_archive,readback_before)
    semantic=audit_archived_stage124_pair(stage124_drive_readback_archive,
        expected_size=readback_before[0],expected_sha256=readback_before[1])
    if semantic.get("stage124_paired_capture_semantics_verified_in_archive") is not True:
        raise ValueError("Stage124 previous capture pair semantic audit not verified")
    if not isinstance(expected_runner_sha256,str) or not SHA256.fullmatch(expected_runner_sha256):raise ValueError("invalid Stage125 executable SHA-256")
    if type(seconds)is not int or not 1<=seconds<=MAX_SECONDS:raise ValueError("invalid Stage125 timeout")
    if not executable.is_absolute() or executable.is_symlink() or not executable.is_file() or not os.access(executable,os.X_OK):raise ValueError("absolute nonsymlinked executable required")
    _not_in_checkout(executable)
    if any(not p.is_absolute() for p in (cue,track1,track2)):raise ValueError("absolute private media paths required")
    manifest=_build_manifest(cue,track1,track2)
    if not control.is_absolute() or not enabled.is_absolute() or control.resolve()==enabled.resolve():raise ValueError("two absolute output paths required")
    _pair_shape(control,enabled)
    for d in (control,enabled):
        _private_directory(d)
        if any(d.iterdir()):raise ValueError("Stage125 outputs must be fresh and empty")
    sources={cue.resolve(),track1.resolve(),track2.resolve(),executable.resolve()}
    for d in (control.resolve(),enabled.resolve()):
        if d in sources or any(p in d.parents for p in sources) or any(d in p.parents for p in sources):raise ValueError("private output overlaps source")
    media_before=_check_media(manifest,pins);runner_before=_fingerprint(executable)
    if runner_before[1]!=expected_runner_sha256:raise ValueError("runner differs from independent CI SHA-256")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=(pool.submit(_run_one,executable,cue,control,tenth=False,seconds=seconds),
                     pool.submit(_run_one,executable,cue,enabled,tenth=True,seconds=seconds))
            for future in futures:future.result()
    finally:
        try:
            if _check_media(manifest,pins)!=media_before:raise ValueError("source media changed")
        except (OSError,ValueError) as exc:raise ValueError("source media changed during Stage125") from exc
        if _fingerprint(executable)!=runner_before:raise ValueError("Stage125 executable changed")
        if _fingerprint(stage124_drive_readback_archive)!=readback_before:raise ValueError("Stage124 Drive readback archive changed during Stage125")
    report=audit_private_prologue_continue_tenth_c(control,enabled)
    report.update({"same_pinned_original_media_before_and_after_both_processes":True,
        "same_public_runner_file_identity_and_digest_before_and_after":True,
        "both_private_processes_returned_zero_status":True,"private_environment_allowlisted":True,
        "first_battle_claimed":False})
    return report

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("cue","track1","track2","executable","control","enabled"):p.add_argument("--"+flag,type=Path,required=True)
    p.add_argument("--stage124-drive-receipt",type=Path,required=True)
    p.add_argument("--stage124-drive-readback-archive",type=Path,required=True)
    p.add_argument("--expected-runner-sha256",required=True);p.add_argument("--timeout",type=int,default=14400);a=p.parse_args()
    try:r=run_private_prologue_continue_tenth_c(a.cue,a.track1,a.track2,a.executable,a.expected_runner_sha256,a.control,a.enabled,a.stage124_drive_receipt,a.stage124_drive_readback_archive,seconds=a.timeout)
    except (OSError,ValueError,TypeError,subprocess.SubprocessError):
        print("STAGE125_PRIVATE_TENTH_C_RUN_REJECTED",file=sys.stderr);return 1
    print(json.dumps(r,sort_keys=True));return 0
if __name__=="__main__":sys.exit(main())
