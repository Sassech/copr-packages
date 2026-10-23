# Built via .copr/Makefile (scripts/make-srpm.sh): it resolves the latest
# upstream release tag and prepends %%global commit/upstream_version, and
# provides Source0 plus the vendored crates in Source1 (offline build).
%global forgeurl https://github.com/sonorahq/sonora
%global srpm_track release
%global cargo_manifest_dir .
%{!?commit:%global commit 0000000000000000000000000000000000000000}
%{!?upstream_version:%global upstream_version 0}
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:           sonora
Version:        %{upstream_version}
Release:        1%{?dist}
Summary:        Native music streaming client built with Rust and GPUI

# sonora itself is GPL-3.0-or-later; licenses of the statically linked crates
# are listed in LICENSE.dependencies and cargo-vendor.txt.
License:        GPL-3.0-or-later
URL:            %{forgeurl}
Source0:        %{forgeurl}/archive/%{commit}/sonora-%{commit}.tar.gz
Source1:        %{name}-vendor-%{shortcommit}.tar.xz

ExclusiveArch:  x86_64

BuildRequires:  cargo-rpm-macros >= 26
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  desktop-file-utils
BuildRequires:  pkgconfig(alsa)
BuildRequires:  pkgconfig(dbus-1)
BuildRequires:  pkgconfig(fontconfig)
BuildRequires:  pkgconfig(freetype2)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(sqlite3)
BuildRequires:  pkgconfig(vulkan)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(x11)
BuildRequires:  pkgconfig(x11-xcb)
BuildRequires:  pkgconfig(xcb)
BuildRequires:  pkgconfig(xcursor)
BuildRequires:  pkgconfig(xi)
BuildRequires:  pkgconfig(xkbcommon)
BuildRequires:  pkgconfig(xkbcommon-x11)

# GPU, input and display libraries are loaded at runtime (dlopen).
Requires:       hicolor-icon-theme
Requires:       libxkbcommon-x11
Requires:       vulkan-loader
Requires:       wayland-libs
Conflicts:      sonora-git

%description
Sonora is a native desktop music streaming client written in Rust with the
GPUI toolkit. It plays from several streaming services and local files with a
fast interface that supports custom themes.

%prep
%autosetup -n sonora-%{commit} -p1 -a1
%cargo_prep -v vendor
# Wire vendored git dependencies (if any) next to crates.io.
awk '/^\[source\./ { keep = ($0 !~ /^\[source\.(crates-io|vendored-sources)\]$/) } keep' \
    vendor/vendor-config.toml >> .cargo/config.toml
# Executable .rs files starting with "#![" break brp-mangle-shebangs.
find vendor -type f -name "*.rs" -perm /111 -exec chmod a-x {} +

%build
%cargo_build -- -p sonora
%{cargo_license_summary}
%{cargo_license} > LICENSE.dependencies
%{cargo_vendor_manifest}

%install
install -Dpm0755 target/rpm/sonora %{buildroot}%{_bindir}/sonora
desktop-file-install --dir=%{buildroot}%{_datadir}/applications assets/linux/sonora.desktop
install -Dpm0644 assets/linux/sonora.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/sonora.svg
for icon in assets/linux/icons/hicolor/*/apps/sonora.png; do
    size="$(basename "$(dirname "$(dirname "$icon")")")"
    install -Dpm0644 "$icon" %{buildroot}%{_datadir}/icons/hicolor/${size}/apps/sonora.png
done
mkdir -p licenses
install -pm0644 assets/fonts/LICENSE.txt licenses/LICENSE.Inter
for lic in assets/icons/*/LICENSE; do
    install -pm0644 "$lic" "licenses/LICENSE.icons-$(basename "$(dirname "$lic")")"
done

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/sonora.desktop

%files
%license COPYING THIRD-PARTY.md LICENSE.dependencies cargo-vendor.txt licenses/*
%doc README.md CHANGELOG.md PRIVACY.md
%{_bindir}/sonora
%{_datadir}/applications/sonora.desktop
%{_datadir}/icons/hicolor/*/apps/sonora.*

%changelog
