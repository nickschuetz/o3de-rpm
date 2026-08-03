# Follow-ups & state-of-play

End-of-day capture: what landed, what's pending, what's loaded for next session.

This file is intentionally a living scratchpad. Entries get added or removed as work progresses. Promote anything tracker-worthy to `FEDORA_ROADMAP.md`, a GitHub issue, or a memory note. Anything below that's gone stale by the time you read it can be deleted.

---

## monolithic PROMOTED to o3de-development (2026-08-03)

DONE (Nick's go): all 3 o3de-development chroots flipped via `edit-chroot --rpmbuild-with 'development_snapshot qt6 monolithic'` (F44 / rawhide / CS10), verified with get-chroot. o3de-development now carries the identical bcond set to o3de-experimental. All three promotion prerequisites were MET beforehand: (1) second green experimental build across a dev-tip movement (10780077), (2) meshoptimizer fix validated on real COPR builders, (3) upstream issue filed as o3de/o3de#19962.

Docs synced in the same pass: README (both the `development` snapshot bullet and the COPR-project bullet now state monolithic + release-export works; `make copr-development` one-liner), Makefile (`copr-development` header comment), and the o3de-development COPR metadata (description.md + instructions.md, pushed live via `scripts/copr-metadata.sh push o3de-development`, verified `monolithic` present in the live API description). Cost carried into every dev build: ~+0.7 GB, ~+1.5 h (proven acceptable, experimental ran the same config green twice under the 8h COPR --timeout with ~1.2h margin).

MADE LIVE: fired the dev build immediately (Nick's call) rather than waiting for the Sunday cron. Build **10808197** to o3de-development (dev tip 6a55279, 2026-08-03, -108, all 3 chroots now with `monolithic`): https://copr.fedorainfracloud.org/coprs/build/10808197 . Submitted `--nowait` (1.96 GB SRPM, avoids the copr-cli upload hang). This is the build that actually ships monolithic to the development channel; until it lands the published o3de-development RPMs are still profile-only. Runs ~6-7h externally, no local notification. Commit a4eeb31 pushed to main.

EXPERIMENTAL RETASK (Nick's call 2026-08-03): retarget o3de-experimental to the **OpenSSL 3.x engine-pin (monolithic)** experiment. SCOPING FINDING before any chroot flip: o3de/o3de `development` still pins `OpenSSL-1.1.1t-rev1-linux` in `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` (verified 2026-08-03 via gh api). #387 bumped the 3p-package-source RECIPE to 3.6.3 but development has NOT rewired its association, so development (and experimental-as-mirror today) still build against 1.1.1t. So the experiment IS genuinely distinct from development: override the OpenSSL association 1.1.1t -> 3.6.3 (the #387 package) in a monolithic build and check clean build + run (probes Jan's 1.1.1-vs-3.x monolithic collision). NOT a chroot flip -- it needs a spec change (patch or bcond redirecting the OpenSSL 3rdParty association) plus confirming the OpenSSL-3.x-rev*-linux package is actually PUBLISHED on the O3DE 3rdParty CDN (name + hash), which #387 merging into the recipe repo does not guarantee. #376 is a separate track (system-OpenSSL for the bundled Python, files under package-system/python/), NOT the engine pin. PLAN PENDING Nick review before touching experimental's chroots (a wrong pin burns a 6-7h build). The Makefile `copr-experimental` header comment still says "the only per-channel difference is the monolithic bcond" -- STALE, reword once the OpenSSL-pin config lands.

## o3de-experimental REALIGNED to development + monolithic (2026-07-22), monolithic proof build running

Decision (Nick, 2026-07-22): stabilization is dead (26050 frozen, no 26100), so o3de-experimental is realigned off its old Stage-1 base (stabilization + all system swaps + swap_hook, idle since 2026-06-05, last green build 10570032 @ snapshot 20260523 / -102) onto **development** (Qt6 forward branch, 26.10-bound). Chosen over stable because stable is a frozen shipped 2605.0 Qt5 tarball (backward-looking, off-purpose for an experimental sandbox), and development matches the config the monolithic work was validated against locally.

DONE: all 3 experimental chroots realigned via edit-chroot to `['development_snapshot', 'qt6', 'monolithic']` (= o3de-development's `['development_snapshot','qt6']` + monolithic). Submitted the dev-snapshot SRPM (o3de2605-2605.0^20260722git9d4f4d2-106, the same one o3de-development uses) to o3de-experimental as build https://copr.fedorainfracloud.org/coprs/build/10768483 to prove the monolithic build on real COPR builders. Watching by ID (COPR is external, no local task notification).

SECOND GREEN across a dev-tip movement 2026-07-27: build 10780077 (snapshot 20260726git2eee29a, -108, DIFFERENT dev tip than 10768483's 9d4f4d2) succeeded on all 3 chroots (F44 6.07h, rawhide 6.19h, CS10 5.90h) WITH the meshoptimizer workaround. Published COPR RPM confirmed to contain lib/Linux/release/libmeshoptimizer.a + ConfigurationTypes_release.cmake, so the meshoptimizer fix is validated on real COPR builders, not just locally. NOTE: the first resubmit attempt (build 10778333) went F44/rawhide GREEN but CS10 RED in ~1min on an unescaped `%install` in the -108 changelog (CS10 rpm 4.19 misparse -> "second %install"); fixed in commit 8784f19 (%%install), which is why 10780077 is the clean 3-chroot green. So two of the three prerequisites for promoting monolithic to o3de-development are now MET: (1) a second green experimental build across a dev-tip movement, (2) meshoptimizer fix validated on COPR. ALL THREE prerequisites now MET: (3) upstream meshoptimizer issue FILED 2026-07-30 as o3de/o3de#19962. So the monolithic -> o3de-development promotion is no longer gated; Nick to decide when to wire the monolithic bcond into development chroots + Makefile.

FIRST GREEN 2026-07-22: build 10768483 succeeded on all 3 chroots (F44 6.82h, rawhide 6.26h, CS10 6.82h; ~6.8h wall-clock, under the 8h --timeout with ~1.2h margin). Experimental RPM confirmed = full development RPM + monolithic: ConfigurationTypes_release.cmake (1) + 196 release/Monolithic/*.a static libs present, AND the functional half intact (60 Qt6 libs, profile Editor binary, 20502 total files). So the monolithic build works on real COPR builders across all 3 chroots, not just locally. ACCEPTANCE: end-to-end release EXPORT test RUN 2026-07-24 against the installed experimental monolithic RPM (HellaTestProject). RESULTS: gate PASSES ("Preparing monolithic build for export", the line that replaced Donnie's "No monolithic artifacts are detected"), the launcher build runs root-free (0 /opt writes, output to project dir) and correctly links the monolithic static libs from /opt/O3DE/26.05.0/lib/Linux/release/Monolithic/*.a. BUT the final launcher LINK FAILS: `ld.lld: error: undefined symbol: meshopt_decodeIndexBuffer / meshopt_decodeVertexBuffer`, referenced by libAtom_RPI.Public.a.

NEW BUG (real, caught only by the end-to-end test, not the artifact-presence check): **the meshoptimizer static lib is not installed into the SDK at all** (0 *meshopt*.a in the install tree; only Findmeshoptimizer.cmake). It builds as build/lib/<cfg>/libmeshoptimizer.a but has no install rule, so Atom_RPI's static archive references meshopt_* symbols with no lib to resolve them at monolithic launcher-link time. Other FetchContent statics DO get installed (lib/Linux/release/libogg.a, libvorbis.a, libminiaudio*.a all present and linked fine), so meshoptimizer is specifically missing. meshoptimizer is one of the deps upstream #19622 (2026-07-16, the same PR that broke CS10 FetchContent) converted to URL-archive FetchContent, so #19622 likely also dropped meshoptimizer's monolithic install rule. LIKELY UPSTREAM (any SDK-based monolithic release export of an Atom-mesh project would hit this), NOT our spec, but needs confirmation against the upstream pre-built SDK's monolithic permutation. ROOT-CAUSED 2026-07-24 (full): meshoptimizer's static lib (libmeshoptimizer.a, present in the build tree at build/lib/<cfg>/) is NEVER installed into the SDK, AND its installer Findmeshoptimizer.cmake is an empty `add_library(meshoptimizer IMPORTED INTERFACE GLOBAL)` stub with no IMPORTED_LOCATION, unlike Findminiaudio/Findogg which have a proper installer branch (`STATIC IMPORTED` + IMPORTED_LOCATION_RELEASE -> lib/Linux/release/lib<name>.a) AND ship their .a. Why profile export works but monolithic doesn't: in the profile/shared build meshoptimizer is statically folded INTO libAtom_RPI.Public.so with hidden visibility (engine uses -fvisibility=hidden), so that .so is self-contained (nm -D shows ZERO meshopt symbols) and the non-monolithic launcher gets meshopt internally. In the monolithic build libAtom_RPI.Public.a instead REFERENCES meshopt externally (nm: 2 undefined meshopt_decode*) and expects a separate libmeshoptimizer.a at launcher-link time, which is not installed -> link fails. NOT introduced by #19622 (its diff only swapped the fetch method GIT->o3de_fetch_content; meshoptimizer never had an installer branch). So this is a PRE-EXISTING UPSTREAM O3DE gap affecting any Linux SDK monolithic release export of an Atom-mesh project, not our spec.

FIX (both, 2026-07-24):
- (a) UPSTREAM issue FILED 2026-07-30 as o3de/o3de#19962 (https://github.com/o3de/o3de/issues/19962): engine should install libmeshoptimizer.a + give Findmeshoptimizer.cmake a STATIC IMPORTED installer branch mirroring Findminiaudio/Findogg. Root mechanism: the source Findmeshoptimizer.cmake ly_install's only its Installer/Findmeshoptimizer.cmake (an empty stub) and NEVER ly_install's the library; miniaudio/ogg ly_install both. Still the empty stub at dev HEAD. Prior-art search returned nothing.
- (b) DOWNSTREAM workaround IMPLEMENTED + VALIDATED, committed bebd7e8 (release -107 -> -108). Monolithic %install now `find build-mono -name libmeshoptimizer.a`, installs it to lib/Linux/release/libmeshoptimizer.a, and overwrites the stub cmake/3rdParty/Findmeshoptimizer.cmake with a STATIC IMPORTED version (mirrors Findogg.cmake). Gated to --with monolithic. VALIDATION 2026-07-24: local rebuild 87fedfb-107 (now the fix is -108) installed, `export-project -cfg release` on HellaTestProject LINKED CLEAN -- built a 182 MB monolithic HellaTestProject.GameLauncher, 0 undefined meshopt symbols in the final binary, EXPORT_EXIT=0, 0 /opt writes (root-free). So a release game export from the monolithic RPM now works end-to-end. Retire the workaround when the upstream fix lands.

CORRECT export invocation (for reruns): `o3de2605-cli export-project -es <script> -pp <proj> -ll INFO -cfg release -noserver -nounified -noassets -out <dir>` -- NOTE -cfg (short) not --config (o3de.py prefix-matches --config to --configure and opens the blocking Tkinter GUI). See [[feedback_export_project_kills_live_editor]].

The "hang" saga that preceded this was NOT a defect: my export invocation used `--config release` which o3de.py argparse prefix-matched to `--configure`, opening the Tkinter settings GUI that blocks in mainloop() (faulthandler stack pinned it); and the export script's real flags are short-form (-cfg, -noserver, -nounified, -noassets, -out), not the --config/--no-*-launcher I guessed. Correct invocation: `export-project -es <script> -pp <proj> -ll INFO -cfg release -noserver -nounified -noassets -out <dir>`. See [[feedback_export_project_kills_live_editor]] (companion gotcha).

HAZARD until fixed: the Makefile `srpm-experimental` / `SRPM_EXPERIMENTAL_FLAGS` still build the OLD stabilization+system-swaps SRPM, which now MISMATCHES the realigned chroots. Do NOT run `make copr-experimental` until srpm-experimental is repointed at the development snapshot (mirror srpm-snapshot-development). Pending once the build proves green: (1) repoint Makefile srpm-experimental/copr-experimental to development+monolithic; (2) update tools/dep-map.yaml + README COPR descriptions + memory project_snapshot_branch (the 8-project layout note) to reflect experimental = development+monolithic, no longer the Stage-1 swap channel; (3) note the swap_hook/system-swap validation is retired from experimental (already validated, filed as o3de#19815). ACCEPTANCE: green on all 3 chroots + ConfigurationTypes_release.cmake / release/Monolithic/ artifacts present in the experimental RPM.

## GAP: RPM ships profile-only, so RELEASE (monolithic) game export fails (raised by Donnie [RKG] in Discord, 2026-07-22)

Donnie hit `[ERROR] root: No monolithic artifacts are detected in the engine installation. Trying to build monolithic without libraries.` when exporting a launcher from Project Manager. Root-caused 2026-07-22 against o3de source + our stable package.

Mechanism (evidence): our RPM builds only `%{_o3de_configs} = profile` (o3de.spec:1432; shared libs). O3DE release export is monolithic and requires the release/monolithic static-lib permutation to be present in the SDK. `export_source_built_project.py:105-110` calls `has_monolithic_artifacts()` (export_project.py:222), which globs `cmake/Platform/Linux/Monolithic/ConfigurationTypes_*.cmake` in the engine root. Our stable package ships ZERO of those (the 31 "Monolithic" files it does ship are gem-template scaffolding under Templates/PrebuiltGem/, not the engine permutation). So release export throws exactly his error.

Donnie's /opt-needs-root framing is the SYMPTOM, not the cause, and his proposed fix (move the SDK out of /opt to a user dir) is WRONG: by default export writes to the PROJECT dir, not the engine install (`default_base_path = ctx.project_path` when not engine-centric; launcher + asset_bundling under project/build/). A working export needs no root. The sudo pain only appears because the missing monolithic libs force a build into read-only /opt. /opt is correct FHS placement; the fix is to SHIP the release/monolithic permutation, not relocate.

Workaround (verified in code, offered to Donnie): export with `--config profile` (which is the CLI DEFAULT, export_project.py:1133). Profile export is non-monolithic, writes to project/build, needs no root and no monolithic libs. Gives a locally-runnable build (good for "see my game run") but NOT a self-contained distributable (that needs monolithic). Donnie was on `release` config (PM export settings) which is the only path that trips the gap.

Is it RPM-specific? YES, our scoping choice, not an upstream export bug. The export code comment states a complete SDK produces "profile shared objects and release static libraries"; the upstream o3de.org pre-built SDK ships both (strong inference, upstream tarball not cracked). Andre's export worked because he built configs from source.

Profile workaround CONFIRMED by the user 2026-07-22: Donnie switched Project Build Configuration to profile and reported the export "created the game build correctly for game launcher, server, headless server and unified package." So `--config profile` (or PM Export Settings -> Project Build Configuration = profile) is a validated, root-free path to a runnable-but-not-self-contained build. (Our own headless validation on HellaTestProject was stopped mid-run as redundant once Donnie confirmed it live.) The failing default combo, seen in the PM Export Settings dialog: Project Build Configuration = release + Build Monolithic checked.

DECISION MADE 2026-07-22: Nick committed publicly to an **o3de-experimental build that ships the monolithic libs** (option a). Plan is TWO-PHASE (see also the experimental-channel notes): (1) revive o3de-experimental first, it has sat idle, so verify its chroots exist and match the others' with_opts, confirm it builds green at profile-only today, check engine_ref/delimiter/NVR handling, BEFORE layering anything on; (2) add a `%bcond_with monolithic` (or release_export) gating a second build+install pass (release config + LY_MONOLITHIC_GAME=ON, per cmake/install/ConfigurationTypes.cmake:21 + cmake/Monolithic.cmake), enabled ONLY on experimental chroots via edit-chroot --rpmbuild-with (replaces full list; --with does not propagate). Acceptance test: a release export from the experimental package produces a working, root-free, self-contained game (Donnie's flow). Open unknown phase 2 answers: does LY_MONOLITHIC_GAME+release actually emit cmake/Platform/Linux/Monolithic/ConfigurationTypes_*.cmake (what has_monolithic_artifacts checks); real build-time/size cost; end-to-end export works.

TRACKING ISSUE: https://github.com/nickschuetz/o3de-rpm/issues/10 ("Release export not working", DonnieAlex, 2026-07-22, OPEN). Notes engine version = stable (o3de), release export fails on missing monolithic artifacts, profile config works. Accurate, matches diagnosis. This is the issue the experimental monolithic build closes. Reply draft to Donnie (posted to Discord): upstream-drafts/donnie-rpm-export-reply.md (local only).

IMPLEMENTED + LOCALLY VALIDATED 2026-07-22: monolithic bcond in o3de.spec (%bcond_with monolithic; second build-mono/ configure+build with LY_MONOLITHIC_GAME=ON + release, installs MONOLITHIC/MONOLITHIC_RELEASE components; catch-all %files sweeps the release/Monolithic subtree). Parses clean, gated, UNCOMMITTED (working tree).

MEASURED (local timed build, dev+qt6+monolithic, 16-core/62GB, 15 parallel jobs, build by3elovgj):
- Monolithic pass build time: ~10 min (18:47:53->~18:57), only ~+33% on top of the ~31 min profile build. Cheap because LY_MONOLITHIC_GAME builds game-runtime targets ONLY (no editor/tools/tests) and reuses the cached LY_3RDPARTY_PATH (no 3rdParty re-fetch). Total rpmbuild 1h13m.
- Release config compiled CLEAN (rc=0). First time we have ever built release; no new failures.
- Two-permutation install merged CLEAN: no unpackaged-files warnings, no file-listed-twice collisions, all 3 RPMs wrote.
- THE FIX LANDED: RPM now contains cmake/Platform/Linux/Monolithic/ConfigurationTypes_release.cmake (exactly what has_monolithic_artifacts globs for) + 196 release static libs under lib/Linux/release/Monolithic/. So the export's monolithic check would now pass.
- Size cost: +0.70 GB installed (release/Monolithic subtree); profile-only baseline ~3.9 GB -> ~4.6 GB (~+18%). Compressed RPM barely changes (~1.7 GB, static archives compress well).

NET: the monolithic addition is far cheaper than the "roughly doubles build time / materially bigger" worst case, ~10 min + 0.7 GB. Shipping it is very viable. STILL UNPROVEN (the final acceptance test): a release EXPORT run against this installed RPM producing a working self-contained game. Artifacts are present so the has_monolithic check passes, but the end-to-end export (linking these static libs into a launcher) has not been run yet. Next: install the built RPM locally + run `export-project --config release`, OR proceed to reviving o3de-experimental and building there. RPM at ~/rpmbuild/RPMS/x86_64/o3de2605-2605.0^20260722git9d4f4d2-106.fc44.x86_64.rpm.

---

## FIXED 2026-07-22: CS10 dev build broke on upstream #19622 FetchContent URL-mode (TIMEBOMB flag, retireable)

o3de-development build 10742547 (snapshot d1f8372, 07-17) failed CS10-ONLY at cmake configure: `Do not know how to extract .../downloaded_packages/googletest/<hash>`. Root cause: upstream o3de/o3de#19622 "O3DE Fetch Content" (merged 2026-07-16) switched ~10 3rdParty deps (googletest, assimp, meshoptimizer, Ogg, vorbis, miniaudio, v-hacd, RecastNavigation, Manifold, OpenMesh) from git-clone to URL-archive FetchContent, cached named-by-hash with NO extension. CMake < 4.0 extracts by filename extension and chokes; CS10 ships CMake 3.31.8 (fails), F44/rawhide ship CMake 4.3.0 (sniff by content, pass). googletest just failed first (AzTest builds early); the others would follow. Still URL mode on development tip, so it recurs every CS10 dev snapshot until upstream changes it.

FIX (spec-only, no carry-patch): added `-DO3DE_FETCHCONTENT_FORCE_GIT=ON` to the cmake block (o3de.spec ~1482), upstream's OWN escape hatch (added in #19622: `cmake/3rdParty.cmake` var, gated at 3rdPartyPackages.cmake:819/884, falls back to GIT_REPOSITORY). Forces the pre-#19622 git-clone path for every dep at once. Release bumped 105->106. VERIFIED GREEN 2026-07-22 on all 3 chroots, build 10763794 (snapshot 20260722git9d4f4d2-106); CS10 log shows `Cloning into 'googletest-src'` etc. and no extract error. Our existing spec googletest workaround (~line 1500) was NOT the fix path: it runs after config, which now died before creating build/_deps/googletest-src.

RETIRE the flag when #19622's URL path works on CMake 3.x (upstream fix), or CS10 ships CMake 4.x. Low urgency, FORCE_GIT is a permanent upstream feature and git-clone is what we ran for months pre-07-16. Only development-family channels (development, experimental) are affected; stable/stabilization build from the 2605.0 tag which predates #19622. Upstream issue for the CMake<4.0 extract bug: NOT yet filed (awaiting Nick's go; no existing report found).

## TRIGGER: qt6 merges into o3de/development (MERGE IMMINENT per sig-build, 2026-06-09; live state validated below)

Merge PR: o3de/o3de#19567 ("Build against Qt6.10.2", base development <- head qt6). As of 2026-06-09 16:50 UTC it is OPEN + APPROVED + CLEAN + MERGEABLE (one click from merge; sig-build planned to start the merge ~2026-06-10 09:30 PT). `make check-qt6-merge` reports this PR's state plus the authoritative BuiltInPackages Qt-pin verdict.

Guillaume rebased the qt6 branch on development + fixed DCO; pyside6 rev2 (#381, merged) was the last Linux consumable; sig-build is getting ready to merge. The day it merges, the o3de-development channel's Sunday cron builds a Qt6 engine WITHOUT the qt6 gates, so:

Live state verified 2026-06-09: o3de-development chroots = `with_opts=['development_snapshot']`; o3de-development-qt6 chroots = `with_opts=['development_snapshot','qt6']` (green at -103). The flip below just moves o3de-development to the qt6 project's already-green config.

1. Add `qt6` to the o3de-development chroots' with_opts (all 3) BEFORE the next cron tick, or the build fails at link (dbus-devel BR is qt6-gated) and, if it survives, ships with dangling requires (the jpeg8/tiff5/Qml excludes are qt6-gated). edit-chroot REPLACES, so pass the full list: `copr-cli edit-chroot hellaenergy/o3de-development/<chroot> --rpmbuild-with 'development_snapshot qt6'` for each of fedora-44-x86_64, fedora-rawhide-x86_64, centos-stream-10-x86_64, then `get-chroot` to confirm `['development_snapshot','qt6']`. DE-RISKED: target config is identical to the o3de-development-qt6 chroots that are already green, and the SRPM is bcond-neutral (the qt6 forward-test SRPM is built WITHOUT --with development_snapshot yet its chroots apply it), so no Makefile / `make copr-development` change is needed, only the chroot flip + a normal rebuild. CANNOT pre-flip: development is still Qt5 today and --with qt6 on a Qt5 tree is untested/wrong, so the flip has to land in the window between the merge and the next cron.
2. Confirm the merged dev tip actually carries the rev6 qt + rev2 pyside6 pins (Guillaume's rebase). If yes, our %install patchelf RUNPATH cleanup is a no-op against the clean rev2 package and can be RETIRED (it was the workaround for #378).
3. Run the promised #380 verification round on the first post-merge build: configure with system qt6-qtbase-devel installed (contamination fix live) + native-wayland PM startup (deploy fix live), report back on #380.
4. Decide the o3de-development-qt6 channel's future: redundant once qt6 IS development; probably retire after one overlap cycle (it has the channel description + testers pointed at it; coordinate, don't just delete).
5. The Lua gating reminder: dev tip on Qt6 reworked WatchesPanel.cpp; Patch0010/0011 are system_lua-gated already (caught in the qt6 channel era), no action, just don't re-add.
6. Native-Wayland Editor crash for dev-channel testers: o3de/o3de#19835 (qt6 Editor SIGSEGVs in the Vulkan swapchain surface-format query under native Wayland on the proprietary NVIDIA driver; `QT_QPA_PLATFORM=xcb` is the workaround; retested 2026-06-09 on driver 595.80, still crashes). FIX IN FLIGHT: DrogonMar's o3de/o3de#19837 ("[Wayland] Force QPA...") makes the Editor force `QT_QPA_PLATFORM=xcb` itself when the build is XCB-only (`PAL_TRAIT_LINUX_WINDOW_MANAGER_WAYLAND=OFF`, which is what we ship), so once #19837 lands in qt6/development our dev-channel builds self-enforce xcb on a Wayland session and need NO manual workaround. #19837 is blocked on the Qt 3p rev7 from o3de/3p-package-source#383. So: until #19837 reaches development, add the xcb workaround to a KNOWN_ISSUES note for dev-channel testers; after it lands, drop that note (it becomes automatic). Full native Wayland (`WAYLAND=ON`) is a separate, later track (single-display-connection done in #19837, but the viewport-overlay sub-surface composition is still open) and stays unshipped.
7. Local dev-branch build + install on Nick's host (he wants to test it the same way as the 2026-06-09 qt6 local build): `make rpm-local-development` (mirrors the validated qt6 recipe with REF=development, now Qt6 -- all-patches SRPM, builddep the Qt6 deps, --rebuild with --with snapshot --with development_snapshot --with qt6; ~70 min). Then install main + devel together: `sudo dnf install --allow-downgrade ~/rpmbuild/RPMS/x86_64/o3de2605-*.rpm` (the -devel subpackage pins the exact NVR). Run ONLY after the merge -- before it, development is Qt5 and --with qt6 is wrong (the qt6 BuildRequires + parse were pre-validated 2026-06-09; only the compile is untested-until-merge, and it is identical to the green qt6 build).

### Personal fork sync (independent of the RPM pipeline)

The RPM snapshot build pulls o3de/o3de directly (make-snapshot-tarball.sh), so a fork sync is NOT required for packaging. But Nick's own dev forks should be brought current after the merge: `gh repo sync nickschuetz/o3de --branch development`, then locally `cd ~/PROJECTS/o3de && git fetch upstream && git branch -f development upstream/development` (local checkout sits on a patch branch, not development). Optionally the other dev-tracking forks too: o3de-extras, o3de.org (both default development), 3p-package-source (main).

## Merge-day tooling (built 2026-06-09, ready)
- `make check-qt6-merge` -- probe: has qt6 merged into development? (watches the Linux x86_64 3rdParty Qt5->Qt6/pyside flip; exit 0 not-yet / 10 merged / 2 unknown, version-agnostic, outage-aware). tools/check-qt6-merge.py.
- `qt6-merge-gate` -- pre-flight interlock auto-run by copr-development / -debug / -and-test: hard-stops the COPR build if development is merged to Qt6 but the target chroots lack the qt6 bcond, printing the exact edit-chroot flip commands. NOT-YET passes through; upstream outage warns + proceeds.
- `make rpm-local-development` -- local host build of the dev branch (item 7).

---

## STRATEGIC WATCH: "O3DE 2.0.0 -- The Object Model" RFC + working implementation (flagged by Nick, 2026-07-28, "starting to warm up")

Links: RFC https://github.com/accesspointmg/org.o3de.repo.o3de/blob/development/Engines/o3de/rfc/o3de-2.0.0.md | 117 split object repos https://github.com/orgs/accesspointmg/repositories | tooling https://github.com/accesspointmg/o3de-pilot

WHAT: An accesspointmg fork's re-architecture (NOT yet in o3de/o3de) that recasts engine/gems/projects/templates/overlays as versioned "canonical objects" (e.g. org.o3de.engine.o3de 4.2.0) with a PubGrub dependency solver, a uniform 3-channel release model (git refs / code archives / prebuilt per-platform BINARIES), and a manifest-driven CMake build. It is a WORKING system, not a proposal: 117 org.o3de.repo.* repos already extracted from the monorepo via git filter-repo (Phase D done), solver/workspaces/binary-consumption working (1055 tests), current with upstream through tag 2510.2. o3de-pilot is a CLI-first, npm-like, AI-powered (Claude/Ollama) REPLACEMENT for Project Manager that follows the RFC spec, downloads the object repos, assembles a workspace, and builds a working O3DE. Project Manager is "removed" in their status table.

WHY IT MATTERS TO FEDORA PACKAGING (three ways):
1. It directly dissolves our biggest Fedora blockers: the monolith (gems inside engine, 10GB LFS clone) -> per-object repos, "O3DE 25.10 is a lockfile not a 10GB clone"; source-only-assembly -> a first-class prebuilt BINARY channel with <name>Config.cmake consumable by find_package; no-versioned-resolution -> the solver. Linux binaries advertise a glibc ABI floor (resolver picks highest compatible) -- maps onto our CS10 glibc-2.28 vs F44/rawhide problem.
2. OR it becomes a COMPETING distribution: their own registry (canonical.o3de.org) + solver + lockfiles is itself a distribution mechanism overlapping dnf/rpm. If O3DE ships object-distribution, the question is how a Fedora RPM relates to it.
3. It replaces the exact tooling our RPM wraps: we ship o3de.sh / o3de2605-cli + the C++ Project Manager; this retires PM for a new npm-style workspace-assembly CLI. Our launcher wrappers + "monolithic engine to /opt" shape would need rethinking.

NET: if upstream adopts this, our "one spec, snapshot the monorepo" model is obsoleted and reframed around lockfiles-of-objects; it reshapes the whole FEDORA_ROADMAP staging plan. CAVEAT: it's a fork's ambitious pitch, adoption undecided; "warming up" (Nick_L demoing in Discord #sig-build-ish) is the signal, not a decision. WATCH: the accesspointmg repos for activity, and any o3de/o3de or sig-core/sig-build RFC thread when it lands upstream. Not yet reflected in FEDORA_ROADMAP (offered; Nick to decide).

NICK'S PUBLIC OFFER (Discord, 2026-07-28): "I'd be happy to test/PoC it at some point if given implementation and prerequisite instructions. I'm noting this in my O3DE rpm work as well." So the trigger for our hands-on involvement is: getting build/assembly prerequisite instructions (likely the o3de-pilot README + the RFC's resolve/assemble flow). Candidate next step when Nick wants: scope o3de-pilot's setup requirements (does it need Python? a particular CLI? what does "assemble a workspace + build" actually require on a Fedora host) and, if reasonable, run the pilot to produce a working engine as a hands-on read on the model. Low priority until Nick says go or instructions materialize.

---

## CHECK OUR FIND-SHIMS: Find*.cmake scoping bug flagged by Nick_L (2026-07-25, #sig-build)

While building OpenImageIO, Nick_L flagged that O3DE's general Find*.cmake pattern is subtly wrong about SCOPE: the files use an include-guard (`if(TARGET 3rdParty::<X>) return()`) and then create the imported target `add_library(<X> STATIC IMPORTED GLOBAL)` (global) AND set the find-result variables (`<X>_FOUND`, `<X>_INCLUDE_DIR`, ...) in the CURRENT scope. Because the target is GLOBAL but the variables are LOCAL, a later `find_package(<X>)` from a DIFFERENT scope hits the guard, returns early (target already exists), and never sets those variables in that scope. Any consumer in that scope that reads `<X>_INCLUDE_DIR` (rather than linking the target) gets nothing. Correct pattern: set the variables FIRST (so every calling scope gets them), THEN create the target only `if(NOT TARGET ...)`.

ACTION: audit OUR system-swap Find shims (sources/Find<X>-system.cmake: zlib, freetype, png, expat, lz4, mikkelsen, openexr/imath, poly2tri, lua, assimp, sqlite, libsamplerate, googlebenchmark, tiff, mcpp, rapidjson, xxhash, cityhash) for the same pattern. Most of ours likely mirror the engine's guard-then-create-then-set order, so they may carry the same latent bug. Low urgency (works today because consumers mostly link the target, not read the vars), but worth fixing to match the correct order and pre-empt a scope-dependent break. Relates to [[project_system_stub_recommends_cross_check]] and [[project_system_swap_shim_two_mechanisms]].

---

## o3de/3p-package-source#387 bumps bundled OpenSSL 1.1.1 -> 3.6.3 -- MERGED 2026-07-23

FIRES NOW that #387 merged (was: watch for merge): (1) reword the `bundling_exception: OpenSSL` "EOL 1.1.1t" rationale in tools/dep-map.yaml + BUNDLED_LIBRARIES.md -- the EOL argument is dissolving at the 3p level, keep the exception on Fedora's no-bundled-libs argument. (2) Our #376 rebase-onto-387 + re-validate commitment is now due once #376 itself moves. (3) NOTE: the ENGINE still pins OpenSSL-1.1.1t-rev1-linux in BuiltInPackages; a separate engine-side PR must bump it to consume the new 3.6.3 package before our builds change (dev-tip 20260726 still statically links 1.1.1t, seen in the monolithic launcher link). Watch for that engine PR.



**State 2026-07-21:** out of draft, APPROVED by nick-l-o3de (2026-07-20T16:08Z), mergeStateStatus CLEAN, 19 files (+77/-116), Android build fixed 2026-07-21T13:54Z. Merge can land any time, which arms both follow-ups below.

**Audit posted upstream 2026-07-21.** Two comments, evidence tables in `upstream-drafts/pr-387-qt-rebuild-scoping-comment.md` and `upstream-drafts/pr-376-openssl-coexistence-data-comment.md`:
- #387 (https://github.com/o3de/3p-package-source/pull/387#issuecomment-5036270128): the Qt rebuild nick-l-o3de flagged is **Windows-only**. `build-windows.bat` sets OPENSSL_ROOT to OpenSSL-1.1.1o-rev1-windows (lines 29-35) and configures `-openssl-linked` (line 55); `build-linux.sh` assigns `OPENSSL_FOLDER_NAME=$3` on line 19 and never uses it again (verified across the full 101-line script), and the Linux configure line carries no OpenSSL flag; both Mac scripts have zero OpenSSL references. Corroborated downstream: our Qt6 ships no TLS backend plugin and the engine has zero `QSsl*` refs.
- #376 (https://github.com/o3de/3p-package-source/pull/376#issuecomment-5036270261): measured coexistence. `libAzFramework.so` statically links AND exports 1637 OpenSSL 1.1.1t symbols; bundled Qt5 resolves OpenSSL at runtime and picks up system 3.5.7. Both live in one process today. **No cross-binding**: 0 of 26497 `LD_DEBUG=bindings` entries crossed, because OpenSSL 3.x symbols are versioned (`EVP_DigestInit@@OPENSSL_3.0.0`) and AzFramework's static copy is unversioned (`Base`, 0 verdefs). Residual gap: unversioned `dlsym(RTLD_DEFAULT, ...)` lookups DO land on the 1.1.1t copy.

**Jan replied to both 2026-07-22, and it reconciles as one vindication + one imprecision (gut-checked):**
- #376: Jan reported a LIVE segfault, a Gem depending on OpenSSL 3.x crashes when added, "collisions between the embedded (in AzFramework via AzNetworking) OpenSSL 1.1.1 and OpenSSL 3.x ... layout/struct mismatches between the two versions' internal EVP_PKEY_CTX representation caused the segfault." **REPRODUCED + VERIFIED 2026-07-22, and it CORRECTS the posted comment.** The posted #376 comment said "it doesn't actually cross-bind, 0 of 26497 bindings." That was true ONLY for the trivial Qt probe I ran (supportsSsl + version number, no real crypto). Built an actual repro: a gem.so linked to system OpenSSL 3.x doing EC keygen. Standalone it works; with AzFramework loaded RTLD_GLOBAL first (faithful to the engine, where AzFramework is a NEEDED lib of the launcher so its symbols are in the executable's global scope) the SAME keygen fails with `pkey_ec_keygen: no parameters set`, and LD_DEBUG=bindings shows ~1016 OpenSSL symbols from libcrypto 3.x resolving INTO AzFramework's 1.1.1t. Counterfactual proves causation and the fix: RTLD_LOCAL (symbols not exported to global scope) makes the same keygen pass with no other change. **TRUE mechanism (gut-checked 2026-07-22, after TWO wrong first passes, do not repeat them):** it is NOT libcrypto's internals cross-binding (measured libcrypto->AzFramework = 0; the ~1600 "OpenSSL symbols in AzFramework" from the naive grep were AzFramework's own SELF-references, not cross-binds). The real bug: glibc binds a VERSIONED reference to an UNVERSIONED definition when it is first in scope, so the gem's own versioned 3.x calls (EVP_PKEY_keygen@OPENSSL_3.0.0 etc.) get captured by AzFramework's unversioned 1.1.1t exports. Symbols present in BOTH versions (EVP_PKEY_CTX_new_id, keygen_init, keygen) bind to 1.1.1t; a symbol only 3.x exports (EVP_PKEY_CTX_set_ec_paramgen_curve_nid, a macro in 1.1) falls through to real libcrypto 3.x. So one logical operation is SPLIT across two OpenSSL versions on the same ctx object -> incompatible struct layouts -> "no parameters set" (my repro) or a deref segfault (Jan). **This REFUTES my posted #376 claim ("versioning quietly enforces the match, 0 cross-bindings"): that 0 was a Qt-only artifact (Qt resolves via dlsym on its own handle, bypassing global ELF resolution) and the versioning lesson was flat wrong.** Fix direction validated: RTLD_LOCAL -> all gem calls resolve to 3.x -> works; real fix is hidden visibility on AzNetworking's OpenSSL. NET: the posted comment's central technical claim is wrong and needs an open correction (Jan reply draft v2 does the retraction). Repro harness in scratchpad: gem.c/gem2.c, host.c/host2.c, all.log (LD_DEBUG). Reusable lesson -> memory [[project_openssl_versioned_unversioned_shadowing]].
- #387: Jan confirmed the dead-code finding and extended it (TIFF_FOLDER_NAME and ZLIB_FOLDER_NAME are also dead in build-linux.sh, all three removable). BUT he corrected one word: he pulled upstream qt-6.10.2-rev8-linux and it DOES ship plugins/tls/libqopensslbackend.so (with no static OpenSSL symbols, which supports the "Qt doesn't embed OpenSSL" conclusion). My posted "no backend .so ever gets built or installed" was wrong on "built": upstream builds it. "Not installed in our package" was correct, verified 2026-07-22 via repoquery on the newest Qt6 dev build (o3de2605-2605.0^20260717gitd1f8372-105): 0 qopensslbackend, while platforms/ imageformats/ xcbglintegrations/ are all present.

**NEW finding (surfaced by Jan's correction), root-caused 2026-07-22: it is UPSTREAM, not our packaging. The O3DE engine never deploys the Qt TLS plugin on Linux.** Upstream 3p qt-6.10.2-rev8-linux ships plugins/tls/libqopensslbackend.so, but the engine's Qt-plugin deploy list, `cmake/3rdParty/Platform/Linux/Default/3rdParty__Qt__Gui__Plugins.cmake`, explicitly enumerates the plugin categories it copies (imageformats, platforms, iconengines, xcbglintegrations, wayland-decoration-client, wayland-graphics-integration-client, wayland-shell-integration; translations via a sibling file) and `tls` is NOT among them (grep -c tls = 0). So our package faithfully ships exactly what the engine deploys; the omission is in the engine's runtime-dependency list, not in o3de.spec, and it affects EVERY O3DE Linux build, not just ours. Mechanism: the TLS backend is a lazy dlopen plugin (loaded only on first QSslSocket use), so it is not in the Qt link-time dependency graph and only lands if explicitly listed, which it is not, presumably because nothing in the engine uses Qt TLS. INERT today (engine has zero QSsl*/QNetworkAccessManager usage, re-verified 2026-07-22: 0 files across all source extensions). LATENT for any gem/tool doing Qt HTTPS on ANY O3DE Linux build. If we ever care, it is an UPSTREAM ask (add tls to that plugin list), NOT a downstream spec change. Do not "fix" it in o3de.spec.

**Two findings deliberately NOT raised upstream** (see the #376 draft file): bundled Qt 5.15.1 cannot resolve `EVP_PKEY_base_id` / `SSL_get_peer_certificate` against OpenSSL 3.x while Fedora's patched 5.15.18 can (inert today, engine has zero QSsl usage, and arguably our rebuild's problem); and an interposition-crash theory that measurement DISPROVED, so do not resurrect it.

**Prior art: abandoned, do not block on it.** 3p#209 (https://github.com/o3de/3p-package-source/pull/209, "Add cmake cache var to allow for use of system openssl", OPEN since 2023-07-28) and o3de#16375 (https://github.com/o3de/o3de/issues/16375, OPEN, updated 2026-05-12) cover ground overlapping our o3de#19815, which references NEITHER. Both are by `nicholas-rh`, who is inactive upstream, so treat #209/#16375 as dead prior art rather than live proposals (do not wait on a response). Practical effect: #19815 does not need to defer to, coordinate with, or wait on them, and neither does #376. Cross-linking is still worth doing as attribution and context (it stops #19815 reading as though we ignored three-year-old prior work), but purely as a one-way reference; expect no response and do not treat either as a gating dependency. #209 also documents that O3DE's `FindOpenSSL.cmake` collides with CMake's builtin module of the same name (same for Freetype), which is directly relevant to our Find-shim work. Also open and related: o3de#14761 (https://github.com/o3de/o3de/issues/14761, libssl.so.1.1 missing on Ubuntu 22.04 breaks the official installer, OPEN since 2023-02-23), which #387 would fix.

## Original watch entry (opened 2026-07-20, then DRAFT)

https://github.com/o3de/3p-package-source/pull/387 (jhanca-robotecai / Jan Hanca, RobotecAI). Unifies the OpenSSL 3rdParty package to 3.6.3 across all platforms: Linux, Linux-aarch64, Mac and Mac-arm64 source builds retarget `openssl-3.6.3`; the vcpkg path (Mac-Intel, iOS, Windows, Android) bumps its pin to a commit shipping 3.6.3 natively and drops the two legacy 1.1.1-era patches (`set_openssl_port_to_1_1_1_x.patch`, `enable-stdio-on-iOS.patch`); package license metadata changes to Apache-2.0. Author states Linux x86_64 was built and tested end-to-end via the real Docker pipeline, vcpkg validated by a Linux-triplet dry run, and the remaining platforms left to CI. Diff read 2026-07-20: touches `package-system/OpenSSL/*`, `Scripts/packaging/package.py`, and the `package_build_list_host_*.json` files; it does NOT touch `package-system/python`, so there is no file conflict with our #376.

**Why we care: it dissolves the stated rationale for our OpenSSL bundling exception.** `tools/dep-map.yaml` (`bundling_exception: OpenSSL`) and the matching `BUNDLED_LIBRARIES.md` filing both justify the exception as "Stage 4, EOL 1.1.1t needs upstream migration to 3.x". #387 IS that migration. Assessment (inference, not yet settled with Fedora review): the exception itself should survive, because Fedora's guidelines discourage bundled copies of system libraries regardless of version, but the EOL-crypto justification becomes stale the moment #387 merges and needs rewording to the version-independent argument. Do not delete the exception, reword it.

**Fires on merge (when #387 leaves DRAFT and lands):**
1. Reword the `bundling_exception: OpenSSL` note in `tools/dep-map.yaml` and the `BUNDLED_LIBRARIES.md` filing off the EOL argument onto the no-bundled-libs argument.
2. Make good on the public commitment in Nick's 2026-07-20 comment on #376: rebase https://github.com/o3de/3p-package-source/pull/376 onto #387 and re-validate the Python system-openssl variant against the 3.6.3 bundle (rebuild plus tier-suite re-run). No date was promised; the comment says "once it settles".

**Engine-side context, separate track.** Jan's 2026-07-15 comment on #376 reports that OpenSSL 1.1.1 is statically burned into `AzNetworking`, which links into `AzFramework`, so in a MONOLITHIC build a Gem pulling 3.x collides with the already-linked 1.1.1 and segfaults. He has a PoC splitting `AzNetworking` into a shared object, which does not help the monolithic case. That is an o3de/o3de change, not covered by #387 (which only bumps the 3rdParty package), so a merged #387 does not by itself prove the engine consumes 3.6.3 cleanly. Watch for the follow-on engine PR.

Full thread record, as-posted comment, and claim audit: `upstream-drafts/pr-376-openssl-bundle-vs-system-reply.md`.

---

## Carry-patch retirement audit (run 2026-06-04): zero retirements, one 26.10 obligation

Full four-check sweep against the 2605.0 tag, stabilization/26050, and development ee805f49. All six merged-upstream patches (0001/#19748, 0002/#19751, 0005/#19750, 0007/#19734, 0008/#19733, 0012/#19747) are in development ONLY; stabilization/26050 has zero commits since the release tag, so no channel can drop anything and the development_snapshot gating is exactly right. Dev-channel applied set (0003+0004) dry-runs clean at tip; Lua 5.5 re-grep found the same 3 covered sites, no new ones.

UPDATE 2026-06-09: Patch0004 is now SUPERSEDED upstream by o3de/o3de#19752 ("LYPython: install from sdist when engine is installed (read-only)", merged into development 2026-06-09, same cmake/LYPython.cmake read-only fix). Applying 0004 against development tip now reports "previously applied", so it would have failed %prep on the next development_snapshot build. Gated it under `%if %{without development_snapshot}` like the other merged patches (seven now: 0001/0002/0004/0005/0007/0008/0012). Patch0003 (get_python.sh) is untouched by #19752 and stays the only ungated dev-channel patch. Non-dev channels keep 0004 (stabilization/26050 still lacks #19752).

**Forward obligation: regenerate Patch0009 PhysX5-only when stabilization/26100 cuts.** PhysX4 Deprecation (o3de/o3de#19726) merged 2026-05-08; `Gems/PhysX/Core/PhysX4/Source/Platform/Linux/PAL_linux.cmake` no longer exists on development. Do NOT regenerate earlier: the 26.05-era refs the patch actually applies to still carry PhysX4. Next audit trigger: stabilization/26100 opening, or any commit landing on stabilization/26050 (would also be the 26.05.1 / UV-fix cherry-pick signal).

**Retirement trigger corrected post-release (2026-07-13, doc sweep 7b33e2d).** 26.05.0 shipped 2026-05-27, so the old "retire when stabilization/26050 absorbs it" wording is a DEAD trigger for all seven TIMEBOMBs (0001/0002/0004/0005/0007/0008/0012) and the Patch0009 forward-item: 26050 is frozen at the release state and will not backport dev-only merges. The correct trigger is PER-CHANNEL, when a channel's engine ref rebases onto the 26.10 base (stabilization/26100 when it opens, then the 26.10 release tarball, both branch from development and already carry the fixes). The stable channel keeps all seven until stable_tag rolls 2605.0 -> 2610.0 (the 26.05.0 tarball it serves lacks them all). Reworded uniformly across o3de.spec (retirement-model banner atop the patch block), README.md, CONTRIBUTING.md, and tools/dep-map.yaml (engine_ref noted as the deliberate 26.05-line drift target). Gut-check 2026-07-13 verified against upstream: all seven merge commits are reachable from development, NONE from stabilization/26050, and NONE from the 2605.0 tag (so the stable-channel gating is correct, Patch0001 was flagged as a possible release cherry-pick but did NOT land). One inference not yet fact: stabilization/26100 does not exist, and "branches from development" assumes upstream repeats the observed development -> stabilization/NNNNN -> merge-to-main flow (it will, but the branch-cut hasn't happened). Memory: project_branch_alignment_before_retirement.md.

---

## 26.05.0 release validation (closed 2026-05-28)

**Stable RPM validated end-to-end against two community game projects.** Build 10519208 (o3de2605-2605.0-1.fc44) installed cleanly via the announcement install sequence (`dnf copr enable hellaenergy/o3de && dnf install o3de2605`). All tier passes against the clean install:

- Tier 1-4: 55/56 (1 skipped by design): install integrity, system-swap auto-Requires, first-run venv setup, engine smoke
- Tier 5: PASS. `o3de create-project` + cmake configure against installed engine
- Tier 7: 21/21. system-swap library health (all 13 SONAMEs loadable, engine .so's link to /lib64/)
- Tier 9 (MultiplayerSample): 13/0. clone + LFS pull + cmake + ninja (GameLauncher + ServerLauncher + HeadlessServerLauncher + bare gem) + full AssetProcessorBatch bake + GameLauncher smoke
- Tier 10 (NewspaperDeliveryGame): 7/0. register + cmake + AP batch + GameLauncher smoke (loaded Levels/CharacterSample/CharacterSample.spawnable)
- Tier 6 (UI smoke) was skipped because Xvfb stack wasn't installed on the validation host; covered visually instead (PM launched, project created, Editor splash showing "Version 2605.0")

No packaging regressions surfaced. The two community-game tests are the strongest validation gates we have short of community testers reporting back, and both pass cleanly.

## Packaging correctness

**Snapshot Version uses `^` (post-release) but means pre-release; blocks auto-upgrade from snapshot to stable (caught 2026-05-28, FIXED 2026-05-28 in -80).** `o3de.spec:263` was building the snapshot Version as `%{stable_tag}^%{snapshot_date}git%{shortcommit}`, so a 2026-05-23 snapshot of the 26.05 line came out as `2605.0^20260523git8e75050-1.fc44`. In RPM versioning `^` is a POST-release delimiter, meaning the snapshot was being interpreted as higher than the bare tag (`rpmdev-vercmp 2605.0^20260523git8e75050-1.fc44 2605.0-1.fc44` returned `>`). Consequence was that any community tester who installed from `hellaenergy/o3de-stabilization` during the pre-release window got stuck on the snapshot when they enabled `hellaenergy/o3de` and tried `dnf upgrade`, because dnf saw the stable as a downgrade and refused. Caught locally on 2026-05-28 trying to upgrade from `2605.0^20260523git8e75050` to `2605.0-1.fc44`; `dnf upgrade` returned "Nothing to do."

Fix landed 2026-05-28 in changelog `-80`: `^` to `~`. Tilde is the actual RPM pre-release delimiter, so `2605.0~20260523git8e75050-1.fc44` now compares less than `2605.0-1.fc44`. Verified locally via rpmdev-vercmp. Future snapshots in o3de-stabilization / o3de-development / o3de-experimental will use the corrected form.

Migration for existing testers stuck on `^` snapshots (one-time downgrade): `sudo dnf --disablerepo='*o3de-stabilization*' downgrade -y o3de2605 o3de2605-devel`. After that, all future `~` snapshot to next-release-tag transitions work normally.

**Refinement 2026-07-07 in -105: the `~` fix was correct for stabilization but wrong for development, so the delimiter is now channel-aware.** The 2026-05-28 change applied `~` to ALL snapshot builds, but `~` (pre-release) is only correct for the stabilization/experimental source, which is a genuine pre-release of the current tag. Development tracks `o3de/development` AFTER the tag shipped (heading to the next release), so it is POST-release and needs `^`. Under the unconditional `~`, every development build came out `2605.0~<date>` and sorted BELOW the bare `2605.0` tag, so the one legacy `2605.0^20260521git5bdb8cc` build (built before 2026-05-28, still in the o3de-development COPR) outranked every newer `~` build. Result: `dnf install`/`upgrade` on the development channel pinned users to the stale 20260521 snapshot and never advanced. Caught 2026-07-07. Fix: `o3de.spec` now gates the delimiter on `%{with stabilization}` (`~` for stabilization/experimental, `^` for development/qt6/arbitrary snapshots). Validated with `rpm.labelCompare`: `2605.0^20260703...` is newer than the stale `^20260521` build, newer than the `~` builds, above `2605.0-1`, and still below a future `2605.1`. The next development build published with -105 unsticks the channel (its `^<date>` outranks everything currently in the repo). **Poison pruned 2026-07-07:** the `2605.0^20260521git5bdb8cc-1` package was carried by o3de-development builds 10520941 (SRPM build) and 10506162 (forked in from o3de-snapshot build 10493483); both deleted via `copr-cli delete-build`, then `copr-cli regenerate-repos`. Verified with `repoquery`: poison gone, `2605.0~20260703gita8d3d35-104` (Jul 3) is now the channel's newest, so the channel is unstuck ahead of the next cron build. The remaining `~` builds are harmless (all below the next `^<date>` build the cron will publish).

## Sample bake / smoke -- post-release window items

Parked 2026-05-22 from the Tier 9/10 "what's next with these games" sweep.

**AP cold-bake perf (Tier 9)**: Tier 9 cold-cache takes ~3h49m, dominated by `Image Compile: PNG` (2h cumulative across 1007 jobs, ~7s avg/job). Warm-cache is 3-10 min so the CI/dev iteration loop isn't blocked. Investigation surface: `/Amazon/AssetProcessor/Settings/Platforms/<plat>/...` regsets for builder-count tuning + whether AP runs PNG jobs in parallel across multiple AssetBuilder processes or serialized through one. Defer unless CI wall-time becomes a real budget problem. Cross-ref: [[project_tier7_serial_pass_option.md]] for the `--regset maxJobs=1` pattern (different problem but adjacent CLI surface).

**MPS audio migration research (AzAudio -> MiniAudio) -- scope mapped 2026-05-22**: Surveyed MPS source to estimate effort for migrating from legacy AzAudio (broken on Linux; no backend implementation in MPS's enabled-gems set) to MiniAudio (working, Apache-2.0 OR MIT engine wrapper around mackron/miniaudio Public-Domain-or-MIT-No-Attribution). Surface: 16 files affected -- 2 C++ source pairs (`BackgroundMusicComponent` ~110 LoC, `Multiplayer/GameplayEffectsComponent` ~206 LoC), 5 ScriptCanvas graphs (`JumpPad`, `PredictiveJumpPad`, `AudioTester`, `ShieldGeneratorRoundEffects`, `EnableAudioListener`), 7 prefabs (Energy_Ball, AudioTester, Sound_Effect, GamePlay_Effects, Player, BubbleBall, NewStarbase). MiniAudio has direct replacements for `AudioListenerComponent` (`MiniAudioListenerComponent`) and `AudioTriggerComponent` (`MiniAudioPlaybackComponent`); `AudioProxyComponent` has no equivalent (MiniAudio doesn't need a proxy). Biggest gotcha is architectural: AzAudio uses one-component-plays-many-triggers via string IDs (Wwise-shaped); MiniAudio uses one-component-per-sound-asset. Each entity needs structural rework, not a search-and-replace. Plus `.atl_audio_controls` XML mappings need to be replaced with direct sound-asset references. Estimated 1-4 days focused work for someone familiar with O3DE audio. NOT something to drive from the packaging side -- best done by community contributors / sig-content with audio domain knowledge.

**RPM-packaging the community samples (parked 2026-05-22)**: Idea of `o3de2605-sample-<name>` RPMs for NewspaperDeliveryGame + MultiplayerSample is blocked on asset licensing. Standalone licensing review at [`docs/SAMPLE_PROJECT_LICENSING_AUDIT.md`](docs/SAMPLE_PROJECT_LICENSING_AUDIT.md); shared to upstream 2026-05-26.

**Editor window doesn't honor GNOME tile-snap / edge-drag -- upstream fix sketched 2026-05-26**: Nick noticed Editor windows can't be tile-snapped via mouse-drag-to-edge on GNOME, even though Project Manager (same Qt 5.15 bundle) interacts with Mutter normally. Diagnosed: Editor uses `AzQtComponents::WindowDecorationWrapper` (`Code/Framework/AzQtComponents/AzQtComponents/Components/WindowDecorationWrapper.{h,cpp}`); PM does not. The wrapper overrides `nativeEvent()` and `changeEvent()` to manage custom dark-themed chrome for cross-platform consistency. Even in `OptionDisabled` mode (the Linux/Mac path where the WM is supposed to draw the native title bar instead of the Qt-rendered custom one), the `nativeEvent()` override still runs and processes WM messages before they reach the inner QMainWindow. That's where tile-snap drag gestures get swallowed.

Not ours -- WindowDecorationWrapper landed 2021-03-05 in O3DE's initial commit, 12 commits in its history, none related to event filtering. Our Patch0005 only adds 1 line in the OptionDisabled title-propagation path (already merged upstream as PR #19750), doesn't touch event handling. The behavior is a deliberate upstream design choice from when Wayland was experimental and Linux WM-integration polish was less expected. In 2026 with Wayland mature and tile-snap a daily-use feature, the tradeoff has shifted.

Fix sketch: add an early-return at the top of `WindowDecorationWrapper::nativeEvent()` when `OptionDisabled` is set AND the platform is Linux, letting WM messages flow through to the native window manager unmolested. Scope is small (low single-digit LoC); risk to Windows/Mac behavior is zero if the platform-check is correctly gated. Keep the wrapper for its load-bearing features (tear-off floating docks, multi-monitor chrome adaptation, custom title-bar widgets); only relinquish event filtering on Linux where the native compositor is the better citizen.

Workaround in the meantime: `Super+arrow` keyboard shortcuts (GNOME WM bindings) often work because they go through a different code path than the mouse-drag-to-edge gesture the wrapper intercepts. `Super+Up` toggles maximize, `Super+Left`/`Super+Right` half-tile, `Alt+F7` enters move-via-keyboard mode. Covers maybe 80% of tile-snap UX without the engine fix.

Cost/benefit: small engineering, modest per-user benefit, larger perception benefit -- this is exactly the kind of papercut that makes Linux feel "second-class" in cross-platform DCC tools. Post-release worth filing as an issue + draft PR; not a 26.05.0 blocker. Cross-platform DCC tools (Blender, Maya, Houdini, Substance, Unity Editor) all use similar custom chrome for the same cross-platform consistency reason, but most respect the native WM for tile/snap events specifically.

**Gameplay-smoke beyond level-load -- IMPLEMENTED as Tier 11 (2026-05-22)**: `tests/post-load-liveness-test.sh` + `make test-tier11`. Runs the launcher for `LIVENESS_SECONDS` (default 60s) after `LEVEL_LOAD_END`, verifies (a) launcher alive at end-of-window, (b) zero crash markers in Game.log, (c) the success marker was present, (d) Game.log accumulated at least `LIVENESS_MIN_NEW_LINES` (default 50) new lines during the window. Passes against NewspaperDeliveryGame. Caught a real crash against MultiplayerSample on first run -- see new entry below.

**MultiplayerSample post-load crash diagnosed end-to-end 2026-05-22 (corrected from earlier LyShine misattribution)**:

Initial diagnosis was wrong. The `UiCanvasAssetRefComponent::LoadCanvas` stack frame I'd seen via coredumpctl was a downstream consequence of broken module state, not the root cause. Filed [o3de/o3de#19780](https://github.com/o3de/o3de/issues/19780) against LyShine then had to close it the same day.

Actual root cause: the cmake change merged via our own [PR #501](https://github.com/o3de/o3de-multiplayersample/pull/501) (commit `09f162375964`) added `add_dependencies(MultiplayerSample.Client MultiplayerSample)` lines that the engine's `o3de_get_gem_load_dependencies` walker (`cmake/SettingsRegistry.cmake:81`) interprets as runtime LOAD dependencies, not build-order. The bare gem ends up in the launcher's `cmake_dependencies.<project>.multiplayersample_gamelauncher.setreg`. Launcher dlopens both `libMultiplayerSample.so` and `libMultiplayerSample.Client.so`. Each contains its own `MultiplayerSampleModule`, each constructs its own `m_userSettings`, each calls `BusConnect` on a Single-handler-policy bus. Second `BusConnect` asserts "Bus already connected to!" and the launcher aborts within 1 to 2 seconds of `LEVEL_LOAD_END`. We filed [PR #502](https://github.com/o3de/o3de-multiplayersample/pull/502) reverting the cmake change + adding a README note documenting the dual-target build requirement instead. Closes #500 via doc instead of cmake.

Verified end-to-end on Fedora 44 (after revert, before pushing #502): launcher loads startmenu cleanly, MULTIPLAYER SAMPLE title screen renders with the cyberpunk UI, IP entry / Join Game / Quit buttons all interactive, network stack initialized. Same launcher state that was aborting deterministically with the broken cmake change applied.

JT_SCB_GameDesign (Discord, 2026-05-22) confirmed Windows users see analogous behavior intermittently (his "bail-out window UI 2-3 times then it works" framing). Linux determinism gave us a cleaner repro than the Windows community had. JT also noted the downloadable MPS Dg is a 23.x Windows build, which explains how the 25.x/26.x experience drifted; the merged-but-broken cmake change in #501 only made things worse on Linux specifically.

**RESOLVED 2026-05-22 19:29 UTC:** PR #502 merged by nick-l-o3de (~90 minutes after we opened it). Approved + DCO check passed + zero review comments. Upstream `o3de/o3de-multiplayersample:development` is now clean again. Docs (README + CONTRIBUTING + tests/README + ARCHITECTURE Mermaid) simplified to drop the "blocked pending #502" framing.

**MPS gameplay-side crash modes from sustained-play test (caught 2026-05-22 14:14-14:19 CDT)**: After verifying multiplayer works end-to-end (server + client, NewStarbase, ROUND 1 of 3, player character active), sustained play surfaced two distinct upstream-side crash modes:

1. **AudioSystemAllocator exhaustion (14:14 CDT, first session)**: Hundreds of `[Error] (System) - Failed to get a new instance of an AudioObject from the implementation. If this limit was reached from legitimate content creation and not a scripting error, try increasing the Capacity of Audio::AudioSystemAllocator.` entries in the seconds leading up to the SIGABRT. Secondary symptoms: `Autonomous Desync` (netcode reconciliation, normal under load) and `Processing time exceeded, discarding 171/382 received packets` (server main loop fell behind because audio errors slowed it down). Crash logs at `/tmp/mps-crash-2026-05-22/{Game.log,client-stdout.log,server-stdout.log}`. **Per Nick_L (Discord, 2026-05-22 14:29 CDT)**: this is NOT a capacity-tune issue. MPS has code paths still using the legacy `AzAudio` system (`AudioObject` / `ATL`), but the engine direction is `miniaudio` (which uses its own pool, not the legacy `AudioObject` infrastructure). PR #499 was a partial step; remaining legacy-Audio code in MPS is what exhausts the pool. The real fix is migrating those last code paths to miniaudio. Project-side, not engine-side.

2. **UiSettingsComponent::OnResolutionToggle crash, graphical-server-specific (14:19 CDT, second session)**: User-triggered crash when changing resolution / toggling fullscreen via the in-game settings UI. Stack: `MultiplayerSample::UiSettingsComponent::OnResolutionToggle` -> `AZ::Entity::Activate` -> `ApplyEffectiveActiveState` -> `GameEntityContextComponent::OnContextEntitiesAdded` -> `SpawnableEntitiesManager::ProcessRequest(SpawnAllEntitiesCommand)` -> assertion -> later SIGABRT. Server died ~19 s after client (cascading network timeout). The resolution-toggle code path triggers a respawn of all NewStarbase entities (probably to handle pipeline reconfigure for the new resolution); the respawn cascade hits an assertion. MPS-side bug; the offending code is in `Gem/Code/Source/Components/UI/UiSettingsComponent.cpp`. Preceding warning: `[Warning] (FrameGraph) - Invalid State: attachment 'Root.MainPipeline_-10.PipelineOutput' was added but never used!` -- the FrameGraph rebuild path is part of the resolution-toggle response. Crash logs at `/tmp/mps-crash-2026-05-22/{Game.log.resolution-toggle,client-stdout.resolution-toggle.log,server-stdout.resolution-toggle.log}`. **Refined 14:25 CDT after retest with `HeadlessServerLauncher`: the crash is specific to the graphical `ServerLauncher` variant.** With the headless server, the client's resolution change goes through cleanly because the server has no rendering pipeline to reconfigure and doesn't respawn entities on the broadcast. The dual-respawn race between graphical-server + client is the actual root cause; the `UiSettingsComponent` code itself is fine, it just exposes a server-vs-client coupling that breaks under load. **Operational rule for stable interactive use: graphical `ServerLauncher` is dev/debug only, never touch settings menu while it's running; for sustained play use `HeadlessServerLauncher`, which is also what production-deployed MPS would use anyway.**

Neither is Linux-specific or related to our packaging or the PR #501/#502 gem-double-load. JT's "community devs have private fixes that never upstreamed" framing likely covers exactly these gameplay-side fragility classes. Not filing upstream right now; we have a release in 5 days and these aren't blockers. Worth coming back to post-26.05.0 for two upstream issues / PRs:

- engine: AudioSystemAllocator default capacity is too low for documented gameplay session length
- multiplayersample: UiSettingsComponent::OnResolutionToggle asserts when respawning NewStarbase entities

For interactive demo / screenshot purposes, MPS is fine. Avoid the in-game settings menu (don't toggle fullscreen / resolution) and keep sessions short to avoid the audio exhaustion. Test infrastructure (Tier 9 / Tier 11) doesn't exercise either path, so our CI stays green.

Lessons:
- When a stack frame implicates a system gem (LyShine), check upstream load order + project-side gem-dep graphs before filing against the system gem. The actual culprit was 3 frames up from where I was looking.
- `add_dependencies` on a GEM_MODULE target in O3DE is NOT a build-only dep. The engine's gem walker reads it as a runtime LOAD dep. There's no current escape-hatch to express "build but don't load." Engine-side feature request parked.
- Tier 11 (post-load liveness) earned its keep: caught a real upstream regression on its first non-NewspaperDeliveryGame run.

## 2026-05-21 session capture

Big day. RC-build prep, Tier 10 unblocked + first clean pass, AP search-bar fix research, MSVC gate-value research, dev-snapshot RPM build succeeded after 4 attempts of spec drift gating.

### Wins

- **PR #19725 (UV transform Vulkan fix) cherry-picked into stabilization/26050** as PR #19772 (merge commit 91aac37, 2026-05-21 11:26 UTC). Tip moved 2956111 -> 91aac37. RC-trigger sequence cued up but waiting on Mike_C's engine-version bump to 2.6.0 per the consensus from sig-release "Internal Version Number" thread.
- **PR #19776 (AP search bar fix) filed by zakmat and verified F44.** Posted [#19773-style verification comment](https://github.com/o3de/o3de/pull/19776#issuecomment-4508543839) -- one-line fix to AssetTreeFilterModel.cpp, mismatched writer (`setFilterRegExp`) vs reader (`filterRegularExpression`) introduced by PR #19282's incomplete qt6 migration. Pre-build a dev-tree AP with patch in 22s on warm build dir; search works after.
- **MSVC 2026 patch gate analysis.** Microsoft compiler-versions table confirmed `_MSC_VER >= 1938` (the current gate in VSCompat.h) is the deprecation point (VS 2022 17.8), not the removal point. Removal landed at 1951 (MSVC 14.51, May 6 2026), not 1950 (14.50 RTM still had it). Nick_L + Cheddarspice testing the new gate value now.
- **Tier 10 NewspaperDeliveryGame unblocked + first clean pass.** Mike_C/amzn-changml fixed the LFS server-side 403. Local recovery sequence: `git reset --hard HEAD` (the original broken-LFS clone never had smudge-filter run, so working tree was missing 145 files until reset triggered it). First clean Tier 10 pass 6/0 on F44 -- AP batch processed 3697 jobs (60 min cold cache), GameLauncher ran 15s without crash markers. Posted [verification comment](https://github.com/o3de/NewspaperDeliveryGame/issues/19#issuecomment-4513674098). Dropped BLOCKED annotation in tests/README.md.
- **Snapshot-development COPR build 10493483 GREEN** across F44 + rawhide + CS10 after 4 attempts. Caught 9 patches + the `lib64/` entry as dev-tip drift that needed gating under `--with development_snapshot`. The pattern keeps holding: every upstream `find_package`-style migration (assimp, recast) breaks our carry-patches whose context anchors are now gone.

### Filed upstream

- **[o3de/o3de#19773](https://github.com/o3de/o3de/issues/19773)** -- Android-Asset workflow tar.exe / libarchive false positive (from 2026-05-20). Status: open, awaiting sig-build triage.
- **[o3de/NewspaperDeliveryGame#19](https://github.com/o3de/NewspaperDeliveryGame/issues/19)** -- LFS 403 (server-side fixed; comment posted, issue still open).
- **[o3de/o3de#19776](https://github.com/o3de/o3de/pull/19776)** -- not filed by us, but cross-platform-verification comment posted.

### Gotchas caught

- **Phantom venv-lib engine registration.** Nick's `o3de_manifest.json` had `~/.o3de/Python/venv/673a0e36/lib` registered as an engine -- artifact of his other-session experimenting. AP's discovery walked the registered engines, found the engine.json symlink target there first, and skipped the install path as "already found." Recovery: `o3de.sh register --remove --engine-path <path>`. Patch0003's symlink is NOT structurally responsible (verified by nuking + recreating the venv; phantom did NOT auto-recur).
- **Stale dev-tree AP daemon blocks new launcher negotiations.** The AP I'd left running from the search-bar test (against AiCompanionTest + dev-tree engine) caught the Tier 10 GameLauncher's connection attempt and rejected it (different project). Killed PID 449491 -> Tier 10 passed clean. Lesson: any AP running for ANY project will catch connection attempts and reject mismatches; only run one AP at a time, or none.
- **Dev-snapshot %files audit needed alongside %prep audit.** Build 10492367 compiled successfully for 4h then died at %files on missing `lib64/` (Recast moved from bundled install to find-package shim upstream). %prep failures cost minutes; %files failures cost hours. Captured in [[feedback_dev_snapshot_preflight_should_include_files_section]].
- **Authorization-vs-content rules.** Posted PR #19776 comment on a "#1"-captioned screenshot that I read as approval but was just context. Caught + memory note saved: [[feedback_explicit_approval_required_for_upstream_posts]]. ONLY explicit verbal go counts.

### State at end of session

- Spec at 2605.0-66 (dev-snapshot bcond now covers 9 patches + lib64/).
- Stabilization tip: `91aac37` (UV fix in).
- Waiting on Mike_C's 2.6.0 engine-version bump to trigger RC build.
- Polling task `bsz160gem` still watching stabilization tip.
- Memory: [[feedback_verify_api_change_version_not_just_release_version]], [[feedback_dev_snapshot_preflight_should_include_files_section]], [[feedback_explicit_approval_required_for_upstream_posts]] all saved.

---

## 2026-05-20 session capture

Tier 10 staged but blocked on upstream LFS. Android-Asset tar.exe corruption diagnosed and filed.

### Filed upstream

- **[o3de/o3de#19773](https://github.com/o3de/o3de/issues/19773)** -- Android-Asset workflow silently uploads truncated artifacts (tar.exe / libarchive false positive on Windows runners). Root cause: [libarchive#1630](https://github.com/libarchive/libarchive/issues/1630) -- Windows NTFS truncated 48-bit pseudo-inode collision triggers "Can't add archive to itself" false positive that silently skips files while tar exits 0. Cascading: poisoned archive uploaded, next run downloads it, AP fails on missing files, new poisoned archive uploaded, repeat. Issue includes inline diffs for two fixes: option 1 (workflow YAML detect-and-fail, applies to both android-build.yml + windows-build.yml), option 2 (drop --zeroAnalysisMode from Android asset_profile build config). Labels: kind/bug, sig/build, platform/windows, platform/android, feature/build.

### Tier 10 status

- **Infrastructure committed:** `tests/newspaper-delivery-build-test.sh` (200+ lines, pinned to nickschuetz/NewspaperDeliveryGame@80d94e7, 2-pass absorber for AP cold-cache quirk), `make test-newspaper-delivery` target, Tier 10 row added to `tests/README.md` (marked BLOCKED), Tier 10 node added to ARCHITECTURE.md diagram.
- **Blocked on:** [o3de/NewspaperDeliveryGame#19](https://github.com/o3de/NewspaperDeliveryGame/issues/19). Atomic mint-and-fetch test 2026-05-20 15:31 UTC reproduced the 403: Batch API returns 200 with fresh signed URL; CloudFront returns 403 AccessDenied (RequestId AZJ4F76QT52WX2N1). Mike_C self-claimed and is fixing, "inbetween things atm" -- no ETA but he committed to GHI updates. Don't nudge.
- **What's recoverable without LFS:** project structure (300 non-LFS files: 159 .material + 42 .prefab + 29 Media/*.png + 18 .json + 13 .scriptcanvas + 6 .setreg + 6 .cmake + assorted configs). Could run a degraded smoke test that registers the project + runs AP over the non-LFS subset (would fail on .fbx/.png/.actor LFS pointers but validate the script_only side of the project). Not implemented; holding for LFS fix.

### Trigger sequence on LFS unblock

1. Retry `git lfs pull` in `/home/nschuetz/o3de-test-projects/NewspaperDeliveryGame` -- if 200 OK on at least one signed URL, unblock confirmed.
2. Drop the BLOCKED annotation from Tier 10's row in `tests/README.md`.
3. Run `make test-newspaper-delivery` for the actual validation.
4. If the smoke passes: commit the unblock + send Mike_C a thank-you. If it fails: capture error, file a separate issue (don't reopen #19 since that one was specifically about LFS). Note: project.json `engine_version: 4.2.0` vs runtime 26.05.0 is INFORMATIONAL ONLY, not a compatibility gate -- internal versioning and release versioning are intentionally decoupled per the ongoing sig-release "Internal Version Number" thread (Matteo / Nick_L / Mike_C). Real compatibility test is "do the gems / asset shapes / scripting APIs still work" -- which is what the Tier 10 run actually validates.

### Note on community sample maintenance gap (Mike_C TSC 2026-05-20)

Mike_C raised at TSC: API/ABI changes per engine release mean community sample projects (NewspaperDeliveryGame, multiplayersample, etc.) will silently rot unless volunteers maintain them. Sig-release thought process is "they're out there, people will look at them and try them" -- but the actual maintenance gap is real. This is a sig-build / sig-content structural issue, not ours to solve. Captured in [[project_o3de_sample_maintenance_gap]] memory note for future reference.

---

## 2026-05-18 session capture

Cherry-picks landed + release blocker mitigated + new bcond shipped.

### Wins

- **Release blocker [#19754](https://github.com/o3de/o3de/issues/19754) mitigated.** [PR #19758](https://github.com/o3de/o3de/pull/19758) (MSVC 2026 compile fixes) merged directly to `stabilization/26050` by nick-l-o3de at 2026-05-18 14:42 UTC. Issue #19754 still technically OPEN (probably paperwork) but the fix has landed. 2026-05-27 release date no longer AT RISK.
- **Three cherry-picks landed in stabilization/26050 today.** Tip moved `246b46f` -> `295611159e6b`:
  - [#19757](https://github.com/o3de/o3de/pull/19757) preWarm particle migrated to new OPS formats (2026-05-16, Mateusz Zak)
  - [#19758](https://github.com/o3de/o3de/pull/19758) MSVC 2026 compile fixes (2026-05-18, the release-blocker)
  - [#19739](https://github.com/o3de/o3de/pull/19739) project-local AzTestRunner for SDK-installed builds (2026-05-18, Mateusz Zak)
- **[PR #19746](https://github.com/o3de/o3de/pull/19746) merged into development** by nick-l-o3de this morning (2026-05-17 11:40 UTC; review + merge within 30s of the commit landing). ProcessWatcher prctl threading doc -- our (a) of the four-level [#19745](https://github.com/o3de/o3de/issues/19745) fix sequence. Total upstream merges in May now stands at **9 PRs**.
- **Issue [#19745](https://github.com/o3de/o3de/issues/19745) status update posted.** Body edited to flip `Status: draft PR ready` -> `Status: MERGED` lines for (a) and (b); status comment posted noting both #19746 + #19747 merged, (c) BuilderManager refactor + (d) ProcessLauncher refactor remain as future architectural work. Lifecycle decision deferred to nick-l.
- **New `--with development_snapshot` bcond shipped.** Gates 6 carry-patches whose upstream equivalents have merged into o3de/development but NOT into stabilization/26050:
  - Patch0001 (#19748 clang21), Patch0002 (#19751 manifest.py engine path), Patch0005 (#19750 AzQtComponents title), Patch0007 (#19734 libtiff C99), Patch0008 (#19733 Lua lobject), Patch0012 (#19747 AssetBuilder watchdog).
  - Default OFF so stabilization / snapshot / experimental channels apply all 13 patches as before.
  - `Makefile`'s `copr-snapshot-development` target sets the flag automatically via `SNAPSHOT_REF_EXTRA_BCOND`.
  - Verified spec parse: 13 patches default, 7 with `--with development_snapshot`.
- **PR [#19752](https://github.com/o3de/o3de/pull/19752) thread advanced.** Posted two further clarifications (Windows MSI scope question + setup.py vs PEP 660 / `.egg-info`-into-source-tree mechanism). nick-l replied confirming MSI ships everything (not just binaries); diagnosis matches our EROFS empirically. Discord side-thread (2026-05-18) had nick-l writing he was "under the impression" that `pip install -e` doesn't modify the source folder -- which holds for PEP 660 packages but NOT legacy setup.py packages. Discord follow-up draft ready (single-paragraph form); declined to send pending nick-l circling back to the PR.
- **PR #19725 (UV transform Vulkan fix) validation initiated.** Author Styx-Hc, merged to development 2026-05-08 by nick-l-o3de. NOT in stabilization yet (verified via blob-SHA mismatch on Transform2DFunctor.cpp). Linux is exclusively Vulkan so the bug actively affected Linux users for any UV-transformed material. JT [SCB_GameDesign] clarified Mac/iOS are not officially supported per SIG-Platform; Qt 6 migration is the path to "fully usable" by Fall release -- so Mac validation deferred to 26.10.0. Linux test per nick-l-o3de: "go into mat editor and mess with uv offset" -- if it does nothing, broken; if it transforms, fixed. We fired `make copr-snapshot-development` against dev tip; the new bcond makes this build path actually work.
- **Stabilization rebuild 10476214 GREEN across all 3 chroots** (F44 + rawhide + CS10, ended ~17:00 CDT, ~5.5h wall). Absorbs today's cherry-picks (#19758 MSVC + #19757 preWarm + #19739 AzTestRunner SDK). Clean RC baseline going into the 2026-05-27 release window. Supersedes the canceled 10476087.
- **Snapshot-development rebuild 10476223 FAILED at SRPM rebuild** -- the local SRPM (built with `--with development_snapshot` and only 7 patches) was rejected by COPR's mock chroot because COPR re-evaluated the spec with the chroot's default bconds (all OFF) and tried to apply all 13 patches; the 6 gated-off patches threw `Bad file: /builddir/build/SOURCES/00NN-*.patch: No such file or directory`. **This is a manifestation of [[feedback_copr_with_propagation]]** -- `--with` flags don't carry through SRPM rebuild. Recovery requires setting `--rpmbuild-with development_snapshot` on the chroot config via `copr-cli edit-chroot`. **Captured in commit `6187fb1` doc updates** but not yet resubmitted.

### Gotchas caught

- **`make copr-stabilization-and-test` uses spec's hardcoded `snapshot_commit`, not a fresh fetch.** First attempt this morning re-built against old `246b46f` (the pre-cherry-pick commit), which would have produced the same content as build 10460860 (no value added). Caught after build 10476087 already started running on COPR; canceled via `copr-cli cancel` per [[feedback_cancel_doomed_copr_builds]] (saved ~5h CI runner time). The right workflow is: bump `snapshot_commit` in the spec FIRST, then run `make copr-stabilization-and-test`. Recovery sequence: `cd sources && ./make-snapshot-tarball.sh stabilization/26050` -> paste new commit/date/sha into spec macros at lines 133-135 -> commit -> run stabilization target.
- **Snapshot-against-development is structurally broken without the new bcond.** First `copr-snapshot-development` attempt (build 10475746) failed at `%prep` in ~4 minutes with `1 out of 1 hunk FAILED -- saving rejects to file cmake/Platform/Common/Clang/Configurations_clang.cmake.rej` -- Patch0001's upstream equivalent ([#19748](https://github.com/o3de/o3de/pull/19748)) is already in development tip, so the patch fails to apply. Six of our 13 carry-patches are in this state. The new `--with development_snapshot` bcond is the fix.
- **NEW (2026-05-18): `--with` flags don't propagate through COPR's SRPM rebuild even with the spec-side bcond gate in place.** Build 10476223 failed because COPR ignored the local `--with development_snapshot` flag baked into the SRPM (only 7 patches inside) and re-evaluated the spec under chroot defaults (all 13 expected). The full fix is two-sided: (a) the spec-side `%bcond_with development_snapshot` is the SRPM-build half (✓ shipped in commit `6187fb1`); (b) the chroot-config-side `--rpmbuild-with development_snapshot` is the COPR-rebuild half (NOT shipped yet -- requires `copr-cli edit-chroot --rpmbuild-with development_snapshot hellaenergy/o3de-snapshot/fedora-44-x86_64` etc. per chroot). Also: this needs to be UNSET when subsequent builds in the same project target a non-development ref like the `qt6` branch (those still want all 13 patches).

### Doc updates this session

- spec: `%changelog 2605.0-63` + new bcond `%bcond_with development_snapshot` + six `%if %{without development_snapshot}` blocks around merged-upstream patches
- Makefile: `SNAPSHOT_REF_EXTRA_BCOND` variable + wired into `srpm-snapshot-ref` + `copr-snapshot-development`
- SBOM bumped 62 -> 63
- This entry + bcond mentions in README / CONTRIBUTING / ARCHITECTURE / FLATPAK_NOTES (mirror)
- Memory: `user_discord_handle.md` (Nick = "Hellaenergy [Red Hat]" on Discord)

### Loaded for next session

- Stabilization rebuild 10476214 LANDED GREEN. 26.05.0-readiness baseline established.
- PR #19725 UV transform validation: confirmed working on Linux/Vulkan via local standalone build (Fedora 44 + NVIDIA RTX 2080 Ti). Result posted to PR thread. Cherry-pick decision into stabilization/26050 is in nick-l's court; hex's Ubuntu 24.04 result expected 2026-05-19. If the cherry-pick lands, follow `project_uv_fix_cherry_pick_trigger.md` for the new-stabilization-build trigger sequence.
- Open question on what to do with [PR #19725](https://github.com/o3de/o3de/pull/19725): not cherry-picked into stabilization today. Either nick-l doesn't consider it critical enough for 26.05.0, or it's coming in a later batch. Either way, our validation result feeds back to the cherry-pick decision.
- nick-l's Discord question about `pip install -e` setup.py vs PEP 660 still open; he hasn't circled back to PR #19752 since the 2026-05-16 thread.

---

## 2026-05-14 session capture (busy day)

Built on yesterday's Patch0013 v4 GREEN result. Today was promotion + upstream-merge + Tier 9 day.

### Wins

- **5 of 6 filed upstream PRs MERGED.** Three landed today (2026-05-14 ~13:42-13:44 UTC) on `o3de/o3de:development`:
  - [#19748](https://github.com/o3de/o3de/pull/19748) (clang21 -Wno-error=) -- 2 approvals, CI clean. nick-l-o3de flagged for 26.05.0 cherry-pick consideration ("we may need this one for this release").
  - [#19750](https://github.com/o3de/o3de/pull/19750) (AzQtComponents title propagation) -- approved, clean.
  - [#19751](https://github.com/o3de/o3de/pull/19751) (manifest.py O3DE_ENGINE_PATH) -- approved, clean.
  Plus the two from 2026-05-08: [#19733](https://github.com/o3de/o3de/pull/19733) (Lua include) + [#19734](https://github.com/o3de/o3de/pull/19734) (libtiff C99). Still open: [#19746](https://github.com/o3de/o3de/pull/19746) (ProcessWatcher doc-only, no review activity), [#19747](https://github.com/o3de/o3de/pull/19747) (watchdog, nick-l-o3de "okay with accepting this for now"), [#19752](https://github.com/o3de/o3de/pull/19752) (LYPython sdist, nick-l-o3de actively investigating).
- **TIMEBOMB doc sweep** -- 5 carry-patches now formally marked TIMEBOMB in README + CONTRIBUTING patch tables: Patch0001/0002/0005 (today's merges) + Patch0007/0008 (last week's). All stay active until our snapshot pin re-pins post-release.
- **Stage 2 (`system_dxc` + `system_spirvcross` + `system_mcpp`) promoted to o3de-stabilization** alongside the Stage 1 14-pack. Spec changelog 2605.0-60. Build 10460860 in flight (resubmitted after the EPEL-10 CS10 gotcha -- see below).
- **CS10 with_opts gap FULLY CLOSED 2026-05-14 AM.** experimental CS10 = 19/19 matches F44+rawhide. stabilization CS10 = 14/14 (15 post-Stage-2 promotion) matches F44+rawhide. All 7 prior-missing packages confirmed in CS10 base + EPEL-10 via `dnf repoquery`.
- **Snapshot 10460369 SUCCEEDED** -- clean stabilization/26050-source build via `make copr-snapshot`. Restored o3de-snapshot channel to non-failed state. (Note: `make copr-snapshot-development` is still expected to fail against dev tip due to Patch0001 TIMEBOMB reject -- deferred to post-release.)
- **Tier 9 implemented** -- `tests/multiplayersample-build-test.sh` + `make test-multiplayer-sample`. Validates the full project-build pipeline against the installed o3de2605 RPM (clone o3de-multiplayersample + companion -assets, register, cmake configure + ninja build, AssetProcessorBatch full project bake, GameLauncher smoke). Tier 10/11 (visual regression / render correctness) bumped to future entries. tests/README.md updated.
- **Snapshot helper /home tmpfs fix** -- `sources/make-snapshot-tarball.sh` now uses `$HOME/.cache/o3de-snapshot-tarball` (was `/tmp`). The O3DE LFS checkout overflows the default 16GiB tmpfs and triggered `disk quota exceeded` mid-clone. Trap-cleanup preserved.
- **Documented Gmail-MCP draft-only limitation** -- Gmail connector creates drafts but doesn't send. PushNotification is the right mechanism for build-state alerts. Remote Control + Claude mobile app is the path for "interact from phone while keeping session on workstation."

### Gotchas caught + memory'd

- **COPR `--repos` REPLACE semantics** -- same gotcha shape as `--rpmbuild-with`. While wiring up Stage 2 stabilization promotion, I set `--repos copr://hellaenergy/o3de-dependencies` on the CS10 chroot which REPLACED an implicit EPEL-10 setting. Build 10459758 then failed CS10 at BR resolution (assimp-devel, google-benchmark-devel, poly2tri-devel, pkgconfig(libunwind) all missing). Fc44 + rawhide dragged down with CS10 (COPR kills the whole build when any chroot fails). ~3h compute wasted. Fix: full intended repo list in one shot: `--repos "https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/ copr://hellaenergy/o3de-dependencies"`. Memory `feedback_copr_edit_chroot_replaces.md` expanded.
- **Tier 9 RAM-hungry link step** -- two host crashes (32 GB workstation) during ninja's parallel C++ link phase. Each large engine/gem .so link consumes 6-10 GB; default `--parallel $(nproc)` OOMs on tight systems. Script now auto-throttles via `MPSAMPLE_PARALLEL=max(2, MemTotal_GiB/8)` on <48GB hosts. Memory: `project_tier9_ram_constraint.md`. RAM upgrade 32GB -> 64GB landed afternoon 2026-05-14; throttle no longer kicks in.
- **Release blocker [#19754](https://github.com/o3de/o3de/issues/19754)** -- MSVC 2026 dropped `stdext::make_checked_array_iterator`; bundled Qt 5.15 unconditionally uses it on MSVC. nick-l-o3de filed today as a release blocker for 26.05.0. **Windows-only**; Linux Fedora packaging unaffected. 2026-05-27 release date now at-risk; the 5 TIMEBOMB carry-patches stay active longer if release slips. Memory `project_2605_release_date.md` updated.

### Tier 9 investigation arc -- full breakdown of the 19 failures

The day went deep on Tier 9 step 5 after the initial 19-failure observation. Final attribution + resolution:

**Round 1 (1593/1612 cold-bake, 19 failures attributed to "Pick_Ups/Gems materials")**

Initial superficial grep showed all 19 in `level_art_mps/Assets/Pick_Ups/Gems[/skins]/*.material`. Real composition turned out to be 11 + 8, three distinct root causes.

**11 .material failures -- real upstream bug** (fixed by [PR #177](https://github.com/o3de/o3de-multiplayersample-assets/pull/177))

Eleven files reference `standardpbr.materialtype` (lowercase) but engine ships `StandardPBR.materialtype` (CamelCase). Linux case-sensitive FS fails; Windows/macOS case-insensitive FS silently folds. Bug latent on `development`, `main`, AND `stabilization/25100` -- present since the assets were authored. Mechanical fix: rename the reference in all 11 files. Filed as:

- Issue: [o3de/o3de-multiplayersample-assets#176](https://github.com/o3de/o3de-multiplayersample-assets/issues/176)
- PR: [o3de/o3de-multiplayersample-assets#177](https://github.com/o3de/o3de-multiplayersample-assets/pull/177) -- 11 files, 11 lines, all mechanical, DCO-signed, validation evidence on PR

**8 .scriptcanvas failures -- Tier 9 harness bug, NOT upstream**

`WeaponImpactDecal.scriptcanvas` + `ShieldGeneratorRoundEffects.scriptcanvas` (2 source files * per-platform job variants = 8 failed jobs). Reference `NetworkHealthComponent` + `SendHealthDelta` + `Network Match Component Requests` -- MultiplayerSample's own multiplayer components. AP failed to load `libMultiplayerSample.so` (`ComponentApplication: Failed to load dynamic library at path "libMultiplayerSample.so"`), so the BehaviorContext didn't have these components reflected, so the scriptcanvas couldn't deserialize, so deserialization hit a rapidjson assert. Root cause: Tier 9 only built `MultiplayerSample.GameLauncher` which produces `libMultiplayerSample.Client.so`; AP needs the bare (no-suffix) `libMultiplayerSample.so` to load the gem at build time. Fix: also build the bare `MultiplayerSample` target (commit `7a0e547`).

**Clean re-run with both fixes**: 6010 successfully processed (up from 1593 -- because AP could now process gem-dependent assets it previously couldn't), **1 remaining failure**. Different class:

**1 preWarm.particle failure -- engine-side AP JobDependency declaration gap** (filed as [o3de/o3de#19755](https://github.com/o3de/o3de/issues/19755))

`OpenParticleSystem/Assets/Particles/preWarm.particle` failed cold-cache with `ParticleAssetData: Cannot create particle data - no material assigned to render in emitter Emitter`. The .particle file's `material` reference is well-formed (`ParticleSpriteEmit.material`); the referenced material is in our RPM and bakes cleanly elsewhere in the same run -- just AFTER preWarm.particle in AP's processing order. preWarm's alphabetic position puts it before its dep. Second AP pass succeeds (material is now cached). Same shape as the original Tier 7 ShaderAssetBuilder/SRG-merge ordering quirk: builder's `CreateJobs` doesn't declare `JobDependency` on the referenced upstream asset.

Filed at o3de/o3de#19755 with diagnostic + repro + workaround + proposed fix direction. Mechanical fix would be ~5 lines in `ParticleBuilder::CreateJobs` -- offered to PR if sig/graphics-audio wants the help. Memory note: `project_ap_jobdep_cold_cache_pattern.md` (recurring pattern; likely more instances exist).

**Tier 9 hardened with 2-pass AP absorber** (commit `dab77ab`)

Step 5 now runs AP batch once; if pass 1 had failures, runs a second pass; counts overall PASS if pass 2 is clean (with a log line noting the cold-cache quirk was absorbed). This makes Tier 9 robust against the JobDependency gap class without false-flagging the test. Real failures (failures that persist into pass 2) still fail loudly.

**Final Tier 9 state**: validated end-to-end, 0 failures with case-fix branch active + bare-target built + 2-pass absorber, GameLauncher smoke PASS. Committed `tests/multiplayersample-build-test.sh` with full doc comments explaining all three findings.

### State of in-flight work at end of session

- **Build 10460860 (stabilization 14+3 pack, EPEL-10 fix)**: running on COPR, fc44 at ~54-60% ninja last check. ~1-2h to terminal. CI test trigger chained via `make copr-stabilization-and-test`. If green, ships the Stage 1 14-pack + Stage 2 3-pack + Patch0012 v2 + CS10-parity all in one promotion.
- **Build 10460369 (snapshot, clean stabilization/26050 source)**: SUCCEEDED. Restored o3de-snapshot channel to non-failed state.
- **Tier 9 local**: VALIDATED end-to-end. 6010 assets baked clean on the case-fix branch with bare-target built; 2-pass AP absorber added to handle cold-cache JobDependency quirk. Zero remaining failures.
- **Remote Control session**: armed (Nick ran `/remote-control` to expose this CLI session to claude.ai/code + the Claude mobile app).
- **Spec at 2605.0-61.** 13 active patches (5 TIMEBOMBs marked).

### Filed today

- Issue: [o3de/o3de-multiplayersample-assets#176](https://github.com/o3de/o3de-multiplayersample-assets/issues/176) (case-sensitivity bug)
- PR: [o3de/o3de-multiplayersample-assets#177](https://github.com/o3de/o3de-multiplayersample-assets/pull/177) (mechanical 11-file fix; validation evidence in comments)
- Issue: [o3de/o3de#19755](https://github.com/o3de/o3de/issues/19755) (ParticleBuilder JobDependency gap, sig/graphics-audio)

### Loaded for next session

- Watch 10460860 terminal state; if green, the 14+3 + Stage 2 + Patch0012 v2 + CS10-parity promotion is officially live in o3de-stabilization. Draft community announcement (mention the Tier 9 validation as confidence-builder).
- Optional: pokes for [#19746](https://github.com/o3de/o3de/pull/19746) (silent) and [#19747](https://github.com/o3de/o3de/pull/19747) (informal-approval-not-formalized).
- Tier 9 follow-ups (low priority): more AP audits will likely surface more JobDependency-gap instances; add rows to `project_ap_jobdep_cold_cache_pattern.md` as they appear. If sig/graphics-audio engages on #19755, offer the ParticleBuilder PR.
- Post-release-day work: snapshot pin re-pin to 2605.0 tag, Patch0001/0002/0005/0007/0008 retirement re-check, COPR rebuild from release tag, tester announcement. **Note 2026-05-27 release date is AT RISK per [#19754](https://github.com/o3de/o3de/issues/19754).**
- snapshot-against-development TIMEBOMB-skip path: deferred until post-release (`make copr-snapshot-development` will keep failing on Patch0001 reject until then).

---

## 2026-05-13/14 overnight: Patch0013 v4 lands GREEN

Build 10457745 (Patch0013 v4, experimental, 5.5h runtime) **SUCCEEDED on all three chroots** (fc44 + rawhide + CS10) at 04:03 UTC on 2026-05-14. Outcomes:

- **14th Stage 1 system swap (`system_vulkan_validation_layers`) is validated end-to-end** -- experimental now runs Stage 1 14-pack + Stage 2 3-pack on F44 + rawhide; CS10 runs Stage 1 12-pack + Stage 2 3-pack (CS10 with_opts missing googlebenchmark + vulkan_validation_layers, presumed unavailable in CS10 base + EPEL-10 -- unverified, low priority).
- **CS10 viability reconfirmed** -- second consecutive green CS10 build with 17 swaps active (10456101 then 10457745). Memory note `project_cs10_with_opts_gap.md` updated to reflect mostly-closed gap.
- **Patch0013 v3 -> v4 diagnosis** -- v3 failed at cmake configure with `Findvulkan-validationlayers.cmake must either be part of this project itself...` because the patch gated `ly_associate_package` in `BuiltInPackages_linux_x86_64.cmake` but didn't gate `VULKAN_VALIDATION_LAYER` in `Gems/Atom/RHI/Vulkan/Code/Source/Platform/Linux/PAL_linux.cmake` -- the gem still expanded `${VULKAN_VALIDATION_LAYER}` to `3rdParty::vulkan-validationlayers` in BUILD_DEPENDENCIES and `ly_parse_third_party_dependencies` walked the list. v4 adds the third hunk to gate the variable assignment (left unset in system mode so `${VULKAN_VALIDATION_LAYER}` expands to nothing in the BUILD_DEPENDENCIES list).
- **Docs sweep** -- README + CONTRIBUTING patch tables 12 -> 13; copr-experimental instructions reflect 14-pack; FEDORA_ROADMAP + BUNDLED_LIBRARIES + ARCHITECTURE + FLATPAK_NOTES mirror the same.

State of in-flight work:

- Build 10457745 succeeded; spec at 2605.0-58; 13 active patches (Patch0001-0013).
- Pre-release sweep agent scheduled 2026-05-25 09:00 America/Chicago (trig_01Sd4hj6uh1J8ZQgADPNj7zi).
- Engine fork branch `builtinpackages-gate-vulkan-validation-on-system` has 2 commits (Patch0006 intermediate + Patch0013 v4). Squash before any upstream pitch (post-release).

Loaded for next session:

- Optional: propagate `system_vulkan_validation_layers` to CS10 chroot (verify pkg availability in CS10 base + EPEL-10 first).
- Optional: propagate `system_googlebenchmark` to CS10 chroot (same check).
- Optional: propagate the 6 missing Stage 1 swaps to o3de-stabilization CS10 chroot.
- Held: F44 AR builder pitch (per resource-constraints memory; offer only if sig-build signals felt need).
- Post-release: re-pin snapshot to 2605.0 release tag; re-run four-step retirement check on Patch0007 + Patch0008 against the re-pinned base.

---

## 2026-05-13 session capture

Work delivered today:

- **Stabilization 13-pack promotion landed early morning** -- `hellaenergy/o3de-stabilization` build 10452477 GREEN across F44 + rawhide + CS10. Adds googlebenchmark + Patch0012 v2 watchdog to the community-tester channel. CS10 included as a chroot.
- **Patch0013 (`system_vulkan_validation_layers` Stage 1 swap)** -- 14th system swap candidate. Engine fork branch + spec wiring + launcher pre-set of `VK_LAYER_PATH`. Three experimental build attempts: builds 10455992 + 10456041 both failed at %prep with "1 out of 1 hunk FAILED" because the patch context was generated against pre-Patch0006 state but %autosetup runs Patch0006 first. Fixed by rebuilding Patch0013 on top of a Patch0006-applied tree; v3 build 10456101 in flight (state: running as of 10:06).
- **Upstream stabilization-branch-locked context captured** (`project_2605_stabilization_branch_locked.md`). `o3de/o3de:stabilization/26050` is in pre-release lockdown until 2026-05-27 release; non-critical merges land on `development` only. Re-frames Patches 0007/0008 retirement timing (they stay until post-release snapshot pin re-pin) and reinforces the "no upstream PRs mid-window" stance.
- **`o3de/o3de:stabilization/26050` vs `hellaenergy/o3de-stabilization` naming-collision doc sweep** -- tightened the bare-"stabilization" framing in `FEDORA_ROADMAP.md` (4 spots) and `copr-metadata/o3de-experimental/instructions.md` (1 spot). Naming-collision concern memory-noted in the locked-branch memory.
- **AR / sig-build F44-builder Discord ping** -- drafted, pressure-tested twice for missed counter-questions (Ubuntu version selection; runner cost), final shape reframes the ask as "we can take this on (workflow PR ready)" rather than "please add F44 to AR for us". Nick will send when he gets to it.
- **Three new feedback-memory rules** captured from today's pressure-tests by Nick:
  - `feedback_gut_check_before_drafting_messages.md` -- pressure-test outgoing drafts for obvious counter-questions before suggesting
  - (Reinforced) `feedback_no_fabricated_timeframes_in_upstream.md`
  - (Reinforced) `feedback_check_prior_art_before_drafting_upstream.md`
- **Scope-creep walkbacks** (twice on the same topic) -- the engine-side validation-error issue I'd planned to file was tied to a `Requires`->`Recommends` demotion we're not doing. Dropped entirely.
- **`vulkan-validation-layers` Requires-vs-Recommends audit** -- decided to keep as `Requires` to avoid the RTFM-user silent-failure path (user runs `dnf autoremove`, layer removed, enables validation later, silent fail). Rest of system_X audit: correctly classified, no changes needed.

State of the in-flight work at end of session:

- Build 10456101 (Patch0013 v3) is running. Monitor `bq1zneskt` armed. Expected ~5h to terminal state.
- Pre-release sweep agent scheduled for 2026-05-25 09:00 CDT.
- Spec at 2605.0-57 (vulkan-validation-layers bcond + Patch0013 directive + launcher pre-set).
- 13 active patches in the spec (would be 14 once Patch0013 build is validated and we keep it active; or 13 still if we walk back).
- 7 upstream artifacts open in `o3de/o3de` -- no new review activity since this morning's nick-l-o3de + amzn-changml comments. Per the stabilization-locked memory, only #19748 (clang21) has a plausible 2605.0 cherry-pick case.

Open next-session items:

- If Patch0013 v3 lands green: update README + CONTRIBUTING patch tables 12 -> 13 (or 13 -> 14 if we kept the count), update `copr-metadata/o3de-experimental/instructions.md` to reflect the 14th Stage 1 swap as active.
- If Patch0013 v3 lands red: triage logs, identify cause.
- Engine fork branch `builtinpackages-gate-vulkan-validation-on-system` has 2 commits (Patch0006 intermediate + Patch0013) -- needs squash-to-1-commit cleanup BEFORE we file the upstream PR (which is post-release territory anyway).
- Patch0013 upstream PR -- post-release (stabilization locked + no-upstream-until-baked rule).
- AR-builder Discord ping -- Nick to send when he gets to it.

---

## CS10 engine build: FIRST EVER SUCCESS 2026-05-12 (build 10450340)

Major CS10 milestone: build 10450340 (`o3de-experimental`, `centos-stream-10-x86_64` chroot only, SRPM from spec 2605.0-53 with the `gcc-toolset-15-libatomic-devel` BR fix) completed end-to-end at 16:42 CDT and produced `o3de2605` + `o3de2605-devel` + SRPM artifacts tagged `1.el10`. First time any CS10 engine build has cleanly succeeded.

Caveat: this build ran with empty `--rpmbuild-with` flags (per `project_cs10_with_opts_gap.md` memory), so it shipped bundled-3p everywhere. Zero Stage 1 or Stage 2 swaps were exercised. Proves the engine COMPILES on CS10 once -latomic is in place, but the Stage 1/2 swap stack still hasn't been validated on CS10.

To make CS10 genuinely viable for end users:
- Trigger CS10 builds of the `o3de-dependencies` COPR project's packages (mikkelsen, azslc, ISPCTexComp, astc-encoder, PhysX, AWSNativeSDK, Qt5).
- Propagate `--rpmbuild-with` flags to the CS10 chroot via `copr-cli edit-chroot`.
- Re-build CS10 with the full Stage 1+2 swap stack and confirm it stays green.

These three steps are chained (deps need to exist before with_opts can fire). The release-day window is tight; CS10 viability with swaps may slip to post-release work.

---

## 26.05.0 release: 2026-05-27 (set 2026-05-12)

Sig-release chair (Nick) set the release date 2026-05-12. 15-day window. See memory `project_2605_release_date.md` for the full pre-release checklist; high-level packaging work:

- Watch o3de-extras#1052 + canonical.o3de.org#38 merge into stabilization/26050 + sync into the central catalog.
- Re-run the four-step retirement check on Patch0007 (libtiff) + Patch0008 (lobject) once stabilization/26050 absorbs the upstream merges of #19734 + #19733.
- Bump snapshot pin in o3de.spec to the release-tagged commit once 2605.0 is tagged; full COPR experimental + stabilization rebuild from the new pin.
- Update test-installed.yml cron target to the release-tagged build before May 27 to catch surprises.
- Announce version flip on `hellaenergy/o3de-stabilization` (community-tester COPR) and any tester Discord channels.
- Today's 6 upstream PRs (#19746-19752) sit on the 15-day review window. If maintainers review fast they land in 26.05.0; otherwise they slip to a backport or to 26.10.x. Either is fine; track but don't push.

---

## Upstream issue backlog (technical, no TSC needed)

### AssetBuilder.resident orphans on AssetProcessor death (raised 2026-05-12)

Seen repeatedly during ROS2_Project bake cycles: when AP dies (crash, GUI close, SIGKILL), its `AssetBuilder --resident` children get reparented to PID 1 / systemd-user and keep running indefinitely. Each AP restart leaves another ~3-6 ghost workers. Saw 18 accumulate in one batch, then 3 more in the next AP-restart cycle, in a single session.

Wastes ~300MB RSS per orphan + holds file descriptors / shared-memory segments. Eventually contends with newly-launched AP's own resident pool.

**Root cause**: AssetBuilder's main loop has no parent-death detection. Doesn't call `prctl(PR_SET_PDEATHSIG)`, doesn't poll `getppid()` for reparenting (a return of 1 means original parent died), doesn't treat IPC channel close as fatal.

**Fix is mechanically trivial -- 5 lines of C++**:

In the AssetBuilder resident main():
```cpp
#if defined(AZ_PLATFORM_LINUX)
#include <sys/prctl.h>
prctl(PR_SET_PDEATHSIG, SIGTERM);
#endif
```

Kernel sends SIGTERM when AP dies. Linux-only but resident mode IS Linux/macOS-relevant; macOS would need a different approach (kqueue NOTE_EXIT on parent pid).

**Action items**:
- File upstream issue at `o3de/o3de` describing the orphan pattern + reproduction steps (`pkill -9 <AP-pid>` then `ps -o pid,ppid,comm -C AssetBuilder` shows orphans with PPID 1 or systemd-user PID).
- Open PR with the `m_tetherLifetime` change (`Code/Tools/AssetProcessor/native/utilities/Builder.cpp`). Engine already plumbs this through ProcessLauncher cross-platform; AP just never opted in.
- Low-risk, well-scoped, single-file change. Good first-PR material.

**Status (2026-05-12 10:30)**: **v2 watchdog approach RUNTIME-VALIDATED.** v1 (prctl-based) was withdrawn earlier today after the kernel-binds-PDEATHSIG-to-forking-thread footgun was diagnosed. v2 (child-side getppid() polling in AssetBuilder/main.cpp) was committed as Patch0012 in spec 2605.0-52, built locally in ~34 min, dnf-reinstalled, and verified end-to-end:

- Editor launches cleanly (no SIGTERM-cascade like v1)
- AP spawns its resident builder pool normally
- `kill -9 <AP-pid>` with 2 alive builders attached -> both builders self-exited within 4 seconds of AP death
- Zero alive orphans at T+4s and T+8s
- No regression in clean-shutdown path

v2 patch shipping as `sources/0012-v2-assetbuilder-parent-watchdog.patch`. Engine commit on branch `assetbuilder-parent-death-watchdog` (62fdd36e) in nickschuetz/o3de fork. Doc-comment companion commit on `processwatcher-pdeathsig-doc` (2f95c7af).

**Upstream submission**: FILED 2026-05-12 10:40. Three artifacts as a coordinated trio:

- **Issue [o3de/o3de#19745](https://github.com/o3de/o3de/issues/19745)** -- "BuilderManager forks AssetBuilders from short-lived TaskWorker threads, silently breaking m_tetherLifetime". Frames the architectural cause + proposes four fix directions (doc / watchdog / BuilderManager refactor / ProcessLauncher refactor).
- **PR [o3de/o3de#19746](https://github.com/o3de/o3de/pull/19746)** -- "ProcessWatcher: document prctl(PR_SET_PDEATHSIG) threading constraint". 20-line warning comment next to the prctl call. Doc-only, smallest piece, expected to land first.
- **PR [o3de/o3de#19747](https://github.com/o3de/o3de/pull/19747)** -- "AssetBuilder: add child-side parent-death watchdog". The v2 watchdog patch itself. Cross-references both #19745 and #19746.

Branches in nickschuetz/o3de fork: `assetbuilder-parent-death-watchdog` (62fdd36e) and `processwatcher-pdeathsig-doc` (2f95c7af). Both DCO-signed, ASCII-clean, single-commit, against fresh `upstream/development`.

Drafts retained in `upstream-drafts/` as historical reference for the body content + design conversation.

**Original v1 failure history (kept for context):**
v1 COPR 10447331 built green on F44 + rawhide; on `dnf reinstall` + AP launch, every spawned builder received SIGTERM within ~21 ms of fork and AP could never establish a resident pool. Editor hung at "Asset Processor working...".

**Root cause:** `PR_SET_PDEATHSIG` (the kernel mechanism behind `m_tetherLifetime` on Linux) fires when the **THREAD that called fork()** terminates, not when the parent process terminates. AssetProcessor's BuilderManager forks builders from short-lived TaskWorker threads -- the launching thread retires as soon as the child is spawned, the kernel sees the forking-thread die, signals the freshly-spawned builder, builder dies in <21 ms, AP gives up. The Multiplayer gem's use of `m_tetherLifetime` works fine because it forks from a long-lived UI thread; the prctl footgun is documented in `prctl(2)` but easy to miss when reading just the engine API.

**Spec state:** Patch0012 directive commented out, patch file retained in sources/ as reference. Changelog 2605.0-51 documents the withdrawal. Engine fork branch `assetbuilder-tether-lifetime` (commit d18027540) NOT pushed -- effectively abandoned in current form.

**Replacement approach under design (v2):**

1. **Watchdog poll inside the builder's main loop.** Each AssetBuilder spawns a background thread that calls `getppid()` every N seconds. If it returns 1 (or systemd-user PID), `_exit(0)`. Cross-platform safe. Doesn't depend on the parent's threading model. Costs one extra thread per builder + N seconds of orphan-lifetime on AP death; both are negligible.
2. **Have AP fork builders from a dedicated long-lived thread** (e.g., a single Builder-launcher service thread). Engine-side BuilderManager refactor. Cleaner architecturally but more invasive. Could still use `m_tetherLifetime` on top once the threading is fixed.
3. **Avoid in-process orphan-prevention entirely.** Wrap the engine with a small launcher script that tracks AP's PID and reaps stragglers if AP dies. Packaging-side workaround; no engine change required. Worth evaluating as an option for shipping without upstream cooperation.

Recommended sequence: (1) v2 patch with watchdog (simplest engine-side win). If upstream resists, (3) packaging-side fallback.

**Validation lesson for the memory log:** runtime test caught a bug that ALL static analysis + build-time tests missed. Spec parsed clean, compile was clean, F44/rawhide RPMs built clean, the patch even applied correctly. The bug only surfaced when AP actually ran. Build-validated != runtime-validated; the Tier 7 library-health check doesn't catch this class (it tests SONAME + symbol presence, not process-lifecycle interactions). Worth noting in CONTRIBUTING.md test-tier section.

Diagnosis memory notes: `project_assetbuilder_orphan_lifecycle_bug.md` (the underlying bug), and a new note on the prctl-PDEATHSIG-thread-vs-process gotcha.

---

## Backlog -- pending TSC conversation

### AssetProcessor desktop-menu entry (raised by Nick 2026-05-11 night)

Surfaced when Nick tried to launch AP standalone from the apps menu (no entry exists; ran the binary directly and hit "Path '/opt/O3DE/<v>/bin/Linux/profile/Default' is not a valid project path" -- the engine binary path was used as cwd because no project context was provided). Today, the only way to standalone-launch AP is from terminal with `--project-path=<path>`. The normal UX path is "open Editor in Project Manager, which spawns AP as a child process" -- AP is a side-effect, not a destination.

**The case for adding a menu entry**: standalone AP launch has legitimate use cases (1) pre-bake assets BEFORE opening Editor, avoiding the race-condition crashes we just hit on ROS2_Project; (2) re-launch AP after a crash without restarting Editor; (3) monitor asset processing while Editor is busy with other work.

**Three implementation shapes considered**:

(A) Wrapper script (`/usr/bin/o3de2605-ap`) that reads `~/.o3de/o3de_manifest.json` for the most-recently-active project and execs AssetProcessor with `--project-path=<that>`. Single-click "open AP for the project you were just working in." Works for the common single/few-project case. ~30 min spec change.

(B) Wrapper that prompts via zenity/Qt for project path if multiple projects are registered. More work; supports multi-project workflows cleanly.

(C) Raw exec of AssetProcessor in the .desktop file; user has to launch from a project directory. Cheapest, worst UX.

**Why this needs TSC conversation rather than unilateral implementation**: AssetProcessor's role in the UX (destination vs. side-effect) is a cross-platform design question. Windows .msi installer and Mac .pkg may already have AP entries; if so, the Linux/Fedora packaging should match the established pattern, not invent its own. If not, this is an opportunity to propose a unified cross-platform AP-launcher pattern that upstream can adopt across all installers. Either way, Nick wants TSC alignment before our Fedora packaging diverges.

**Discussion topics for the TSC**:
- Should AP be a top-level launch destination at all, or always-spawned-by-Editor?
- If yes, what's the cross-platform UX pattern? (Windows Start Menu, Mac Applications, Linux .desktop)
- Project-context resolution: manifest most-recent, interactive prompt, default-to-cwd, or some new mechanism?
- Should we implement on Fedora first as a proof-of-concept + then propose upstreaming, or wait for cross-platform alignment before any work?

**Status**: blocked on TSC conversation. Nothing implemented in our packaging. After TSC direction, this becomes an actionable ~30 min - 2 hour spec change depending on which shape is chosen.

---

## 2026-05-11 evening -- Stabilization 12-pack LIVE + snapshot-ref patch-conflict finding

### Wins from the overnight queue landing

- **10444166 (experimental 18-pack) GREEN** -- system_googlebenchmark Stage 1 swap validated end-to-end. Engine builds clean with Fedora's libbenchmark.so linkage in AzTest/AzTestRunner. 13-swap Stage 1 stack proven.
- **10444167 (stabilization 12-pack promotion) GREEN** -- the 12-pack is now LIVE for community testers. Adds system_assimp + system_libsamplerate + system_lua + system_poly2tri + system_sqlite to the existing 7-pack. Mike's CDN issue should resolve naturally now (fresh artifact for Pulp to regenerate metadata against).
- **10444466 (ISPCTexComp drift fix) GREEN** earlier today -- engine pin's `36b80aa-rev1` now matches what we ship. Drift report's 2 out-of-date items now down to 1 (just qt 5.15.2-rev9 vs 5.15.1-10, which is intentional per the Qt 6 migration plan).

### Snapshot-ref patch-conflict finding (10445300 + 10445322 both failed at %prep)

Both dev-branch snapshot builds submitted today (10445300 development, 10445322 qt6) failed at %prep with the same root cause: **Patch0006 doesn't apply cleanly against branches that diverged from stabilization/26050**. Specifically, both branches have modifications to `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` (the qt6 branch updates Qt pin to qt-6.10.2-rev4; development has its own evolution) that conflict with our Patch0006 hunks.

This is expected, not a bug. Our patches were authored against stabilization/26050; `%autosetup -p1` applies all patches unconditionally, so any patch touching a file that diverged in the target branch will fail.

**What worked**: snapshot-ref infrastructure itself -- tarball generation, SRPM build, baked-in snapshot pins (today's spec fix), COPR upload, mock extraction, build-deps install. All those steps validated. The patch step is the friction point.

**Three options for handling this** (deferred, not implemented tonight):

A. **`--with no_patches` bcond** to skip all engine-side patches in snapshot mode. Vanilla upstream source + our packaging structure. Honest "what does this branch compile like?" test. ~30 min spec change.

B. **Per-patch conditional application** via `%patch -P N -p1` inside `%if` blocks, replacing `%autosetup`. Gate Patch0006/Patch0007/etc. behind `--with stabilization` so snapshot-only mode skips them. More invasive.

C. **Accept the limitation, document it.** Dev-branch snapshots may fail at %prep when patches conflict; that's the cost of having local patches. Manual patch refresh per branch tip if we want them to apply.

Recommended: **A**, when bandwidth allows. The snapshot-ref use case is "build the qt6 branch as-is and see if Linux compiles" -- which doesn't benefit from our packaging-side patches, only from our packaging-side structure (spec / Find shims / Makefile glue). Vanilla upstream is the right test surface.

For now: dev-branch snapshot builds are documented as "validates source extracts + SRPM generation + early %prep, NOT engine compile". Library-health Tier 7 + drift workflow + main stabilization/experimental builds remain unaffected.

---

## 2026-05-11 late afternoon -- Mike-C feedback + Tier 7 deeper reframe + Qt 6 PR tracking

### Mike-C feedback from 2026-05-07 (caught up 2026-05-11)

Mike posted to Discord on 5/7 with three observations testing the then-current stabilization build. Surfaced late; addressed:

1. **`libAzGameFramework.a` missing during native project build.** Downstream of #3 below. The static archive lives in `o3de2605-devel` subpackage (carved out 2026-05-04 via commit `285d924`). When the COPR Pulp CDN bug bailed his `o3de2605-devel` install mid-stream, the .so's and runtime tooling landed but the .a's never did. Resolution path: in-flight build **10444167** (12-pack stabilization promotion, due ~5h from 2026-05-11 mid-afternoon) will publish a fresh artifact to Pulp, regenerating the metadata and resolving the Content-Length inconsistency naturally. Mike doesn't need to do anything except retry `sudo dnf install o3de2605-devel` after the new build lands.

2. **CMake bundling question** (he noted Project Manager downloaded bundled CMake 4.2.3 but our path `/opt/O3DE/26.05.0/cmake/runtime/` is empty; asked if removed for licensing). Answer: no, BSD-3-Clause -- not licensing. Per Fedora packaging guideline 12 ("don't bundle libraries Fedora ships"), we depend on system CMake via `Recommends: cmake`. The empty `cmake/runtime/` tree stays declared as a placeholder for future in case the engine ever pins a patched CMake; today engine just uses whichever cmake is on PATH. Spec comment is accurate.

3. **COPR Pulp CDN Content-Length inconsistency** (501,315,746 advertised vs 501,182,865 in repodata for o3de2605-devel). Pulp/S3 storage-layer bug on COPR's side; not our packaging. Retry sometimes clears it; the in-flight build above will give Pulp a fresh artifact to regenerate metadata against.

Side note from the same investigation: o3de2605-devel is ~500MB compressed (~4GB expanded; 178 static archives). Only relevant for native C++ Gem development against engine internals -- end users running games or Lua/ScriptCanvas project authors don't need it. Worth noting in user docs at some point.

### Tier 7 deeper reframe (post `--scanfolders` experiment)

Earlier today's `--scanfolders=$ENGINE_PATH/Gems` fix (commit `832689e`) was validated against the failing run and didn't actually fix it. Cold log analysis revealed the deeper truth: even a single-file cube.fbx bake through SceneAPI declares a `JobDependency` on `DefaultVertexBufferPool.resourcepool`, which transitively requires shaders + SRG merge + Atom RPI gem. The empty scratch project can't satisfy that dep chain. Adding engine Gems to scan folders made it worse (600 engine-asset bakes failed for the same chain reasons, drowning out the cube.fbx signal).

**Implication**: the original Tier 7 test premise ("single-file scratch project that just exercises assimp's import path") was conceptually wrong. FBX -> azmodel through SceneAPI is NOT standalone from the Atom rendering pipeline.

`--scanfolders` change reverted. Test script stays in tree as a known-broken record of the dep-chain finding. Real fix options documented in updated `project_tier7_cold_cache_quirk.md`:
- **(a)** Skip AP entirely; test assimp at C++ API level (compile small binary against system_assimp, assert mesh count etc.). Recommended.
- **(b)** Use AutomatedTesting project structure (heavy; touches whole engine asset library).
- **(c)** Drop Tier 7 entirely.

Tier 7 cron stays OFF; rebuild won't happen until (a)-style direct-assimp test is implemented. This is a fundamental redesign, NOT a quick fix; defer until next sprint.

### Qt 6 tracking now includes PR #19567

User pointed at PR [o3de/o3de#19567](https://github.com/o3de/o3de/pull/19567) -- this is the actual merge candidate (qt6 -> development). Updated `tools/check-deps-drift.py` to also track PR state in the drift report's "Upstream migration tracking" section. Drift report now shows:

```
| #19567 | OPEN | 57d | 1662 | +2547/-5075 | development | qt6 | Linux-Profile=SUCCESS / Linux-Asset=FAILURE |
```

**Key insight from PR scope review**: Linux-Profile builds GREEN on Qt 6.10.2. Engine compiles cleanly on Linux against vanilla Qt 6 -- empirical proof that `system_qt6` Stage 1 swap is feasible the day this PR merges. Mac-Profile + Windows-Profile + Windows-Release all FAIL (Mac toolchain + Windows VS2019 -> 2022 toolset bump issues). PySide2 not yet migrated (major author-flagged blocker). AP/APB hangs on exit (caught by nick-l-o3de 2026-02-18).

Stalled since 2026-03-14; nick-l-o3de's earlier "hold merging until stabilization/26050 is cut" gate is long since released (26050 cut weeks ago). PR is now just waiting on review + work bandwidth.

### Other items wrapped this session

- **Tier 7 actual fix attempt** -- reverted (didn't work; see above).
- **`make srpm-snapshot-qt6` smoke test** -- caught 2 infra bugs (cd-scoping in Makefile + %global override in spec); both fixed. SRPM now generates end-to-end against the qt6 branch tip.
- **Cruft cleanup** -- deleted PhysX + aws-gamelift-server-sdk from o3de-dependencies (engine no longer references either).
- **ISPCTexComp drift fix** -- rebuilt from commit 36b80aa (the engine-pinned source) instead of 691513b. Build 10444466 GREEN on F44+rawhide.
- **Drift report `bundled-exception` classification** -- 5 documented bundles (OpenSSL/openimageio-opencolorio/pyside2/squish-ccr/vulkan-validationlayers) moved out of "gap" bucket. Drift report now: 0 gap, 0 minor-drift, 2 out-of-date (ISPCTexComp resolving + Qt intentional).

---

## 2026-05-11 afternoon -- F44 consolidation session + Qt 6 strategic clarification

After pausing CS10, ran four-track F44 hardening:

1. **Tier 7 root-cause investigation: ✓ DONE.** Reframed the failure -- not a parallel-jobs SRG-merge race, but a **scan-folder configuration** problem. Test scratch project doesn't include `/opt/O3DE/26.05.0/Gems/` in its scan folders, so `MergeShaderResourceGroupAsset`'s outputs (viewsrg.srgi, scenesrg.srgi) are invisible to `ShaderAssetBuilder`. The `--regset maxJobs=1` validation experiment failed and was reverted (commit `705ea99`). Memory notes `project_tier7_cold_cache_quirk.md` + `project_tier7_serial_pass_option.md` reframed with the corrected understanding. Workflow updated to upload BOTH cold + warm AP logs (`f0ac388`). Actual fix scope (next item in queue, not yet started): pass `--scanfolders=$ENGINE_PATH/Gems` to AP in `tests/asset-bake-test.sh:run_ap_pass()`. Bonus finding from same investigation: SQLite header/library version mismatch produces three `Trace::Assert` blocks at AP startup (system_sqlite swap firing SQLite's built-in version-sanity check). Non-fatal; low priority noise.

2. **Stabilization 7-pack -> 12-pack promotion: ✓ APPLIED + VALIDATING.** o3de-stabilization F44 + rawhide chroots extended from 8 with_opts to 13 (added system_assimp + system_libsamplerate + system_lua + system_poly2tri + system_sqlite). New SRPM_STABILIZATION_FLAGS list in Makefile mirrors the chroot config. Build **10444167** queued (F44+rawhide; CS10 untouched per pause). ETA ~5h each chroot. Will land the 12-pack for community testers if green; rollback is just reverting the chroot edit.

3. **Qt 5.15.1 -> 5.15.2-rev9 rebuild: RETIRED-as-DEAD-WORK.** Investigation revealed the rev9 source isn't published anywhere (only as a binary on packages.o3de.org), so "rebuild" isn't mechanical. Bigger picture: engine team's strategic direction is Qt 6 for 26.10.0, NOT improving Qt 5. Don't invest in o3de-qt5 anymore. See "Qt 6 migration tracking" entry below for the forward plan.

4. **system_googlebenchmark activation: ✓ APPLIED + VALIDATING.** Plumbing landed 2026-05-08 (bcond+Source+Find shim) but was OFF; today's activation adds `--with system_googlebenchmark` to SRPM_EXPERIMENTAL_FLAGS + experimental chroot. Engine still ships AzTest+AzTestRunner+gbench unconditionally (architecturally correct shape per closed PR #19738 redirect); linkage now pulls Fedora's `google-benchmark-devel`. Build **10444166** queued (F44+rawhide). ETA ~5h each. Validates the 18-pack stack in one go.

Reference state at end of session: HEAD `f0ac388` ("test(tier7): upload both cold + warm AP logs..."). Spec changelog `2605.0-47`.

### Builds in flight (overnight)
- 10444166 (experimental F44+rawhide, 18-pack incl. googlebenchmark)
- 10444167 (stabilization F44+rawhide, 12-pack promotion)

---

## Upstream PR status (2026-05-11 refresh)

- **#19733 (AzCore Lua include cleanup)** -- MERGED 2026-05-08 by nick-l-o3de. Our Patch0008 becomes redundant on next snapshot rebase.
- **#19734 (libtiff C99 typedefs)** -- MERGED 2026-05-08 by nick-l-o3de. Our Patch0007 becomes redundant on next snapshot rebase.
- **#19737 (Microphone libsamplerate PAL-trait gate)** -- **MERGED 2026-05-10 by nick-l-o3de.** When we pull a fresh snapshot from development (or once stabilization/26050 cherry-picks it forward), our local Microphone-related patch hunks become redundant. Action: audit local patches against the merged PR on next snapshot rebase. Three of three upstream PRs this cycle now merged.
- **#19738 (googlebenchmark gate on LY_DISABLE_TEST_MODULES)** -- CLOSED 2026-05-08 (architecturally wrong premise per nick-l-o3de). Replaced by today's system_googlebenchmark Stage 1 swap activation (build 10444166).
- **#19740 (libbenchmark.a missing from engine install set)** -- filed as upstream issue 2026-05-08; awaiting volunteer pickup. Memory note `project_az_test_runner_architecture.md`. Not blocking on us.
- **#19743 (AP minimal-scope flag request)** -- filed 2026-05-11. **Nick_L responded same day** with three messages of context: (1) AssetBuilder executable (not AssetProcessorBatch) already has `--task=debug --debug=<file> --output=<folder>` for single-asset debug runs (ref: `ap_builder_test.py` + `LyTestTools/asset_processor.py:L474`); (2) requires AssetProcessor GUI running in background to answer DB queries; (3) **load-bearing insight**: "*a single asset compile is a contradiction in reality*" -- even cube.fbx output depends on input material type, scene settings, scene builders present, prefab-generation Python scripts. There's no stable expected output for any given asset without controlling everything. **This validates our library-health pivot** -- it's not a compromise, it's the right design. Update comment posted on the issue 2026-05-11 documenting the reframe. AssetBuilder debug mode remains useful for a different test class (structural smoke vs byte-stable regression). Memory `project_tier7_cold_cache_quirk.md` updated with the full Nick_L quotes.

---

## Qt 6 migration tracking (planned for 26.10.0; NOT guaranteed)

Replaces the retired "Qt 5.15.1 -> 5.15.2-rev9 rebuild" item with the actual strategic shape.

**Upstream tracking links**:
- **Feature request**: [o3de/o3de#19081](https://github.com/o3de/o3de/issues/19081) -- "Upgrate O3DE tools to QT6", OPEN, priority/major (sig/content + feature/editor + feature-need/important-soon).
- **Engine PR**: [o3de/o3de#19567](https://github.com/o3de/o3de/pull/19567) -- "Build against Qt 6.10.2", OPEN, base=development head=qt6, last activity 2026-03-14. The actual merge candidate for the qt6 branch.
- **3p side**: [o3de/3p-package-source#293](https://github.com/o3de/3p-package-source/pull/293) -- "Update from QT5.15 to QT6.10.2" -- **MERGED 2026-02-13 by sptramer.** Recipe for Qt 6.10.2 builds is now upstream.
- **Engine branches** (TWO of them now):
  - `o3de/o3de:qt6` at HEAD `b74cbc8` (2026-03-10). 19 commits ahead of development, 36 commits behind, ~300 files changed. Main Qt 6 work.
  - `o3de/o3de:qt6_pyside` at HEAD `719eb73` (2026-03-14). 5 commits ahead of `qt6`, 0 behind. PySide6 migration sub-branch off qt6 -- the work that addresses PR #19567's "PySide2 not yet migrated" blocker. Author-flagged WIP (`(WIP) cmake package change` is the last commit message); no PR open yet.
- **Discord thread**: https://discord.com/channels/805939474655346758/1420144310908616725 -- "QT6 Support" thread in O3DE Foundation Discord's `gems-and-features` channel. Opened by Guillaume [Cloud Imperium] 2025-09-23 with initial status: Windows+Linux "builds and launches, needs deep testing"; Mac "will build soon". Tracked manually (Claude can't access Discord); valuable for status updates between commit/PR activity windows.
- **Linked discussion**: [o3de/o3de#14940](https://github.com/o3de/o3de/discussions/14940) -- closed; 2025-era community offer of Qt 6.3.2 work from a 22.05 branch fork.

**Activity timeline**: substantive work happened in two waves (Sept 2025 = initial Linux/Windows runtime; Feb-Mar 2026 = PR opened + 3p recipe merged + PySide branch started). Idle since 2026-03-14 (~2 months as of 2026-05-11). The "hold merging until stabilization/26050 cut" gate from nick-l-o3de 2026-02-17 is long since released.

**Critical for packaging**: Qt 6 will be **VANILLA** (no custom O3DE patches). PR #293's description states *"Nothing, we are using vanilla QT. In the process, we are nuking the custom changes"*. The Qt 5.15 fork's load-bearing patches (PropagateStyleToChildren / ManualStyleSheet / tooltip layouting / TIFF support / tree-view expand) are being dropped, not forward-ported. Means: when Qt 6 migration lands, **Fedora's system qt6 packages CAN substitute** -- the entire `o3de-qt5` bundle (101MB tarball, multi-hour build) can be retired in favor of `BuildRequires: qt6-qtbase-devel qt6-qttools-devel qt6-qtsvg-devel ...` + `system_qt6` Stage 1 swap.

**Volunteer-project caveat**: 26.10.0 (fall 2026 stable release) is the goal date, but O3DE is open-source volunteer work. The qt6 branch hasn't received commits since 2026-03-10 -- two months of inactivity. There's a real-but-low chance Qt 6 slips past 26.10.0. **Don't preemptively retire o3de-qt5 packaging.** Wait for empirical merge to development + stabilization/26100 cutover before drafting `system_qt6`.

**Action items (in order)**:
1. **Nothing right now.** Engine team owns the qt6 branch merge cadence; packaging-side work is contingent on that.
2. **When stabilization/26100 branch is cut** (typical cadence: ~3-4 months before stable release, so likely mid-July 2026): inspect `cmake/3rdParty/Platform/Linux/BuiltInPackages_linux_x86_64.cmake` on the stabilization branch. If `qt-6.10.2-*-linux`: draft system_qt6 swap. If still `qt-5.15.2-rev9-linux`: Qt 6 slipped; keep o3de-qt5 for one more cycle and revisit for 27.05.x.
3. **Adjacent: PySide6** migration. PR #19361 (Component Creation Class Wizard Expansion) introduces PySide6 dependency. Same shape as Qt 6 -- F44 ships `python3-pyside6`; retire bundled `pyside2-5.15.2.1-py3.10-rev7` when engine migrates.

**Why Qt 6 didn't make 26.05.0** (referenced from the curious question 2026-05-11): timing + scope. The qt6 branch had its substantive activity Jan-Mar 2026; stabilization/26050 was cut ~Feb 2026 (typical 3-month-before-release cadence) and the qt6 work missed that cutoff. The 300-file / 19-commit scope plus 35-commit-behind rebase backlog plus the cross-platform validation cycles (Mac still pins 5.15.2-rev8 in 3p build_config; Mac path lags Linux/Windows) compound. Volunteer cadence means PR #293 merged in February and then nothing has driven the qt6 engine-branch forward since March. Memory note `project_o3de_bundles_custom_qt.md` documents the migration plan + cautions.

---

## CS10 (CentOS Stream 10) -- PAUSED 2026-05-11

CS10 chroot pivot effort started 2026-05-08, paused 2026-05-11 to consolidate on F44 + rawhide first.

**Why paused:** The remaining CS10 work isn't bounded. `ispc` (Intel SPMD compiler) has no `epel10` branch in Fedora -- ISPCTexComp can't be built on CS10 without either us packaging ispc ourselves (significant scope creep) or adding an engine-side cmake gate. The heavier deps (Qt5, PhysX, AWSNativeSDK) haven't been CS10-tested and likely surface their own per-spec quirks. F44 + rawhide just went green end-to-end yesterday on the full 14-pack + Patch0010 + Patch0011 stack (build 10442708); that foundation should harden before splitting attention. Tier 7 still fails on F44 + rawhide (the `--regset maxJobs=1` hypothesis was wrong -- see `project_tier7_serial_pass_option.md`); that's a higher-leverage F44 win than CS10 grinding.

**Stance**: leave the CS10 chroots configured but stop submitting to them. Nothing gets torn down; nothing gets added. The work that landed is correct and harmless; it just sits idle.

**What landed that's keeper-state (do NOT revert)**:
- All 4 engine COPR projects + o3de-dependencies have `centos-stream-10-x86_64` chroot enabled. Empty + idle is fine.
- `o3de-experimental` CS10 chroot has the full 17 with_opts + EPEL-10 + o3de-dependencies repo wired. Will be picked up unchanged when CS10 work resumes.
- Spec-side: o3de.spec round-1 + round-2 escape fixes (2605.0-45 + 2605.0-46), Makefile timeout bump to 8h (28800s). All behavior-preserving on F44/rawhide.
- mcpp PoC rev10 (debug_package + bulk escape), dxc-spirv PoC rev14 (prophylactic escape). Both have CS10-green RPMs in o3de-dependencies.
- 5 CS10-green dep RPMs in o3de-dependencies: mikkelsen, azslc, astc-encoder, aws-iot-device-sdk-cpp-v2, aws-gamelift-server-sdk (built 2026-05-11 from F44 SRPMs).

**What's known-blocked when we resume**:
- ISPCTexComp CS10 build needs `ispc` for EL10. No upstream solution. Resume options:
  - (a) Package ispc ourselves in `hellaenergy/o3de-dependencies` as a CS10-targeted SRPM.
  - (b) Engine-side cmake gate to skip ISPCTexComp on CS10 builds.
  - (c) Drop CS10 support indefinitely if neither (a) nor (b) lands.
- Qt5 + PhysX + AWSNativeSDK haven't been CS10-built yet. Multi-hour each.
- Engine compile on CS10 has never reached the build phase (always blocked at BR resolution so far). Once deps are sorted, expect to surface clang 19 vs F44's clang 21 diagnostic differences and libstdc++ 14.3 vs 15.x deprecation deltas.

**Resume-from-here ledger**: memory notes `project_cs10_engine_build_blockers.md` (incremental discovery list), `project_cs10_with_opts_gap.md` (chroot config fix recipe -- already applied; documents the gotcha for future chroot additions), `project_cs10_debuginfo_quirk.md` (the two known RPM 4.19 quirks + escape pattern).

**Resume conditions** (any one is enough to revisit):
- An external user requests CS10 / RHEL 10 support (would shift priority from speculative to real-demand).
- F44 + rawhide are at a stable "no critical pending work" state (Tier 7 fixed, stabilization channel at 12-pack or 14-pack, drift items at zero, upstream PR backlog cleared).
- ispc lands an `epel10` branch in Fedora (eliminates the biggest unbounded chunk).

---

## End-of-day 2026-05-10 -- what landed

Short evening session focused on diagnosing build 10439258 (the post-Patch0011 validation rebuild) and clearing the next round of blockers.

### Build 10439258 outcome (the post-Patch0011 validation rebuild)

Mixed result with one new gotcha:

- **F44 chroot**: ran 5h02m, **engine compiled fully**, packaging emitted Provides/Requires for both `o3de2605` and `o3de2605-devel` subpackages, killed at the final `Checking for unpackaged file(s)` step by the COPR default 5h wall-clock timeout (`!! Copr timeout => sending INT`). Build essentially "done" -- binaries were generated, just couldn't finish RPM finalization. Underlying cause: Makefile passes `--timeout 25200` (7h) but the rebuild was submitted via raw copr-cli without the flag, defaulting to 5h (18000s) and being killed at 18141s.
- **rawhide chroot**: same 5h timeout pattern; same compiled-fully + packaging-emitted state. Crucially, the Requires list shows `liblua-5.5.so` -- meaning **Patch0010 + Patch0011 cleared all Lua 5.5 sites and the engine compiled clean on Lua 5.5**. No third break site emerged.
- **CS10 chroot**: failed at SRPM-prep in 134s with a NEW RPM 4.19 quirk -- `error: line 1087: second %install`. Different from the mcpp debuginfo quirk caught on 2026-05-08. Root cause: the o3de.spec had a comment inside the `%install` block reading `# Per-version mutation lands here at %install time:` -- RPM 4.19 (CS10) parses the unescaped literal `%install` token inside that comment as a section-start marker; RPM 6.x (F44 + rawhide) ignores it.

### Fixes landed today

- **CS10 spec quirk fix** (commit `d889edb`) -- rephrased the line-1087 comment to drop the percent sign + added an inline note documenting the RPM 4.19 quirk so future edits don't reintroduce it. Swept the rest of the active `%install` block: no other comments in that block contain the token, so the fix is local. Other `%install` references elsewhere in o3de.spec (lines 455, 524, the changelog) sit outside the active `%install` block and are unaffected by the parser bug.
- **Makefile COPR timeout bump 25200 -> 28800** (same commit) -- 8h ceiling for all four `copr-cli build` invocations (stable / snapshot / stabilization / experimental) + the internal `_copr-and-test` helper. F44's empirical 5h02m baseline + rawhide's typical 10-30% slowdown could overflow even 7h on a worst-case run; 8h gives usable headroom for rawhide AND CS10 (CS10 build time unknown until first end-to-end run completes). Updated the inline comment block explaining the choice.
- **Validation rebuild submitted as build 10442708** (o3de-experimental, all 3 chroots, 8h timeout). https://copr.fedorainfracloud.org/coprs/build/10442708 -- expected to land sometime overnight depending on rawhide + CS10 compile times.

### Lua 5.5 break-site pre-flight audit (concluded: Patch0010 + Patch0011 are sufficient)

Per the existing `project_lua_5_5_newstate_break.md` memory note's hedge ("there may be MORE Lua 5.5 break sites we haven't tripped on yet"), ran the recommended comprehensive grep against `o3de/development @ 706cd0f3` (head of upstream development) to enumerate ALL potential Lua 5.5 break sites prophylactically:

- `LUA_NUMTAGS`: exactly 2 sites, both in `Code/Tools/LuaIDE/Source/LUA/WatchesPanel.cpp:834,838`. **Both covered by Patch0011.**
- `lua_newstate`: exactly 1 site in `Code/Framework/AzCore/AzCore/Script/ScriptContext.cpp:4360`. **Covered by Patch0010.**
- Other Lua 5.5-vulnerable symbols swept (`luaL_register`, `lua_open`, `lua_resume`, `LUAI_FUNC`): zero hits across `Code/` + `Gems/`.

Conclusion matches the empirical evidence (rawhide compiled the full engine in 10439258 with `liblua-5.5.so` linkage). **No Patch0012 needed.** The "may be MORE sites" hedge in the memory note can retire when next updated. If a future engine snapshot adds new Lua surface area, re-run the same grep before assuming the patches are still complete.

### Stage 2 dep spec sweep (CS10 quirks)

Swept the three Stage 2 dep specs (`o3de2605-mcpp-az`, `o3de2605-dxc-spirv`, `o3de2605-spirv-cross`) for the `%install`-in-comment pattern that broke o3de.spec on CS10: **all three clean** (none contain `%install` text inside their `%install` blocks). The o3de engine spec was unique in having that comment.

Separately applied the known mcpp `%global debug_package %{nil}` fix per memory note `project_cs10_debuginfo_quirk.md`:

- **mcpp rev9 spec change**: added `%global debug_package %{nil}` near the top with an inline comment explaining the RPM 4.19 vs RPM 6.x asymmetry. Bumped `mcpp_pkgrev` to rev9 + added a changelog entry.
- **mcpp rev9 SRPM built** at `/home/nschuetz/o3de2605-mcpp-az-poc/o3de2605-mcpp-az-2.7.2-1.rev9.fc44.src.rpm`.
- **CS10-only mcpp validation build submitted as build 10442715** (`o3de-dependencies`, CS10 chroot only via `-r centos-stream-10-x86_64`). Should complete in ~2-3 min and either confirm the debug_package fix works, or surface the next CS10 quirk. Independent of the engine build so doesn't compete for builder slots. https://copr.fedorainfracloud.org/coprs/build/10442715

If mcpp rev9 builds clean on CS10, the same `%global debug_package %{nil}` macro can be propagated prophylactically to `o3de2605-spirv-cross` and `o3de2605-dxc-spirv` specs as belt-and-suspenders before their first CS10 build attempts (currently only mcpp has had a CS10 attempt; spirv-cross's CS10 result on 2026-05-08 was a different non-debuginfo SRPM, so debuginfo quirk wasn't tested there yet).

### Other notes

- The `o3de2605-devel` subpackage split appears to have landed at some point during 2026-05-08's work; confirmed by 10439258's packaging output showing both `o3de2605` and `o3de2605-devel` Provides lists. Not in scope for this session's investigation; flagged here for visibility.
- The mcpp PoC working tree's git history doesn't include the rev6-rev8 commits (those were spec edits without local commits). Today's rev9 edit also not committed to the PoC's local git -- pure SRPM build + COPR submit. If the PoC eventually graduates to a real repo, the changelog entries in the spec ARE the canonical history.

### Reference state at end-of-day 2026-05-10

- **HEAD on main**: `7a31d01` ("fix(cs10): bulk-escape ALL section-keyword tokens in o3de.spec comments/changelog (round 2)")
- **Spec changelog**: `2605.0-46`
- **Active in `o3de-experimental` chroot config**: still 17 with_opts entries (snapshot + stabilization + 12 Stage 1 + 3 Stage 2)
- **Builds in flight overnight**:
  - 10442708 (engine validation, all 3 chroots, ORIGINAL post-2605.0-45 spec): F44 + rawhide should succeed in ~5-8h; CS10 chroot of THIS build is now known-doomed (will trip at next unescaped section token past line 1087) but not cancelled because F44 + rawhide still produce useful artifacts.
  - 10442734 (engine CS10-only, ROUND-2 escaped spec at 2605.0-46): queued behind 10442708's CS10 slot; will start when capacity opens. First true CS10 engine compile attempt; expected 5-8h.
- **Builds that completed during the session**:
  - 10442715 (mcpp rev9 CS10): FAILED with the second CS10 quirk that drove the round-2 escape work.
  - 10442733 (mcpp rev10 CS10, post-bulk-escape): SUCCEEDED -- empirical proof the bulk-escape fix works.
- **Stage 2 PoC working trees**: paths unchanged. mcpp PoC now at rev10 (debug_package + bulk escape), local git up-to-date with HEAD `8167b9f`. dxc-spirv PoC has the prophylactic escape fix applied (no rev bump yet; HEAD `c62581c`). spirv-cross PoC unchanged (no unescaped section tokens; nothing to fix).

### Memory notes refreshed this session

- `project_lua_5_5_newstate_break.md`: hedge "may be MORE Lua 5.5 sites" retired; comprehensive grep audit at `o3de/development @ 706cd0f3` confirmed Patch0010 + Patch0011 are the complete set. Future engine snapshots should re-run the grep.
- `project_cs10_debuginfo_quirk.md`: renamed + expanded to cover BOTH known CS10/RPM 4.19 quirks (debuginfo double-emission + literal `%install` in comments anywhere). Scope correction: in-comment section tokens trip the parser ANYWHERE in the spec, not just inside the active section block (corrected mid-session after empirical evidence from build 10442715).
- `MEMORY.md` index entries updated for both.

### Autonomous overnight continuation (added 2026-05-10 22:35 CST)

Five more tracks completed after the initial "ALL" go-ahead:

1. **Drift workflow re-triggered** (run 25648396886) -- conclusion: failure (intentional design; red dot surfaces drift items). Issue #9 still surfacing the 5 drift items from 2026-05-08: ISPCTexComp commit drift, qt5 5.15.1 vs .2, AWSNativeSDK .288 vs .361, astc-encoder 3.2 vs 5.3, mikkelsen label-form. Plus 2 cruft (aws-gamelift, PhysX). No new actionable items beyond what we already had.

2. **Stage 2 dep CS10 audit + prophylactic escape**:
   - mcpp PoC: rev10 ✓ GREEN on CS10 (build 10442733). Validated the bulk-escape pattern.
   - dxc-spirv PoC: rev14 in flight as CS10-only (build 10442739, started 22:18 CST, running). Prophylactic escape applied at 4 lines; no debuginfo suppression added yet (large library binaries may warrant debug symbols).
   - spirv-cross PoC: no unescaped tokens; already empirically green on CS10 (build 10438108 from 2026-05-08). No action needed.

3. **CS10 engine source compat pre-flight** (`grep -rn` against `o3de/development @ 706cd0f3`):
   - Zero hits for: C23 reserved-word collisions, OpenSSL 3 deprecated APIs, glibc symbol-version assumptions, boost deps, `<experimental/...>` includes.
   - Engine sets `CMAKE_CXX_STANDARD 20`. Requires clang >= 19 (CS10 boundary).
   - One special handling: clang >= 21 branch for googletest workaround (CS10 won't trigger; harmless).
   - **CS10 toolchain confirmed from build 10442734 dnf logs**: clang version not visible but expected 19+; gcc/libstdc++ 14.3.1 (F44 ships 15.x); glibc 2.39 (F44 ships 2.42); **lua 5.4.8** (Patch0010+0011 are NO-OPS on CS10 -- gated on `LUA_VERSION_NUM >= 505`); openssl 3.5.5.
   - All findings + predictive next-blockers documented in new memory note `project_cs10_engine_build_blockers.md`.

4. **Doc drift identification (NOT updated, only enumerated)**:
   - **Patch0010 + Patch0011 (Lua 5.5 compat) -- ZERO mention in user-facing docs (README, ARCHITECTURE, BUNDLED_LIBRARIES, FEDORA_ROADMAP, CONTRIBUTING).** Major gap. These are the most significant engine-side patches added in the last week.
   - **CS10 chroot -- mentioned in README, CONTRIBUTING, FEDORA_ROADMAP; NOT mentioned in ARCHITECTURE.md or BUNDLED_LIBRARIES.md.** Minor gap.
   - **-devel subpackage + system_googlebenchmark + versioned-major naming**: all well-covered across docs.

5. **Tier 7 design research**:
   - **MAJOR FIND: AssetProcessor supports `--regset` CLI flag** (Code/Tools/AssetProcessor/native/utilities/ApplicationManagerBase.cpp:303).
   - Hypothesis: `AssetProcessorBatch --regset "/Amazon/AssetProcessor/Settings/Jobs/maxJobs=1"` forces serial processing, which should sidestep the cold-cache parallel SRG-merge ordering quirk without ANY engine code change.
   - If validated, Tier 7 can switch from the current two-pass design to a simple single-pass-serialized-on-cold design.
   - Documented as new memory note `project_tier7_serial_pass_option.md` with the predicted validation plan.

### BIG SECONDARY FINDING (caught while investigating 10442734)

**CS10 chroot has empty `with_opts` across all engine COPR projects.** When CS10 chroot was added 2026-05-08, the `--rpmbuild-with` flags didn't propagate; CS10 currently runs builds with all bconds at default (bundled libs, NOT system swaps). This is the inverse-side of the REPLACE-not-append memory rule -- `add-chroot` defaults `with_opts` to empty.

Empirical state (verified 22:30 CST):
- `o3de`: F44=0, CS10=0 (both intentionally clean stable channels; no gap).
- `o3de-snapshot`: F44=0, CS10=0 (same).
- `o3de-stabilization`: F44=8, **CS10=0 (GAP -- 8 flags missing)**.
- `o3de-experimental`: F44=17, **CS10=0 (GAP -- 17 flags missing)**.

This means: **all CS10 build attempts so far have NOT exercised any Stage 1/2 swap.** When CS10 engine compile eventually succeeds, it'll be a bundled-libs validation, not Stage 1/2 validation. Documented in new memory note `project_cs10_with_opts_gap.md` with the fix recipe (copr-cli edit-chroot with the FULL list per chroot, per the REPLACE-not-append rule). NOT auto-fixed -- chroot config edits need your judgment.

### 10442734 progress (the CS10 engine attempt with round-2 spec)

Failed at BR resolution after 147s: `No matching package to install: 'pkgconfig(libunwind)'`. Crucially: **cleared the spec-parse hurdle** -- the round-2 bulk-escape fix works for the engine spec at scale.

`libunwind-devel` exists in EPEL-10 (verified at https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/Packages/l/) but NOT in base CS10 repos. Fix recipe: enable EPEL-10 as an additional_repo on the CS10 chroot config. Per `project_cs10_engine_build_blockers.md`, deferred until your morning review since chroot config is yours to decide.

### Reference state at end-of-autonomous-session 2026-05-10 22:35 CST

- **HEAD on main**: `99fcc38` ("docs(follow-ups): capture round-2 CS10 escape work + mcpp rev10 validation")
- **Spec changelog**: `2605.0-46`
- **Builds in flight (still running overnight)**:
  - 10442708 (engine all 3 chroots, 2605.0-45 spec): F44 + rawhide expected to succeed by morning; CS10 known-doomed at next unescaped token (~3-4 hours wasted CS10 runtime, accepted).
  - 10442739 (dxc-spirv rev14 CS10-only): running ~15+ min so far; first CS10 attempt for this spec, may surface more CS10 quirks.
- **Builds completed during autonomous session**:
  - 10442715 (mcpp rev9 CS10): FAILED -> drove round-2 fix.
  - 10442733 (mcpp rev10 CS10, post-bulk-escape): SUCCEEDED ✓.
  - 10442734 (engine CS10-only, round-2 spec): FAILED at BR-resolution on libunwind-devel; cleared spec-parse ✓.
- **New memory notes (3)**: `project_cs10_with_opts_gap.md`, `project_cs10_engine_build_blockers.md`, `project_tier7_serial_pass_option.md`. All indexed in MEMORY.md.
- **PoC working tree commits (2, local-only, not pushed)**: mcpp `8167b9f` (rev9 + rev10), dxc-spirv `c62581c` (prophylactic escape).

### Morning priority queue

1. **Check 10442708 F44 + rawhide** -- if both succeed, full Stage 1+2 stack is validated on those chroots.
2. **Check 10442739 (dxc-spirv CS10)** -- likely success unless a new CS10-specific issue surfaces for this spec shape.
3. **Decide CS10 chroot config fixes**: enable EPEL-10 + propagate with_opts. Both per-project per-chroot, both require explicit copr-cli invocations with full lists.
4. **Doc drift fixes** if time permits: add Patch0010/0011 mention to BUNDLED_LIBRARIES.md (the natural home); CS10 mention to ARCHITECTURE.md's Mermaid diagram + paragraph.
5. **Tier 7 `--regset` validation**: low-effort experiment; one workflow_dispatch run with `run_asset_bake=true` after manually modifying the test to add `--regset maxJobs=1`. If it works, the cold-cache quirk gets a clean fix.
6. **Stabilization channel still on 7-pack**; community testers untouched. No promotions needed until F44 + rawhide validate clean on 10442708.

---

## End-of-day 2026-05-08 -- what landed

Bigger day than yesterday. Fifteen commits on `main` plus three PoC dirs plus two upstream PRs.

### Stage 1 system swaps (5 added today; engine now consumes 12 system libs)

- **`system_sqlite` activated (10-pack)** -- audit-confirmed cleanest Stage 1 candidate. 29 sqlite3_* symbols all in Fedora 3.51.2; no extension API used. `Findsqlite-system.cmake` mikkelsen-pattern shim sidesteps the runtime-walker side-effect target issue.
- **`system_libsamplerate` activated (11-pack)** -- lowest-risk swap; Linux PAL is a do-nothing None stub so the engine never calls `src_*` at runtime, but the static lib still needs to satisfy the link.
- **`system_assimp` activated (12-pack)** -- 5.4 to 6.0 major bump caveat noted; symbols verified, runtime FBX behavior covered by new Tier 7 `tests/asset-bake-test.sh` (added end-of-day; not yet validated against a live install).
- **`system_spirvcross` activated (Stage 2 first binary-only swap)** -- engine-side glue via `%install`-time symlink to `/usr/bin/spirv-cross` from the o3de-spirv-cross COPR package. No engine code change.
- **`system_dxc` activated (Stage 2 second binary-only swap)** -- same install-overlay shape but three symlinks (dxc, dxsc, libdxcompiler.so).

### Stage 2 PoCs (third one landed today; full set now ✓ green)

- **DXC PoC ✓ GREEN** -- `o3de-dxc-spirv-1.8.2505.1-1.rev12` (build 10435628). 12 iterations rev4 -> rev12. Final fix: Patch0002 added `SPIRV-Tools` to clangSPIRV's LINK_LIBS at the consumer side (rev11's transitive `target_link_libraries(IMPORTED INTERFACE)` form didn't propagate). Functional verification: `dxc -spirv -T ps_6_0 -E main shader.hlsl` produces valid SPIR-V output.
- **mcpp PoC ✓ GREEN + engine-side glue activated** -- `o3de-mcpp-az-2.7.2-1.rev7` (build 10436752, F44 + rawhide). 7 iterations rev1 -> rev7. Library-link variant of the DXC-class pattern (different shape from spirvcross/dxc which are binary shellouts -- mcpp is `#include <mcpp_lib.h>` + linked into the engine binary at build time). Source: upstream mcpp 2.7.2 (BSD-2-Clause, abandonware-class, 2008) + o3de/3p-package-source's 566-line `_az.2` patch. Configure: `--with-pic --enable-mcpplib`. Outputs the four expected RPMs: o3de-mcpp-az (libmcpp.so.0, /usr/bin/mcpp, man page), o3de-mcpp-az-devel (libmcpp.so + libmcpp.a + mcpp_lib.h + mcpp_out.h), debuginfo, debugsource. Iteration history: rev1 missing libtool BR, rev2 GCC 14 strictness on pointer types, rev3 LL_FORM undefined (configure AC_RUN_IFELSE silent fail), rev4 `true`/`false` keyword conflict in C23, rev5 trim AUTHORS + info docs from %files, rev6 unpackaged docs from autotools install, rev7 fix.
- **system_mcpp engine-side glue activated** (commit `1cf44dc`) -- third Stage 2 swap, first library-link variant. `Findmcpp-system.cmake` shim + Patch0006 `LY_USE_SYSTEM_MCPP` gate + spec wiring (`%bcond_with system_mcpp`, Source44 declaration, BR `o3de-mcpp-az-devel`, Requires `o3de-mcpp-az`, cmake `-DLY_USE_SYSTEM_MCPP=ON`). Engine code unchanged. SBOM bumped 2605.0-39 -> 2605.0-40. The two Stage 2 architectural variants (binary shellout for spirvcross/dxc, library link for mcpp) are now both proven in production engine builds.

### Upstream PRs (2 new + 1 fix on existing)

- **PR #19737** (Microphone libsamplerate PAL-trait gate) -- submitted 2026-05-08. Adds `PAL_TRAIT_MICROPHONE_USES_LIBSAMPLERATE` (FALSE on Linux/None, TRUE elsewhere) so Linux builds drop the libsamplerate dep entirely. Initial submission failed o3de's `UnicodeValidator` (em-dashes in comments); force-pushed em-dash-free version. CI re-running.
- **PR #19738** (BuiltInPackages googlebenchmark gate on LY_DISABLE_TEST_MODULES) -- submitted 2026-05-08, **NEEDS TO BE CLOSED 2026-05-08 (architectural premise wrong)**. Nick_L on the PR + sig-build Discord clarified: `LY_DISABLE_TEST_MODULES` means "skip our internal test modules" NOT "disable test infrastructure". AzTestRunner + AzTest + googletest + googlebenchmark + googlemock all ship unconditionally so gem developers can run their own tests. Verified at `Code/Framework/AzTest/CMakeLists.txt:34` (AzTest links `3rdParty::GoogleBenchmark` directly) + the explicit comment in `Code/Tools/AzTestRunner/CMakeLists.txt` ("note that LY_DISABLE_TEST_MODULES is a CMake variable that controls whether test modules are built or not and it should be interpreted as 'build our own tests'..."). Memory captured at `project_az_test_runner_architecture.md`. Replacement direction: close #19738 + write a `system_googlebenchmark` Stage 1 swap against Fedora's `google-benchmark-devel`, same shape as system_lua / system_assimp / etc.
- **PR #19733** (AzCore Lua) -- still open, awaiting maintainer merge.
- **PR #19734** (libtiff C99) -- 15 of 16 CI checks passed after re-run; Mac-Asset still in `macos-15-intel` runner queue.

### Audits (1 new today; 9 cumulative)

- **mcpp audit** -- reframed the existing `project_mcpp_architectural_choice.md` memory note: half-true ("any preprocessor would work" philosophically yes; in practice the engine binds to mcpp's specific library API, and Fedora ships zero mcpp packages). Right answer is the DXC-class library-rebuild we just shipped as the PoC.

### Infrastructure / hygiene

- **F43 chroot dropped** from `hellaenergy/o3de-dependencies` (was failing on EOL distro per `project_target_distros.md` rule).
- **`o3de-dependencies` COPR project added to `scripts/copr-metadata.sh`** managed-projects list (4 -> 5). Description + instructions populated and live-pushed.
- **Tier 7 cron default flipped OFF** (commit `a7c6e18`) -- first live run (CI run 25553050229) confirmed test infrastructure works end-to-end (Tiers 1+2+3 green, AP launched, log + artifact upload clean) but revealed a cold-cache parallel-jobs SRG-merge ordering quirk that fails 76+ FBX bakes + 210 shader builds spuriously on first AP pass. NOT a packaging regression -- same on upstream from-source build. Cron-driven cycle would keep red-flagging a non-bug; flipped to opt-in via workflow_dispatch only until design fix. Memory captured at `project_tier7_cold_cache_quirk.md`.
- **COPR edit-chroot REPLACE-not-append gotcha caught** -- single-flag `copr-cli edit-chroot --rpmbuild-with system_mcpp` reduced o3de-experimental's 16-entry with_opts list to 1 entry. Detected via post-edit `get-chroot` verification within ~5 min, restored full list before any builds were submitted in the corrupt window. Two in-flight builds (10435647 + 10436540) had already resolved their chroot config at task pickup over an hour earlier so they're unaffected. Memory rule + Makefile copr-init hint updated (commits `ddb299f` and the new `feedback_copr_edit_chroot_replaces.md`) to make the REPLACE semantic explicit.
- **Lua 5.5 LUA_NUMTAGS macro removed -- Patch0011 covers it** (this commit) -- second-of-N Lua 5.5 compat patches sibling to Patch0010. `Code/Tools/LuaIDE/Source/LUA/WatchesPanel.cpp` references `LUA_NUMTAGS` at two sites (a bounds check + a static_assert); 5.5 dropped that public macro. Patch0011 adds a one-line `#define LUA_NUMTAGS LUA_NUMTYPES` shim guarded on `#if LUA_VERSION_NUM >= 505 && !defined(LUA_NUMTAGS)`. Caught on rawhide chroot of build 10437498 (the chain-built rename + Patch0010 + system_mcpp validation run); the build progressed past Patch0010's covered site in ScriptContext.cpp only to trip on this LuaIDE site later. F44 chroot of the same build separately failed with "Build root is locked by another process" (transient COPR/mock infrastructure flake; not our code) -- the next experimental rebuild should clear F44 cleanly. SBOM bumped 2605.0-43 -> 2605.0-44. Memory note `project_lua_5_5_newstate_break.md` updated to reflect there are MORE Lua 5.5 sites we haven't tripped on yet (right way to find them all is `grep -rn LUA_NUMTAGS\|lua_newstate Code/ Gems/` against a Lua-5.5 sysroot; surfaces naturally during CS10 Phase 2).
- **Lua 5.5 lua_newstate signature break -- Patch0010 covers it** (commit `7f0c403`) -- Fedora rawhide has shipped Lua 5.5 ahead of F45, adding a required third `unsigned seed` parameter to `lua_newstate`. Engine's `Code/Framework/AzCore/AzCore/Script/ScriptContext.cpp:4359` calls the 5.4 two-arg form. Caught on builds 10436540 (14-pack rawhide chroot, 2026-05-08, FAILED) + 10435647 (10-pack rawhide chroot, same failure -- F44 still building so overall state still "running"). Patch0010 wraps the call in `#if LUA_VERSION_NUM >= 505` guard, passing seed=0 on 5.5+. Behavior-preserving on Lua 5.4. SBOM bumped 2605.0-40 -> 2605.0-41. Memory note: `project_lua_5_5_newstate_break.md`. Worth pitching upstream once the patch shape settles -- benefits every distro on rawhide's Lua 5.5 trajectory.
- **Versioned-major rename of Stage 2 COPR deps** (commit `0e5f751` engine-side; three rename builds 10437362/10437377/10437378 in flight) -- `o3de-spirv-cross` / `o3de-dxc-spirv` / `o3de-mcpp-az` renamed to `o3de2605-spirv-cross` / `o3de2605-dxc-spirv` / `o3de2605-mcpp-az` to mirror the engine package's o3deNNNN convention. Future `o3de2610-<dep>` packages co-exist in the same `hellaenergy/o3de-dependencies` COPR for the 26.10.x line. Rejected per-major COPR projects in favor of versioned-package-names-in-single-project (mirrors postgresql10/postgresql10-server in Fedora's main repo + matches upstream's CDN keying model). Empirical research showed cross-engine-branch divergence is small (1-3 lines between main/stabilization/development BuiltInPackages files), upstream's CDN co-hosts versions across major lines, and 3p-package-source has no engine-aligned branching -- so versioned-package-names is the architecturally-correct mirror of upstream's mental model. Rationale captured as a new "Eighth separation" in ARCHITECTURE.md + memory note `project_o3de_3p_versioning_research.md`. SBOM bumped 2605.0-41 -> 2605.0-42. Live COPR metadata for both `o3de-experimental` and `o3de-dependencies` refreshed and pushed.

- **system_googlebenchmark Stage 1 swap PLUMBING** (replaces closed PR #19738's intent in the architecturally-correct shape). Bcond + Find shim + Patch0006 hunk + spec wiring + Makefile spec-parse-experimental include + dep-map.yaml entry. Bcond is OFF by default; not yet in SRPM_EXPERIMENTAL_FLAGS or any chroot config so today's chain-built 15-pack experimental (10437498) is unaffected. Activation deferred to a separate commit after the chain-build + smoke-testing cycle. Linkage variance noted: Fedora ships only libbenchmark.so (no -static), so AzTestRunner ends up dynamically linked rather than having gbench compiled in statically; gbench's API is stable across 1.7.0 (engine pin) -> 1.9.5 (Fedora ship). Sibling-fix-not-replacement: o3de/o3de#19740 (libbenchmark.a missing from the engine's install set) is still the right fix on the engine side; the system swap is partial mitigation for external gem developers because they can satisfy benchmark links via Fedora's google-benchmark-devel directly. SBOM bumped 2605.0-42 -> 2605.0-43.

- **CentOS Stream 10 chroot pivot (Phase 1 ✓ verified)** -- corrected an earlier misalignment where the project's stated target was "F44+ / RHEL 10+" but only `hellaenergy/o3de` had a RHEL 10-targeted chroot enabled (`epel-10-x86_64`), and the actual intent per Nick was the CentOS Stream 10 line (which is upstream of RHEL 10). Phase 1 chroot pivot applied to all 5 COPR projects: dropped `epel-10-x86_64` from `hellaenergy/o3de`, added `centos-stream-10-x86_64` to all of `o3de`, `o3de-stabilization`, `o3de-snapshot`, `o3de-experimental`, `o3de-dependencies`. Each project now has F44 + rawhide + CS10. Two smoke builds run on CS10 chroot only: build 10438101 (`o3de2605-mcpp-az`) FAILED with `error: line 235: %package debuginfo: package o3de2605-mcpp-az-debuginfo already exists` -- a CS10/RPM 4.19-specific macro double-definition that doesn't fire on F44's RPM 6.x; per-spec fix is `%global debug_package %{nil}`. Build 10438108 (`o3de2605-spirv-cross`) SUCCEEDED in 2 min, confirming the COPR + mock + RPM-build chain works on CS10 for our shape. So the CS10 viability is proven for cmake-based simple builds; the mcpp result is a per-spec quirk to fix in Phase 2 (memory note `project_cs10_debuginfo_quirk.md`). Phase 2 (engine-side iteration on CS10 + per-spec fixes for mcpp + heavier deps) is the natural next session. Memory note `project_target_distros.md` updated to reflect F44+ / CS10+ instead of F44+ / RHEL 10+; doc sweep across CONTRIBUTING.md, FEDORA_ROADMAP.md, Makefile copr-init hint, tests/test-branch.sh.
- **New memory rules** -- `feedback_no_em_dashes.md` (user preference, ASCII punctuation everywhere); `project_o3de_unicode_validator.md` (upstream gate that caught PR #19737); `project_tier7_cold_cache_quirk.md`; `feedback_copr_edit_chroot_replaces.md`.

### In flight (background agents)

- **Drift-detection workflow** -- `tools/check-deps-drift.py` + `.github/workflows/check-deps-drift.yml` + `tools/dep-map.yaml` (compares engine BuiltInPackages vs COPR builds vs 3p-package-source; sticky issue updates weekly).
- **Tier 7 FBX-bake integration test** for assimp -- script committed (`tests/asset-bake-test.sh`); pending live-install validation to confirm the assumptions in its "Manual verification status" header (cache layout, .azmodel magic prefix, AssetProcessorBatch arg surface).

### COPR builds in flight

- **10-pack experimental** (10435647) -- running ~4h; queued before today's chroot config bump. May effectively run as a 14-pack-equivalent if its binary phase saw the new chroot config; otherwise validates the 10-pack as planned.
- **14-pack experimental** -- just queued (background task `bbjeb3mnt`), incoming build_id.
- **mcpp PoC rev1** (10436552) -- running.

---

## Pending -- what's loaded for next session

### Hot

- **9-pack stabilization promotion** -- the 9-pack validated end-to-end yesterday (build 10433646, CI run 25522053232 green). Currently only the 7-pack is in `o3de-stabilization`. Per `project_active_community_testers.md` we should give the 7-pack a ~1-week soak before pushing the 9-pack to testers. Earliest reasonable promotion: 2026-05-14ish. Mechanical: extend stabilization chroot config with `system_lua` + `system_poly2tri` + queue build.
- **14-pack stabilization promotion** -- same shape but adds 4 more flags (system_assimp + system_libsamplerate + system_spirvcross + system_dxc). Consider whether to do incrementally (12-pack first, then 14-pack) or all at once. Probably incrementally, with 7-pack -> 12-pack -> 14-pack staircase, gating each on tester soak.
- **mcpp PoC engine-side glue** -- mcpp PoC ✓ green as of 2026-05-08 (rev7). Next: write `LY_USE_SYSTEM_MCPP` bcond + Patch0006 gate + `Findmcpp-system.cmake` shim creating `3rdParty::mcpp` IMPORTED target against `/usr/lib64/libmcpp.so` + `/usr/include/mcpp_lib.h`. This is the third Stage 2 swap (library-link variant; spirv-cross + dxc were binary shellouts). Probably ~1-2 iterations to nail the cmake target shape.

- **Tier 7 redesign** -- run 25553050229 (2026-05-08) confirmed Tier 7 infrastructure works end-to-end, but the test design is too tight: AssetProcessorBatch's parallel-jobs scheduler hits a cold-cache SRG-merge dependency-ordering quirk on first pass (viewsrg.srgi / scenesrg.srgi auto-generated AFTER ShaderAssetBuilder runs), spuriously failing 76+ FBX bakes + 210 shaders. Workflow flipped to opt-in (run_asset_bake default false) for cron until design fix. Next iteration options: (a) AP `--scanFolders` to scope to project Assets/ only, (b) two-pass AP run + check second-pass results, (c) upstream bug report on the cold-cache parallel SRG ordering. Memory captured at `project_tier7_cold_cache_quirk.md`.

### Warm

- **Patch0009 PhysX4-hunk timebomb** -- when PR #19726 (PhysX 4 retirement) merges upstream, our `Gems/PhysX/Core/PhysX4/.../PAL_linux.cmake` patch hunk will fail to apply. Mechanical rebase: drop the PhysX4 hunk; regenerate Patch0009 with only the PhysX5 hunk. Not blocked on us. Annotated in three places (spec Patch0009 declaration, patch file header, NvCloth memory).
- ~~**Drift-detection workflow rollout**~~ -- DONE 2026-05-08. Workflow committed (`.github/workflows/check-deps-drift.yml`), first manual trigger uncovered a "dubious ownership" git-config issue (Fedora container + actions/checkout uid mismatch), fixed in commit 360b088 (`safe.directory` step), re-trigger created sticky [issue #9 "Dependency drift report"](https://github.com/nickschuetz/o3de-rpm/issues/9). The 'drift' label was created proactively + applied. Weekly cron at Mondays 06:00 UTC active. The workflow's exit-non-zero-on-drift behavior is intentional (red GHA dot surfaces real action items).
- ~~**Tier 7 FBX-bake test rollout**~~ -- DONE 2026-05-08 in the sense of "first live run executed". Run 25553050229 confirmed the AssetProcessorBatch invocation works against the RPM-installed engine; the test fired end-to-end and uploaded artifact logs cleanly. Remaining design issue (cold-cache AP ordering quirk; not packaging) tracked as the new "Tier 7 redesign" item above.

### Cool (someday/maybe)

- **Drift-detection findings act-on** -- the audit research agent today identified 5 drift items in `o3de-dependencies` (qt5 5.15.1 vs .2; AWSNativeSDK .361 vs .288; astc-encoder 5.3.0 vs 3.2; ISPCTexComp commit 691513b vs 36b80aa; mikkelsen label form). Plus 2 cruft (aws-gamelift, PhysX no longer referenced on Linux). When the drift-detection workflow lands and the sticky issue surfaces these, decide which to fix.
- ~~**F43 cleanup verification**~~ -- DONE 2026-05-08. Audited all 4 engine projects (`o3de`, `o3de-stabilization`, `o3de-snapshot`, `o3de-experimental`); all already F44 + rawhide only (plus `o3de` had `epel-10-x86_64` per Nick's intent at the time, which was shorthand for the CS10 line; that chroot was replaced with `centos-stream-10-x86_64` later in the same day during the CS10 pivot, see entry below). No action needed.
- **CryCommon int64/uint64 C99 migration** -- Nick_L 2026-05-05 said upstream is "open" to this; if an engine PR lands, `system_tiff` activates automatically. Not blocking; pure optionality for someone else to pick up.
- **Engine-side cmake-gate cleanup for Stage 2 swaps** -- both system_spirvcross and system_dxc currently use install-time symlink overlays (the bundled fetches still happen at cmake-config time, then we overlay). Cleaner long-term: write Find shims that create IMPORTED EXECUTABLE / IMPORTED SHARED targets pointing at /usr/bin/, then gate Patch0006 to skip the upstream fetch entirely. Saves the cmake-time fetch.

---

## Reference state at end-of-day 2026-05-08

- **HEAD on main**: `0e5f751` ("feat(stage2-rename): o3de-<dep> -> o3de2605-<dep> for versioned-major coexistence")
- **Spec changelog**: `2605.0-42`
- **Active in `o3de-stabilization`**: 7-pack
- **Active in `o3de-experimental` chroot config**: 16 system_* flags (snapshot + stabilization + 12 Stage 1 + 3 Stage 2 = 17 with_opts entries)
- **In `o3de-dependencies`** (after F43 chroot drop, F44 + rawhide only): 9 existing deps + 3 Stage 2 PoCs all ✓ green AND renamed to `o3deNNNN-<dep>` form: `o3de2605-spirv-cross-1.3.275.0-1.rev3`, `o3de2605-dxc-spirv-1.8.2505.1-1.rev13`, `o3de2605-mcpp-az-2.7.2-1.rev8` (rename builds 10437362/10437377/10437378 in flight as of end-of-day; the unversioned predecessor packages stay live as Obsoletes-from-the-new ones until they land green).
- **Upstream PRs**: **#19733 (Lua) MERGED 2026-05-08** by Nicholas Lawson into development. **#19734 (libtiff C99) MERGED 2026-05-08** same day, same reviewer. Both happened within ~1h of each other (~11:18 AM). #19737 (Microphone libsamplerate PAL gate) still REVIEW_REQUIRED + 1 unrelated Android-Asset CI failure. #19738 (googlebenchmark gate) **CLOSED 2026-05-08** -- Nick_L clarified architectural premise was wrong (LY_DISABLE_TEST_MODULES means "skip our internal test modules" not "disable test infrastructure"; AzTest + AzTestRunner + gbench all ship unconditionally for gem developers). Replacement direction: `system_googlebenchmark` Stage 1 swap against Fedora's `google-benchmark-devel`. **Side bug surfaced from the same investigation:** `libbenchmark.a` standalone archive is NOT installed alongside `libgtest.a` + `libgmock.a` even though gbench source IS compiled into AzTestRunner -- exactly the missing-benchmark-libs case Nick_L predicted on the PR thread. NOT a packaging-side issue (we just ship what cmake installs); it's an upstream cmake-install rule mismatch worth a separate o3de/o3de PR. Memory note: `project_az_test_runner_architecture.md` updated with the empirical finding.

- **Patch dropoff implication of #19733 + #19734 merging**: when we pull a fresh snapshot from `development` (or once `stabilization/26050` cherry-picks these forward), our `sources/0008-azcore-drop-lua-lobject-include.patch` and `sources/0007-libtiff-c99-typedefs.patch` become redundant. Either they'll fail with "patch already applied" at `%autosetup -p1` time (forcing the drop) or they'll apply cleanly because the upstream merges haven't reached the snapshot yet. Action: when next snapshot rebase happens, audit these two patches; drop them from spec + sources/ if upstream has the fix, or keep them if the snapshot pre-dates the merge. No urgency since stabilization/26050 doesn't auto-pick from development.
- **Audits done**: 9 (Lua, poly2tri, squish-ccr, assimp, SQLite, libsamplerate, SPIRVCross, googlebenchmark, mcpp); plus the empirical 3p-versioning research that drove the rename decision.
- **Memory notes added today**: `feedback_no_em_dashes.md`, `project_o3de_unicode_validator.md`, `project_tier7_cold_cache_quirk.md`, `feedback_copr_edit_chroot_replaces.md`, `project_lua_5_5_newstate_break.md`, `project_az_test_runner_architecture.md`, `project_o3de_3p_versioning_research.md`, plus update to `project_mcpp_architectural_choice.md` (Update 2026-05-08 audit reframing section).
- **PoC working trees** (local-only git, not pushed upstream): `/home/nschuetz/o3de2605-dxc-spirv-poc/`, `/home/nschuetz/o3de2605-spirv-cross-poc/`, `/home/nschuetz/o3de2605-mcpp-az-poc/` (renamed from unversioned form 2026-05-08 to align dir names with the spec-internal versioned package names).
- **Audit notes** (gitignored, ephemeral): `/tmp/o3de-assimp-audit/{INVESTIGATION_NOTES,SQLITE_INVESTIGATION_NOTES,LIBSAMPLERATE_INVESTIGATION_NOTES,SPIRVCROSS_INVESTIGATION_NOTES,GOOGLEBENCHMARK_INVESTIGATION_NOTES,MCPP_INVESTIGATION_NOTES}.md`, `/tmp/o3de-poly2tri-audit/INVESTIGATION_NOTES.md`

---

## End-of-day 2026-05-07 (history) -- what landed

Big day. Five concrete milestones across the Stage 1 / Stage 2 / upstream-PR tracks.

- **9-pack VALIDATED end-to-end on `o3de-experimental`** (build 10433646; CI run 25522053232). Adds system_lua + system_poly2tri to the 7-pack.
- **7-pack PROMOTED to `o3de-stabilization`** (build 10433491; CI run 25520049089). Real users can install via `dnf copr enable hellaenergy/o3de-stabilization && dnf install o3de2605`.
- **SPIRV-Cross PoC ✓ GREEN** (`o3de-spirv-cross-1.3.275.0-1.rev2`, build 10434617). First binary-only PoC to land.
- **DXC PoC at 99.5%** -- rev10 reached step 1106/1111; rev11 transitive-link attempt didn't propagate. Today's rev12 fix (Patch0002 at clangSPIRV's LINK_LIBS) made it green.
- **8 audits in one day** (Lua/poly2tri/squish-ccr/assimp/SQLite/libsamplerate/SPIRVCross/googlebenchmark) -- all 5 "trivial flip" annotations from the original BUNDLED_LIBRARIES.md verified or reframed.
- **2 upstream PRs submitted** (#19733 AzCore Lua, #19734 libtiff C99); both approved by nick-l-o3de.

Reference state at end-of-day 2026-05-07:
- HEAD: `09baf37` ("copr-metadata: sync 9-pack experimental + 7-pack stabilization status")
- Spec: `2605.0-34`
- Memory notes added: `feedback_audit_pattern_yields_findings.md`; updates to `project_nvcloth_status.md` + `project_o3de_restricted_bundles.md`
