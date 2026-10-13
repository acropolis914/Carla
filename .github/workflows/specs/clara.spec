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
# Built in prior step
true

%install
rm -rf %{buildroot}
make install PREFIX=/usr DESTDIR=%{buildroot} DEFAULT_QT=6

%files
/usr/*

%changelog
* Tue Oct 13 2026 CI Builder <ci@build.local> - 0.1.0-1
- Automated CI package build
