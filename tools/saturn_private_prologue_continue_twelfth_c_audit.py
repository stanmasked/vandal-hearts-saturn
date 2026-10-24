#!/usr/bin/env python3
"""Stage145 integrity-only audit for a paired twelfth-C private Saturn run."""
from __future__ import annotations

from pathlib import Path

from tools.saturn_private_capture_cohort import _private_directory, _private_regular
from tools.saturn_private_first_battle_window import _equal_frame
from tools.saturn_private_original_start_sequence import FRAME_STATS, SH2_LINE, VIDEO_LINE, _frame
from tools.saturn_private_start_ab import _count_canonical_fads, MAX_PNG_BYTES
from tools.saturn_private_prologue_continue_eleventh_c_audit import (
    ELEVA_EVENTS, ELEVA_STATE, TERM132, STATE132,
)

FRAME_COUNT = 144000
CONFIRM11_PRESS = 120000
CONFIRM11_RELEASE = 120006
CONFIRM12_PRESS = 132000
CONFIRM12_RELEASE = 132006
CHECKPOINTS = tuple(range(120, FRAME_COUNT + 1, 120))
PRE_TWELFTH_CHECKPOINTS = tuple(f for f in CHECKPOINTS if f < CONFIRM12_PRESS)
POST_TWELFTH_CHECKPOINTS = tuple(f for f in CHECKPOINTS if f > CONFIRM12_PRESS)
POST_TWELFTH_BY_133200 = tuple(range(CONFIRM12_PRESS + 120, 133200 + 1, 120))
TERM144 = f"VH_PAD mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
STATE144 = f"VH_PADSTATE mode=1 completed_frames={FRAME_COUNT}\n".encode("ascii")
CONTROL_EVENTS = ELEVA_EVENTS.replace(TERM132, TERM144)
CONTROL_STATE = ELEVA_STATE.replace(STATE132, STATE144)
TWELFTH_EVENTS = CONTROL_EVENTS.replace(
    TERM144,
    (f"VH_PAD frame={CONFIRM12_PRESS} button=C action=PRESS\n"
     f"VH_PAD frame={CONFIRM12_RELEASE} button=C action=RELEASE\n").encode("ascii") + TERM144,
)
TWELFTH_STATE = CONTROL_STATE.replace(
    STATE144,
    (f"VH_PADSTATE frame={CONFIRM12_PRESS} button=C active_low_bit=0\n"
     f"VH_PADSTATE frame={CONFIRM12_RELEASE} button=C active_low_bit=1\n").encode("ascii") + STATE144,
)


def _pair_shape(a: Path, b: Path) -> None:
    a, b = a.resolve(), b.resolve()
    if a.parent != b.parent or len(str(a)) != len(str(b)):
        raise ValueError("Stage145 paired paths must be equal-shape siblings")


def _check_frames(directory: Path) -> tuple[int, tuple[int, int]]:
    expected_frames = {f"frame-{n}.png" for n in CHECKPOINTS}
    expected = expected_frames | {"pre.png", "post.png", "frames.stats", "fad.vhcdlog",
        "pad-events.txt", "pad-state.txt", "sh2-window.txt", "video-state.txt"}
    if {p.name for p in directory.iterdir()} != expected:
        raise ValueError("Stage145 output file set mismatch")
    dims = None
    for n in CHECKPOINTS:
        size, _ = _frame(directory, n)
        if not (64 <= size[0] <= 704 and 64 <= size[1] <= 512):
            raise ValueError("Stage145 PNG geometry invalid")
        if dims is None:
            dims = size
        elif dims != size:
            raise ValueError("Stage145 PNG geometry changed")
    pre = _private_regular(directory / "pre.png", MAX_PNG_BYTES)
    post = _private_regular(directory / "post.png", MAX_PNG_BYTES)
    from tools.saturn_private_frame_witness import validate_png_file
    pre_dims = validate_png_file(pre)
    post_dims = validate_png_file(post)
    if dims is None or not (64 <= pre_dims[0] <= 704 and 64 <= pre_dims[1] <= 512) or post_dims != dims:
        raise ValueError("Stage145 pre/post geometry invalid")
    stats = FRAME_STATS.fullmatch(_private_regular(directory / "frames.stats", 256))
    if not stats:
        raise ValueError("Stage145 frame stats malformed")
    completed, pc0, pc1, width, height = map(int, stats.groups())
    if completed != FRAME_COUNT or pc0 > 0xffffffff or pc1 > 0xffffffff or (width, height) != dims:
        raise ValueError("Stage145 frame stats mismatch")
    samples = [0] + list(CHECKPOINTS) + [FRAME_COUNT]
    for name, pattern in (("sh2-window.txt", SH2_LINE), ("video-state.txt", VIDEO_LINE)):
        raw = _private_regular(directory / name, 1024 * 1024)
        if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
            raise ValueError("Stage145 noncanonical diagnostics")
        lines = raw.splitlines()
        if len(lines) != len(samples):
            raise ValueError("Stage145 diagnostic sample count mismatch")
        seen = []
        for line in lines:
            match = pattern.fullmatch(line)
            if not match:
                raise ValueError("Stage145 diagnostic record malformed")
            seen.append(int(match.group(1)))
        if seen != samples:
            raise ValueError("Stage145 diagnostic sequence mismatch")
    _count_canonical_fads(directory)
    return len(CHECKPOINTS), dims


def audit_private_prologue_continue_twelfth_c(control: Path, enabled: Path) -> dict:
    if not control.is_absolute() or not enabled.is_absolute() or control.resolve() == enabled.resolve():
        raise ValueError("two distinct absolute Stage145 output paths required")
    _pair_shape(control, enabled)
    _private_directory(control)
    _private_directory(enabled)
    if _private_regular(control / "pad-events.txt", 4096) != CONTROL_EVENTS:
        raise ValueError("Stage145 shared-eleventh-C control receipt mismatch")
    if _private_regular(control / "pad-state.txt", 4096) != CONTROL_STATE:
        raise ValueError("Stage145 shared-eleventh-C control state receipt mismatch")
    if _private_regular(enabled / "pad-events.txt", 4096) != TWELFTH_EVENTS:
        raise ValueError("Stage145 twelfth-C event receipt mismatch")
    if _private_regular(enabled / "pad-state.txt", 4096) != TWELFTH_STATE:
        raise ValueError("Stage145 twelfth-C active-low state receipt mismatch")
    control_pre = _private_regular(control / "pre.png", MAX_PNG_BYTES)
    enabled_pre = _private_regular(enabled / "pre.png", MAX_PNG_BYTES)
    if control_pre != enabled_pre:
        raise ValueError("Stage145 cold boots differ before START")
    control_count, control_dims = _check_frames(control)
    enabled_count, enabled_dims = _check_frames(enabled)
    if control_count != 1200 or enabled_count != 1200 or control_dims != enabled_dims:
        raise ValueError("Stage145 checkpoint count/dimensions mismatch")
    equal = sum(_equal_frame(control, enabled, frame) for frame in PRE_TWELFTH_CHECKPOINTS)
    if equal != len(PRE_TWELFTH_CHECKPOINTS):
        raise ValueError("Stage145 cohorts diverged before twelfth C")
    changes = [frame for frame in POST_TWELFTH_CHECKPOINTS if not _equal_frame(control, enabled, frame)]
    early = [frame for frame in POST_TWELFTH_BY_133200 if not _equal_frame(control, enabled, frame)]
    if not early:
        raise ValueError("Stage145 twelfth C had no framebuffer effect by frame 133200")
    control_cd_count, control_cd_hash = _count_canonical_fads(control)
    enabled_cd_count, enabled_cd_hash = _count_canonical_fads(enabled)
    return {
        "schema_version": 1,
        "kind": "STAGE145_PRIVATE_PROLOGUE_CONTINUE_TWELFTH_C_INTEGRITY_ONLY",
        "frames_per_process": FRAME_COUNT,
        "paired_cold_boot_processes": 2,
        "checkpoint_png_count_per_process": 1200,
        "all_checkpoint_pngs_and_diagnostic_sequences_verified": True,
        "same_dimensions_across_runs": True,
        "shared_tenth_C_press_frame": 108000,
        "shared_tenth_C_release_frame": 108006,
        "shared_eleventh_C_press_frame": CONFIRM11_PRESS,
        "shared_eleventh_C_release_frame": CONFIRM11_RELEASE,
        "twelfth_C_press_frame": CONFIRM12_PRESS,
        "twelfth_C_release_frame": CONFIRM12_RELEASE,
        "pre_twelfth_checkpoint_equal_count": equal,
        "pre_twelfth_checkpoint_total": len(PRE_TWELFTH_CHECKPOINTS),
        "first_post_twelfth_framebuffer_divergence_by_133200": min(early),
        "first_post_twelfth_framebuffer_divergence_through_144000": min(changes),
        "frame_144000_differs": not _equal_frame(control, enabled, FRAME_COUNT),
        "control_cd_event_count": control_cd_count,
        "intervention_cd_event_count": enabled_cd_count,
        "cd_logs_differ": control_cd_hash != enabled_cd_hash,
        "first_battle_or_player_control_verified": False,
        "requires_private_visual_review_of_dialogue_and_battle_state": True,
        "original_media_or_frame_hashes_exported": False,
    }
