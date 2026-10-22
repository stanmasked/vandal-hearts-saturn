# Stage104 — private progression beyond the first visible original Saturn splash

Stage103 was a decisive original-media private A/B test: enabling the
public pinned Yabause **C68K** sound processor in place of the previous
M68K dummy allowed the English-v1.1 Saturn disc to render its actual
KONAMI splash in the first 600 emulated frames.

The Stage02 original Track1/Track2/CUE SHA-256 values were rechecked,
and the private 600-frame C68K run produced 997 genuine ISOCD callback
events (966 distinct), 499652 nonzero VDP2 VRAM bytes and 61440
nonblack rendered RGB pixels. The previous dummy-M68K run remained
black with 396 callbacks, demonstrating strong experimental evidence
that functioning M68K execution is required to progress through
initialization under our historical emulator build.

Stage104 keeps the genuine original disc core configurations unchanged
(C68K, SH2 interpreter, software video, HLE BIOS, ISOCD) but increases
the opt-in frame limit from 600 to **3600 frames**. It retains locally
protected PNG checkpoints every 120 frames, numerical VDP state and
the private SH2 register/instruction-window file from Stages101–102.

Public CI uses *only fabricated media*, recompiles the immutable
historical Yabause core under GCC/Clang and uploads only public GPL
program binaries as temporary artifacts. No original game BIN/CUE,
screenshots, private SHA-256 records, SH2 instruction words, CD callback
trace or copyrighted game resource is committed.

A private long run should document whether the game leaves the KONAMI
splash, whether a genuinely identifiable title/menu appears, and at
which emulator frame it first becomes visible. A visible title alone
is **not** evidence of a first battle, and a blank or unchanged frame
is not a success. That requires a separate independent screenshot and
actual gameplay CD trace bound to the guest frame counter.

A private operator may run a bounded command like:

```bash
VH_SATURN_CAPTURE_GATE=/private/run3600/gate \
VH_SATURN_FAD_LOG=/private/run3600/fad.vhcdlog \
VH_SATURN_PRIVATE_FRAMES_DIR=/private/run3600 \
  /private/pinned-public-yabause-c68k vh-private-frame-boot \
  /private/actual-owned-saturn-disc.cue 3600
```

All sample paths above are placeholders. Run with a hardened private
directory (0700), subprocess umask077, and an external wall-clock
timeout. Do not upload actual private scene images or CD traces to
public CI or Issue #11.

**Acceptance boundary:** only observable original video and
independently bound gameplay reads can support title/battle claims;
Issue #11 remains open for first tactical battle verification.
