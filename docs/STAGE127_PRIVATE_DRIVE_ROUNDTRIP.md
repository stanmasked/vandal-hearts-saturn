# Stage127 — Private Google Drive archive upload and independent readback

## Purpose and current limits

The historical Stage124 capture archive remains ABSENT from the owner-only Google Drive captures folder and current temporary workspace. No Stage125 original-disc experiment has run. Stage126 has fully passed the public ROM-free CI. Stage127 cannot recover missing bytes: it is a guarded handoff for future recovery of the exact historical archive or for a fresh, separately attested Stage124 recapture. Do not conflate the two cases.

## Private transfer (NEVER from public GitHub Actions)

Use an independently validated Stage124-shaped TAR.GZIP in a private host environment, outside the public checkout. Take the expected archive size and SHA-256 from the appropriate original private experiment manifest. Keep both values, all paths, and raw game data out of public build logs.

Set up a privately configured rclone Google Drive remote with its credentials outside Git. The destination must be the owner-only VH-Saturn / Private Archives / Stage124 Private Captures and Logs folder. The script does not discover remote permissions.

Private invocation:

    python3 -m tools.saturn_private_drive_roundtrip \
      --archive "$PRIVATE_STAGE124_ARCHIVE" \
      --remote-object "$PRIVATE_RCLONE_REMOTE_OBJECT" \
      --readback "$PRIVATE_DISTINCT_DRIVE_DOWNLOAD" \
      --expected-size "$PRIVATE_EXPERIMENT_ARCHIVE_BYTES" \
      --expected-sha256 "$PRIVATE_EXPERIMENT_ARCHIVE_SHA256"

The program verifies the full local archive using the Stage126 audit before transfer (two complete 900-frame cohorts, diagnostic sidecars, PNG chunk CRC and archive bounds). It invokes rclone by an argument array, never through a shell, and never prints the provider's raw command errors. Upload uses the ignore-existing option to avoid overwriting a previous remote object. In either case a separate download is mandatory. The script downloads to a new private file, verifies its size, SHA-256, TAR.GZIP structure and both cohorts, then confirms that the original file has not changed. On failure it deletes only the newly reserved readback, not the original archive, original captures or remote object.

The local success report confirms only a configured-remote byte-for-byte roundtrip. It deliberately sets:
- configured_remote_roundtrip_verified = true
- google_drive_owner_only_verified = false
- stage125_drive_receipt_issued = false

A matching checksum cannot by itself prove that the configured remote is actually Google Drive, belongs to the owner or is unshared. Before Stage125, obtain authenticated Drive metadata (file ID, parent folder, size, owner-only permissions and sharing) using the connected Google Drive tool or authenticated Google Drive API, and check an independent readback against the matching original private manifest. Only after this evidence is recorded privately may a Stage125 receipt be issued. Do not remove original archives or captured outputs before owner-only Drive persistence and readback are verified.

## Public CI boundary

Public tests replace the transfer routine with mocks, exercising only invented TAR.GZIP and PNG data. No Drive credentials, original source media, private receipts, original image payloads or fingerprints appear in GitHub. The Stage127 workflow uses read-only repository permissions, publishes no artifacts and cannot claim a true Drive upload.
