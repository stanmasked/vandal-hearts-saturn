# Stage 20 — Experimental NeXium framebuffer test

The existing Nintendo Switch build workflow now has a separate
**run-in-nexium** job that depends on a real successfully built,
header-verified `vh_saturn_demo.nro` artifact. It does not fabricate a
game boot or treat a correctly structured NRO as runtime proof.

The runtime job runs on Ubuntu 26.04, installs Xvfb, Mesa Lavapipe, NeXium
nightly and GUI helpers, then launches the actual compiled NRO. It saves
the NeXium console log and a screenshot of the visible emulator window.
A simple pixel check requires a minimum screenshot resolution and blue/red
colors consistent with the ROM-free allied/enemy marker rendering.

The emulator log and evidence folder are uploaded **even on failure**.
Passing the screenshot gate means only the app displayed a plausible
colorful game frame in NeXium. It does not prove input, mechanics, long-term
stability, or the original Saturn first mission. A color-only check can
produce false positives; independent human review of the screenshot is
required before claiming a verified playable boot.

The pipeline reuses the NeXium nightly download and Linux dependency
approach already used in the existing project
`stanmasked/vandal-hearts-switch-remaster`'s emulator-smoke workflow.

No original CD media, extracted graphics, sprites or music are used.
The first Saturn battle and its data decoder remain unverified.

Required follow-up: inspect the new job's conclusion and screenshot/log,
then add explicit control input probes if the first actual frame is valid.
