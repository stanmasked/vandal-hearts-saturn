# Data storage and evidence policy

This policy applies to Vandal Hearts Saturn and its Stage experiments.

## Private Google Drive is the durable archive

- Keep original BIN/CUE media, split source archives, BIOS/configuration inputs, unprocessed captures, screenshots, raw traces, diagnostic logs, and private experiment outputs in the owner-only Google Drive archive.
- Do not modify the original source items. Any working copy is derived for execution only; verify its size and SHA-256 against the private manifest before and after a run.
- Keep raw/unprocessed captures separate from derived reports, summaries, and visual-review notes.
- Use stage-specific folders under `VH-Saturn/Private Archives`: reports/manifests, private captures/logs, and build/CI evidence.
- After every significant stage, verify that the Drive folder is reachable, the new files exist, their sizes and hashes match the manifest, and sharing remains owner-only.

## Public GitHub boundary

Public GitHub may contain source code, synthetic/ROM-free tests, and safe technical documentation only.

Never commit or upload original game media, BIOS files, private memory traces, real-disc captures, screenshots, raw experiment logs, local absolute paths, or private capture hashes. Do not retain build binaries, NROs, CI source bundles, or screenshot/evidence ZIPs as public Actions artifacts. CI jobs may emit only non-sensitive pass/fail diagnostics required to test the public code.

Where a workflow requires an inter-job build handoff, keep it temporary, minimize its retention, and delete it after use. Do not use that handoff as an archive. Prefer building locally from pinned public sources for private experiments.

## Required manifest fields

Every meaningful stage record must contain:

- project and stage identifier;
- exact code revision and relevant upstream/toolchain pins;
- input names, sizes, and private SHA-256 values;
- build/runner identity and SHA-256 where applicable;
- commands or workflow/run identifiers;
- tests, counts, pass/fail results, and limitations;
- output inventory, file sizes, SHA-256 values, and private archive location;
- next action and explicit statements about what has **not** been proven.

## Temporary workspace safety

Do not delete a temporary workspace containing the only copy of a capture, trace, screenshot, or derived report. First upload the files to the appropriate private Drive archive and verify them by readback. If the available connector cannot upload a binary artifact, preserve it intact, report the limitation, and do not claim it has been archived. Original source files in Drive remain the durable source of truth.

## Evidence discipline

Synthetic CI success is not proof that the original game reached a scene or that gameplay is restored. Keep authenticity claims, dialogue progression, tactical battle entry, and player control as separate gates. Never infer a battle from non-black pixels alone.
