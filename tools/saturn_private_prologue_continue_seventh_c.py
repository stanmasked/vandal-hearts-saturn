#!/usr/bin/env python3
"""Stage122 private paired 84,000-frame seventh-C experiment; integrity metadata only."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import json, os, signal, subprocess, sys
from pathlib import Path
from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_capture_session import PINNED, _fingerprint, _not_in_checkout
from tools.saturn_private_frame_witness import validate_png_file
from tools.saturn_private_first_battle_window import _equal_frame
from tools.saturn_private_original_start_pair import _build_manifest, _check_media
from tools.saturn_private_original_start_sequence import MAX_SECONDS, SHA256, FRAME_STATS, SH2_LINE, VIDEO_LINE, _frame
from tools.saturn_private_start_ab import MAX_PNG_BYTES, _count_canonical_fads
from tools.saturn_private_prologue_continue_sixth_c import (
    FRAME_COUNT as STAGE121_FRAME_COUNT, CONFIRM6_PRESS, CONFIRM6_RELEASE,
    TERM72, STATE72, HEXA_EVENTS, HEXA_STATE,
)

FRAME_COUNT=84000
CONFIRM7_PRESS=72000
CONFIRM7_RELEASE=72006
CHECKPOINTS=tuple(range(120,FRAME_COUNT+1,120))
PRE_SEVENTH_CHECKPOINTS=tuple(range(120,CONFIRM7_PRESS,120))
POST_SEVENTH_CHECKPOINTS=tuple(f for f in CHECKPOINTS if f>CONFIRM7_PRESS)
POST_SEVENTH_BY_73200=tuple(range(CONFIRM7_PRESS+120,73200+1,120))
TERM84=f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n".encode()
STATE84=f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n".encode()
HEXA_EVENTS_84=HEXA_EVENTS.replace(TERM72,TERM84)
HEXA_STATE_84=HEXA_STATE.replace(STATE72,STATE84)
HEPTA_EVENTS=HEXA_EVENTS_84.replace(TERM84,(f"VH_PAD frame={CONFIRM7_PRESS} button=C action=PRESS\n"
    f"VH_PAD frame={CONFIRM7_RELEASE} button=C action=RELEASE\n").encode()+TERM84)
HEPTA_STATE=HEXA_STATE_84.replace(STATE84,(f"VH_PADSTATE frame={CONFIRM7_PRESS} button=C active_low_bit=0\n"
    f"VH_PADSTATE frame={CONFIRM7_RELEASE} button=C active_low_bit=1\n").encode()+STATE84)

def _pair_shape(a:Path,b:Path)->None:
    a,b=a.resolve(),b.resolve()
    if a.parent!=b.parent or len(str(a))!=len(str(b)):raise ValueError("Stage122 paired paths must be equal-shape siblings")

def _check_frames(d:Path)->tuple[int,tuple[int,int]]:
    pngs={f"frame-{n}.png" for n in CHECKPOINTS}
    expected=pngs|{"pre.png","post.png","frames.stats","fad.vhcdlog","pad-events.txt","pad-state.txt","sh2-window.txt","video-state.txt"}
    if {p.name for p in d.iterdir()}!=expected:raise ValueError("Stage122 output file set mismatch")
    dims=None
    for n in CHECKPOINTS:
        size,_=_frame(d,n)
        if not (64<=size[0]<=704 and 64<=size[1]<=512):raise ValueError("Stage122 PNG geometry invalid")
        if dims is None:dims=size
        elif dims!=size:raise ValueError("Stage122 PNG geometry changed")
    pre=validate_png_file(_private_regular(d/"pre.png",MAX_PNG_BYTES))
    post=validate_png_file(_private_regular(d/"post.png",MAX_PNG_BYTES))
    if dims is None or not (64<=pre[0]<=704 and 64<=pre[1]<=512) or post!=dims:raise ValueError("Stage122 pre/post geometry invalid")
    m=FRAME_STATS.fullmatch(_private_regular(d/"frames.stats",256))
    if not m:raise ValueError("Stage122 frame stats malformed")
    completed,pc0,pc1,w,h=map(int,m.groups())
    if completed!=FRAME_COUNT or pc0>0xffffffff or pc1>0xffffffff or (w,h)!=dims:raise ValueError("Stage122 frame stats mismatch")
    samples=[0]+list(CHECKPOINTS)+[FRAME_COUNT]
    for name,pattern in (("sh2-window.txt",SH2_LINE),("video-state.txt",VIDEO_LINE)):
        raw=_private_regular(d/name,1024*1024)
        if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:raise ValueError("Stage122 noncanonical diagnostics")
        lines=raw.splitlines()
        if len(lines)!=len(samples):raise ValueError("Stage122 diagnostic sample count mismatch")
        seen=[]
        for line in lines:
            m=pattern.fullmatch(line)
            if not m:raise ValueError("Stage122 diagnostic record malformed")
            seen.append(int(m.group(1)))
        if seen!=samples:raise ValueError("Stage122 diagnostic sequence mismatch")
    _count_canonical_fads(d)
    return len(CHECKPOINTS),dims

def audit_private_prologue_continue_seventh_c(control:Path,enabled:Path)->dict:
    if not control.is_absolute() or not enabled.is_absolute() or control.resolve()==enabled.resolve():raise ValueError("two distinct absolute Stage122 paths required")
    _pair_shape(control,enabled);_private_directory(control);_private_directory(enabled)
    if _private_regular(control/"pad-events.txt",2048)!=HEXA_EVENTS_84:raise ValueError("Stage122 six-C control receipt mismatch")
    if _private_regular(control/"pad-state.txt",2048)!=HEXA_STATE_84:raise ValueError("Stage122 six-C control active-low receipt mismatch")
    if _private_regular(enabled/"pad-events.txt",2048)!=HEPTA_EVENTS:raise ValueError("Stage122 seventh-C event receipt mismatch")
    if _private_regular(enabled/"pad-state.txt",2048)!=HEPTA_STATE:raise ValueError("Stage122 seventh-C active-low receipt mismatch")
    a=_private_regular(control/"pre.png",MAX_PNG_BYTES);b=_private_regular(enabled/"pre.png",MAX_PNG_BYTES)
    if validate_png_file(a)!=validate_png_file(b) or a!=b:raise ValueError("Stage122 cold boots differ before START")
    ca,da=_check_frames(control);cb,db=_check_frames(enabled)
    if ca!=700 or cb!=700 or da!=db:raise ValueError("Stage122 checkpoint count/dimensions mismatch")
    equal=sum(_equal_frame(control,enabled,f) for f in PRE_SEVENTH_CHECKPOINTS)
    if equal!=len(PRE_SEVENTH_CHECKPOINTS):raise ValueError("Stage122 diverged before seventh C")
    changes=[f for f in POST_SEVENTH_CHECKPOINTS if not _equal_frame(control,enabled,f)]
    early=[f for f in POST_SEVENTH_BY_73200 if not _equal_frame(control,enabled,f)]
    if not early:raise ValueError("Stage122 seventh C had no framebuffer effect by frame 73200")
    cc,ch=_count_canonical_fads(control);ec,eh=_count_canonical_fads(enabled)
    return {"schema_version":1,"kind":"STAGE122_PRIVATE_PROLOGUE_CONTINUE_INTEGRITY_ONLY",
        "frames_per_process":FRAME_COUNT,"paired_cold_boot_processes":2,"checkpoint_png_count_per_process":700,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified":True,"same_dimensions_across_runs":True,
        "seventh_C_press_frame":CONFIRM7_PRESS,"seventh_C_release_frame":CONFIRM7_RELEASE,
        "pre_seventh_checkpoint_equal_count":equal,"pre_seventh_checkpoint_total":len(PRE_SEVENTH_CHECKPOINTS),
        "first_post_seventh_framebuffer_divergence_by_73200":min(early),
        "first_post_seventh_framebuffer_divergence_through_84000":min(changes),
        "frame_84000_differs":not _equal_frame(control,enabled,FRAME_COUNT),
        "six_C_control_cd_event_count":cc,"seven_C_intervention_cd_event_count":ec,
        "cd_logs_differ":ch!=eh,"first_battle_or_player_control_verified":False,
        "requires_private_visual_review_of_dialogue_and_battle_state":True,"original_media_or_frame_hashes_exported":False}

def _run_one(exe:Path,cue:Path,d:Path,*,seventh:bool,seconds:int)->None:
    env={"HOME":str(d),"TMPDIR":str(d),"PATH":os.defpath,"LANG":"C","LC_ALL":"C","TZ":"UTC",
      "VH_SATURN_CAPTURE_GATE":str(d/"gate"),"VH_SATURN_FAD_LOG":str(d/"fad.vhcdlog"),
      "VH_SATURN_PRIVATE_FRAMES_DIR":str(d),"VH_SATURN_START_AT_FRAME":"12060",
      "VH_SATURN_CONFIRM_AT_FRAME":"12240","VH_SATURN_CONFIRM_BUTTON":"C",
      "VH_SATURN_CONFIRM_AT_FRAME2":"31200","VH_SATURN_CONFIRM2_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME3":"36000","VH_SATURN_CONFIRM3_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME4":"42000","VH_SATURN_CONFIRM4_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME5":"48000","VH_SATURN_CONFIRM5_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME6":"60000","VH_SATURN_CONFIRM6_ENABLED":"1",
      "VH_SATURN_CONFIRM_AT_FRAME7":str(CONFIRM7_PRESS),"VH_SATURN_CONFIRM7_ENABLED":"1" if seventh else "0"}
    p=subprocess.Popen([str(exe),"vh-private-frame-boot",str(cue),str(FRAME_COUNT)],cwd=d,env=env,
      stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,umask=0o077)
    try:status=p.wait(timeout=seconds)
    except subprocess.TimeoutExpired as exc:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.wait();raise ValueError("Stage122 private process timed out") from exc
    if status!=0:raise ValueError("Stage122 Yabause process failed")
    if (d/"gate").exists() or (d/"gate").is_symlink():raise ValueError("Stage122 CD gate remained open")

def run_private_prologue_continue_seventh_c(cue:Path,track1:Path,track2:Path,executable:Path,
    expected_runner_sha256:str,control:Path,enabled:Path,*,seconds:int=14400,pins:dict=PINNED)->dict:
    if not isinstance(expected_runner_sha256,str) or not SHA256.fullmatch(expected_runner_sha256):raise ValueError("invalid Stage122 executable SHA-256")
    if type(seconds)is not int or not 1<=seconds<=MAX_SECONDS:raise ValueError("invalid Stage122 timeout")
    if not executable.is_absolute() or executable.is_symlink() or not executable.is_file() or not os.access(executable,os.X_OK):raise ValueError("absolute nonsymlinked executable required")
    _not_in_checkout(executable)
    if any(not p.is_absolute() for p in (cue,track1,track2)):raise ValueError("absolute private media paths required")
    manifest=_build_manifest(cue,track1,track2)
    if not control.is_absolute() or not enabled.is_absolute() or control.resolve()==enabled.resolve():raise ValueError("two absolute output paths required")
    _pair_shape(control,enabled)
    for d in (control,enabled):
        _private_directory(d)
        if any(d.iterdir()):raise ValueError("Stage122 outputs must be fresh and empty")
    sources={cue.resolve(),track1.resolve(),track2.resolve(),executable.resolve()}
    for d in (control.resolve(),enabled.resolve()):
        if d in sources or any(p in d.parents for p in sources) or any(d in p.parents for p in sources):raise ValueError("private output overlaps source")
    media_before=_check_media(manifest,pins);runner_before=_fingerprint(executable)
    if runner_before[1]!=expected_runner_sha256:raise ValueError("runner differs from independent CI SHA-256")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=(pool.submit(_run_one,executable,cue,control,seventh=False,seconds=seconds),
                     pool.submit(_run_one,executable,cue,enabled,seventh=True,seconds=seconds))
            for future in futures:future.result()
    finally:
        try:
            if _check_media(manifest,pins)!=media_before:raise ValueError("source media changed")
        except (OSError,ValueError) as exc:raise ValueError("source media changed during Stage122") from exc
        if _fingerprint(executable)!=runner_before:raise ValueError("Stage122 executable changed")
    report=audit_private_prologue_continue_seventh_c(control,enabled)
    report.update({"same_pinned_original_media_before_and_after_both_processes":True,
        "same_public_runner_file_identity_and_digest_before_and_after":True,
        "both_private_processes_returned_zero_status":True,"private_environment_allowlisted":True,
        "first_battle_claimed":False})
    return report

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("cue","track1","track2","executable","control","enabled"):p.add_argument("--"+flag,type=Path,required=True)
    p.add_argument("--expected-runner-sha256",required=True);p.add_argument("--timeout",type=int,default=14400);a=p.parse_args()
    try:r=run_private_prologue_continue_seventh_c(a.cue,a.track1,a.track2,a.executable,a.expected_runner_sha256,a.control,a.enabled,seconds=a.timeout)
    except (OSError,ValueError,TypeError,subprocess.SubprocessError):
        print("STAGE122_PRIVATE_SEVENTH_C_RUN_REJECTED",file=sys.stderr);return 1
    print(json.dumps(r,sort_keys=True));return 0
if __name__=="__main__":sys.exit(main())
