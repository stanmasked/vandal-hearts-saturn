#!/usr/bin/env python3
"""Strict, per-launch ROM-free NeXium reproducibility report.

Each trial must have distinct captured files from an independent GUI session.
A passed guest framebuffer does not mask a host panic or missing input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image
from tools.nexium_frame_verify import verify_frame
from tools.nexium_guest_evidence import inspect_files
from tools.nexium_log_health import inspect_log
from tools.nexium_lifecycle_audit import assess, read_log

COUNT = 3


def parse_attempt_receipt(value: str) -> tuple[int, int, bool]:
    """Require exactly one winning screenshot attempt, never 'sent key' alone."""
    lines = value.splitlines()
    labels = [v.partition("=") for v in lines if "=" in v]
    names = [(k, v) for k, sep, v in labels if sep]
    selected = [v for k, v in names if k == "selected_attempt"]
    if len(selected) != 1 or not selected[0].isdecimal():
        raise ValueError("missing or unverified selected input attempt")
    index = int(selected[0])
    if (("probe", "bounded_right_v2") in names):
        limits = [v for k, v in names if k == "max_attempts"]
        if len(limits) != 1 or not limits[0].isdecimal():
            raise ValueError("invalid max-attempt receipt")
        limit = int(limits[0])
        if not 1 <= limit <= 8 or not 1 <= index <= limit:
            raise ValueError("selected attempt outside bounded range")
        wins = [k for k, v in names if v == "visible_movement" and
                k.startswith("attempt") and k[7:].isdecimal()]
        if wins != [f"attempt{index}"]:
            raise ValueError("selected attempt has no unique verified motion receipt")
        return index, limit, True
    if (("probe", "bounded_right_v1") in names):
        if index not in (1, 2):
            raise ValueError("legacy input attempt must be 1 or 2")
        return index, 2, False
    raise ValueError("unknown input probe receipt version")


def audit_trial(folder: Path) -> dict:
    result = {
        "trial": folder.name, "launcher_exit_code": None,
        "frame_passed": False, "guest_state_and_input_passed": False,
        "host_log_passed": False, "lifecycle_passed": False,
        "window_manager_reaped": False, "selected_input_attempt": None,
        "cursor_dx_pixels": None, "cursor_dy_pixels": None,
        "passed": False,
    }
    try:
        code = (folder / "launcher-exit.txt").read_text().strip()
        if not code.isascii() or not code.isdecimal():
            raise ValueError("Launcher exit receipt must be a nonnegative decimal integer")
        result["launcher_exit_code"] = int(code)
        with Image.open(folder / "nexium-window.png") as frame:
            result["frame_passed"] = bool(verify_frame(frame)["plausible_training_frame"])
        guest = inspect_files(
            folder / "nexium-window.png", folder / "nexium-after-right.png",
            folder / "input-probe-status.txt")
        result["guest_state_and_input_passed"] = bool(guest["guest_visual_evidence_passed"])
        result["cursor_dx_pixels"] = guest["cursor_dx_pixels"]
        result["cursor_dy_pixels"] = guest["cursor_dy_pixels"]
        result["host_log_passed"] = bool(inspect_log(folder / "nexium.log")["no_known_fatal_host_errors"])
        lifecycle = assess(
            read_log(folder / "nexium-log-before-close.log"),
            read_log(folder / "nexium.log"),
            (folder / "lifecycle-status.txt").read_text(encoding="utf-8"))
        result["lifecycle_passed"] = bool(lifecycle["clean_lifecycle"])
        result["window_manager_reaped"] = (
            (folder / "window-manager-shutdown.txt").read_text(encoding="utf-8").strip()
            == "window_manager_reaped")
        attempts = (folder / "input-probe-attempts.txt").read_text(encoding="utf-8")
        selected, limit, updated = parse_attempt_receipt(attempts)
        result["selected_input_attempt"] = selected
        result["max_input_attempts"] = limit
        if updated:
            import json
            # A selected-attempt receipt is not proof on its own: the same
            # genuinely observed PNG must be the image used by guest audit.
            winning = folder / f"nexium-after-right-attempt-{selected}.png"
            promoted = folder / "nexium-after-right.png"
            if winning.read_bytes() != promoted.read_bytes():
                raise ValueError("promoted cursor frame differs from winning screenshot")
            status = json.loads(
                (folder / f"input-motion-attempt-{selected}.json").read_text("utf-8"))
            if status.get("plausible_right_cursor_movement") is not True:
                raise ValueError("selected attempt did not prove visible cursor motion")
        result["passed"] = bool(
            result["launcher_exit_code"] == 0
            and result["frame_passed"]
            and result["guest_state_and_input_passed"]
            and result["host_log_passed"]
            and result["lifecycle_passed"]
            and result["window_manager_reaped"])
    except (OSError, ValueError, KeyError) as error:
        result["error_type"] = type(error).__name__
        result["passed"] = False
    return result


def summarize(folder: Path, audit_fn=audit_trial) -> dict:
    trials = [audit_fn(folder / f"trial-{i:02d}") for i in range(1, COUNT + 1)]
    successes = sum(bool(t["passed"]) for t in trials)
    first_attempts = sum(t.get("selected_input_attempt") == 1 and t["passed"] for t in trials)
    retries = sum(t.get("selected_input_attempt") == 2 and t["passed"] for t in trials)
    return {
        "version": 1,
        "sample_size": COUNT,
        "passed_trials": successes,
        "failed_trials": COUNT-successes,
        "first_attempt_successes": first_attempts,
        "verified_retry_recoveries": retries,
        "all_independent_trials_passed": successes == COUNT,
        "trials": trials,
        "limitations": ("Three independent headless emulator launches are a small reliability "
                        "sample, not a statistical guarantee. X11 keyboard is not Joy-Con input; "
                        "the original Saturn first battle is not implemented."),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.evidence_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["all_independent_trials_passed"]:
        raise SystemExit("At least one independent NeXium trial failed")


if __name__ == "__main__":
    main()
