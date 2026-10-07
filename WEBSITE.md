# Zoomer3D website

The website is plain HTML, CSS and JavaScript in `docs/`. It includes the original images, video and downloadable files. It needs no build step, server backend, ChatGPT account or ChatGPT hosting service. Fonts load from Google Fonts, as they do on the original website.

Preview it from the repository root:

```sh
python3 scripts/preview_website.py
```

Open <http://127.0.0.1:8794/>. The preview server supports byte ranges for video seeking. Use an HTTP server or GitHub Pages so the drawing editor can load its example JSON.

Run the file checks:

```sh
python3 scripts/validate_website.py
```

The drawing editor supports four marker colors, pointer and keyboard drawing, undo, clear, replay, JSON import and export, and a browser draft. Training runs in the downloaded local simulator, as on the original website. Drafts are stored per website origin, so an existing draft on the old site can be transferred with JSON export and import.

The GitHub Actions workflow publishes `docs/` when `main` changes. After the intended repository is verified, select GitHub Actions as the source in its Pages settings. The deployment job supplies the live URL. Publication has not yet been completed.

The export came from the original Site's version 9, source commit `b296b446e77055809638362b8dee912557438fc9`. The original is <https://zoomer3d.dgdg17291346462nk.chatgpt.site/>. HTML changes remove the two metadata URLs pointing at that host. The visible content, styles, scripts and assets are preserved. `website-source-manifest.json` records their SHA-256 hashes.
