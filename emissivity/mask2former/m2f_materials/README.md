# emissivity/mask2former/m2f_materials/ (package)

Imported by `../classify_session_m2f.py`. No CLI.

| Module | What |
|---|---|
| `segmentation_m2f.py` | `load_model` (`AutoImageProcessor` + `Mask2FormerForUniversalSegmentation`, default `facebook/mask2former-swin-large-ade-semantic`; transformers needs **torchvision** for the processor) and the forward pass, returning connected regions with ADE label and `ade_confidence`. |
| `category_prior.py` | Reads and validates `../ade_material_prior.csv` against the emissivity table, the checkpoint labels and `zones.py`; restricts and renormalises CLIP's ranking per ADE class. |
| `crops.py` | What CLIP is shown: `bbox` (default, measured best), `masked`, `texture`. |
