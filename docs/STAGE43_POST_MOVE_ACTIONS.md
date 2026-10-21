# Stage 43 — Reject a second Scout move and cancel selection in real NeXium

## Starting point

Stage42 established a genuine ROM-free Nintendo Switch guest screenshot of
Scout moved from (1,5) to (2,5), with the battle fingerprint changing from
`ae38b0b5ab887f00` to `ef9c7d67953c9b2a`.
Its evidence is from [run 39475370553](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39475370553).
This does not demonstrate the original Sega Saturn game's combat behavior.

## Why a preserved battle hash is not enough

An unchanged battle hash following an X11 `Return` or `BackSpace` could
merely mean that NeXium dropped the key. Stage43 therefore renders an
extra 16×16 colored **last-action** square at logical pixel (1210,60) of
the deliberately ROM-free synthetic SDL window:

- green `(66,220,132)`: the last processed action was **Moved**
- red `(239,79,76)`: the last processed action was **Rejected**
- amber `(251,220,90)`: the last processed action was **Cancelled**
- blue `(63,167,239)`: a unit was **Selected**

This receipt is *outside* the 64-bit game-state digest cells and anchors.
The guest draws it from the same shared `TrainingEffect` used by both
keyboard and controller code paths. A separate decoder uses the existing
three-magenta-anchor image registration to locate the square in a real
NeXium PNG. It does not use a sender-side acknowledgement.

## Stage43 live test

This opt-in test starts **only if Stage42 actually moved Scout**.

1. Validate the 64-bit moved screenshot hash, moved green receipt, and
   persistent yellow selection outline around Scout at (2,5).
2. Return the yellow terrain cursor to empty (1,5) with up to eight
   screenshot-observed Left/Right pulses, preserving the moved hash.
3. Press `Return` on empty (1,5) with Scout still selected.
   Require the original post-move hash, a new **red Rejected receipt**,
   yellow Scout outline still present at (2,5), and the cursor still
   at empty (1,5). This is an actual processed rejection, not a dropped key.
4. Press `BackSpace` and independently require unchanged battle hash,
   a new **amber Cancelled receipt**, and *absence* of yellow Scout outline.
5. CI independently opens archived action PNGs and checks the signatures,
   the receipts and selected-state transition. An absent JSON or PNG fails
   rather than silently skipping the test.

Stage43 adds host-only synthetic PNG regression tests for missed input,
false success, oscillation, invalid state, and forged visual receipts.
The three independent NeXium cursor/close sessions remain separate from
the one tactical action chain.

## Scope limitations

The entire training map, actors and HUD are original placeholder graphics.
No Saturn BIN/CUE, art, animation, music or authentic Saturn maps are pushed
to GitHub. Host tests are separate from live guest evidence. The next
unproven behavior is an **actual live attack**; prior C++ synthetic duel
tests do not establish live NeXium attacks.
