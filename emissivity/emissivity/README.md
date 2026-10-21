# emissivity/emissivity/ (package)

Library imported by `../classify_session.py`, `../mask2former/classify_session_m2f.py`,
`../../radiometric_correction/correct_session.py` (`EmissivityTable` only) and, by file
path, `../voxel_consensus.py` (`zones.py` only). No CLI.

| Module | What |
|---|---|
| `table.py` | `EmissivityTable`: loads `../emissivity_table.csv` (pandas), lookup by material. |
| `classifier.py` | `MaterialClassifier`: CLIP zero-shot over the table prompts (`classify`, `classify_batch`). torch/transformers are imported lazily, so the package imports in the light env. |
| `segmentation.py` | SLIC superpixels (scikit-image) and SAM masks (`facebook/sam-vit-base`), plus `segment_boxes`. |
| `zones.py` | Geometric prior: `zone_of` (floor/ceiling/vertical from the bbox shape), `ZONE_CANDIDATES`, `restrict_ranking`. No imports. |
| `sources.py` | Live frame grabbers (`ImageSource`, `WebcamSource`, `ZedSource`, `ZedUvcSource`). No current caller; kept because `__init__.py` exports them. |

The folder is named like its parent (`emissivity/emissivity/`). Scripts put the parent
`emissivity/` on `sys.path`, and `import emissivity` resolves to this package (a regular
package takes precedence over the namespace directory). This was checked in a fresh venv.
