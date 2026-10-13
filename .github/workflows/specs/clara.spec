Name:           clara
Version:        0.1.0
Release:        1%{?dist}
Summary:        Clara audio application (Carla Improved)

License:        GPL-3.0-or-later
Source0:        clara-source.tar.gz

BuildRequires:  gcc-c++ make pkgconf
BuildRequires:  qt6-qtbase-devel qt6-qtsvg-devel qt6-qttools-devel
BuildRequires:  SDL2-devel python3-devel
Requires:       qt6-qtbase qt6-qtsvg SDL2 python3-pyqt6

%description
Clara is a modular audio plugin host and patchbay based on Carla, built with Qt6 and SDL2.

%prep
%autosetup -n clara-source

%build
%make_build DEFAULT_QT=6

%install
rm -rf %{buildroot}
make install PREFIX=/usr DESTDIR=%{buildroot} DEFAULT_QT=6

%files
%{_bindir}/*
%{_libdir}/carla
%{_datadir}/carla
%{_datadir}/applications/*
%{_datadir}/icons/hicolor/*/*/*
%{_datadir}/mime/packages/*
%{_datadir}/appdata/*
%{_includedir}/carla
%{_libdir}/pkgconfig/*
%optional %{_libdir}/lv2/*
%optional %{_libdir}/vst/*

%changelog
* Tue Oct 13 2026 CI Builder <ci@build.local> - 0.1.0-1
- Automated CI package build
