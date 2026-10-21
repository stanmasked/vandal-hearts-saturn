# Stage95 — four private menu/battle capture receipts as a single cohort

## Why

Stage94 atomically checks locally pinned original Track1/Track2/CUE and
emulator executable around **one** manually gated FAD capture, revoking an
early receipt if source postflight fails. That still does not establish
a repeated independent observation of both a menu control and a first-battle
entry. Stage73–76 expect multiple separately named sessions, and interpreting
one log as all phases would be unsafe.

## Four-session local-only procedure

The source must first meet Stages92–94, including complete Stage02
Track1/Track2/CUE SHA-256, exact CUE and ISO9660 inventory. Repeat the
Stage94 local operation **four separate times** in freshly created 0700
private directories: two declared `menu_control`, followed by two
declared `first_battle_entry`, preferably from independently observed
cold boots. Never reuse workspaces, logs, or source output paths.

After the four Stage94 operations have each completed successfully, run:

```bash
mkdir -m 700 /private/saturn/cohort-review
python3 -m tools.saturn_private_capture_cohort \
  --menu-dir /private/saturn/menu-one \
  --menu-dir /private/saturn/menu-two \
  --battle-dir /private/saturn/battle-one \
  --battle-dir /private/saturn/battle-two \
  --summary /private/saturn/cohort-review/summary.json \
  --private-trace /private/saturn/cohort-review/trace-lba.json
```

All sample paths are placeholders. The program **does not** launch emulators
or claim to observe a screen. It inspects only the four locally created
Stage94/Stage86 receipts and numeric-only `fad.vhcdlog` files.

## Exactly what the tool establishes

- Exactly four distinct 0700 workspaces and distinct per-file inodes,
  with only the three expected Stage94/86 artifacts each.
- Each complete handoff reports full Stage02 source integrity, checked
  executable SHA-256 and exact CUE argv; each lower receipt reports
  source immutability, closed gate and numeric-only FAD events.
- Each FAD file and receipt is a bounded nonsymlinked, non-hardlinked,
  non-world-readable regular file. Stage95 also tightens Stage86 subprocess
  creation to `umask 077` so original numeric logs use mode 0600.
- The two receipts' event counts equal the exact numeric FAD log's length.
  The four self-reported 128-bit hex session IDs are distinct, with two
  operator-declared menu and two operator-declared battle-entry phases.
- Only FAD addresses inside the *known data Track1* (FAD=ISO LBA+150)
  may be normalized for comparison. CDDA FAD must not be mistaken for a
  logical data-sector LBA. Any invalid address makes the entire cohort fail.
- The sanitized summary records counts and whether the two logs in each
  phase are identical. **Identical FAD reads are legal for deterministic
  game loads**: such equality is informative, not a rejection or proof
  of duplicate recording.
- The normalized LBA trace is stored only in a 0600 private file.
  No paths, original media hashes, sector bytes, original catalog number,
  CUE text, asset data or source screenshots are included in the summary.
  Both outputs must be in a fresh protected output directory.

## What it absolutely does NOT prove

Four different workspace inode numbers and random session IDs are not proof
of four genuinely independent emulator boots. The phase labels are supplied
by the operator; **no synchronized screen frame is captured** by Stage95.
A successful cohort is **not** proof that Vandal Hearts Saturn booted,
that the scene was the first battle, or that a candidate resource extent
was loaded by the game. The trace is prepared for later private Stage73–75
crosswalk and human observation, with explicit unverified source/loader
flags.

Public CI tests this with four actual **fake Python child processes**
driven by Stage94, an invented 22-sector Saturn-shaped Track1, artificial
CUE/audio, and two repeated but different invented FAD sequences. It checks
the positive flow and failures for altered receipts, files/permissions,
duplicate session IDs, phase mismatch, illegal audio FAD, swapped/invalid
logs and false screen claims. **It contains no copyrighted game data.**

The original 621,755,904-byte English v1.1 Track1 still requires a separate
local full SHA-256 verification: the connected ChatGPT Drive raw download
limit prevents the complete transfer in this session. Stage92 describes a
separately authorized local Range approach. Continue holding Issue #11
as BLOCKED until original-game boots and independently synchronized first-
battle frame/CD read evidence exist.
