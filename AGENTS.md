# Blender on this Mac

The Blender executable is `/Users/dgoldenh/Applications/Blender.app/Contents/MacOS/Blender`.

Run Blender background jobs with an approved `exec_command` using `sandbox_permissions: "require_escalated"`. Restricted execution crashed Blender 4.5.3 during Metal device detection, before the project script ran. CPU rendering still passes through that startup code. Do not retry the same restricted launch after this failure.

Use `--background --factory-startup` before the input file and `--python-exit-code 1` before a Python script. These flags keep automated runs independent of personal startup settings and report script errors to the caller. Keep Cycles rendering on CPU for the Zoomer inspection renders.

Blender 4.5.14 LTS passed the model load, joint-control and render checks on September 28, 2026. See [the maintenance record](diagnostics/blender/README.md). Preserve existing model files when testing application updates.
