# Built via .copr/Makefile (scripts/make-srpm.sh): it resolves the latest
# upstream release tag and prepends %%global commit/upstream_version, and
# provides Source0. No cargo_manifest_dir: C/C++ project, nothing to vendor
# (rnnoise and catch2 are bundled in external/).
%global forgeurl https://github.com/werman/noise-suppression-for-voice
%global srpm_track release
%{!?commit:%global commit 0000000000000000000000000000000000000000}
%{!?upstream_version:%global upstream_version 0}

Name:           noise-suppression-for-voice
Version:        %{upstream_version}
Release:        1%{?dist}
Summary:        Real-time noise suppression plugin for voice based on RNNoise

# The plugin is GPL-3.0-only; the statically linked rnnoise is BSD-3-Clause.
License:        GPL-3.0-only AND BSD-3-Clause
URL:            %{forgeurl}
Source0:        %{forgeurl}/archive/%{commit}/noise-suppression-for-voice-%{commit}.tar.gz

BuildRequires:  cmake
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  libatomic

%description
Real-time noise suppression plugin for voice, based on Xiph's RNNoise
recurrent neural network. Only the LADSPA plugin is built (JUCE-based
LV2/VST/VST3 plugins are disabled).

%package        ladspa
Summary:        LADSPA noise suppression plugin for voice

%description    ladspa
LADSPA plugin providing real-time noise suppression for voice, based on
RNNoise. It can be loaded by the PipeWire filter-chain module or by
PulseAudio's module-ladspa-sink to remove background noise from a microphone.

%prep
%autosetup -n noise-suppression-for-voice-%{commit} -p1

%build
# BUILD_FOR_RELEASE enables x86 run-time CPU detection (AVX2/SSE4.1 kernels).
%cmake \
    -DBUILD_FOR_RELEASE=ON \
    -DBUILD_TESTS=ON \
    -DBUILD_LADSPA_PLUGIN=ON \
    -DBUILD_VST_PLUGIN=OFF \
    -DBUILD_VST3_PLUGIN=OFF \
    -DBUILD_LV2_PLUGIN=OFF \
    -DBUILD_AU_PLUGIN=OFF \
    -DBUILD_AUV3_PLUGIN=OFF
%cmake_build

%install
%cmake_install

%check
# Upstream enables CTest only in src/common, so the top-level ctest finds no tests.
ctest --test-dir %{__cmake_builddir}/src/common --output-on-failure

# No %%files for the main package: only the -ladspa subpackage is produced.
%files ladspa
%license LICENSE external/rnnoise/COPYING
%doc README.md
%dir %{_libdir}/ladspa
%{_libdir}/ladspa/librnnoise_ladspa.so

%changelog
