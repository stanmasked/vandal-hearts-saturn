# Stage 41 — Live NeXium two-cell aim overshoot and bounded pixel correction

## New genuine observation

On Stage40 corrective head `fce7488c`, Host GCC and Clang both passed, the
Nintendo Switch NRO compiled/validated, and NeXium launched and shut down
cleanly. The 64-bit *initial* guest battle checksum and Right-key screenshot
checks passed. But the independent real-move gate failed with
`aim cursor did not reach exactly one tile right`, correctly withholding
any claim that Scout moved. Source: CI run 39470822567, archived action
evidence artifact 12286748359.

The downloaded *real* NeXium PNG frames show these yellow cursor centers:

| PNG | Cursor center | Meaning |
| --- | --- | --- |
| nexium-window.png | (490.5, 251.0) | Scout start |
| nexium-after-right.png | (562.5, 285.5) | earlier Right moved two tiles |
| action-return-1.png | (490.5, 251.0) | bounded Left returned to Scout |
| action-selected.png | (490.5, 251.0) | Scout selected |
| action-aimed.png | (562.5, 285.5) | new Right again overshot target |

So the first Stage40 return correction worked in the real guest; the remaining
failure was aiming. Passing C++ expected fingerprints did not prove an actual
guest move. The real post-move fingerprint `ef9c7d67953c9b2a` was **not**
observed and must not be reported as validated in NeXium yet.

## Stage41 changes

- The live X11 action sender uses `xdotool key --delay 0` for directional
  pulses only. This attempts to prevent a 12 ms held key from being sampled
  across multiple guest frames. Confirm keeps its previous timing. Whether
  short pulses solve the real guest issue is *unverified* until another run.
- Target acquisition is now a **bounded eight-observation closed loop**:
  after every actual PNG, compare the measured yellow component center with
  the required one-tile target; choose Left/Right accordingly, and refuse
  Confirm until the target is seen. Out-of-row trajectories, no progress
  and repeated two-tile oscillation remain fail-closed.
- Every intermediate aiming screenshot is persisted for independent audit.
  Host synthetic regression tests include successful overshoot recovery,
  pathological oscillation, and wrong-row rejection.
- After Confirm, only the full 64-bit post-move screenshot state hash
  `ef9c7d67953c9b2a` authorizes a pass.

## Scope

The screenshot data comes from a ROM-free original training scene running
as a homebrew NRO in NeXium, **not** from an emulation of the Sega Saturn
Vandal Hearts disc. This work does not establish physical Switch-controller
support or original game fidelity; no Saturn assets, sounds, maps, BIN or
CUE were uploaded.
