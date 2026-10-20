# Stage 12 — duplicated MAP values and monotone-order falsification

Source: privately held Sega Saturn **English v1.1 translation-patched** disc (`T-9526G`). No game assets, music, graphics, executable code, scripts, original values or exact coordinates are included in GitHub.

## What was tested

Prior stages identified a candidate 28 × 64 area A of BE16 words and an association with BE16 word 1 (zero-based) of the six-word candidate records. This study asks whether the two sequences can be aligned **monotonically**, despite repeated values.

1. For each nonzero A occurrence, count matching record-field-1 occurrences (zero, one or several).
2. Treat matches unique in **both** sequences as unambiguous *value anchors*; keep their positions private.
3. Compute a longest strictly increasing subsequence (LIS) of the record indexes of these anchors in A order.
4. Test whether duplicate-valued layer occurrences have exactly one matching record position **inside one interval bounded by LIS anchors**. Flag collisions where several occurrences claim the same record.
5. Export only counts, not assignments. Since LIS may discard unique anchors, every narrowed duplicate is marked **hypothetical** and unsuitable for a production importer.

## Findings: all 74 .MAP files

| Metric | Count |
| --- | ---: |
| Nonzero A occurrences | 21,610 |
| No equal record value | 1,951 |
| Exactly one matching record occurrence | 1,031 |
| Multiple matching record occurrences | 18,628 |
| Value anchors unique in both A and record sequence | 952 |
| Anchors retained in longest increasing chains (sum across maps) | 731 |
| Anchors excluded due to ordering contradictions | **221** |
| Maps containing an anchor-order contradiction | **45 / 74** |
| Duplicated A positions with one candidate in a LIS-bounded interval | 2,152 |
| Conditional candidates without local record collision | 1,550 |
| Conditional candidates with conflicting reuse of a record | 602 |
| Intervals containing an excluded contradictory anchor | 99 |

Example: `M_MAP13.MAP` contains 76 unique-value anchors; only 47 fit a single increasing chain, with 29 excluded. The same holds for `M_MAP14.MAP`.

**Interpretation:** The naïve rule “record indexes increase whenever candidate A position increases” fails in many maps even among unique values. The 1,550 noncolliding conditional candidates **cannot** be promoted to mapped coordinates: they depend on an ordering assumption already shown to fail globally. This could be a rendering-resource order, multiple sequences, chunk reordering, or an incorrect interpretation of A.

## Reproduce locally

```bash
python3 -m tools.saturn_map_duplicate_order "/private/path/to/Track 1.bin" \
  --output /private/stage12_duplicate_order.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
ctest --test-dir out --output-on-failure
```

Locally verified: **83/83 Python tests**, **1/1 C++ CTest**, 74/74 private Saturn MAP files read. The 12 new tests use synthetic fixtures only and exercise order inversion, duplicate collisions, bounds, invalid data and metadata-only reports.

## Next gate

Do not build a tile-coordinate importer from these guesses. Instead, determine whether A contains **tile order, sprite/surface order, map chunks or reference IDs**, using reference gameplay images plus unrelated known map objects and exact coordinate tests. Keep the original-disc contents private; Nintendo Switch NRO and NeXium runtime are independent unverified milestones.
