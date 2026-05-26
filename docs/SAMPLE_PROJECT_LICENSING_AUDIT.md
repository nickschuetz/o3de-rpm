# O3DE community sample project asset licensing review

**Review date:** 2026-05-26.
**Scope:** asset-side licensing for the two community sample projects most commonly exercised end-to-end on Linux: MultiplayerSample (MPS) and NewspaperDeliveryGame.
**Engine code:** both samples are Apache-2.0 OR MIT (matches upstream O3DE). The findings here are entirely about non-code assets (3D models, image textures, motion files, audio, VFX).

## Summary

The two samples have substantially different licensing postures:

- **MultiplayerSample** has explicit per-cluster license declarations. The asset-side repository ships a top-level `LICENSE-CC-BY-NC-4.0.txt` covering "3D models, image textures, and other asset files" by reference, and the project repo's `credits.md` separately calls out four third-party contributors (Adobe Y-Bot, KitBash3D High Tech Streets, Hexany Audio, PopcornFX) under "Special Thanks for contributing" rather than under an open-source license. The Kevin MacLeod music tracks are CC-BY-4.0.
- **NewspaperDeliveryGame** has no asset-side license declaration at all. There is no `credits.md`, no per-asset license files, and the project-root `LICENSE.txt` covers only the engine-code component with boilerplate "third party components have their own terms" language. Asset filename patterns strongly indicate Adobe Mixamo origin for the character and motion files, but the repository does not document this.

Both samples build and run on Fedora 44 against the installed engine; the question this review addresses is what's known about asset provenance and redistribution terms.

## Evidence levels

- **CONFIRMED** -- direct evidence in the repository: a license file, a `credits.md` statement, an explicit directory name, or a filename uniquely identifying the source.
- **INFERRED** -- strong contextual evidence (naming patterns matching known catalogs, file structure consistent with known sources) without an explicit upstream statement.
- **UNCLEAR** -- the repository alone is insufficient to determine; upstream clarification needed.

---

## MultiplayerSample (MPS)

Two repositories in scope: `o3de/o3de-multiplayersample` (project code, sounds, level config) and `o3de/o3de-multiplayersample-assets` (3D assets organized into per-cluster gems).

### Asset-side license declaration

**CONFIRMED** -- `o3de-multiplayersample-assets/LICENSE-CC-BY-NC-4.0.txt`, verbatim:

> Copyright 2022 Amazon.com, Inc. or its affiliates, all rights reserved.
>
> 3D models, image textures, and other asset files are licensed under a Creative Commons Attribution-NonCommercial 4.0 International License, available at http://creativecommons.org/licenses/by-nc/4.0/.

CC-BY-NC-4.0 is a Non-Commercial license. The "NC" restriction prohibits commercial use of derivative works without separate permission. Anyone considering MPS-derived work for a commercial release needs to either negotiate alternative terms with Amazon or replace the encumbered assets.

The asset repo also ships `LICENSE-CC-BY-4.0.txt`, `LICENSE_APACHE2.TXT`, and `LICENSE_MIT.TXT` files at the same level, presumably for the other content categories (music, code, etc.), but the per-asset mapping to which file applies is not documented in either repo.

### Third-party contributed assets

**CONFIRMED** -- `o3de-multiplayersample/credits.md` (2305 release block, still current on `development`):

> ## Special Thanks
>
> * Adobe for contributing the Y-Bot character model and its animations.
> * KitBash3D for contributing the High Tech Streets set.
> * Hexany Audio & Owen Cooper for creating the game's audio.
> * PopcornFX for creating the game's VFX.

**CONFIRMED** these assets are physically present in the asset repo, in directories named after their contributing source:

| Source | Directory | Size | File count |
|---|---|---|---|
| Adobe Mixamo Y-Bot | `o3de-multiplayersample-assets/Gems/character_mps/Assets/Mixamo/Ybot/` | 794 MB | 198 |
| KitBash3D High Tech Streets | `o3de-multiplayersample-assets/Gems/kb3d_mps/` (includes a `.src` subdirectory with the Maya source `.mb` files) | 1008 MB | 579 |
| Hexany Audio | `o3de-multiplayersample/Sounds/wwise_project/Originals/SFX/Hexany/` and adjacent | (audio cluster) | (multiple `.wav`) |

The Maya `.mb` source files for KitBash3D content are notable: the arrangement was sufficient for upstream to host source-of-truth files, not just baked exports.

The "Special Thanks for contributing" framing is distinct from an open-source license grant. None of the four contributors have published a license attached to their contribution as part of the o3de-multiplayersample repos. KitBash3D's standard commercial-asset-pack licensing typically allows use of the assets in customer projects but does not grant the customer redistribution rights for the assets as a standalone library; the publicly-stated tiers should be consulted directly. Adobe Mixamo terms similarly grant use within projects without granting third-party redistribution. Anyone reviewing for redistribution should check the current terms with each contributor.

These terms shape what kind of work derived from MPS can be distributed and under what conditions.

### Music tracks

**CONFIRMED** -- `credits.md` Music section:

> "Rocket", "Beauty Flow", "Future Gladiator" Kevin MacLeod (incompetech.com)
> Licensed under Creative Commons: By Attribution 4.0 License
> http://creativecommons.org/licenses/by/4.0/

The three Kevin MacLeod tracks are present as `.wav` files in `o3de-multiplayersample/Sounds/wwise_project/Originals/SFX/`. CC-BY-4.0 is one of the more permissively-licensed asset categories in MPS, allowing commercial use with attribution.

### PopcornFX VFX

**UNCLEAR** -- `o3de-multiplayersample/PopcornFX/` directory currently contains `.pkfx` particle effect files including `Straight_Shot_Effect.pkfx`, `SpaceSoldiers_Gun_Impact.pkfx`, `VFX_SpeedPowerUp.pkfx`, `FX_JumpPad.pkfx`, and more. The `credits.md` "Special Thanks" line cites PopcornFX as a VFX contributor.

A downstream note (in the o3de-rpm scratchpad) recorded that PR #499 removed PopcornFX VFX. The `.pkfx` files being currently present suggests one of: the removal didn't merge, it removed a different scope, it was reverted, or the note was inaccurate. Upstream clarification would resolve this and the broader question of whether MPS still depends on the PopcornFX runtime at all.

### Engine + scripted content

**CONFIRMED** -- `o3de-multiplayersample/LICENSE.txt`, `LICENSE_APACHE2.TXT`, `LICENSE_MIT.TXT` confirm the engine-code and project-script components are Apache-2.0 OR MIT.

### MPS summary

The asset-licensing posture is documented in the repository. CC-BY-NC-4.0 covers the bulk of 3D content. Specific third-party contributed clusters (Adobe Mixamo, KitBash3D, Hexany, PopcornFX) are credited but not under an open license. Kevin MacLeod music is CC-BY-4.0. Engine code and project scripts are Apache-2.0/MIT.

---

## NewspaperDeliveryGame

Single repository at `o3de/NewspaperDeliveryGame`.

### Asset-side license declaration

**CONFIRMED** -- no `credits.md` file exists at the repository root. The only license-touching files at the project root are `LICENSE.txt`, `LICENSE_APACHE2.TXT`, `LICENSE_MIT.TXT`. The `LICENSE.txt` is the standard upstream O3DE boilerplate covering engine code; it includes a "THIRD PARTY COMPONENTS" section that says "It is your responsibility to comply with the applicable licenses" but does NOT list specific third-party assets contributed to this project.

**UNCLEAR** -- without a `credits.md` or comparable asset-license disclosure, the asset provenance of this project is not documented in the repository. The repository contains 41 `.fbx` mesh / motion files, 60 `.png` textures, 159 `.material` files, plus a smattering of `.jpg`, `.font`, `.uicanvas`. None carry per-file license disclosures.

### Mixamo-pattern character + motion evidence

**INFERRED** -- the motion files in `Assets/Motions/` have names consistent with Adobe Mixamo's published motion catalog naming:

```
Fast Run.fbx       Happy Idle.fbx     Jump.fbx
Left Strafe.fbx    Left Strafe Walking.fbx
Right Strafe.fbx   Right Strafe Walking.fbx
Throw.fbx          Walking.fbx
```

These names match the display-name pattern Mixamo uses (Mixamo's web UI presents motions with display names that default-name the downloaded `.fbx`). They are also names that could occur in other motion libraries; the inference is suggestive, not definitive.

**INFERRED** -- `Assets/Actors/Paper_Kid_jer_walk_Jerrey.material` contains the substring `Jerrey` and the `jer_walk` infix. This naming pattern is consistent with workflows where a Mixamo-derived rig is renamed or paired with a custom character label, but "Jerrey" does not match a known Mixamo preset character name list, so the strongest claim available is "consistent with Mixamo workflow," not a definitive identifier.

The two character `.fbx` files (`Paper_Kid.fbx`, `Newsman.fbx`) ship alongside `.motionset` + `.animgraph` companions whose structure is consistent with Mixamo-rigged characters, but they are not matched to a specific Mixamo catalog entry by name.

Adobe Mixamo's publicly-stated licensing terms generally allow use of Mixamo content within projects but do not grant third-party redistribution rights for the Mixamo content itself; specific terms should be consulted directly.

### Neighborhood / environment assets

**UNCLEAR** -- `Assets/Neighborhood/` contains assets named `Hills.fbx`, `Fence.fbx`, `HouseOne.fbx` through `HouseFour.fbx` (plus `_Dark` variants), and `HouseThree.fbx`, with no clear source attribution in filenames. Without a credits.md, the audit can't determine whether these are original O3DE-team work (Apache-2.0/MIT-eligible) or sourced from a stock asset library.

### NewspaperDeliveryGame summary

Asset-licensing posture is undocumented in the repository. Character + motion content has filename patterns consistent with Adobe Mixamo workflow (not definitive); environment content provenance is unknown without upstream input. Adding a `credits.md` matching the MPS pattern would close the documentation gap.

---

## Outstanding questions worth resolving upstream

1. **MPS CC-BY-NC-4.0 status.** The license file is dated 2022. Is there context on the choice, and is it open to revisiting (or is this the canonical current position)?
2. **MPS PopcornFX status.** Were the `.pkfx` files supposed to be removed (per a downstream-recorded PR #499)? They are currently present in `o3de-multiplayersample/PopcornFX/`. Clarifying this also clarifies whether MPS still depends on the PopcornFX runtime at all.
3. **NewspaperDeliveryGame asset provenance.** A `credits.md` declaring the source and licensing of the character + motions and the neighborhood environment assets would document what's currently undocumented.
4. **Per-license mapping in the MPS assets repo.** The asset repo ships CC-BY-NC-4.0, CC-BY-4.0, Apache-2.0, and MIT license files at the same level. A short note mapping which file applies to which content cluster (e.g., "all `.fbx` and `.png` under `Gems/character_mps` → CC-BY-NC-4.0; all audio under `Sounds/.../Hexany/` → see contributor agreement; ...") would make per-cluster licensing self-evident from the repo.

---

## Cross-references

- Engine + sample license file paths in this document are absolute against locally-cloned working trees at the audit date; the same files exist at the same relative paths in the upstream GitHub repos.
- Test infrastructure that exercises these samples end-to-end: `tests/multiplayersample-build-test.sh` (Tier 9) and `tests/newspaper-delivery-build-test.sh` (Tier 10) in the o3de-rpm repository. Both samples are validated as building and running against the installed engine on Fedora 44 as of 2026-05-22.
