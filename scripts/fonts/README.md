# Fonts

`scripts/build.py` subsets these files and embeds them in the SVGs under `assets/`.
GitHub loads those SVGs as images, which cannot fetch a font from the network, so the
subset travels inside the file.

These are not the faces used by the profile this design was inspired by. That set
(Bricolage Grotesque, Work Sans, DM Mono) is also under the SIL Open Font License,
which would allow reuse. This profile uses a different trio so the cards are not a reskin.

All three families are licensed under the [SIL Open Font License 1.1](https://openfontlicense.org).
The full license text ships next to each family. Do not sell the font files on their own.

| File | Family | Weight | Copyright |
| --- | --- | --- | --- |
| `Oxanium-wght.ttf` | [Oxanium](https://fonts.google.com/specimen/Oxanium) | variable, instanced at 500 and 700 | Copyright 2019 The Oxanium Project Authors |
| `Sora-wght.ttf` | [Sora](https://fonts.google.com/specimen/Sora) | variable, instanced at 400 and 600 | Copyright 2019 The Sora Project Authors |
| `JetBrainsMono-Medium.ttf` | [JetBrains Mono](https://www.jetbrains.com/lp/mono/) | 500 | Copyright 2020 The JetBrains Mono Project Authors |

| License file | Family |
| --- | --- |
| `OFL-Oxanium.txt` | Oxanium |
| `OFL-Sora.txt` | Sora |
| `OFL-JetBrainsMono.txt` | JetBrains Mono |
