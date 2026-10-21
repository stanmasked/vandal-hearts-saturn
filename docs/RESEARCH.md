# Saturn source validation checklist

The original Japanese Sega Saturn release is `T-9526G` dated 1997-11-27.
Saturn-specific gameplay/data differences must be derived from the actual Saturn disc or
controlled observation of the running original; internet feature lists vary.

Upon receiving a user-provided original-disc dump locally:
1. Keep CUE + track BIN files outside this repository (`private/`).
2. Run `python3 tools/disc_inventory.py /path/to/original.cue`.
3. Check hashes, tracks and sector modes and record version.
4. Detect filesystem/layout without publishing content.
5. Create a *non-copyrighted* battle reference report with coordinates, mechanics
   and expected outcomes; exact screenshots/audio remain private.
6. Only after validation, implement source-specific loaders and full remaster stages.

The 2020 English translation patch is a potentially useful comparison reference, but
it is not the source of truth for original Japanese Saturn game behavior.
