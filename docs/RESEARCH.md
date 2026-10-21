# Saturn source validation checklist

The original Japanese Sega Saturn release is `T-9526G` dated 1997-11-27.
Saturn-specific gameplay/data differences must be derived from the actual Saturn disc or
controlled observation of the running original; internet feature lists vary.

The user has already supplied an English v1.1 translation-patched T-9526G image set (split Track 1, Track 2 audio BIN and CUE). Prior local metadata inventory is documented in `docs/STAGE02_DISC_FINDINGS.md`; do not request the same files again.

1. Keep CUE + track BIN files outside this repository (`private/`).
2. Re-run `python3 tools/disc_inventory.py /path/to/source.cue` and
   `python3 -m tools.saturn_iso /path/to/track1.bin --list-files` only when the
   private source bytes are available locally.
3. Correlate resource names, ISO extents and file sizes as hypotheses only.
4. Create a *non-copyrighted* battle reference report with verified coordinates,
   mechanics and expected outcomes; exact screenshots/audio remain private.
5. Compare against the unpatched Japanese master only when an authentic separate
   reference is available; the translation-patched image alone is not proof.

The 2020 English translation patch is a potentially useful comparison reference, but
it is not the source of truth for original Japanese Saturn game behavior.
