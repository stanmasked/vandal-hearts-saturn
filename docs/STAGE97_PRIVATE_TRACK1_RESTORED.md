# Stage97 — original English v1.1 Saturn Track1 recovered from split ZIP

## The private source is now available

The user has added two files into the existing private Google Drive
\`VH-Saturn\` folder, as parts **.zip.001** and **.zip.002** of **one**
ZIP archive (rather than two independent ZIP files).

- First part: 220,000,000 bytes.
- Second part: 196,416,458 bytes.
- Total combined compressed ZIP: 416,416,458 bytes.
- Only one ZIP member, an uncompressed 621,755,904-byte Track1 file
  (deflated inside the ZIP).

Both parts were privately obtained through the already connected Google
Drive integration, and the actual concatenated archive was successfully
opened locally. The ZIP decompressor validated the member CRC. The full
restored Track1 was streamed, and its SHA-256 **exactly matched Stage02's
existing pin** (the same pin is stored in
\`tools/saturn_private_capture_session.py\`). Neither original Track1,
its parts, nor any extracted bytes are committed to public GitHub.

Also independently reconfirmed private Stage02 hashes for Track2
(2,102,688 bytes) and the original CUE (305 bytes), including the
two-file AUDIO layout.

## Actual private disc-format validation

The restored Track1 and original Track2/CUE were placed together in a
protected temporary local directory, under the basenames required by the
CUE. A read-only sector/PVD and ISO9660 directory traversal confirmed:

- Sega Saturn boot magic and original T-9526G identifying metadata.
- Primary Volume Descriptor \`CD001\` and \`VANDAL_HEARTS\`.
- Exactly 264,352 RAW MODE1/2352 data sectors.
- Two ISO directories and 848 files.
- Every inspected file extent within Track1 bounds.
- The two previously inventoried resource **candidate filenames**
  (\`MAP_1_1C.BIN\` and \`BATL1PRG.BIN\`) are present.

These checks validate the original media's structure, not that game
code has executed, the first battle appeared, or any map was decoded.
No source game asset has been extracted/published.

## Two valid archive delivery conventions — do not confuse

The uploaded \`.zip.001/.zip.002\` files are **pieces of one ZIP byte
stream**. Concatenate in numeric order, *then* open the ZIP archive.
Do **not** open \`.001\` and \`.002\` as individual ZIP archives.

\`tools/saturn_private_track1_splitzip_join.py\` implements that exact
flow privately with no dependence on archive member order:

- Require ascending, gap-free numeric parts with a shared name and each
  below the 256-MiB transfer limit;
- Assemble to a randomly named local 0600 temporary ZIP and refuse
  missing volumes, symlinks, hardlinked sources or unsafe workspaces;
- Require one archive member whose basename matches the requested
  output, with the exact Stage02 uncompressed size;
- Verify ZIP CRC while streaming, then full original Track1 SHA-256
  *before* exposing a 0400 read-only \`.bin\` via non-overwriting link;
- Remove temporary or rejected bytes on failure.

The earlier \`tools/saturn_private_track1_split_zip.py\` separately
supports a **different**, optional convention: one *independent* small
ZIP per raw data chunk with an accompanying checksum manifest. That
convention was **not** what the user uploaded here.

## Local private reproduction

When the user's original split parts are available in a local 0700 folder
and an empty protected output folder exists outside all Git checkouts,
use:

\`\`\`bash
python3 -m tools.saturn_private_track1_splitzip_join \
  --part /private/parts/track1.zip.001 \
  --part /private/parts/track1.zip.002 \
  --output /private/restored/original-track1-name.bin
\`\`\`

Use **the original Track1 basename referenced by the private CUE** for
the output. These example paths are placeholders. The utility will
reject anything whose full contents do not match the immutable
Stage02 size + SHA-256.

Stage97 CI only uses fabricated ZIPs holding tiny synthetic
sector-aligned data, never an actual original disc image.

## What is now next

**Issue #11's former source-access blocker is resolved.** Next, use the
locally verified private image in a real pinned Yabause binary that
supports the two-file CATALOG-first CUE. Obtain independently observed
guest frames and numeric read windows, and verify two true cold boots
for menu and first-battle entry. The historical Yabause version's CUE
and ISOCD test harness has passed synthetic two-file tests; the
current runtime has not yet confirmed the original game booted.

Do not publish BIN, CUE, private frame captures, audio, ZIP parts or
any protected asset in GitHub issues, commits, Actions, or attachments.
