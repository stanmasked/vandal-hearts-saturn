#!/usr/bin/env python3
"""Flag fatal emulator-host errors without confusing ALSA warnings with guest crashes.

This checks the NeXium host log only. It never authenticates guest input,
original Saturn gameplay, or successful emulation by itself.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

MAX_LOG_BYTES = 2 * 1024 * 1024
PATTERNS = {
    'rust_panic': r'\bpanicked at\b',
    'x11_connection_failure': r'Connection\(IoError',
    'segmentation_fault': r'\bsegmentation fault\b|\bSIGSEGV\b',
    'vulkan_device_lost': r'\bVK_ERROR_DEVICE_LOST\b|\bdevice lost\b',
    'fatal_error_marker': r'\bFATAL\b',
}


def assess_log(log: str) -> dict:
    if not isinstance(log, str):
        raise TypeError('Expected decoded log text')
    flags = [category for category, expression in PATTERNS.items()
             if re.search(expression, log, re.IGNORECASE)]
    return {
        'log_nonempty': bool(log.strip()),
        'fatal_categories': flags,
        'known_fatal_error_count': len(flags),
        'no_known_fatal_host_errors': bool(log.strip()) and not flags,
        'audio_device_warning_present': 'ALSA lib' in log,
        'limitations': ('Absence of recognized host errors is not proof of guest boot or stability. '
                        'The framebuffer and input checks must be assessed independently.'),
    }


def inspect_log(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > MAX_LOG_BYTES:
        raise ValueError('Emulator log unexpectedly large')
    return assess_log(path.read_text(encoding='utf-8', errors='replace'))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = inspect_log(args.log)
    report = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding='utf-8')
    print(report, end='')
    if not result['no_known_fatal_host_errors']:
        raise SystemExit('NeXium host log contains a fatal or missing-runtime marker')


if __name__ == '__main__':
    main()
