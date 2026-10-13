Name:           clara
Version:        0.1.0
Release:        git_${{ github.sha }}%{?dist}
Summary:        Clara audio application

License:        GPL-3.0-or-later
Source0:        clara-git-${{ github.sha }}.tar.gz

BuildRequires:  gcc-c++ make pkgconf
BuildRequires:  qt6-qtbase-devel qt6-qtsvg-devel qt6-qttools-devel
BuildRequires:  SDL2-devel python3-devel
Requires:       qt6-qtbase qt6-qtsvg SDL2 python3-pyqt6

%description
Clara is a Qt6 and SDL2-based application.

%prep
%autosetup -n clara-git-${{ github.sha }}

%build
%make_build DEFAULT_QT=6

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_bindir}
find build -type f -executable -exec install -Dpm 0755 {} %{buildroot}%{_bindir}/ \;

%files
%{_bindir}/*

%changelog
* Tue Oct 13 2026 CI Builder <ci@build.local> - 0.1.0
- Automated CI package build
