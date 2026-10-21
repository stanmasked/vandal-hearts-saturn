# Stage75 — self-declared Saturn read capture provenance preflight

Stage74 verifies a numerical repetition pattern when at least two
`first_battle_entry` and two `menu_control` records are supplied. But one
copied recording can be submitted repeatedly and would pass this *numerical*
gate. Stage75 makes that limitation visible and requires a private,
ordered **capture metadata sidecar** before a researcher reviews the evidence.

## Private sidecar format

```json
{
  "schema_version": 1,
  "source": {
    "product_code": "T-9526G",
    "release_kind": "translation_patched",
    "image_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "instrumentation": "emulator_cd_block_hook",
  "runs": [
    {
      "phase": "first_battle_entry",
      "capture_id": "opaque-capture-01",
      "session_id": "opaque-session-01",
      "image_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "release_kind": "translation_patched",
      "boot_kind": "cold_boot",
      "frame_start": 10,
      "frame_end": 120
    }
  ]
}
```

**Everything in the example is illustrative and fabricated**; the complete
sidecar needs one run record for each run in the Stage73 trace, in exactly the
same order (at least two battle-entry and two menu controls). Real run/session
IDs, image fingerprints and capture timestamps stay private. Records must
have distinct opaque capture IDs *and* session IDs. All run hashes and release
kinds must agree with the source; the image digest can optionally be
checked against a separately pinned local Track-1 reference.

```bash
python3 -m tools.saturn_capture_provenance \
  --inventory /private/iso_metadata.json \
  --trace /private/saturn_lba_trace.json \
  --capture-sidecar /private/captures.json \
  --expected-image-sha256 <locally_pinned_sha256> \
  --output /private/saturn_capture_preflight.json
```

A Boolean success flag (`metadata_preflight_ready_for_human_review`)
indicates only that the provided labels are unique, source fingerprints
are consistent with a supplied reference, captures *claim* cold boots,
and Stage74 received enough trace records.

It **does not verify** whether files were captured separately, whether the
emulator actually booted from the asserted source, whether a control window
was exhaustive, or whether original Saturn content is authentic. These remain
explicit false fields in every report. Identical normalized sector coverage
is reported as an **informational count**: it is expected for a deterministic
game and does not automatically prove duplicate capture files.

No original disc bytes or capture logs are included in GitHub CI. Synthetic
tests use invented source hashes, intervals, session labels and windows. Output
contains aggregate counts and fixed blocker codes; it never exposes hashes,
paths, labels or captured sector intervals.
