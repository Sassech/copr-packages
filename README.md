# copr-packages

RPM packaging for the COPR project [`sassech/packages`](https://copr.fedorainfracloud.org/coprs/sassech/packages/)
(Fedora 44, 45 and rawhide, x86_64). Versions are never pinned: each build
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
| `sonora` / `sonora-git` | [sonorahq/sonora](https://github.com/sonorahq/sonora) | latest release tag / latest commit (x86_64) |
| `stremio-linux-shell` / `stremio-linux-shell-git` | [Stremio/stremio-linux-shell](https://github.com/Stremio/stremio-linux-shell) | latest release tag / latest commit |

## Layout

```
.copr/Makefile                  COPR make_srpm entry point
scripts/make-srpm.sh            resolves upstream, vendors crates, builds the SRPM
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
  from git repositories and are vendored as well. x86_64 only.
- **stremio-linux-shell**: installs `/usr/bin/stremio` (a wrapper that sets
  `SERVER_PATH`) and the bundled streaming server, which runs on Node.js. It
  conflicts with the legacy Qt `stremio` package. Releases up to 1.2.2 look
  up translations only in the build tree, so the UI shows English.
