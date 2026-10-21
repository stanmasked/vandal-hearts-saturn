# Stage 10 — Candidate MAP layer-A-to-record-word association

Source: user-owned Sega Saturn T-9526G disc, English v1.1 translation-patched.
Only **numeric counts, per-file names, and synthetic test data** are published.

## Method

- Candidate layer A is 28 rows × 64 BE16 words, beginning at MAP offset 0x24400.
- Ignore zero words from A and count repeated values as a multiset.
- From the candidate 12-byte record table [0x1E800,0x23804), count word at zero-based index **1**.
- Intersect the multisets, counting shared occurrences with multiplicity.
- To test specificity, pair A from each file with the **record field 1 of every other file within its own family**. Record average overlap and whether own pairing wins strictly, ties, or loses.
- These are numeric **value-association tests**, not decoded tile coordinates or original gameplay data.

## Findings from all 74 MAP files

| Family | Maps | Same-file mean | Other-file mean | Strict same-file wins | Ties |
|---|---:|---:|---:|---:|---:|
| M_MAP | 34 | 88.9673% | 19.3242% | 34 | 0 |
| M_KEY | 17 | 94.0410% | 7.1708% | 16 | 1 |
| M_IVE | 22 | 98.4425% | 17.1318% | 20 | 2 |
| M_SHOW | 1 | 96.3542% | no control | — | — |

- **21,610** nonzero layer-A words across all MAPs.
- **19,582** of these matched record-field-1 words from the same map, with multiplicity (**90.6155%** of all layer A words).
- For **40/74** maps, the entire candidate A multiset is contained within the record field-1 multiset.
- **73** maps have a same-family foreign comparison. **70** strict own-file wins, **3** ties, **0** foreign wins.
- Tied maps: M_IVE10.MAP (vs M_IVE09), M_IVE14.MAP (vs M_IVE22), M_KEY17.MAP (vs M_KEY02).

## Verification

Locally: Python unittest **61/61** and C++ CTest **1/1** passed.
Real user-owned disc: all **74** files were processed.
Run privately:

```bash
python3 -m tools.saturn_map_field_link "/private/Track 1.bin" --output /private/stage10.json
python3 -m unittest discover -s tests -p "test_*.py" -v
ctest --test-dir out --output-on-failure
```

## Important limitations and next validation gate

Shared value distributions could originate from linked indexes, repeated graphics IDs, palettes or another internal table. No **position-by-position** correspondence was established; zero-based record index 1 is a candidate association, not a proved gameplay field. Next check positional ordering and cross-reference actual Saturn runtime behavior. Native Switch .nro / NeXium runtime remains unverified.
