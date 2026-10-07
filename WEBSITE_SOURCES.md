# Zoomer3D sources

The four notebook scans and two finished-print photographs were supplied by the owner. The owner clarified that the body in the finished-print photographs is metallic silver. The owner states that the drawings were made in 1991 at age 13, and that GPT-6 Astra was used to develop the printable model and generate the printer files. On October 5, 2026, the owner confirmed that the cover shown in the photographs is the faceted printed PETG cover.

Body dimensions, joints, orientations, assembly steps and baseline settings come from `print/modular/PRINTING.md` and the embedded configurations in the XL projects. The five-color v2 project's settings differ from the baseline and are identified separately on the site.

The dome history comes from `README.md`, `print/vase_dome/PRINTING.md`, and `print/flat_window_domes/PRINTING.md`. Older notes about the faceted cover being unprinted are superseded by the owner's new photographs and confirmation. The sheet-window alternative is described as another option without a claim that it was printed.

The owner supplied `IMG_3064.JPEG` to illustrate several attempts at a more transparent head cover. It is included unchanged as `docs/assets/head-cover-attempts.jpg`.

The head-cover section uses the existing faceted-cover 3D render to identify the final design. Its numbered history ends at the faceted cover; the sheet-window design is a separate optional alternative.

The site is a static exhibit with local image and download assets. It contains no credentials or analytics. Original repository files and source photographs are preserved.

## Assembly and drawing additions

The exploded robot, cap underside and adapter views were rendered from the existing faceted-cover Blender scene on CPU. The original model files were not saved or changed. Existing cover and articulated-robot renders come from the repository.

Training metrics and programmed-versus-learned descriptions were checked against `simulation/TRAINING.md`, `training/zoomer_readable/status.json` and the recorded run metadata. The website drawing editor preserves the existing target schema and exports JSON for the local MuJoCo app. Training runs locally, not in the hosted page. The packaged MP4 is the existing 202.12-second recorded run.

The six-frame collage contains direct JPEG extractions from that packaged MP4. Captions use video playback times, not simulation time. Exact frame times and the source path are saved in `docs/assets/drawing-stills/frames.json`.
