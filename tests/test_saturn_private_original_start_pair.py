"""Stage110: genuinely separate subprocesses over completely INVENTED CD data."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.saturn_private_original_start_pair import (
    run_original_pair, audit_joint_evidence,
)

# An invented stand-in process: never Yabause, never an original-game image.
# It exposes the same bounded numeric and PNG output contract without
# transmitting or bundling copyrighted Saturn code or data.
FAKE_RUNNER = r'''#!/usr/bin/env python3
import os
from pathlib import Path
import struct, sys, zlib

def chunk(k,p):
    return struct.pack(">I",len(p))+k+p+struct.pack(">I",zlib.crc32(k+p)&0xffffffff)

def png(colour):
    return (b"\x89PNG\r\n\x1a\n"+
            chunk(b"IHDR",struct.pack(">IIBBBBB",64,64,8,2,0,0,0))+
            chunk(b"IDAT",zlib.compress((b"\x00"+bytes(colour)*64)*64))+
            chunk(b"IEND",b""))

assert len(sys.argv)==4 and sys.argv[1]=="vh-private-frame-boot"
assert sys.argv[3]=="13200"
directory=Path(os.environ["VH_SATURN_PRIVATE_FRAMES_DIR"])
assert directory==Path.cwd()
assert not any(k in os.environ for k in ("LD_PRELOAD","LD_LIBRARY_PATH",
                                         "DYLD_INSERT_LIBRARIES","PYTHONPATH",
                                         "DISPLAY"))
pressed=os.environ.get("VH_SATURN_START_AT_FRAME")
assert pressed in (None,"12060")
assert Path(sys.argv[2]).is_file()

gate=Path(os.environ["VH_SATURN_CAPTURE_GATE"])
gate.write_text("1\n")
Path(os.environ["VH_SATURN_FAD_LOG"]).write_bytes(
    b"VHCD_FAD 150\nVHCD_FAD 151\n" if pressed else b"VHCD_FAD 150\n")
p=directory/"pad-events.txt"
s=directory/"pad-state.txt"
if pressed:
    p.write_text("VH_PAD frame=12060 button=START action=PRESS\n"
                 "VH_PAD frame=12066 button=START action=RELEASE\n"
                 "VH_PAD mode=1 completed_frames=13200\n")
    s.write_text("VH_PADSTATE initial_start_bit=1\n"
                 "VH_PADSTATE frame=12060 start_bit=0\n"
                 "VH_PADSTATE frame=12066 start_bit=1\n"
                 "VH_PADSTATE mode=1 completed_frames=13200\n")
else:
    p.write_text("VH_PAD mode=0 completed_frames=13200\n")
    s.write_text("VH_PADSTATE initial_start_bit=1\n"
                 "VH_PADSTATE mode=0 completed_frames=13200\n")
for n in range(120,13201,120):
    different=bool(os.environ.get("STAGE110_FAKE_PRE_DIVERGE")) and pressed and n==12000
    colour=(1,9,3) if different else (12,13,14) if n<=12000 else (3,4,5) if pressed else (6,7,8)
    (directory/f"frame-{n}.png").write_bytes(png(colour))
(directory/"frames.stats").write_text(
    "STAGE99_FRAMES 13200\n"
    "STAGE99_PC_BEFORE 1000\n"
    "STAGE99_PC_AFTER 2000\n"
    "STAGE99_WIDTH 64\n"
    "STAGE99_HEIGHT 64\n")
gate.unlink()
if os.environ.get("STAGE110_FAKE_MUTATE"):
    (Path(sys.argv[2]).parent/"invented-track1.bin").write_bytes(b"CHANGED")
if os.environ.get("STAGE110_FAKE_FAIL"):
    sys.exit(3)
'''


class PrivatePairTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        self.root.chmod(0o700)
        self.source=self.root/"media"
        self.source.mkdir(mode=0o700)
        self.cue=self.source/"invented.cue"
        self.t1=self.source/"invented-track1.bin"
        self.t2=self.source/"invented-track2.bin"
        for path,raw in (
            (self.cue,b'FILE "invented-track1.bin" BINARY\n'),
            (self.t1,b"\x00"*4096),
            (self.t2,b"\x42"*1024),
        ):
            path.write_bytes(raw)
            path.chmod(0o600)
        self.runner=self.root/"invented-runner"
        self.runner.write_text(FAKE_RUNNER)
        self.runner.chmod(0o700)
        self.sha=hashlib.sha256(self.runner.read_bytes()).hexdigest()
        self.pins={k:(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
                   for k,p in (("cue",self.cue),("track1",self.t1),("track2",self.t2))}
        self.control=self.root/"control"
        self.pressed=self.root/"pressed"
        for p in (self.control,self.pressed):
            p.mkdir(mode=0o700)
            p.chmod(0o700)

    def run_pair(self, *, runner_sha=None, sources=None):
        a,b,c=sources or (self.cue,self.t1,self.t2)
        return run_original_pair(a,b,c,self.runner,
                                 self.sha if runner_sha is None else runner_sha,
                                 self.control,self.pressed,seconds=15,pins=self.pins)

    def set_fake_runner_behavior(self, old, new):
        source=self.runner.read_text()
        if source.count(old)!=1:
            raise AssertionError("synthetic fault-injection anchor is not unique")
        self.runner.write_text(source.replace(old,new))
        self.runner.chmod(0o700)
        self.sha=hashlib.sha256(self.runner.read_bytes()).hexdigest()

    def test_two_actual_independent_fake_subprocesses_pass_integrity(self):
        report=self.run_pair()
        self.assertTrue(report["same_stage02_full_media_digest_before_and_after_both_processes"])
        self.assertTrue(report["two_processes_returned_zero_status"])
        self.assertTrue(report["pre_start_png_checkpoints_match"])
        self.assertTrue(report["emulator_frame_stats_verified_in_both_processes"])
        self.assertTrue(report["final_frame_dimensions_crosschecked_to_both_stats"])
        self.assertEqual(report["completed_frames_from_both_emulator_stats"],13200)
        self.assertEqual(report["checkpoint_png_count_per_process"],110)
        self.assertTrue(report["all_checkpoint_pngs_valid_and_sequential"])
        self.assertTrue(report["subprocess_environment_allowlisted"])
        self.assertTrue(report["post_start_12120_png_files_differ"])
        self.assertTrue(report["post_start_13200_png_files_differ"])
        self.assertTrue(report["start_press_seen_in_host_padbits_as_active_low_zero"])
        self.assertFalse(report["title_to_menu_verified_by_visual_inspection"])
        self.assertFalse(report["actual_first_battle_verified"])
        self.assertNotIn(str(self.root), str(report))
        self.assertNotIn(self.sha, str(report))
        self.assertNotIn("VHCD_FAD", str(report))

    def test_wrong_or_noncanonical_runner_sha_rejected_before_execution(self):
        for v in ("",self.sha.upper(),"0"*64):
            with self.subTest(v=v), self.assertRaises(ValueError):
                self.run_pair(runner_sha=v)
        self.assertEqual(list(self.control.iterdir()),[])

    def test_pre_start_difference_rejected(self):
        self.set_fake_runner_behavior(
            'different=bool(os.environ.get("STAGE110_FAKE_PRE_DIVERGE")) and pressed and n==12000',
            'different=bool(pressed) and n==12000',
        )
        with self.assertRaisesRegex(ValueError, "before START"):
            self.run_pair()

    def test_original_media_mutation_detected_immediately(self):
        self.set_fake_runner_behavior(
            'if os.environ.get("STAGE110_FAKE_MUTATE"):',
            'if True:',
        )
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.run_pair()
        self.assertEqual(self.t1.read_bytes(),b"CHANGED")

    def test_runner_failure_has_no_success_receipt(self):
        self.set_fake_runner_behavior(
            'if os.environ.get("STAGE110_FAKE_FAIL"):',
            'if True:',
        )
        with self.assertRaisesRegex(ValueError, "runner returned an error"):
            self.run_pair()

    def test_inherited_start_variable_cannot_contaminate_control(self):
        with patch.dict(os.environ,{"VH_SATURN_START_AT_FRAME":"12060",
                                    "VH_SATURN_FAD_LOG":"/tmp/unsafe.log"}):
            self.run_pair()
        self.assertEqual((self.control/"pad-events.txt").read_bytes(),
                         b"VH_PAD mode=0 completed_frames=13200\n")

    def test_source_symlink_refused(self):
        alias=self.root/"cue-alias"
        alias.symlink_to(self.cue)
        with self.assertRaises(ValueError):
            self.run_pair(sources=(alias,self.t1,self.t2))

    def test_different_track_parent_rejected(self):
        other=self.root/"other"
        other.mkdir(mode=0o700)
        other_track=other/"track.bin"
        other_track.write_bytes(self.t1.read_bytes())
        with self.assertRaises(ValueError):
            self.run_pair(sources=(self.cue,other_track,self.t2))

    def test_world_readable_or_nonempty_private_output_rejected(self):
        self.control.chmod(0o755)
        with self.assertRaises(ValueError):
            self.run_pair()
        self.control.chmod(0o700)
        (self.control/"existing").write_text("x")
        with self.assertRaises(ValueError):
            self.run_pair()

    def test_same_control_and_pressed_folder_rejected(self):
        with self.assertRaises(ValueError):
            run_original_pair(self.cue,self.t1,self.t2,self.runner,
                              self.sha,self.control,self.control,
                              seconds=15,pins=self.pins)

    def test_missing_emulator_final_stats_rejected(self):
        self.run_pair()
        (self.pressed/"frames.stats").unlink()
        with self.assertRaises((OSError,ValueError)):
            audit_joint_evidence(self.control,self.pressed)

    def test_forged_incomplete_emulator_frame_count_rejected(self):
        self.run_pair()
        path=self.pressed/"frames.stats"
        path.write_bytes(path.read_bytes().replace(b"STAGE99_FRAMES 13200",
                                                  b"STAGE99_FRAMES 13199"))
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,"frame contract"):
            audit_joint_evidence(self.control,self.pressed)

    def test_valid_final_png_rejected_if_stats_geometry_disagrees(self):
        self.run_pair()
        path=self.control/"frames.stats"
        path.write_bytes(path.read_bytes().replace(b"STAGE99_WIDTH 64",
                                                  b"STAGE99_WIDTH 320"))
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,"dimensions differ"):
            audit_joint_evidence(self.control,self.pressed)

    def test_extra_junk_in_emulator_frame_stats_rejected(self):
        self.run_pair()
        path=self.control/"frames.stats"
        path.write_bytes(path.read_bytes()+b"STAGE99_FRAMES 13200\n")
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,"malformed"):
            audit_joint_evidence(self.control,self.pressed)

    def test_inherited_loader_python_and_display_hooks_are_removed(self):
        hostile = {
            "LD_PRELOAD": "/tmp/untrusted-preload.so",
            "LD_LIBRARY_PATH": "/tmp/untrusted-libs",
            "DYLD_INSERT_LIBRARIES": "/tmp/untrusted.dylib",
            "PYTHONPATH": "/tmp/untrusted-python",
            "DISPLAY": ":999",
        }
        with patch.dict(os.environ,hostile):
            report=self.run_pair()
        self.assertTrue(report["subprocess_environment_allowlisted"])

    def test_missing_intermediate_checkpoint_png_rejected(self):
        self.run_pair()
        (self.control/"frame-600.png").unlink()
        with self.assertRaisesRegex(ValueError,"sequence is incomplete"):
            audit_joint_evidence(self.control,self.pressed)

    def test_bad_disc_hash_rejected_before_execution(self):
        bad={**self.pins,"track1":(4096,"0"*64)}
        with self.assertRaises(ValueError):
            run_original_pair(self.cue,self.t1,self.t2,self.runner,
                              self.sha,self.control,self.pressed,
                              seconds=15,pins=bad)
        self.assertFalse(any(self.control.iterdir()))


if __name__=="__main__":
    unittest.main()
