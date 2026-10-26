# BT3 PS4 Compat

[Español](README.md)

An ISO9660 inspection/normalization tool and reproducible packaging workflow for investigating **Budokai Tenkaichi 3 mods on Sony's PS2 emulator for PS4**.

**This is not a universal converter.** Anime War vs Dragon Ball AF V2 (2022) was confirmed playable by its user on a PS4 Fat running firmware 13.50 and GoldHEN, including correct graphics and local two-player battles. Other mods and emulator revisions require their own tests.

## What was fixed

In the inspected emulator's DVD branch, the root selector searches sectors 257–999 for the first little-endian word `0x0030`. The original mod has a normal 34-byte `.` directory record (`0x22`), so this selector skips the actual root at sector 259. It finds an accidental match in executable data at sector 340, interpreting 589744 bytes as a directory length.

The normalizer adds 14 zero System Use bytes to directory records and normalizes directory sizes to their existing allocated sectors. The `.` record becomes 48 bytes (`0x30`), allowing the selector to choose **259 / 2048**. Game file data and LBAs remain unchanged. This accommodates a specific emulator heuristic; it does not mean the original ISO was invalid.

Separate graphics corruption was resolved using the entire GS/VU1 profile documented in the Spanish README, including removal of `--vu1=jit-sync`. The evidence supports the combined profile, not a single option as the isolated cause. No controller-code patch was made; the successful two-player session used two active users with one controller each.

## Usage

Python 3.10+, standard library only. On Windows, `py -3` can replace `python`.

```console
python bt3ps4.py inspect "my-mod.iso" --report inspection.json
python bt3ps4.py normalize "my-mod.iso" --output "my-mod-compatible.iso" --report normalization.json
python bt3ps4.py prepare-pkg "my-mod-compatible.iso" --template "my-local-wrapper" --output "build/my-mod" --title-id BTMX00001 --title "My BT3 mod"
python bt3ps4.py build-pkg "build/my-mod/project.gp4" --builder "path/to/my-local-pkg-builder.exe" --output "output/my-mod.pkg"
```

Supply your own ISO, a locally extracted wrapper matching the inspected emulator revision, and a local builder with the `img_create` interface. The project does not download or distribute these dependencies. `prepare-pkg` creates a **standalone full application**, not a patch for another installed title. Choose an unused PS4 Title ID. The original ISO and any existing output are protected from overwrite.

The normalizer verifies every output byte against the exact planned metadata changes. It rejects overlapping extents, insufficient directory capacity, unsupported System Use data, supplementary/Joliet views, earlier false scan markers, and unsupported layouts. It does not move game files or patch the game's executable.

The profile is restricted to emulator `eboot.bin` SHA256:

```text
83b771a27b1ac03802e4071068885658224732a15dedaed67f120307c6e651e7
```

The initial packaging profile recognizes SLUS-21678 and SLUS-21978 metadata. This is not proof that any executable using those IDs is equivalent. Other regions have not been validated. The template's original game-specific diagnostic hooks are omitted from new projects.

## Validation and limits

The tool was run against the real Anime War source ISO and produced the **exact same normalized SHA256** as the earlier successful fix:

```text
Source: 11d91bc29bbc557c30172c6755faa0303c06dd90452dcfdafc0dd17fc602fd60
Output: 0dfee13a6ddb02c04ef07045726e135ee4b9014da3dc337c32e74dc81cc7e52f
```

A new standalone GP4 project was generated and compiled locally. Its embedded ISO, configuration and emulator components were audited against the prepared files. **This newly generated package has not been run on PS4.** The hardware confirmation belongs to the earlier local 01.03 package. See [the documented case](docs/ANIME-WAR.md) and [tool validation](docs/VALIDACION-HERRAMIENTA.md).

## Tests

```console
python -m unittest discover -s tests -v
```

16 tests use small synthetic images and metadata, requiring no games or emulator. A Windows/Linux CI workflow is included; remote CI results do not exist until the repository is published and the workflow runs.

To report another mod, provide its name/version, source/output hashes, PS2 ID, PS4 model/firmware, emulator hash, normalization report and actual battle/graphics/controller observations. Do not attach games or emulator binaries. See [the compatibility record](docs/COMPATIBILIDAD.md).

Only original tool code, documentation and synthetic tests are distributed, under MIT. No ISO, Sony executable, BIOS/ROM, SDK, game artwork or PKG is included. The technique was developed by comparing with a locally working BT4 wrapper; this project does not redistribute or claim authorship of that team's work. No affiliation with Sony, Bandai Namco or mod teams.
