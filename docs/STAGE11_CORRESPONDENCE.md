# Stage 11 — MAP candidate record/layer association and unique anchors

Source: user-owned Sega Saturn T-9526G English v1.1 translation-patched image. Only aggregate counts, filenames and synthetic fixtures are published. No original data bytes, tiles, executable or graphic assets are committed.

## Experiment: five candidate regions × six BE16 record fields

Each of 74 MAP files is interpreted structurally as a candidate record table (six BE16 fields per record) and a candidate 173×64 BE16-word tail split hypothetically into A=28, B=28, C=14, D=28, E=75 rows.
Multiset overlap, **with duplicate occurrences counted**, gives:

| Region | Nonzero | Field 0 | Field 1 | Field 2 | Field 3 | Field 4 | Field 5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 21,610 | 19 | **19,582** | 101 | 0 | 0 | 368 |
| B | 21,699 | 0 | 0 | 0 | 0 | 0 | 0 |
| C | 11,098 | 0 | 26 | 0 | 0 | 0 | 3 |
| D | 21,625 | 27 | 1,895 | 25 | 0 | 0 | 34 |
| E | 85,745 | 17 | 3,197 | 21 | 0 | 0 | 5,341 |

A-field 1 matches 19,582/21,610 = 90.615% of nonzero occurrences, but this is NOT a position correspondence. B shares no values with any field under this specific counting metric; other types of relationship are not excluded.

## Unique-value candidate anchors

An anchor is a value present exactly once in A and exactly once in record field 1 of the SAME map. Repeated values are excluded, rather than assigned arbitrarily.

- 952 anchors across the 74 files, only ~4.4% of nonzero A positions.
- 57 maps have >=2 anchors and 17 have <2.
- Of 891 adjacent anchors in A order, 791 are ascending in record-table order and 100 descending (**88.7767%** ascending).
- M_MAP13 has 76 unique anchors, 71 ascending and four descending adjacent comparisons.

These observations may reflect an underlying ordering of **resources**, not a spatial ordering of playable map cells. No field meanings, tile geometry, mission assignment or authentic combat mechanics are claimed.

## Reproduction and validation

Run the original disc read-only and privately:

```bash
python3 -m tools.saturn_map_correspondence /private/track1.bin --output /private/stage11.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
ctest --test-dir out --output-on-failure
```

Locally: 71/71 Python unit tests passed, 1/1 C++ CTest passed; 74/74 MAP files analyzed. 10 new Python tests use synthetic data only.

## Next gate

Compare candidate anchor order with observable Saturn gameplay or independently validated rendered scene output; resolve duplicates without inventing per-tile positions; and separately validate the pristine Japanese release. Nintendo Switch NRO/NeXium runtime remain unverified.
