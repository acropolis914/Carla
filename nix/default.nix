{ lib
, stdenv
, fetchFromGitHub ? null
, pkg-config
, makeWrapper
, qt6
, SDL2
, python3
, liblo ? null
, alsa-lib ? null
, libpulseaudio ? null
}:

stdenv.mkDerivation rec {
  pname = "clara";
  version = "0.1.0";

  src = lib.cleanSource ../.;

  nativeBuildInputs = [
    pkg-config
    makeWrapper
    qt6.wrapQtAppsHook
  ];

  buildInputs = [
    qt6.qtbase
    qt6.qtsvg
    qt6.qttools
    SDL2
    python3
    python3.pkgs.pyqt6
  ] ++ lib.optionals (liblo != null) [ liblo ]
    ++ lib.optionals (alsa-lib != null) [ alsa-lib ]
    ++ lib.optionals (libpulseaudio != null) [ libpulseaudio ];

  makeFlags = [
    "DEFAULT_QT=6"
    "PREFIX=$(out)"
  ];

  enableParallelBuilding = true;

  meta = with lib; {
    description = "Clara (Carla Improved) - Modular audio plugin host and patchbay";
    homepage = "https://github.com/acropolis914/Clara";
    license = licenses.gpl3Plus;
    platforms = platforms.linux;
  };
}
