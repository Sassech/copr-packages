# copr-Sassech

RPM packaging for the COPR project [`sassech/packages`](https://copr.fedorainfracloud.org/coprs/sassech/packages/)
(Fedora 44, 45 and rawhide, x86_64).

## Install

```bash
sudo dnf copr enable sassech/packages
sudo dnf install rmpc            # or rmpc-git, whatrust, sonora, ...
```

Each app comes in two flavors that conflict with each other (same files):

| Package | Upstream | Tracks |
|---|---|---|
| `rmpc` / `rmpc-git` | [mierak/rmpc](https://github.com/mierak/rmpc) | latest release tag / latest commit |
| `whatrust` / `whatrust-git` | [karem505/whatRust](https://github.com/karem505/whatRust) | latest release tag / latest commit |
| `sonora` / `sonora-git` | [sonorahq/sonora](https://github.com/sonorahq/sonora) | latest release tag / latest commit |
| `stremio-linux-shell` / `stremio-linux-shell-git` | [Stremio/stremio-linux-shell](https://github.com/Stremio/stremio-linux-shell) | latest release tag / latest commit |

Git snapshots are versioned `<last tag>^<commit date>git<short sha>`, so they
sort below the next upstream release.

## Layout

```
.copr/Makefile         COPR make_srpm entry point
scripts/make-srpm.sh   resolves the upstream tag/commit, downloads sources,
                       vendors crates, writes the spec and builds the SRPM
<package>/<package>.spec
```

No version or commit is stored in this repo. At SRPM time `make-srpm.sh`:

1. resolves the latest stable tag (`git ls-remote --tags`) or the default
   branch HEAD, depending on `%global srpm_track release|git` in the spec;
2. downloads the GitHub archive of that commit (`Source0`);
3. runs `cargo vendor` and packs all crates into `Source1`;
4. prepends `%global commit/upstream_version/snapdate` plus a changelog entry
   to a copy of the spec and runs `rpmbuild -bs`.

The binary build is therefore fully offline: **"Enable internet access during
builds" can stay off** in the COPR project. The SRPM step needs network (COPR
provides it).

## COPR package configuration

Every package uses the SCM source with the `make_srpm` method, the repo root as
subdirectory and its own spec path:

```bash
REPO=<clone URL of this repo>
for pkg in rmpc rmpc-git whatrust whatrust-git sonora sonora-git \
           stremio-linux-shell stremio-linux-shell-git; do
    copr-cli add-package-scm packages --name "$pkg" --clone-url "$REPO" \
        --method make_srpm --spec "$pkg/$pkg.spec"
done
copr-cli build-package packages --name rmpc
```

COPR does not watch upstream projects. To pick up new releases or commits,
rebuild periodically (e.g. a cron job or scheduled CI running
`copr-cli build-package packages --name <pkg>`). Rebuilding an unchanged
upstream produces the same version again.

## Build locally

Needs `make`, `git`, `curl`, `cargo` and `rpm-build` (installed automatically
when run as root, as in COPR):

```bash
make -f .copr/Makefile srpm spec=rmpc/rmpc.spec        # SRPM in _build/srpm/
sudo dnf builddep _build/srpm/rmpc-*.src.rpm
rpmbuild --rebuild _build/srpm/rmpc-*.src.rpm
```

Set `PACKAGER="Name <email>"` to change the changelog identity.

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
