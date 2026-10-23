# Stage130 — durable new Stage124 recapture handoff

## What changes

This stage introduces a single private-host call that chains the already
audited components. It first checks fresh private capture directories and
separate nonexisting archive/readback destinations, plus a syntactically safe
remote object path. The rclone executable must exist before the original
disc runner starts.

After a new, independently audited Stage124 pair, the function archives the
full capture using the Stage126 packager, verifies the TAR.GZIP fingerprint,
performs the Stage127 configured-remote upload and separate readback, and
replays Stage129 paired semantics against the downloaded archive. It checks
the local archive identity again before reporting completion. Failures abort
the chain. It **never deletes** raw captured frames, original BIN/CUE, the
local TAR.GZIP or the downloaded copy.

The new host-only entrypoint is implemented in
tools/saturn_private_stage130_recapture_handoff.py. Invoke
recapture_with_durable_handoff in an authorized private Python environment,
supplying the actual original media paths, independently pinned runner hash,
two empty owner-only capture directories, a fresh archive path, a configured
private rclone destination and a separate private download path. Do not call
from GitHub Actions. No original media paths, private SHA values, object IDs
or transfer credentials may be included in public logs.

## Security boundaries and evidence

This is a **fresh experiment**, not recovery of the missing historical Stage124
TAR.GZIP. Existing source media remains unchanged. A successful mocked public
test does not mean an actual game ran or an archive was stored.

Stage127's rclone readback confirms matching bytes from the configured remote.
It DOES NOT authenticate the remote as Google Drive, identify a Drive object
or verify owner-only access. Even when this Stage130 orchestration succeeds,
the result expressly leaves owner_only_drive_acl_verified=false and
stage125_receipt_issued=false. The Stage125 private tenth-C experiment must
stay BLOCKED until a separate live authenticated Google Drive check of file ID,
parent and owner-only permissions plus a genuine independent readback against
the **correct new experiment manifest**. Never copy or reuse the historical
Stage124 digest/identity for a new capture.

No automatic deletion or cleanup of raw/private data is allowed until an
owner-only cloud copy has been checked independently. If the remote upload
fails, preserve the local archive and raw output; do not rerun on those same
nonempty output directories.

## Public CI

The standalone Stage130 workflow tests only mock calls and invented paths,
without original Saturn media or cloud credentials. It also reruns Stage128
and Stage129 synthetic regressions. Host GCC/Clang and ROM-free Switch/NeXium
workflows remain separate exact-head checks.
