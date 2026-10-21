#!/usr/bin/env python3
"""Determine whether fatal host errors were logged before or after GUI close.

A pre-close log copy is only a snapshot; it cannot prove the exact instant a
panic happened relative to the GPU frame. This audit never hides fatal errors.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

PATTERNS = {
    'rust_panic': r'\bpanicked at\b',
    'x11_connection_failure': r'Connection\(IoError',
    'segmentation_fault': r'\bsegmentation fault\b|\bSIGSEGV\b',
    'vulkan_device_lost': r'\bVK_ERROR_DEVICE_LOST\b|\bdevice lost\b',
    'fatal_error_marker': r'\bFATAL\b',
}
MAX_BYTES = 2 * 1024 * 1024


def categories(log: str) -> list[str]:
    return [key for key, expression in PATTERNS.items()
            if re.search(expression, log, re.IGNORECASE)]


def assess(before: str, complete: str, lifecycle: str) -> dict:
    prefix = complete.startswith(before)
    close_requested = 'shutdown_requested' in lifecycle
    normal_close = ('windowclose_sent' in lifecycle and
                    'forced_sigterm' not in lifecycle and
                    'forced_sigkill' not in lifecycle)
    normal_exit = 'emulator_exit_code=0' in lifecycle
    audit = {
        'capture_snapshot_present': bool(before),
        'snapshot_is_prefix_of_complete_log': prefix,
        'shutdown_request_recorded': close_requested,
        'normal_window_close_requested': normal_close,
        'emulator_exit_zero': normal_exit,
        'fatal_before_close': categories(before),
        'fatal_after_close_request': categories(complete[len(before):]) if prefix else [],
        'fatal_anywhere': categories(complete),
    }
    audit['clean_lifecycle'] = bool(before and prefix and close_requested and
                                    normal_close and normal_exit and
                                    not audit['fatal_anywhere'])
    audit['note'] = ('A clean shutdown alone does not prove stable gameplay; '
                     'the emulator frame and actual guest input require separate checks.')
    return audit


def read_log(path: Path) -> str:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Host log exceeds safe size')
    return path.read_text(encoding='utf-8', errors='replace')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before_log', type=Path)
    parser.add_argument('complete_log', type=Path)
    parser.add_argument('lifecycle', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = assess(read_log(args.before_log), read_log(args.complete_log),
                    read_log(args.lifecycle))
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')
    if not result['clean_lifecycle']:
        raise SystemExit('NeXium lifecycle is not clean; inspect pre/post-close evidence')


if __name__ == '__main__':
    main()
