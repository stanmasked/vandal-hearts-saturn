# Stage 13 — Row-held-out prediction of candidate MAP B from A

Source: privately held, translation-patched English v1.1 Saturn image (T-9526G). No original image, audio, executable, map bytes or field values committed.

Candidate A and B are two 28×64 BE16 arrays in the MAP tail. Their meaning is **not established**.

## Method
Split candidate rows into four disjoint folds by row index modulo four. Train a mode predictor of B for each observed A word on the other three folds. Test only on the held-out rows and nonzero A/B pairs; unknown A words count as uncovered. Compare to the mode of B learned only on the same training folds and tested on the same covered positions. Repeat by cyclically shifting B by 1, 64 and 65 BE16 words.

| B shift (words) | Nonzero test pairs | Covered | Model correct | Model on covered | Baseline on covered |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 21,610 | 19,030 | 13,295 | 69.86% | 47.61% |
| 1 | 20,461 | 17,974 | 11,116 | 61.84% | 46.43% |
| 64 | 20,052 | 17,744 | 10,758 | 60.63% | 46.14% |
| 65 | 19,032 | 16,803 | 9,290 | 55.29% | 45.30% |

Original aligned test-set coverage is 88.06%. The 64/65-shift controls have one empty training fold (correctly skipped). Shifted controls change jointly nonzero sample counts; direct accuracy comparisons have selection effects.

Association and alignment sensitivity support **related structures**, not confirmed tile positions, collision, terrain, sprite IDs, or palette indices. Nearby values remain correlated under shifts. Do not implement a real map converter solely from this experiment.

## Reproduction (private media only)

    python3 -m tools.saturn_map_ab_prediction /private/track1.bin --output /private/stage13.json
    python3 -m unittest discover -s tests -p 'test_*.py' -v

Eleven new synthetic tests cover heldout leakage, alignment shifts, zero filtering, invalid data and numeric-only reporting. Local experiments on 74 real MAP files and synthetic tests passed. CI of the new head needs separate confirmation.

Next: correlate A/B structural patterns with independent Saturn reference rendering, and separately validate the original unpatched Japanese disc. Nintendo Switch NRO and NeXium runtime remain unverified.
