# Stage77 — manual capture windows for Yabause numeric sector reads

Stage76 introduced optional logging of ISO-sector callback reads, but setting VH_SATURN_FAD_LOG could capture the **entire emulator process**, mixing boot, menu, event and battle reads. Stage77 adds a separate, fail-closed **manual capture gate**; it does not detect game scenes or provide true frame synchronization.

## Local private procedure

Keep the owned Saturn image and all game media private. Use a separately built Yabause checkout. On a fresh uninstrumented copy of yabause/src/cdbase.c prepare Stage77's gate-only variant:

```bash
python3 -m tools.saturn_yabause_gated_hook --source /private/yabause/yabause/src/cdbase.c --output /private/cdbase-windowed.c
```

Review the patch before replacing source in the *local* emulator checkout and independently building Yabause. This project has not built or launched complete Yabause.

Launch that emulator with BOTH environment variables:

```bash
export VH_SATURN_FAD_LOG=/private/battle01.vhcdlog
export VH_SATURN_CAPTURE_GATE=/private/window.vhgate
```

The gate file must initially be absent. When the first read callback runs, an absent gate or a gate with anything except the exact bytes ASCII 1 plus LF means **no log record**. No game code or ISO payload is copied.

Independently observe the Saturn screen, then **manually** open and close one capture window:

```bash
python3 -m tools.saturn_capture_gate --gate /private/window.vhgate --start
python3 -m tools.saturn_capture_gate --gate /private/window.vhgate --stop
```

Open uses an atomic local marker write, stop deletes only the expected marker; both refuse unexpected paths. The game itself never asserts that the phase label is true. The gate is sampled on each successful callback, so events at the instant of manual transition may be included/excluded unpredictably. The tool does **not** know any actual Saturn frame number or menu/battle boundary.

Use one separately named, locally stored log file per cold-boot recording; collect at least two first-battle windows and two **comparable** menu-only controls. Attach independently checked screen and emulator-state evidence to the private Stage75 provenance records. Do not treat repeated numeric reads alone as proof of source or loader identity.

Then normalize via Stage76's private numeric FAD log converter, which uses the explicit Track-1 FAD = LBA + 150 convention, and run Stage73/74/75 checks. Out-of-track reads, including CD audio, are not silently skipped.

## Verification scope

Public CI builds and executes a **fabricated C program** with fake read callbacks before/during/after a gate interval in one process. It checks that only the two middle numeric FADs are logged and that malformed markers do not enable capture. This is not a complete Yabause build and it is not a run of the original game.

The original English v1.1 source remains private, unverified against the unpatched Japanese master. Host CD callback activity is not proven SH2 loader consumption; read-ahead/caching differences and human window selection remain unresolved. The original first-battle map, unit data and combat rules are not authenticated.
