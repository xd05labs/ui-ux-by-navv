# Visual question samples

Twelve comparison sheets cover the eleven questions in `wizard/uiux-flow.json` and the expanded style menu. PNG images are the portable chat previews; matching HTML files are self-contained browser sources. All sample content is synthetic and drawn with code. No third-party photos, logos, external fonts or model calls are included.

Options are generated in the same order as the conversation menus. Curated choices use letters; the all-style expansion uses numbers. Examples illustrate directions rather than guaranteeing the generated application's appearance. Motion/video/image/3D concepts are labeled honestly in their captions.

Edit `appforge/uiux_samples.py`, the question flow or the catalogs, then run:

```sh
python scripts/build_uiux_samples.py --render
python scripts/build_ai_start.py
python scripts/check_repository.py
```

Rendering requires the optional Playwright dependency and Chromium (`requirements-dev.txt`). Regular checks and core usage require only Python. The manifest binds PNG hashes and dimensions to the current HTML sources and menu option mapping. Cross-platform font rendering may differ when intentionally regenerating images; byte-identical browser rasterization is not required for integrity checks.
