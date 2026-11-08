# Omega Guns

A **TACZ (Timeless and Classics Zero) addon gunpack** for Minecraft 1.20.1 with 12 original futuristic precision rifles,
7 custom ammo types and 15 attachments. All guns appear in the TACZ **Sniper** creative tab.

## Install (two ways)
**As a mod (Forge 1.20.1):** build the jar (`gradle build`, or download it from the GitHub Actions run) and put
`omega_guns-1.0.0.jar` in your `mods/` folder next to TACZ.

**As a plain gunpack:** run `python tools/build_zip.py`, then put `dist/omega_guns_gunpack.zip`, unextracted,
in `.minecraft/tacz/`. Use one way or the other, not both.

## Guns (each has its own ammo, action and stats)
| Gun | Ammo | Action |
|---|---|---|
| Vanta SR-9 | APX .338 Match | Bolt |
| Aegis RS-1 Railshot | Gauss Slug | Semi |
| Specter DMR | DMR 7.62 Hybrid | Semi |
| Helios Lancer | Plasma Cell | Semi |
| Kestrel-X (bullpup) | DMR 7.62 Hybrid | Bolt |
| Titan Breaker | HV .50 Penetrator | Semi |
| Nyx-S Whisper (integral suppressor) | Subsonic .300 Quiet | Bolt |
| Orion ARC-3 | Flechette Mag Round | 3-round burst |
| Valkyrie Mk2 | Gauss Slug | Semi |
| Reaper LB-50 | APX .338 Match | Bolt |
| Zenith ZR-4 | Plasma Cell | Semi (open bolt) |
| Cobalt Ranger | DMR 7.62 Hybrid | Semi |

Bullets are real projectiles with travel time and drop. There is **no lock-on or auto-hit**: you have to aim.

## Attachments
Scopes (1.25x holo, 4x, 8x, 4-12x variable, 6x thermal), muzzle (suppressor, brake, compensator),
grips (vertical, angled), tactical stock, laser module, extended mags I-III.

## Get items with commands
```
/give @p tacz:modern_kinetic_gun{GunId:"omega_guns:vanta_sr9"}
/give @p tacz:ammo{AmmoId:"omega_guns:apx_338"} 64
/give @p tacz:attachment{AttachmentId:"omega_guns:scope_8x"}
```

## How this repo works
The repo stores the generator, not the generated files. `tools/generate_pack.py` creates the whole gunpack
(JSON, models, textures) into `src/main/resources/assets/tacz/custom/omega_guns/`, and GitHub Actions runs it for you.
To get the files locally, run `python tools/generate_pack.py`.

## Build from source
```
python tools/generate_pack.py   # regenerates the gunpack (JSON, models, textures)
python tools/build_zip.py       # creates dist/omega_guns_gunpack.zip
gradle build                    # creates build/libs/omega_guns-1.0.0.jar (needs JDK 17, Gradle 8.5)
```
Edit the `GUNS`, `AMMO` and `ATTACHMENTS` tables in `tools/generate_pack.py` to add or retune content.

## Repo layout
```
.github/workflows/build.yml     CI: builds the jar and the gunpack zip
src/main/java/                  tiny Forge mod entry class
src/main/resources/
  META-INF/mods.toml, pack.mcmeta
  assets/tacz/custom/omega_guns/   the gunpack (meta, assets, data)
tools/                          generator + zip builder
build.gradle, gradle.properties, settings.gradle
```

## Known limitations
- Models are procedurally generated blocky bedrock models with palette textures. Open the files in
  `geo_models` in Blockbench to hand-sculpt and repaint them for true hyper-realism.
- Uses TACZ's default rifle animations. No custom sounds are included; add some under
  `assets/omega_guns/tacz_sounds/` in the pack folder and reference them in each `*_display.json`.
- Written against the TACZ 1.20.1 gunpack format. If a field is rejected by your TACZ version, check the game log
  and compare with the official TACZ gunpack docs.

Not affiliated with TACZ or Mojang.
