# Stage 14 — blocked spatial holdouts and large-shift controls

Source: privately held, English v1.1 translation-patched Sega Saturn Vandal Hearts disc (T-9526G). Only numeric summaries and fully synthetic tests are published.

## Question and method

Previous Stage 13 observed predictive association of A→B under interleaved row holdout, but contiguous row structure might inflate the relationship. The candidate A/B arrays are **not authenticated game tiles, graphics, or geometry**.

- Candidate A and B are two consecutive 28×64 BE16 regions from `.MAP`.
- Train a modal B value per A value using **only rows outside the held-out fold**.
- `interleaved`: row modulo 4; `blocked`: four contiguous blocks of seven rows each.
- Evaluate the model and an unconditional training-only B-mode baseline on the **same covered test positions** (A seen in training). Missing A values are uncovered; folds lacking training pairs are explicitly skipped.
- As negative controls cyclically rotate B by 1, 64, 448 (7 rows), or 896 (14 rows) words. Shifted controls can change nonzero-pair populations and must not be compared as if test samples were identical.

## Whole-disc results: 74 MAP files

| Holdout | B shift | Nonzero test pairs | Covered | Model correct | Baseline correct | Model accuracy | Baseline accuracy | Skipped folds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Interleaved | 0 | 21,610 | 19,030 | 13,295 | 9,060 | 69.86% | 47.61% | 0 |
| Blocked | 0 | 20,557 | 17,770 | 12,136 | 8,011 | **68.29%** | 45.08% | 17 |
| Blocked | 1 | 19,203 | 16,663 | 10,063 | 7,368 | 60.39% | 44.22% | 19 |
| Blocked | 64 | 18,332 | 16,213 | 9,467 | 6,990 | 58.39% | 43.11% | 23 |
| Blocked | 448 | 10,841 | 8,625 | 3,286 | 3,701 | 38.10% | 42.91% | 84 |
| Blocked | 896 | 8,865 | 7,256 | 3,233 | 3,378 | 44.56% | 46.55% | 132 |

Even with contiguous blocks held out, aligned A predicts B considerably better than a constant-value control. Larger rotations suppress this difference, but may reduce training coverage. The findings support related arrays without proving how either is used in gameplay.

**Important limits:** each file is trained separately; there is no cross-map transfer test. Graphics/palette indexing, material attributes, and many other explanations remain possible. No emulator or Saturn screenshot validation was conducted in this stage. No native Switch NRO or NeXium test is verified.

## Reproduce privately

Run `python3 -m tools.saturn_map_ab_blocked /private/track1.bin --output /private/stage14.json` and the synthetic suite with `python3 -m unittest discover -s tests -p 'test_*.py' -v`.

Stage 14 includes **11 new synthetic tests** for fold separation, skipped training, artificial shifts, malformed input and privacy-safe numerical reports. Locally, the Stage 13+14 combined 22 tests and the C++ tactical_core CTest passed. Original game files remain private.
