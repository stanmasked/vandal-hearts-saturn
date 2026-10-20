# Stage45 — Input-drop recovery and persistent acted state in NeXium

## Evidence-based motivation

The genuine [Stage44 NeXium run #39479994025](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39479994025), archived as [artifact #12291277869](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39479994025/artifacts/12291277869), passed the isolated ROM-free duel's first hit and rejected second hit.

Its **actual** `stage44-session/runtime-evidence/attack-evidence.json`
recorded the following return cursor x-coordinate sequence after repeated
X11 Left commands: `524.5, 524.5, 524.5, 524.5, 524.5, 480.5`.
The first five pulses were *observed* no-ops, not five actual cursor steps.
The sixth moved to Scout. That is a reason to make recovery conditional on
the screenshot; it does not establish exactly which layer dropped those keys.

Stage45 detects a missing directional motion by comparing two screenshots
and calls the existing best-effort X11 window-focus helper **only** after the
miss was witnessed. Twelve attempts is the strict limit for the isolated
duel's horizontal return/aim, with an error if the observed cursor never
reaches the expected tile. A call to `focus` does not count as a successful
movement. The default Stage42–43 scenario and its input behavior stay intact.

## New live continuation, after Stage44 passes

Run in the **same, already verified** duel NRO session, before graceful
shutdown:

1. Confirm the real PNG of the first successful attack and already rejected
   second strike. Full state hash must be `9a0233cdc1acffdb`, Raider HP
   must be 14, and Scout's selection outline must still be visible.
2. Send BackSpace, require an actual amber **Cancelled** action receipt and
   removal of Scout selection outline. Battle hash/HP must remain unchanged.
3. Observe every Left/Right cursor pulse until it returns to Scout, bounded
   at twelve attempts; when a pulse is missed, refocus.
4. Press Return (one Space retry is allowed if no selection outline appears).
   Require an actual blue **Selected** action receipt and visible Scout
   outline. A sent key by itself never counts.
5. Observe the cursor return to Raider and press Y. Require the red
   **Rejected** receipt, unchanged attack-state hash and the same 14 HP.
   Thus removing and recreating the UI selection cannot bypass the
   per-round `acted` flag in the native game core.

The independent GitHub verification step reads genuine guest PNGs for
the cancellation, selection and rejection and verifies their registered
colors, unit outline and cursor location. It **also revalidates Stage44**.
A missing screenshot, unsupported report filename, or forged digest fails.

## Other tests and boundaries

- Nine new host synthetic screenshot tests exercise dropped arrows,
  12-pulse timeout, ignored cancel, forged reselect, HP corruption, false
  success receipts, and the archived-image verifier.
- Host C++ extends the canonical duel fingerprint test with Cancel /
  reselect / rejected strike and confirms that the acted bit and HP do
  not change.
- This is an *original homebrew test scene*, not the Sega Saturn game's
  battle data. Keyboard/X11 evidence is not physical Joy-Con evidence.
- Do not mark Stage45 live verified until the new NeXium job has finished
  and its image verifier has passed.
