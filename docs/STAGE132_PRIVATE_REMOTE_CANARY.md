# Stage132 - actual private remote readiness before Stage124 original-media recapture

Stage131 and Stage130 passed their public synthetic and ROM-free CI. Stage130
previously checked only that the rclone executable existed. An installed
executable does not establish a reachable, writable or readable remote
destination. Starting a long original-disc recapture with an untested remote
risks stranding captured files in a temporary private environment.

Stage132 adds a **synthetic canary transaction before any original-media
runner starts**. The private host uses rclone to upload a unique random
small non-game text object into the destination archive's parent folder,
downloads it to a separate temporary local file, compares its exact bytes,
and deletes **only its own generated canary**. A missing executable,
unavailable destination, rejected write, altered readback, or cleanup
failure stops the experiment before the Stage124 original game runs.
No source BIN/CUE, screenshots, captured traces or private digest are
transferred during this canary probe. The process never logs raw provider
stderr, secret configuration, local private paths or original content.

The upload uses rclone's immutable option to avoid overwriting any
preexisting object; the canary filename includes a random suffix.
If the transfer fails after a remote partial write, a benign probe object
may remain; investigate the destination folder manually before retrying.
No existing game archive or raw source file is deleted. Original captured
frames and outputs are still preserved by Stage130, not cleaned up.

Stage132 changes the existing Stage130 recapture function so that this
remote canary is mandatory AFTER validating fresh private destinations
and finding rclone but BEFORE launching Yabause.

## Provenance boundaries

Passing a synthetic canary proves that the configured rclone remote can
write, read and remove a harmless new object **at the time of the probe**.
It does not establish that the provider is Google Drive, that the user is
the sole owner, that sharing is disabled, or that enough space is available
to save the entire original capture. The separate verified Google Drive
metadata / owner-only permissions / full archive download gate remains
mandatory. Stage125 may not start without its independent private receipt.

All public CI tests use mocks and synthetic bytes only, without connected
Drive credentials or original Saturn media. Neither a live canary nor a
new Stage124 capture has been performed in public GitHub Actions.

The historical Stage124 capture archive remains missing from owner-only
Drive; any new recapture must have its own manifest, control sums and
authenticated readback, not be relabeled as the old lost capture.
