# Stage 15 — Cross-map transfer of Saturn MAP A/B associations

Original privately owned source: Sega Saturn game image, English v1.1 translation-patched (T-9526G). No original binaries, art, audio, MAP values or copyrighted resources are committed.

The candidate A and B sections each contain 28×64 BE16 words, but their meaning is **not verified**.

## Method
Train a most-frequent-B-per-A mapping on **other MAP files only**, never on the target. Compare against a constant-B baseline trained on the identical files and evaluated on the same covered target positions. Unseen A values count as uncovered. Three training pools: same-family excluding the target, all other families, and all other files.

## Results from 74 privately analyzed MAPs

| Training | Evaluated maps | Covered | Model correct | Baseline correct | Accuracy | Baseline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Same family, excluding target | 73 | 20,513 | 6,920 | 7,029 | 33.73% | 34.27% |
| Other families | 74 | 20,933 | 6,966 | 7,315 | 33.28% | 34.94% |
| All others | 74 | 21,526 | 7,901 | 7,341 | 36.70% | 34.10% |

Same-family metrics: M_MAP 36.33% versus 32.20% baseline; M_IVE 43.46% versus 52.97%; M_KEY 22.95% versus 34.24%. M_SHOW has just one MAP; its 576 test positions were **skipped**, not counted as predictions.

Stage 14's within-file blocked holdout gave 68.29% on covered positions, but these different experiments are diagnostic rather than controlled causal comparisons. Evidence is compatible with *file-specific lookup tables* or local identifiers. It does NOT establish whether the arrays store actual map tiles, graphical data, heights, resources or anything else.

## Tests and usage
Stage 15 includes a metadata-only Python analyzer plus 11 synthetic unit tests. Local combined tests for stages 13–15: 33/33 passed; C++ CTest 1/1 passed. All 74 original MAP files processed locally. No original media has been published.

Run privately using Python module tools.saturn_map_cross_transfer with the local Track 1 BIN path and optional --output to write count-only JSON.

The devkitPro/libnx toolchain is not installed in the current runtime; Nintendo Switch NRO and NeXium tests remain unverified. Next: identify local A/B index meanings through independent Saturn runtime visuals and confirm first-battle geometry before writing a real importer.
