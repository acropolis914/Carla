{ pkgs ? import <nixpkgs> {} }:

let
  clara = pkgs.callPackage ./default.nix {};
in
pkgs.mkShell {
  inputsFrom = [ clara ];
  packages = with pkgs; [
    gdb
    valgrind
  ];
}
