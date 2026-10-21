# Installing O3DE from the RPM packages

> **Important:** The RPM packages are a preview and are still in active development. They are maintained by the community and are not built or tested by the O3DE release pipeline that produces the deb package and the Windows installer. Expect rough edges, and report problems with installing or running the RPM packages at https://github.com/nickschuetz/o3de-rpm/issues rather than in the O3DE engine repository.

On Fedora and CentOS Stream, install O3DE from the RPM packages. After a successful install, you'll have a stable, pre-built version of the engine and its Gems, and you'll be ready to create new or open existing projects with the **Project Manager** tool.

The RPM packages are built by the community (https://github.com/nickschuetz/o3de-rpm) and published in the `hellaenergy/o3de` package repository on Fedora COPR. They are available for x86_64 on:

* Fedora 44
* Fedora 45 and CentOS Stream 10 (packages are built, but have had less testing so far)

These steps are for O3DE 26.10 (package `o3de2610`), which reaches `hellaenergy/o3de` when 26.10.0 is released (target 2026-10-28). Until then, 26.10 release-candidate builds are in `hellaenergy/o3de-stabilization`: use that name in the `dnf copr enable` command below, and switch to `hellaenergy/o3de` after the release. For O3DE 26.05, install `o3de2605` instead.

## Installing on Fedora

```shell
sudo dnf copr enable hellaenergy/o3de
sudo dnf install o3de2610 o3de2610-devel
```

## Installing on CentOS Stream 10

CentOS Stream 10 also needs CRB and EPEL 10, which provide some of the libraries the engine uses:

```shell
sudo dnf install dnf-plugins-core
sudo dnf config-manager --set-enabled crb
sudo dnf install epel-release
sudo dnf copr enable hellaenergy/o3de centos-stream-10-x86_64
sudo dnf install o3de2610 o3de2610-devel
```

On CentOS Stream the repository name `centos-stream-10-x86_64` has to be given: without it, `dnf copr enable` looks for an `epel-10-x86_64` repository, which this project does not have, and fails.

## What gets installed

* `o3de2610`: the engine, Gems and tools.
* `o3de2610-devel`: the static libraries that projects link against. Project Manager needs it to build a project.
* The engine's third-party dependencies, from a second repository, `hellaenergy/o3de-dependencies`, which is enabled automatically along with `hellaenergy/o3de`.
* The compiler and tools needed to build projects (`clang`, `cmake`, `ninja-build` and the development headers), installed as recommended packages.

The download is about 2 GiB including dependencies, and the install uses about 8 GiB of disk space. Updates arrive through `dnf upgrade` along with the rest of your system.

If your system skips recommended packages (common in containers, Toolbox, distrobox and minimal installs), the build tools are left out and project builds fail. Install them with:

```shell
sudo dnf install $(rpm -q --recommends o3de2610 | awk '{print $1}')
```

## After installing

O3DE is installed in `/opt/O3DE/26.10.0`. Start **Project Manager** from your desktop's application menu (**O3DE 26.10.0**), or from the shell:
```shell
o3de2610
```

The command line tool is available as `o3de2610-cli`. Example:
```shell
o3de2610-cli create-project --project-path ~/MyProject --project-name MyProject
```

On a Wayland desktop, Project Manager and the Editor run through XWayland automatically. The 26.10 Editor supports X11 and XWayland only, so leave `QT_QPA_PLATFORM` unset or set it to `xcb`: with `QT_QPA_PLATFORM=wayland` the Editor crashes at startup (https://github.com/o3de/o3de/issues/19835).

On first launch, O3DE downloads its Python runtime into your home directory, so the first start needs an internet connection and takes a few minutes. Per-user data, such as registered projects and Gems, is stored in `~/.o3de`.

Some Gems from the remote Gem repository need extra system packages, for example the ROS 2 Gems. See https://github.com/nickschuetz/o3de-rpm/blob/main/docs/GEMS_WITH_SYSTEM_DEPS.md for what each Gem needs and how to install it.

The RPM packages use a separate package per major release (`o3de2605`, `o3de2610`), so you can install more than one O3DE version side by side.

## Next steps

From here, the O3DE documentation applies as written, with these substitutions for the RPM install:

* [System Requirements](https://docs.o3de.org/docs/welcome-guide/requirements/): check your GPU and driver.
* [Creating Projects Using Project Manager](https://docs.o3de.org/docs/welcome-guide/create/creating-projects-using-project-manager/): start Project Manager with `o3de2610` or from the application menu. That page's `<install-directory>/bin/<platform>/profile/Default` is `/opt/O3DE/26.10.0/bin/Linux/profile/Default` for the RPM, and the program there is `o3de` (not `o3de.exe`).
* [Create Projects on Linux (CLI)](https://docs.o3de.org/docs/welcome-guide/create/creating-projects-using-cli/creating-linux/): use `o3de2610-cli` wherever that page runs `scripts/o3de.sh`, and treat the RPM as a pre-built engine (not a source engine). The compiler and build tools the page uses were installed with the package.

## Removing O3DE

```shell
sudo dnf remove o3de2610 o3de2610-devel
```

This leaves `~/.o3de` and your projects in place. Delete `~/.o3de` yourself if you no longer need it.

Report problems with the RPM packages at https://github.com/nickschuetz/o3de-rpm/issues.
