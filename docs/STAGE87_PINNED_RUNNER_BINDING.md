# Stage87 — private executable fingerprint and exact CUE-argument binding

Stage86 verifies that the user's previously supplied English v1.1 T-9526G
Track 1, Track 2 and CUE files match their Stage02 digests before and after
a private local capture. That safeguard alone did **not** identify which
local executable was run or even whether its argv mentioned the pinned CUE.

Stage87 adds a **locally supplied executable SHA-256 pin**, checks it
before and after the capture, and requires the exact manifest CUE absolute
path to appear as one complete command-line argument. It does not upload
any binary or media and does not claim the emulator actually read that CUE.

## How to use privately

1. Build or install a local instrumented Yabause executable from the
   previously pinned public source. Separately validate its provenance
   against trusted build instructions. A SHA-256 given by an arbitrary
   program is **not** a third-party software attestation.
2. Compute its SHA-256 locally, in a separate step. Keep that digest
   private alongside the Stage86 source manifest.
3. Continue to use the Stage86 private, empty, chmod-0700 workspace,
   Stage02 source hashes and Stage77 manual gate. Add the Stage87 option:

```bash
python3 -m tools.saturn_private_capture_session \
  --manifest /private/saturn/source.json \
  --private-dir /private/saturn/capture-menu-02 \
  --phase menu_control \
  --expected-runner-sha256 <your-locally-pinned-64-character-lowercase-sha256> \
  -- /absolute/path/to/instrumented-yabause [its-options] /private/saturn/Disc.cue
```

The CUE argument must be exactly the absolute string in the private
Stage86 manifest, not merely a similar filename or a substring. The
wrapper verifies executable regular-file identity and SHA-256 before
launch, and checks the same inode/metadata/hash after launch; a changed
binary aborts the receipt. Symlinked and hardlinked executables are
rejected for this mode.

A successful private receipt contains only booleans that distinguish
*locally supplied* executable fingerprint agreement and exact CUE argv
binding from independent source/build authentication. In particular,
`emulator_binary_origin_independently_verified=false`,
`game_disc_actually_opened_verified=false`,
`scene_frame_synchronized_verified=false`, and
`first_battle_loader_verified=false` remain explicitly false.

Without the new optional `--expected-runner-sha256` argument, the
previous Stage86 behavior is retained and both new binding flags are false.
For the Stage87 evidence standard, operators must use the option.

## Tested claims and limits

Public CI uses an entirely invented three-file source and a small
locally generated Python executable script instead of the genuine game
or emulator. Tests cover success, a wrong/invalid digest, absent/nearby
CUE token, symlink/hardlink runner, mutation before and during launch,
nonabsolute executable paths, source mutation and the unchanged Stage86
privacy guards. Both Python 3.11 and 3.13 run this suite.

Passing proves that the local wrapper enforces the declared
process/file relationship. It is **not** an independent signed-build
attestation, proof that the referenced CUE was actually opened, a
successful original Saturn boot, a synchronized first-battle window or
a known map/resource loader. Those require direct private gameplay
observation and source-linked runtime captures under Issue #11.

No game media, private data, full sector bytes, source hashes or executable
paths are copied or uploaded to GitHub. The original game image remains
outside the active task workspace.
