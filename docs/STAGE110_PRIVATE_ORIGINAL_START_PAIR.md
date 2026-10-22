# Stage110 — two real original Saturn runs, source pinned before and after

## Status of the prerequisites

Stage106 reached the authentic English-v1.1 "Press START Button" title
privately at frame 12,000. The officially built historical pinned Yabause
C68K runner Stage107 can inject native Saturn START at frame 12060 and
release at 12066; Stage109 adds active-low host pad state readback.

Official public GCC + Clang jobs succeeded on Stage107 at revision
4dcb3fd0 (Actions 39817850431) and Stage109 at 7d19fd68 (Actions
39817569323). These public builds ran **invented disc data only**. Neither
START acceptance nor real title-to-menu navigation was proven by CI.

## Private execution contract

Use the independently downloaded Stage109 GCC or Clang *public GPL
Yabause executable* (not an original game bundle), and externally
calculate its **file** SHA-256. Do not use the ZIP artifact hash in
place of the extracted executable hash.

Place the three full, original English-v1.1 Saturn source files in one
protected directory with their **exact original** names. The exact
Stage02 pins used by the runner are:

- Track1 full 621,755,904 bytes, Stage02 SHA-256 in
  tools/saturn_private_capture_session.py
- Track2 full 2,102,688 bytes, Stage02 SHA-256 there
- CUE exact Stage02 SHA-256 there, with relative FILE names

The Track1 Drive archive was previously delivered in two private ZIP
parts. This script **does not** download, join or decompress any source
media and never touches public CI original bytes. Both the source
media and executable must be already available in a private workspace
outside any Git checkout.

Manually create TWO fresh empty, distinct **0700** directories for
control and pressed evidence. Then use this example, replacing only
paths/hash with your actual private values:

    umask 077
    python3 -m tools.saturn_private_original_start_pair \
      --cue /private/disc/original.cue \
      --track1 /private/disc/original-track1.bin \
      --track2 /private/disc/original-track2.bin \
      --executable /private/runner/yabause \
      --expected-runner-sha256 <64-lowercase-hex-executable-sha256> \
      --control /private/runs/control \
      --start /private/runs/start \
      --timeout 1800

This tool verifies Stage02 **full-file** digests and stable file identities
for Track1/Track2/CUE before and **after each separate process**.
The externally specified Yabause executable digest and file identity
are also compared before/after. The runner cannot be taken from inside
a Git repository, and the private source/output locations must not live
inside a Git checkout.

First process: 13200 frames, same real standard Saturn pad but no
button events. Second process: 13200 frames, same executable and disc,
one six-frame START pulse at 12060/12066. Inputs are sandboxed by
the protected subprocess working directories, private umask and
restricted environment variables. Any nonzero process status, closed
gate failure, failed media/binary hash or missing private receipts is
fatal.

The final integrated audit checks both Stage109 native pad bit
receipts and Stage107 numeric CD/PNG evidence, then verifies that
private PNGs for frames **11880 and 12000** have identical source bytes
between control and START (the Stage108 reproducibility gate). The
same dimensions must hold at all compared frames. It then reports
only **boolean differences** at frames **12120 and 13200**.

No private paths, disc data, PNG pixels, hashes, Yabause stderr or
numeric FAD addresses leave private storage. The printed JSON is
metadata only. Direct visual inspection of the two PRIVATE image
sets is still required. Do NOT publish any original game
screenshots, sectors or logs to GitHub.

## Evidence limits

A passing receipt establishes a correct, protected, file-integrity
bounded pair as far as its recorded artifacts can demonstrate. It
does **not** independently prove original guest Saturn SMPC
consumption, menu selection, correct emulator pacing or first
battle. CD callback logs are not temporally aligned to particular
video frames by this stage.

Keep authenticity issue #11 OPEN until original game's actual
title-to-menu transition and separate original first tactical
battlefield/loader behavior are visually and technically verified.
This stage's GitHub Actions uses only invented 64x64 PNG frames,
invented FAD lines and a small fake local subprocess executable.
