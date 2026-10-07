# Blender maintenance, September 28, 2026

Blender was updated from 4.5.3 to 4.5.14 LTS, within the same release series. The active application remains at `/Users/dgoldenh/Applications/Blender.app`. The previous version is available at `/Users/dgoldenh/Applications/Blender 4.5.3 backup.app`.

The installer came from [Blender's official mirror](https://mirror.blender.org/release/Blender4.5/blender-4.5.14-macos-arm64.dmg). Its SHA-256 matched the [published checksum](https://mirror.blender.org/release/Blender4.5/blender-4.5.14.sha256). The application passed the macOS signature check and was accepted as a notarized release from Stichting Blender Foundation.

## Crash diagnosis

The crash recorded at 17:34 on September 28 occurred in `supports_barycentric_whitelist` and `MTLBackend::metal_is_supported` during Blender startup. The report had no Python backtrace. Blender had not loaded the Zoomer model or run its build script.

That launch ran inside the restricted automation environment. Subsequent launches of the same 4.5.3 binary completed outside it. This points to restricted access during graphics-device detection. It does not establish that the update alone fixes the crash.

Future automated Blender jobs use the approved execution path outside that restriction, with factory startup settings and CPU rendering. The repository's `AGENTS.md` records this requirement. Normal desktop launches continue to use the user's preferences. No macOS security settings were changed.

## Verification

The updated application launched normally on the desktop and displayed the modular model in its camera view. A separate background check opened `assets/zoomer_modular.blend`, evaluated all three joint controls at 15 degrees, restored their neutral positions and rendered the model with Cycles on CPU.

- Blender reported version 4.5.14 LTS.
- The model contained 34 mesh objects and the expected head and shoulder controls.
- The 640 by 800 pixel render completed and Blender exited with status zero.
- The saved model's SHA-256 was unchanged after the check.

The [check results](update_check.json), [render log](update_check.log) and [test image](update_render.png) record the run. This verifies startup, model loading, controls and rendering in the tested configuration. It is not a claim that Blender cannot crash under other workloads.

To roll back, quit Blender and exchange the active and backup application names in Finder. Keep the current version under another name so both remain available. The model files do not need conversion.
