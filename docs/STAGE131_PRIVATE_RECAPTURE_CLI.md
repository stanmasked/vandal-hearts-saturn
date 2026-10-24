# Stage131 — private durable recapture command-line entrypoint

Stage130 already passed its public synthetic contract, Host GCC/Clang, and Nintendo Switch NRO/NeXium builds. However its durable recapture orchestrator was only callable as a Python function, increasing the chance of manual copy-paste mistakes when a private runner is eventually available.

Stage131 adds a command-line entrypoint to the existing Stage130 orchestration module. The private operator supplies original cue, track1, track2, the pinned runner, its independently checked SHA-256, two fresh private capture directories, a new private archive, a separately configured rclone remote object path, and a distinct new private readback filename. On success it reports only bounded boolean status flags. On failure the CLI refuses the handoff and does not echo paths, provider errors or original content.

Private-use command shape (variables refer ONLY to local private runtime values):

    python3 -m tools.saturn_private_stage130_recapture_handoff \
      --cue "$PRIVATE_CUE" --track1 "$PRIVATE_TRACK1" --track2 "$PRIVATE_TRACK2" \
      --runner "$PRIVATE_PINNED_YABAUSE" --runner-sha256 "$PRIVATE_RUNNER_DIGEST" \
      --control "$PRIVATE_NEW_CONTROL" --enabled "$PRIVATE_NEW_ENABLED" \
      --archive "$PRIVATE_NEW_ARCHIVE" --remote-object "$PRIVATE_REMOTE_OBJECT" \
      --readback "$PRIVATE_SEPARATE_DOWNLOAD"

These variables are illustrative only; this instruction is NOT a claim that the original-game run was executed. Existing Stage130 checks continue to reject nonempty output directories and preexisting archive/readback paths. The private rclone configuration must independently be verified by the operator prior to a lengthy run. Merely finding the rclone executable does not demonstrate network availability or permission to write, and the utility makes no such claim.

Stage131 adds synthetic-only command-line tests checking argument forwarding and suppression of confidential details on errors. The tests do not invoke an actual emulator, Google Drive or source BIN/CUE.

The historical Stage124 archive remains absent from owner-only Google Drive storage. A genuine new Stage124 recapture is a separate experiment, not restoration of the earlier historical archive. Even successful remote readback requires an additional authenticated owner-only Drive file/permissions check and new independent manifest before a Stage125 receipt can be issued.
