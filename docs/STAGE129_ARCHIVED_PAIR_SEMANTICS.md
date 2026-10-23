# Stage129 - Archived Stage124 paired-capture semantic audit

## Why a further gate is required

Stage128 checks the Stage124 TAR.GZIP size and matching SHA-256 against the *supplied* expected fingerprint and verifies both complete 900-checkpoint cohorts, mandatory diagnostics, safe TAR entries, and PNG CRCs. That is stronger than a receipt alone but does not prove the captures form the authentic *paired ninth-C experiment*.

Stage129 replays the existing independent Stage124 paired-run auditor on actual archive members before Stage125 is allowed to launch Yabause. It classifies two cohorts by their expected active-low PAD event receipts rather than trusting their TAR path names. It extracts only the allowlisted frame-N.png files and eight diagnostic sidecars into a new short-lived private scratch directory with restricted file permissions. Raw archive paths are never used as destination paths, the original TAR.GZIP stays unmodified, and the scratch data is deleted after the audit.

Required Stage124 paired semantics include 900 frames/checkpoints per cohort; correct eighth-C control and ninth-C intervention receipts; identical cold boots before START and 799 identical checkpoints before the ninth C at 96000; a post-ninth framebuffer difference by 97200; valid canonical diagnostics and stable image dimensions. After the audit, the source TAR.GZIP fingerprint must match its initial identity and hash.

The Stage125 real private entrypoint now requires all of the previous Stage125 receipt checks, Stage128 full archive structure verification, and the new Stage129 paired semantic verification before touching source media or starting the emulator. It fails closed. Public CI uses only invented screenshot bytes, canonical synthetic receipts and mocked executable paths; no original Saturn BIN, CUE, user screenshots, real hashes, authenticated tokens or private manifests are uploaded.

## Remaining preservation block

A structure-and-semantics-passing archive still does not establish historical originality, correct owner-only Google Drive access, nor an authenticated independent downloaded copy. The historical Stage124 archive remains absent from the current owner-only Drive capture folder. The earlier original game only advanced dialogue and did not demonstrate a tactical battle. No Stage125 original-disc tenth-C run has occurred.

Independent verification of Drive file ID, owner-only access, correct manifest provenance, and upload/download readback remains mandatory. If historical raw bytes cannot be recovered, create a separately attested Stage124 repeat experiment and preserve it privately with a new identity; do not substitute its checksum for the historical Stage124 run.
