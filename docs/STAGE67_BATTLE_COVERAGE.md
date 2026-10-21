# Stage67 — first-battle reference coverage gate

## What the gate answers
This stage measures whether a locally authored battle observation manifest is
*filled in sufficiently for a later human source review*. It is **not** a
truth/authenticity oracle and does not recreate any Saturn battle on Switch.

The gate accepts the Stage66 evidence schema. A pass requires:
- a syntactically valid manifest and an observed 128x128-or-smaller scene grid;
- a complete rectangular set of cells with observed terrain, elevation,
  cost, walkability and at least one evidence ID on every cell;
- an observed non-overlapping ally/enemy roster with HP, max HP, movement
  budget and evidence, located on confirmed traversable cells;
- observed movement, attack, turn-order and a terminal victory/defeat outcome;
- an ordered turn/action trace with both move and attack events, actor IDs,
  side-consistent actions, identified attack targets and evidence references.

A fail returns stable blocker codes and aggregate counts to guide further
private research. Missing values do not become invented defaults. Importantly,
`coverage_complete` **never** asserts the image is genuine, that the original
Japanese release is equivalent to the English v1.1 patch, or that native
C++ mechanics reproduce the battle.

## Privacy and reproduction
The report never echoes scene name, user-authored claims, resource names,
evidence references, private file paths, screenshots or source bytes.
The script reads only the private Stage66 JSON manifest. Unit tests use
a small, entirely invented 2x2 scene.

```bash
python3 -m unittest discover -s tests -p 'test_saturn_battle_coverage.py' -v
python3 -m tools.saturn_battle_coverage /private/first-battle.json \
  --output /private/coverage.json
```

Next milestone: actual independent Sega Saturn gameplay evidence and verified
relationships between map/event/program resources, tracked in Issue #11.
