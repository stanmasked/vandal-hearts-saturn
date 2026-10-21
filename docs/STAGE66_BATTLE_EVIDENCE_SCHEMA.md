# Stage66 — provenance-linked first-battle observation manifest

## Purpose
Stages 09–16 tested several candidate structures inside the 74 privately held
MAP files, but their meanings remain unverified. In particular, candidate
28×64 BE16 regions must not be promoted to terrain or coordinates based on
statistical association alone. Stage66 creates an evidence intake contract so
observed Saturn runtime facts can be separated from guesses.

## Manifest format
`tools/saturn_battle_evidence.py` validates a user-authored JSON manifest with:
- source/version label and capture method;
- scene dimensions and explicit grid-coordinate convention;
- cells with nullable terrain, elevation, traversal and movement cost;
- units with nullable class/HP/movement values;
- turns/actions and observations linked to evidence IDs;
- confidence labels: observed, inferred, uncertain or unknown.

Unknown fields are allowed and counted. The validator rejects out-of-bounds
coordinates, duplicate cells/IDs, broken evidence references, impossible HP
bounds, unsafe artifact references and invalid action/unit references. Possible
unit overlaps are reported as warnings, not silently rewritten.

## Privacy and source boundaries
The evidence manifest contains only structured, user-authored observations.
It uses opaque `private-ref:ID` evidence references instead of filesystem paths
or URLs. The optional summary excludes claims, artifact references, paths,
screenshots, video, audio, extracted bytes and hashes. CI tests use only a
synthetic 3×3 fixture; no authentic Saturn observations are fabricated.

## Verification
Run:
```bash
python3 -m unittest tests.test_saturn_battle_evidence -v
python3 -m tools.saturn_battle_evidence /private/first-battle-observations.json \
  --summary /private/first-battle-validation.json
```

A valid manifest is not evidence that the data is authentic by itself. Each
important coordinate, terrain value, unit parameter and action still needs
independent support from controlled Saturn captures or reproducible runtime
observations. The supplied English v1.1 translation-patched image remains
distinct from an authenticated unpatched Japanese master.
