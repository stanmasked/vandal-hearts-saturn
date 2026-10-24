#!/usr/bin/env python3
"""Stage142 ROM-free strict PAD-receipt audit for a partial Saturn experiment.

Checks recorded host-side events only, not whether the guest consumed input.
Does not copy private payloads, paths, register values, or media hashes to stdout.
The Stage141 SIGTERM case is expected to fail closed on zero-length buffers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

MAX_RECEIPT = 4096
# Exact canonical Stage125 first nine shared input presses; the tenth differs.
CANONICAL = ((12060, 'START'), (12240, 'C'), (31200, 'C'),
             (36000, 'C'), (42000, 'C'), (48000, 'C'),
             (60000, 'C'), (72000, 'C'), (84000, 'C'), (96000, 'C'))
TENTH_FRAME = 108000
LINE = re.compile(rb'VH_PAD frame=(\d+) button=(START|C) action=(PRESS|RELEASE)')
STATE = re.compile(rb'VH_PADSTATE frame=(\d+) (?:start_bit=(0|1)|button=C active_low_bit=(0|1))')


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_RECEIPT:
        raise ValueError('missing or unsafe PAD receipt')
    data = path.read_bytes()
    if not data or len(data) > MAX_RECEIPT or not data.endswith(b'\n') or b'\r' in data or b'\0' in data:
        raise ValueError('incomplete PAD receipt')
    return data


def _expected(through_frame: int) -> tuple[bytes, bytes]:
    if (type(through_frame) is not int or through_frame % 120 or
            not 12360 <= through_frame < TENTH_FRAME):
        raise ValueError('invalid pre-tenth capture window')
    events = []
    states = [b'VH_PADSTATE initial_start_bit=1',
              b'VH_PADSTATE initial_confirm_button=C active_low_bit=1']
    for press, button in CANONICAL:
        if press + 6 > through_frame:
            break
        for frame, action in ((press, 'PRESS'), (press+6, 'RELEASE')):
            events.append(f'VH_PAD frame={frame} button={button} action={action}'.encode('ascii'))
            if button == 'START':
                states.append(f'VH_PADSTATE frame={frame} start_bit={0 if action=="PRESS" else 1}'.encode('ascii'))
            else:
                states.append(f'VH_PADSTATE frame={frame} button=C active_low_bit={0 if action=="PRESS" else 1}'.encode('ascii'))
    return b'\n'.join(events)+b'\n', b'\n'.join(states)+b'\n'


def _within_window(receipt: bytes, through_frame: int, *, state: bool) -> bytes:
    expected_prefix = [b'VH_PADSTATE initial_start_bit=1',
                       b'VH_PADSTATE initial_confirm_button=C active_low_bit=1'] if state else []
    lines = receipt.splitlines()
    if state and lines[:len(expected_prefix)] != expected_prefix:
        raise ValueError('PAD initial-bit witness mismatch')
    included = list(expected_prefix)
    for line in lines[len(expected_prefix):]:
        if line in (b'VH_PAD mode=1 completed_frames=120000',
                    b'VH_PADSTATE mode=1 completed_frames=120000'):
            continue
        match = (STATE if state else LINE).fullmatch(line)
        if match is None:
            raise ValueError('noncanonical PAD receipt line')
        frame = int(match.group(1))
        if frame <= through_frame:
            included.append(line)
    return b'\n'.join(included)+b'\n'


def verify_receipt_pair(control: Path, enabled: Path, *, through_frame: int=24000) -> dict:
    exp_events, exp_state = _expected(through_frame)
    if (control.is_symlink() or enabled.is_symlink() or not control.is_dir()
            or not enabled.is_dir() or control.resolve() == enabled.resolve()):
        raise ValueError('independent capture folders required')
    for folder in (control, enabled):
        events = _read(folder / 'pad-events.txt')
        states = _read(folder / 'pad-state.txt')
        if (_within_window(events, through_frame, state=False) != exp_events or
                _within_window(states, through_frame, state=True) != exp_state):
            raise ValueError('canonical pre-tenth PAD receipt mismatch')
    return {'stage':142,'checked_through_frame':through_frame,
            'canonical_host_pad_receipts_verified':True,
            'original_guest_input_consumption_verified':False,
            'tenth_c_effect_verified':False,
            'full_120000_frame_run_verified':False}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--control',type=Path,required=True)
    ap.add_argument('--enabled',type=Path,required=True)
    ap.add_argument('--through-frame',type=int,default=24000)
    a=ap.parse_args()
    try:
        result = verify_receipt_pair(a.control,a.enabled,through_frame=a.through_frame)
    except (ValueError,OSError,UnicodeError):
        print('STAGE142_PARTIAL_PAD_RECEIPT_REJECTED',file=sys.stderr)
        return 1
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
