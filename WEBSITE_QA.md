# Website export verification

Verified on October 6, 2026 against <https://zoomer3d.dgdg17291346462nk.chatgpt.site/>. The local source is `/Users/dgoldenh/Documents/GitHub/zoomer3D/website`, commit `b296b446e77055809638362b8dee912557438fc9`, published as version 9.

The live HTML matches that source apart from an injected Cloudflare hosting script. The export reuses the saved source, removes the original host's canonical and Open Graph URLs, and adds a `.nojekyll` marker. No visible copy, styles, application scripts, images, video or downloads changed. The 54 files other than `index.html` match the original SHA-256 hashes.

## Appearance

Full-page screenshots were compared at these viewport sizes. All nine sections had identical coordinates and heights, with no horizontal overflow or missing images.

| Viewport | Result |
| --- | --- |
| 1440 × 1000 | More than 99.99% of pixels match. Differences occur only in the native video's animated buffering indicator. |
| 768 × 1024 | More than 99.99% of pixels match. Differences occur only in the native video's animated buffering indicator. |
| 390 × 844 | Pixel-identical full-page screenshots. |
| 320 × 780 | Pixel-identical full-page screenshots. |

The recorded-example drawing editor screenshots are pixel-identical at 1440 and 390 pixels wide. The desktop hero and mobile editor were also visually inspected.

## Interactions and files

The same checks passed on the original and export at desktop and mobile widths:

- All eight ribbon links, sticky-header anchor clearance, and back/forward navigation.
- Image links opening in another tab and same-tab image navigation followed by Back.
- Opening and restoring all six visible expandable sections, including the default-open settings table.
- Loading the 19-stroke example, replaying strokes and cancelling replay with Undo.
- Four marker colors in order, keyboard drawing, pointer drawing, Undo and Clear.
- JSON export with the selected name and tolerance, reload persistence, and JSON import/export round trip.
- Error messages for malformed JSON and invalid target data, preserving the current drawing.
- Real mobile touch events creating a red stroke with two points.
- No JavaScript errors during the interaction checks.

The original and export both load the 202.12-second MP4 and expose native controls. Playback advanced on both. On the export's range-capable static preview, playback reached 39.36 seconds, paused, and sought to 199 seconds successfully. The preview returned HTTP 206 for a byte-range request. A simple Python HTTP server without byte-range support reset seeking to zero; the included preview script supports ranges.

All 56 public files returned HTTP 200 with matching SHA-256 hashes, including ZIP, MP4, BLEND, 3MF and PDF downloads. The validator checked two HTML pages, 114 local references and anchors, ZIP integrity, and agreement between the archived and public printing guide. Both JavaScript files passed syntax checks. The preview and validator passed Python syntax checks.

The Pages workflow uses the checkout, configure-pages, upload-pages-artifact and deploy-pages actions listed in [GitHub's workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). Its source directory is `docs/`, with a validation step before upload.

## Publication status

The local Zoomer3D repository has no remote. The authenticated GitHub connector identifies `dgoldenholz`; searches find the older `dgoldenholz/zoomer` repository, while `dgoldenholz/zoomer3D` is unavailable. The intended target remains unconfirmed. No remote write was attempted.

GitHub CLI is signed out. Computer control reports that the Mac is locked, which prevents using GitHub Desktop or an authenticated browser. No push, remote commit verification, CI run, Pages activation or live GitHub URL has been completed.

The export needs no ChatGPT service. Google Fonts remains an external font dependency, matching the original. Browser drafts are scoped to each website origin and can be transferred through JSON export/import. MuJoCo training continues to run in the downloaded local simulator, as on the original site.

Browser logs, source/export screenshots, pixel comparisons and HTTP results are saved in the task workspace's `output/playwright/` directory. The original project and nested website checkout were left unchanged.
