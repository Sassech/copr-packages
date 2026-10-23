# Built via .copr/Makefile (scripts/make-srpm.sh): it resolves the latest
# upstream release tag and prepends %%global commit/upstream_version, and
# provides Source0 plus the vendored crates in Source1 (offline build).
%global forgeurl https://github.com/karem505/whatRust
%global srpm_track release
%global cargo_manifest_dir src-tauri
%{!?commit:%global commit 0000000000000000000000000000000000000000}
%{!?upstream_version:%global upstream_version 0}
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global appid io.github.karem505.whatRust

Name:           whatrust
Version:        %{upstream_version}
Release:        1%{?dist}
Summary:        Lightweight unofficial WhatsApp Web desktop client

# whatRust itself is MIT; licenses of the statically linked crates are listed
# in LICENSE.dependencies and cargo-vendor.txt.
License:        MIT
URL:            %{forgeurl}
Source0:        %{forgeurl}/archive/%{commit}/whatRust-%{commit}.tar.gz
Source1:        %{name}-vendor-%{shortcommit}.tar.xz

ExclusiveArch:  %{rust_arches}

BuildRequires:  cargo-rpm-macros >= 26
BuildRequires:  gcc
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
BuildRequires:  pkgconfig(dbus-1)
BuildRequires:  pkgconfig(gtk+-3.0)
BuildRequires:  pkgconfig(javascriptcoregtk-4.1)
BuildRequires:  pkgconfig(libsoup-3.0)
BuildRequires:  pkgconfig(webkit2gtk-4.1)

# The tray icon library is loaded at runtime (dlopen).
Requires:       libayatana-appindicator-gtk3
Requires:       hicolor-icon-theme
# Owns the polkit actions directory (app lock uses polkit).
Requires:       polkit
Conflicts:      whatrust-git

%description
whatRust is an unofficial, independent desktop client that loads the
official WhatsApp Web interface in the system WebKitGTK web view, adding
multiple accounts, native notifications, a system tray icon and an optional
password lock. It is not affiliated with WhatsApp or Meta.

%prep
%autosetup -n whatRust-%{commit} -p1
# Vendored crates and the cargo config live next to Cargo.toml (src-tauri).
cd src-tauri
tar -xf %{SOURCE1}
%cargo_prep -v vendor
# Wire vendored git dependencies (if any) next to crates.io.
awk '/^\[source\./ { keep = ($0 !~ /^\[source\.(crates-io|vendored-sources)\]$/) } keep' \
    vendor/vendor-config.toml >> .cargo/config.toml
# Executable .rs files starting with "#![" break brp-mangle-shebangs.
find vendor -type f -name "*.rs" -perm /111 -exec chmod a-x {} +

%build
cd src-tauri
# Production build (embedded assets), as `cargo tauri build` does.
%cargo_build -- --features tauri/custom-protocol
%{cargo_license_summary}
%{cargo_license} > LICENSE.dependencies
%{cargo_vendor_manifest}

%install
install -Dpm0755 src-tauri/target/rpm/whatrust %{buildroot}%{_bindir}/whatrust
desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    --remove-key=X-Flatpak flatpak/%{appid}.desktop
install -Dpm0644 flatpak/%{appid}.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
for size in 32 64 128; do
    install -Dpm0644 src-tauri/icons/${size}x${size}.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/%{appid}.png
done
install -Dpm0644 src-tauri/icons/128x128@2x.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/%{appid}.png
install -Dpm0644 src-tauri/icons/icon.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/%{appid}.png
install -Dpm0644 flatpak/%{appid}.metainfo.xml %{buildroot}%{_metainfodir}/%{appid}.metainfo.xml
install -Dpm0644 src-tauri/resources/com.karem.whatrust.policy \
    %{buildroot}%{_datadir}/polkit-1/actions/com.karem.whatrust.policy
install -pm0644 src-tauri/LICENSE.dependencies src-tauri/cargo-vendor.txt .

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/%{appid}.metainfo.xml

%files
%license LICENSE LICENSE.dependencies cargo-vendor.txt
%doc README.md
%{_bindir}/whatrust
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/*/apps/%{appid}.*
%{_metainfodir}/%{appid}.metainfo.xml
%{_datadir}/polkit-1/actions/com.karem.whatrust.policy

%changelog
