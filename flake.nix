{
  description = "Clara (Carla Improved) - Modular audio plugin host and patchbay";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        clara = pkgs.callPackage ./nix/default.nix {};
      in {
        packages = {
          default = clara;
          clara = clara;
        };

        apps = {
          default = {
            type = "app";
            program = "${clara}/bin/carla";
          };
        };

        devShells.default = pkgs.callPackage ./nix/shell.nix { inherit pkgs; };
      }
    );
}
