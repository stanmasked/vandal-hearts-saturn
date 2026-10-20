#!/usr/bin/env python3
"""Separate ROM-free NeXium guest-rendering/input evidence from host shutdown.

A passed guest frame/input receipt is not evidence that the NeXium host process
exited cleanly. The latter has a separate, deliberately failing CI gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
from tools.nexium_cursor_motion import evaluate_motion
from tools.nexium_visual_digest import INITIAL_TRAINING_FINGERPRINT, decode


EXPECTED_INPUT_RECEIPT = 'input_attempted=Right screenshot=ready'


def examine_pair(before: Image.Image, after: Image.Image, receipt: str) -> dict:
    initial = decode(before, INITIAL_TRAINING_FINGERPRINT)
    following = decode(after, INITIAL_TRAINING_FINGERPRINT)
    motion = evaluate_motion(before, after)
    sent_and_captured = receipt.strip() == EXPECTED_INPUT_RECEIPT
    both_decoded = bool(initial['matches_expected_training_state'] and
                        following['matches_expected_training_state'])
    cursor_moved = bool(motion['plausible_right_cursor_movement'])
    return {
        'version': 1,
        'scene': 'ROM-free-training',
        'input_receipt_confirmed': sent_and_captured,
        'before_fingerprint': initial['decoded_fingerprint'],
        'after_fingerprint': following['decoded_fingerprint'],
        'before_checksum_matches_host': initial['matches_expected_training_state'],
        'after_checksum_matches_host': following['matches_expected_training_state'],
        'battle_unchanged_on_cursor_navigation': both_decoded,
        'observed_cursor_motion': cursor_moved,
        'cursor_dx_pixels': motion['delta_x_pixels'],
        'cursor_dy_pixels': motion['delta_y_pixels'],
        'guest_visual_evidence_passed': bool(sent_and_captured and both_decoded and cursor_moved),
        'host_exit_status_verified': False,
        'note': ('Screenshot and X11 Right-command evidence for synthetic Switch guest only. '
                 'It cannot prove physical Switch controls, original Saturn fidelity, '
                 'or clean NeXium host shutdown.'),
    }


def inspect_files(before: Path, after: Path, receipt: Path) -> dict:
    status = receipt.read_text(encoding='utf-8') if receipt.is_file() else ''
    with Image.open(before) as first, Image.open(after) as second:
        return examine_pair(first, second, status)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        report = inspect_files(args.before, args.after, args.receipt)
    except (FileNotFoundError, OSError, ValueError) as error:
        report = {
            'version': 1,
            'scene': 'ROM-free-training',
            'guest_visual_evidence_passed': False,
            'error_kind': type(error).__name__,
            'note': 'Guest images/receipts unavailable or invalid; host shutdown is evaluated separately.',
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not report['guest_visual_evidence_passed']:
        raise SystemExit('Guest visual/input evidence not verified; inspect report')


if __name__ == '__main__':
    main()
