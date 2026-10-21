# Saturn CD-block FAD → ISO logical-LBA conversion (Stage73)

The Saturn CD block addresses sectors by FAD (Frame ADdress). According to
the [Yabause CD Block documentation](https://wiki.yabause.org/index.php5?title=CDBlock),
the first-data-track convention is `FAD = LBA + 150`. Independent
[Mednafen CD-block source](https://sources.debian.org/src/mednafen/1.32.1%2Bdfsg-3/src/ss/cdb.cpp)
also uses `CurSector - 150` when reading raw disc sectors.

**Do not silently guess this difference.** An FAD capture has
`addressing: "saturn_cd_block_fad"` and must be deliberately converted,
using the known first-track length from the user's private ISO metadata.

```bash
python3 -m tools.saturn_fad_trace \
  --inventory /private/saturn_iso_metadata.json \
  --fad-trace /private/saturn_cd_block_fad.json \
  --output /private/saturn_iso_lba_trace.json

python3 -m tools.saturn_read_crosswalk \
  --inventory /private/saturn_iso_metadata.json \
  --trace /private/saturn_iso_lba_trace.json \
  --output /private/saturn_candidate_overlap.json
```

The converter refuses a read before FAD 150, outside the known Track-1
extent, or beyond the bounded numeric ranges. It does not convert Track-2
CD audio addresses, multi-session layouts or uncalibrated timing/physical
sector numbers. A private trace remains unverified until the emulator
instrumentation and original-screen state are independently corroborated.

No original disc data, private file contents or captured addresses are
included in public tests. Numeric fixture FADs 160, 170, etc. are invented.
