{
  description = "A development environment as a Nix Flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";
  };

  outputs =
    { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
    in
    {
      devShells."${system}".default =
        let
          pkgs = import nixpkgs {
            inherit system;
          };
        in
        pkgs.mkShell {
          packages = with pkgs; [
act
commitizen
            entr
            just
poetry
pre-commit
            (python3.withPackages ( ps: with ps; [ ]))
          ];

          shellHook = ''
            echo "Starting development environment..."
          '';
        };
    };
}
