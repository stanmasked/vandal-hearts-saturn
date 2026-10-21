# Stage92 — local-only HTTP Range retrieval of the existing Saturn Track1

## Why this exists

The previously supplied English v1.1 Saturn Track1 remains in the user's
private Google Drive folder **VH-Saturn** (621,755,904 bytes). The connected
ChatGPT Google Drive download tool refuses this full-file size at its
268,435,456-byte limit and does **not** expose arbitrary byte-range reads.
The CUE and Track2 were separately read and verified against Stage02 SHA-256.

This stage creates a **standalone local fallback** that requests chunks
using the documented HTTP `Range` mechanism on Google's Drive media API.
It is not a way to obtain the current ChatGPT connector's OAuth token.
The script only runs with a separately authorized, local user's Drive
OAuth token. It is not automatically runnable within this chat or CI.

## Local private procedure

On a trusted computer, ensure the user already has access to the existing
Drive file under their account, and a **separately acquired access token**
with permission to read it. Do not copy that token into ChatGPT, GitHub,
an issue, a CI secret, a command-line argument or a project file.

Create an empty private directory outside all git checkouts with mode
0700. The script refuses paths inside git or world-readable folders,
and never overwrites existing output. With private environment variables
configured, run:

```bash
mkdir -m 700 /private/saturn-track
export GOOGLE_DRIVE_ACCESS_TOKEN='<locally-authorized-short-lived-token>'
python3 -m tools.saturn_private_track1_range_retrieval \
  --drive-file-id '<existing-private-drive-file-id>' \
  --output /private/saturn-track/Track1.bin \
  --chunk-mib 8
unset GOOGLE_DRIVE_ACCESS_TOKEN
```

The placeholders above are **not** real tokens or publicly disclosed IDs.
The script requests only
`https://www.googleapis.com/drive/v3/files/<id>?alt=media`,
using exact `Range: bytes=start-end` requests. It refuses HTTP 200
full-file responses, redirects, mismatched Content-Range, changed ETag
when provided, compressed data, short/extra response bytes and file
mutation indicated by the final SHA-256. No arbitrary host URLs or
third-party domains are accepted.

The entire 621,755,904-byte file is streamed in bounded 8 MiB default
pieces to a temporary file in the protected folder. **Only if the final
SHA-256 exactly matches the Stage02 Track1 pin** does it create the
final 0400 (read-only) `.bin` file using a non-overwriting hardlink.
Any failure removes the temporary partial file. It prints only the
number of verified bytes and successful ranges, not content, paths,
checksums, tokens or other private values.

Next, run the existing Stage90 local preflight with
`--track1 /private/saturn-track/Track1.bin` alongside the locally
available CUE and Track2 paths. If all three original inputs match
Stage02 pins, Stage86/87's private Yabause runner/gated FAD procedures
become eligible for genuine game boot checks. Merely downloading the
image does **not** prove it booted.

## Evidence status

- Public Stage92 CI tests use a fake HTTP response object and invented
  raw-sector-aligned bytes only, with no network or authorization.
- They check success, wrong hashes, refused HTTP 200, truncated/extra
  bytes, changed ETag, encoded responses, malicious redirects, existing
  destinations, symlinks, 0700 permissions and invalid bounds.
- Real Drive Range delivery through this script has **not** been tested
  in this ChatGPT execution environment. Local OAuth authorization and
  a private machine with file-system access are prerequisites.
- Even a verified Track1 establishes only source identity; it is **not**
  an authentic game boot, a first-battle capture, map extraction or
  equivalence with the unpatched Japanese Saturn release.
- Do not upload the source image, fragments, CUE, CD-audio, game assets,
  FAD captures, credentials or extracted contents to GitHub/CI.

Issue #11 remains the first-battle authenticity gate until a private
boot and independently synchronized frame/CD-read evidence exist.
