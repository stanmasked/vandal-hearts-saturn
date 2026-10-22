"""Synthetic-only tests for Stage114's A/C confirm experiment auditor."""
from pathlib import Path
import tempfile
import unittest

from test_saturn_private_original_start_triple import _png, _write
from tools.saturn_private_original_start_sequence import (
    FRAME_COUNT, FIRST_PRESS, FIRST_RELEASE,
)
from tools.saturn_private_original_confirm_sequence import (
    CONFIRM_PRESS, CONFIRM_RELEASE, FIRST_ONLY_EVENTS, FIRST_ONLY_STATE,
    audit_private_confirm_sequence,
)

INITIAL_STATE = "VH_PADSTATE initial_start_bit=1\n"
SAMPLES = [0] + list(range(120, FRAME_COUNT + 1, 120)) + [FRAME_COUNT]


def _confirm_events(button):
    return (
        f"VH_PAD frame={FIRST_PRESS} button=START action=PRESS\n"
        f"VH_PAD frame={FIRST_RELEASE} button=START action=RELEASE\n"
        f"VH_PAD frame={CONFIRM_PRESS} button={button} action=PRESS\n"
        f"VH_PAD frame={CONFIRM_RELEASE} button={button} action=RELEASE\n"
        f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n"
    ).encode("ascii")


def _confirm_state(button):
    return (
        INITIAL_STATE
        + f"VH_PADSTATE initial_confirm_button={button} active_low_bit=1\n"
        + f"VH_PADSTATE frame={FIRST_PRESS} start_bit=0\n"
        + f"VH_PADSTATE frame={FIRST_RELEASE} start_bit=1\n"
        + f"VH_PADSTATE frame={CONFIRM_PRESS} button={button} active_low_bit=0\n"
        + f"VH_PADSTATE frame={CONFIRM_RELEASE} button={button} active_low_bit=1\n"
        + f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n"
    ).encode("ascii")


def _populate(folder, mode, button=None):
    if mode == "first_only":
        events, state = FIRST_ONLY_EVENTS, FIRST_ONLY_STATE
    else:
        events, state = _confirm_events(button), _confirm_state(button)
    _write(folder, "pad-events.txt", events)
    _write(folder, "pad-state.txt", state)
    _write(folder, "fad.vhcdlog", b"VHCD_FAD 150\n")
    _write(folder, "pre.png", _png((25, 35, 45)))
    _write(folder, "post.png", _png((60, 70, 80) if mode == "first_only" else (90, 100, 110)))
    _write(
        folder,
        "frames.stats",
        b"STAGE99_FRAMES 24000\nSTAGE99_PC_BEFORE 100\n"
        b"STAGE99_PC_AFTER 200\nSTAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n",
    )
    sh2 = "".join(
        f"VH_SH2 frame={n} pc=1 valid=1 sr=0 pr=0 gbr=0 r0=0 r1=0 r2=0 "
        f"r3=0 r4=0 r5=0 r15=0 m8=0 m6=0 m4=0 m2=0\n"
        for n in SAMPLES
    ).encode("ascii")
    video = "".join(
        f"VH_VIDEO frame={n} pc=1 tvmd=0 bgon=0 ramctl=0 vdp1_tvmr=0 "
        f"vdp1_ptmr=0 vdp1_edsr=0 vdp1_nz=0 vdp2_nz=0 cram_nz=0 "
        f"rgb_nz=0 width=64 height=64\n"
        for n in SAMPLES
    ).encode("ascii")
    _write(folder, "sh2-window.txt", sh2)
    _write(folder, "video-state.txt", video)
    for frame in range(120, FRAME_COUNT + 1, 120):
        if frame <= 12000:
            color = (25, 35, 45)
        elif frame <= 12240:
            color = (60, 70, 80)
        elif mode == "first_only":
            color = (60, 70, 80) if frame < 13680 else (15, 15, 15)
        else:
            color = (90, 100, 110)
        _write(folder, f"frame-{frame}.png", _png(color))


class Stage114PrivateConfirmAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.first_only = self.root / "first-only"
        self.confirm = self.root / "confirm"
        for folder in (self.first_only, self.confirm):
            folder.mkdir(mode=0o700)
            folder.chmod(0o700)
        _populate(self.first_only, "first_only")
        _populate(self.confirm, "confirm", "A")

    def test_accepts_a_or_c_when_confirm_changes_frame_before_attract(self):
        for button in ("A", "C"):
            with self.subTest(button=button):
                temp = tempfile.TemporaryDirectory()
                self.addCleanup(temp.cleanup)
                root = Path(temp.name)
                root.chmod(0o700)
                first_only = root / "first-only"
                confirm = root / "confirm"
                for folder in (first_only, confirm):
                    folder.mkdir(mode=0o700)
                    folder.chmod(0o700)
                _populate(first_only, "first_only")
                _populate(confirm, "confirm", button)
                report = audit_private_confirm_sequence(first_only, confirm, button)
                self.assertEqual(report["confirm_button"], button)
                self.assertEqual(report["first_only_and_confirm_identical_through_frame"], 12120)
                self.assertEqual(report["confirm_first_divergence_before_idle_attract_transition"], 12360)
                self.assertFalse(report["new_game_or_first_battle_verified"])
                self.assertFalse(report["original_media_or_frame_hashes_exported"])

    def test_rejects_no_confirm_effect_before_idle_attract_transition(self):
        for frame in range(12360, 13680, 120):
            _write(
                self.confirm,
                f"frame-{frame}.png",
                (self.first_only / f"frame-{frame}.png").read_bytes(),
            )
        with self.assertRaisesRegex(ValueError, "before the idle attract transition"):
            audit_private_confirm_sequence(self.first_only, self.confirm, "A")

    def test_rejects_divergence_before_confirm_pulse(self):
        _write(self.confirm, "frame-12120.png", _png((1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "before the A/C confirm pulse"):
            audit_private_confirm_sequence(self.first_only, self.confirm, "A")

    def test_rejects_wrong_active_low_receipt(self):
        _write(self.confirm, "pad-state.txt", b"VH_PADSTATE frame=12240 button=A active_low_bit=1\n")
        with self.assertRaisesRegex(ValueError, "confirm active-low receipt"):
            audit_private_confirm_sequence(self.first_only, self.confirm, "A")

    def test_rejects_missing_checkpoint(self):
        (self.confirm / "frame-240.png").unlink()
        with self.assertRaisesRegex(ValueError, "checkpoint sequence incomplete"):
            audit_private_confirm_sequence(self.first_only, self.confirm, "A")

    def test_rejects_unknown_confirm_button(self):
        with self.assertRaisesRegex(ValueError, "must be A or C"):
            audit_private_confirm_sequence(self.first_only, self.confirm, "B")


if __name__ == "__main__":
    unittest.main()
