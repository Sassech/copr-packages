# Built via .copr/Makefile (scripts/make-srpm.sh): it resolves the latest
# commit on the default branch and prepends %%global commit, snapdate (commit
# date) and upstream_version (latest release tag, the snapshot base), and
# provides Source0 plus the vendored crates in Source1 (offline build).
%global forgeurl https://github.com/Stremio/stremio-linux-shell
%global srpm_track git
%global cargo_manifest_dir .
%{!?commit:%global commit 0000000000000000000000000000000000000000}
%{!?upstream_version:%global upstream_version 0}
%{!?snapdate:%global snapdate 19700101}
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global appid com.stremio.Stremio

Name:           stremio-linux-shell-git
Version:        %{upstream_version}^%{snapdate}git%{shortcommit}
Release:        1%{?dist}
Summary:        GTK4/WebKitGTK desktop shell for Stremio

# The shell is GPL-3.0-only; licenses of the statically linked crates are
# listed in LICENSE.dependencies and cargo-vendor.txt. server.js is the
# prebuilt Stremio streaming server shipped in the upstream repository.
License:        GPL-3.0-only
URL:            %{forgeurl}
Source0:        %{forgeurl}/archive/%{commit}/stremio-linux-shell-%{commit}.tar.gz
Source1:        %{name}-vendor-%{shortcommit}.tar.xz

ExclusiveArch:  %{rust_arches}

BuildRequires:  cargo-rpm-macros >= 26
BuildRequires:  gcc
BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  glib2-devel
BuildRequires:  pkgconfig(gtk4)
BuildRequires:  pkgconfig(libadwaita-1)
BuildRequires:  pkgconfig(webkitgtk-6.0)
BuildRequires:  pkgconfig(mpv)
BuildRequires:  pkgconfig(epoxy)
BuildRequires:  pkgconfig(dbus-1)

# The streaming server runs on Node.js; libepoxy is loaded with dlopen.
Requires:       /usr/bin/node
Requires:       libepoxy
Requires:       hicolor-icon-theme
Conflicts:      stremio-linux-shell
# Same /usr/bin/stremio and desktop entry as the legacy Qt stremio package.
Conflicts:      stremio

%description
Stremio is a media center for streaming video content. This package provides
the Stremio Linux shell: a GTK4 and WebKitGTK application with native video
playback that runs the Stremio web UI and its local streaming server.

This package tracks the latest commit of the upstream default branch.

%prep
%autosetup -n stremio-linux-shell-%{commit} -p1 -a1
%cargo_prep -v vendor
# Wire vendored git dependencies (if any) next to crates.io.
awk '/^\[source\./ { keep = ($0 !~ /^\[source\.(crates-io|vendored-sources)\]$/) } keep' \
    vendor/vendor-config.toml >> .cargo/config.toml
# Executable .rs files starting with "#![" break brp-mangle-shebangs.
find vendor -type f -name "*.rs" -perm /111 -exec chmod a-x {} +

%build
# Releases <= 1.2.2 look up translations only in the build tree, so they show
# English; newer upstream honors STREMIO_LOCALEDIR. Upstream sets these in .cargo/config.toml, which %%cargo_prep replaces.
export GETTEXT_DIR="$PWD/target/locale"
export GSETTINGS_SCHEMA_DIR="$PWD/target/schemas"
export STREMIO_LOCALEDIR=%{_datadir}/locale
%cargo_build
%{cargo_license_summary}
%{cargo_license} > LICENSE.dependencies
%{cargo_vendor_manifest}

%install
install -Dpm0755 target/rpm/stremio-linux-shell %{buildroot}%{_libexecdir}/stremio/stremio
install -Dpm0644 data/server.js %{buildroot}%{_libexecdir}/stremio/server.js
install -dm0755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/stremio <<'EOF'
#!/bin/sh
# Use the GSK OpenGL renderer on Nvidia cards.
if [ -e /dev/nvidia0 ]; then
    export GSK_RENDERER=opengl
fi
export SERVER_PATH="${SERVER_PATH:-%{_libexecdir}/stremio/server.js}"
export ANV_DEBUG="${ANV_DEBUG:-video-decode,video-encode}"
exec %{_libexecdir}/stremio/stremio "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/stremio

desktop-file-install --dir=%{buildroot}%{_datadir}/applications data/%{appid}.desktop
install -Dpm0644 data/icons/%{appid}.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
install -Dpm0644 data/%{appid}.metainfo.xml %{buildroot}%{_metainfodir}/%{appid}.metainfo.xml
install -Dpm0644 data/%{appid}.gschema.xml %{buildroot}%{_datadir}/glib-2.0/schemas/%{appid}.gschema.xml
install -dm0755 %{buildroot}%{_datadir}/dbus-1/services
sed 's|^Exec=.*|Exec=%{_bindir}/stremio --gapplication-service|' data/%{appid}.service \
    > %{buildroot}%{_datadir}/dbus-1/services/%{appid}.service
install -Dpm0644 data/stremio.1 %{buildroot}%{_mandir}/man1/stremio.1
# build.rs writes catalogs to target/locale (main) or po/ (<= 1.2.2).
for mo in target/locale/*/LC_MESSAGES/stremio.mo po/*/LC_MESSAGES/stremio.mo; do
    [ -f "$mo" ] || continue
    lang="$(basename "$(dirname "$(dirname "$mo")")")"
    install -Dpm0644 "$mo" %{buildroot}%{_datadir}/locale/${lang}/LC_MESSAGES/stremio.mo
done
%find_lang stremio

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop

%files -f stremio.lang
%license LICENSE LICENSE.dependencies cargo-vendor.txt
%doc README.md
%{_bindir}/stremio
%{_libexecdir}/stremio/
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
%{_metainfodir}/%{appid}.metainfo.xml
%{_datadir}/glib-2.0/schemas/%{appid}.gschema.xml
%{_datadir}/dbus-1/services/%{appid}.service
%{_mandir}/man1/stremio.1*

%changelog
