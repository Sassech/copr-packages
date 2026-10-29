# copr-packages

RPM packaging for the COPR project [`sassech/packages`](https://copr.fedorainfracloud.org/coprs/sassech/packages/)
(Fedora 44, 45 and rawhide, x86_64 and aarch64). Versions are never pinned: each build
resolves the latest upstream tag or commit, and a GitHub workflow rebuilds
packages when upstream changes.

```bash
sudo dnf copr enable sassech/packages
sudo dnf install rmpc            # or rmpc-git, whatrust, sonora, ...
```

| Package | Upstream | Tracks |
|---|---|---|
| `rmpc` / `rmpc-git` | [mierak/rmpc](https://github.com/mierak/rmpc) | latest release tag / latest commit |
| `whatrust` / `whatrust-git` | [karem505/whatRust](https://github.com/karem505/whatRust) | latest release tag / latest commit |
| `sonora` / `sonora-git` | [sonorahq/sonora](https://github.com/sonorahq/sonora) | latest release tag / latest commit |
| `stremio-linux-shell` / `stremio-linux-shell-git` | [Stremio/stremio-linux-shell](https://github.com/Stremio/stremio-linux-shell) | latest release tag / latest commit |
| `noise-suppression-for-voice-ladspa` | [werman/noise-suppression-for-voice](https://github.com/werman/noise-suppression-for-voice) | latest release tag |
| `wl-clip-persist` | [Linus789/wl-clip-persist](https://github.com/Linus789/wl-clip-persist) | latest release tag |

## Layout

```
.copr/Makefile                  COPR make_srpm entry point
scripts/make-srpm.sh            resolves upstream, vendors crates (Rust only), builds the SRPM
scripts/upstream-lib.sh         tag/commit resolution shared by both scripts
scripts/check-upstream.sh       compares upstream with COPR, triggers rebuilds
.github/workflows/copr-rebuild.yml  daily / push / manual rebuild workflow
<package>/<package>.spec
```

## Package notes

- **rmpc**: ships the man page, bash/fish/zsh completions and desktop entry
  generated or provided upstream. `mpd` is only recommended.
- **whatrust**: Tauri v2 app; the frontend is static (`settings-ui/`), so no
  Node.js is needed at build time. Installs the upstream desktop entry,
  AppStream metadata, icons and polkit action.
- **sonora**: builds only the `sonora` workspace package; several crates come
  from git repositories and are vendored as well.
- **stremio-linux-shell**: installs `/usr/bin/stremio` (a wrapper that sets
  `SERVER_PATH`) and the bundled streaming server, which runs on Node.js. It
  conflicts with the legacy Qt `stremio` package. Releases up to 1.2.2 look
  up translations only in the build tree, so the UI shows English.
- **noise-suppression-for-voice**: C++/CMake, nothing to vendor. Only the
  LADSPA plugin is built (`%{_libdir}/ladspa/librnnoise_ladspa.so`, for the
  PipeWire filter-chain module); the JUCE-based LV2/VST/VST3 plugins are off.
  The COPR package produces a single `noise-suppression-for-voice-ladspa` RPM.
- **wl-clip-persist**: installs only the binary; start it from the
  compositor's autostart (e.g. `wl-clip-persist --clipboard regular`). Needs
  a compositor with `ext-data-control-v1` or `wlr-data-control-unstable-v1`.
