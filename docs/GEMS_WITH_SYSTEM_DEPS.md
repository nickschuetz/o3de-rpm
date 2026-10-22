# Gems with system runtime dependencies

Some O3DE gems require system-level libraries or runtimes that this RPM does NOT bundle. This page documents which gems those are and how to satisfy their dependencies on Fedora 44+ / CentOS Stream 10+.

## Why this exists

The `o3deNNNN` RPM (`o3de2605`, `o3de2610`) ships the engine and ~117 gems sourced from the `o3de/o3de` repository. Additional gems live in the separate [`o3de/o3de-extras`](https://github.com/o3de/o3de-extras) repository and are not bundled into this RPM. They are discovered automatically by Project Manager via a default-registered remote gem repository and shown in the gem catalog with a download-cloud icon, indicating they fetch on demand into `~/.o3de/gems/<gem-name>/` when the user clicks "Download Gem". This is the same architecture upstream uses on Windows and Debian, and it lets each user opt in to only the gems they need.

A subset of those remote gems require external runtime dependencies that are too heavy or too license-encumbered to bundle into the engine RPM (or to ship from any single COPR project). Project Manager surfaces this requirement directly: each gem with a system dependency shows an information icon next to its description with text like `Requires ROS 2 installation (supported distributions: Humble, Jazzy). Source your workspace before building the Gem.` That message is the canonical source of truth for what each gem needs.

When a user enables one of these gems in their project, the project-side `cmake -B build` invocation calls `find_package(<dep> ...)` to locate the system runtime. If the dependency is not installed (or its setup script is not sourced), cmake fails with a clear error pointing at the missing package.

## General workflow

1. Open Project Manager (run `o3deNNNN`, e.g. `o3de2610`, from a terminal or launch via the desktop entry).
2. Browse the Gem Catalog and find the gem you want.
3. Read the information icon next to the gem description for any runtime dependency notes.
4. Install the required runtime via your preferred path (per-family details below).
5. Click "Download Gem" in Project Manager to fetch the gem source into `~/.o3de/gems/`.
6. Add the gem to your project's gem list (Project Manager `Edit Project Gems` UI or directly in `<project>/project.json`).
7. Source any required setup script in the shell where you run the project's cmake (e.g. `source /opt/ros/lyrical/setup.bash`).
8. Build the project with `cmake -S <project> -B <project>/build` followed by `cmake --build <project>/build`. This needs the `o3deNNNN-devel` subpackage installed: every project's launchers link static engine archives it carries.

## ROS 2 family

The largest family of gems with a shared runtime dependency. All six gems below require a ROS 2 installation and a sourced `setup.bash` before project build. Supported ROS 2 distributions per upstream gem authors (RobotecAI): Humble, Jazzy and, from the 26.10 line, Lyrical.

| Gem | Purpose |
|---|---|
| `ROS2` | Core integration: tools and components for creating ROS 2 simulations |
| `ROS2Controllers` | Robot control via ROS 2 communication interfaces |
| `ROS2Sensors` | Sensor simulation publishing over ROS 2 |
| `ROS2RobotImporter` | Importing robot descriptions (URDF / SDF) |
| `ROS2SampleRobots` | Sample robot models / scenes for getting started |
| `SimulationInterfaces` | ROS 2 + C++ API for simulation control |

`LevelGeoreferencing` (visible in Project Manager as a gem dependency of `ROS2`) auto-enables when `ROS2` is enabled and inherits the same system requirement transitively.

### Which ROS 2 distribution

- **O3DE 26.10 and newer: Lyrical Luth.** The Gems build against Lyrical since o3de/o3de-extras#1061, which is on the `stabilization/26100` branch that pairs with 26.10. `gazebo_msgs` has no Lyrical release; the Gems build without it and their optional Gazebo message support (ContactSensor, the Gazebo-message Spawner) stays off.
- **O3DE 26.05: Jazzy Jalisco.** The `main` branch of o3de-extras (the 26.05 line) does not have the Lyrical fix.

### Three install paths for ROS 2

Listed in order of long-term preference. Pick whichever fits your environment.

**1. Open Robotics official Fedora packages (production).** Open Robotics ships official ROS 2 RPMs for Fedora, but as of 2026-10-16 they cover Fedora 43 only, which is below this RPM's Fedora 44+ / CentOS Stream 10+ floor. Use them once they cover your release; check the [ros2-rpm RELATED-WORK doc](https://github.com/nickschuetz/ros2-rpm/blob/main/docs/RELATED-WORK.md) for status.

**2. `hellaenergy/ros2` (Lyrical) and `hellaenergy/ros2-jazzy` (Jazzy) development COPRs (development today).** Development-only ROS 2 RPMs, not the official ROS 2 packages for Fedora. Built for Fedora 44, 45 and rawhide and CentOS Stream 10, on `x86_64` and `aarch64`, installing under `/opt/ros/<distro>/`. Source: <https://github.com/nickschuetz/ros2-rpm>.

For O3DE 26.10 and newer, one metapackage installs every ROS 2 package the Gems link against (rclcpp, rclcpp_action, tf2_ros, the std, geometry, sensor, nav, ackermann, vision and control message packages, simulation_interfaces, the Fast DDS RMW), plus the `ros2` command line tools as weak dependencies:

```
sudo dnf copr enable hellaenergy/ros2
sudo dnf install ros-lyrical-o3de-gem-deps
source /opt/ros/lyrical/setup.bash
```

Tested end to end on 2026-10-22 in a fresh Fedora 44 container: o3de2610 2610.0-126 with `ros-lyrical-o3de-gem-deps` 1.0.0, and the ROS2 Gem 4.4.0 from o3de-extras `stabilization/26100`. The project configured and built, and a running GameLauncher showed `/o3de_ros2_node` publishing `/tf` and `/tf_static`.

For O3DE 26.05, use Jazzy (`ros-jazzy-gazebo-msgs` adds the optional Gazebo messages):

```
sudo dnf copr enable hellaenergy/ros2-jazzy
sudo dnf install ros-jazzy-ros-base ros-jazzy-gazebo-msgs
source /opt/ros/jazzy/setup.bash
```

When you start Project Manager or the Editor from the desktop menu, the launcher imports the ROS 2 environment from `/opt/ros/<distro>/` for you (newest distribution wins; `O3DE_ROS_DISTRO=<name>` pins one, `O3DE_DISABLE_ROS2=1` turns it off). From a terminal, source `setup.bash` yourself as shown.

**3. Source build via `colcon` and `rosdep` (advanced).** Standard ROS 2 from-source workflow. Useful if you need a ROS 2 component that neither path #1 nor path #2 ships, or if you want to test against an unreleased ROS 2 version. Out of scope for this document; refer to the [ROS 2 official source-install instructions](https://docs.ros.org/en/jazzy/Installation/Alternatives/Ubuntu-Development-Setup.html) (the steps generalize to Fedora with rosdep platform overrides).

### Pitfalls

- **`setup.bash` must be sourced in the SAME shell** that runs `cmake -S <project> -B build`. If you source it then open a new terminal and run cmake there, the environment variables (`AMENT_PREFIX_PATH`, `CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`, etc.) will not be present and cmake's `find_package(rclcpp)` will fail.
- **Distribution mismatch**: the Gems record the ROS 2 distribution a project was configured with and stop with "ROS 2 distribution does not match" if a different one is sourced later; reconfigure the project after switching. Mixing distributions in one build is not supported and may surface as undefined references at link time. Project Manager does not check ROS 2 distribution at gem-download time; the build-time error is your only signal.
- **Mixing install paths**: do not have both `hellaenergy/ros2` packages and a source build of ROS 2 active in the same shell. The shell environment can satisfy `find_package(rclcpp)` from either, but library-version mismatches are easy to introduce. Pick one path per project.
- **First `ros2 node list` comes back empty**: right after the launcher starts, the first `ros2 node list` may return nothing because the ros2 daemon has just started and has not finished discovery; run it again or use `ros2 node list --no-daemon`. The Gem's node is `/o3de_ros2_node`.

## Audio Wwise (stub)

`AudioEngineWwise` requires the Audiokinetic Wwise SDK. License-restricted and not redistributable through Fedora, COPR, or any open-source channel. Users must obtain the SDK directly from Audiokinetic and install per their instructions before enabling the gem.

This section will be expanded with concrete Fedora-side install steps the first time a user reports their workflow. For now the gem's information icon in Project Manager is the canonical reference.

## XR (stub)

`OpenXRVk` and `XR` require an OpenXR runtime appropriate for the target headset (Meta Quest, Valve Index, etc.). Fedora ships `openxr` and `openxr-libs` in the default repositories; headset-specific runtime layers (Meta XR, SteamVR, Monado) are obtained per vendor.

This section will be expanded the first time a user reports their workflow.

## AI / ML (stub)

`MachineLearning` requires an inference runtime; the gem author specifies which one in the Project Manager information icon (likely ONNX Runtime or similar). Fedora ships `onnxruntime` in the main repositories (1.22 on Fedora 44, checked 2026-10-21).

This section will be expanded the first time a user reports their workflow.

## Adding a new gem to this doc

When a new gem-with-system-deps appears in `o3de-extras` or in any registered remote gem repo, add a section here rather than creating a new RPM metapackage. The pattern that works:

1. List the gem(s) and their canonical system dependency.
2. Document one or more install paths for that dependency on Fedora 44+ / CS10+.
3. Note any setup scripts that must be sourced + which shell scope they apply to.
4. Capture pitfalls (version mismatches, distribution mismatches, environment scope) the first time a user hits them.

This keeps the gems-with-system-deps surface in one place, scales as the catalog grows, and avoids the maintenance burden of per-gem convenience metapackages that would couple the engine RPM to specific external distribution mechanisms.
