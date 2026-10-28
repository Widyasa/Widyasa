# Regenerating the profile cards

The SVG cards in `assets/` (everything except the Pac-Man graphs) are generated.
Edit the **DATA** block in `build.py` — projects, inventory, side quests, links —
then rebuild:

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/build.py
```

`build.py` uses only Python plus `fonttools` and `brotli` (to subset and embed
the OFL fonts in `scripts/fonts/`). It writes both light and dark SVGs and
refreshes `README.md`.

After a visual change, bump `VERSION` in `build.py` (`?v=1` → `?v=2`) so GitHub
does not keep a cached image.

The generator refuses to run if body text falls below a 4.5:1 contrast ratio,
or if a line is wider than its card. Shorten the copy and run it again.

## Pac-Man contribution graph

`assets/pacman-contribution-graph.svg` and `assets/pacman-contribution-graph-dark.svg`
are not produced by `build.py`. Refresh them with:

```powershell
scripts/generate-pacman.ps1
```

That script shells out to `pacman-contribution-graph` and overwrites only those two files.

## Fonts

See `scripts/fonts/README.md`. Oxanium, Sora, and JetBrains Mono are SIL Open Font
License 1.1. The license files live beside the fonts.
