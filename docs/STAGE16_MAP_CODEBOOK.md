# Stage 16 — Map-local codebook ambiguity and spatial permutation controls

Source: privately held Sega Saturn Vandal Hearts: Ushinawareta Kodai Bunmei English v1.1 translation-patched Track 1 (T-9526G), **not** the authenticated unpatched Japanese master. The repository contains no original game files, extracted content, audio, graphics or MAP data values.

## Hypothesis and method

A and B are candidate 28x64 arrays of BE16 words in each .MAP. Their meaning is unknown; they are **not confirmed** terrain, tile cells, collision, heights, palette or graphics indexes.

For each map, count distinct A and B values (treating each MAP separately), distinct B values per A, the fraction of paired positions attributable to A values with only one B, and in-sample modal-fit statistics. In-sample agreement can overfit; do not treat it as model validation.

Next use four-fold **contiguous seven-row** holdout and eight fixed pseudo-random control permutations per MAP:

- Within-row: shuffle B across jointly occupied positions in each 64-word row, preserving each row's B histogram.
- Whole-map: shuffle B across jointly occupied positions throughout each file, preserving global B histogram.

Both controls preserve A, exact joint-nonzero occupancy, number of tested positions, and input coverage. The seed derives from SHA-256 of filename, control and repetition index. No game values are exported.

## Verified results — 74 privately processed MAP files

- **21,610** aligned nonzero pairs.
- **2,917** distinct A codes across individual maps (not globally distinct).
- **1,896** map-local A codes have only one observed B value; **1,021** have multiple B values.
- **10,548** paired positions belong to deterministic A codes (**48.81%**).
- In-sample modal A→B agreement **16,816 / 21,610 (77.82%)**, with in-sample B-mode baseline **10,608 / 21,610 (49.09%)**. These are descriptive training-set fits, **not holdout accuracies**.

| Blocked holdout | Nonzero tested | Covered tested | Model correct | Baseline correct | Model accuracy | Baseline accuracy | Skipped folds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original A/B | 20,557 | 17,770 | 12,136 | 8,011 | **68.29%** | 45.08% | 17 |
| Within-row shuffled, 8 replicates | 164,456 | 142,160 | 59,299 | 62,380 | **41.71%** | 43.88% | 136 |
| Whole-map shuffled, 8 replicates | 164,456 | 142,160 | 58,559 | 66,716 | **41.19%** | 46.93% | 136 |

Shuffled totals pool eight repetitions, so denominators are 8x original; baseline distributions change under shuffling. Out of **56 MAPs with evaluable covered positions**, the original model beat within-row shuffled on **50**, tied on **1**, and lost on **5**. Remaining **18** MAPs lacked evaluable covered positions and are **not** victories.

These results show that alignment carries information beyond B marginal distributions, but A→B is ambiguous for many source codes and no terrain, graphics, coordinate or gameplay semantics are proven.

## Reproduce and validate

Run the Python module tools.saturn_map_codebook on the privately owned RAW MODE1/2352 Track 1 BIN; pass --permutations 8 and --output to write a numeric-only JSON report. Run synthetic tests with python -m unittest discover -s tests.

Stage 16 adds 11 synthetic unit tests. Local Stages 13–16 test set: **44/44 passed**; native C++ CTest **1/1 passed**. All 74 original MAP files were read privately; no media is committed.

## Next validation gate

Compare candidate arrays to actual running Saturn gameplay images and scene coordinates; test palette/graphics-index alternatives and the unmodified Japanese disc. Native Switch NRO, NeXium, and a faithful first battle remain **unverified**.
