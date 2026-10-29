# Built via .copr/Makefile (scripts/make-srpm.sh): it resolves the latest
# upstream release tag and prepends %%global commit/upstream_version, and
# provides Source0 plus the vendored crates in Source1 (offline build).
%global forgeurl https://github.com/Linus789/wl-clip-persist
%global srpm_track release
%global cargo_manifest_dir .
%{!?commit:%global commit 0000000000000000000000000000000000000000}
%{!?upstream_version:%global upstream_version 0}
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:           wl-clip-persist
Version:        %{upstream_version}
Release:        1%{?dist}
Summary:        Keep Wayland clipboard even after programs close

# wl-clip-persist itself is MIT; licenses of the statically linked crates are
# listed in LICENSE.dependencies and cargo-vendor.txt.
License:        MIT
URL:            %{forgeurl}
Source0:        %{forgeurl}/archive/%{commit}/wl-clip-persist-%{commit}.tar.gz
Source1:        %{name}-vendor-%{shortcommit}.tar.xz

ExclusiveArch:  %{rust_arches}

BuildRequires:  cargo-rpm-macros >= 26

%description
wl-clip-persist keeps the Wayland clipboard contents available after the
program they were copied from exits. It reads every new selection into
memory and offers it again. The compositor must support the
ext-data-control-v1 or wlr-data-control-unstable-v1 protocol.

%prep
%autosetup -n wl-clip-persist-%{commit} -p1 -a1
%cargo_prep -v vendor
# Wire vendored git dependencies (if any) next to crates.io.
awk '/^\[source\./ { keep = ($0 !~ /^\[source\.(crates-io|vendored-sources)\]$/) } keep' \
    vendor/vendor-config.toml >> .cargo/config.toml
# Executable .rs files starting with "#![" break brp-mangle-shebangs.
find vendor -type f -name "*.rs" -perm /111 -exec chmod a-x {} +

%build
%cargo_build
%{cargo_license_summary}
%{cargo_license} > LICENSE.dependencies
%{cargo_vendor_manifest}

%install
install -Dpm0755 target/rpm/wl-clip-persist %{buildroot}%{_bindir}/wl-clip-persist

%check
%{buildroot}%{_bindir}/wl-clip-persist --version

%files
%license LICENSE LICENSE.dependencies cargo-vendor.txt
%doc README.md
%{_bindir}/wl-clip-persist

%changelog
