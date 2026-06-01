{
  description = "sask development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs   = nixpkgs.legacyPackages.${system};
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.python312
          pkgs.poetry
          pkgs.ruff
          pkgs.sqlite
        ];

        shellHook = ''
          echo "sask dev shell: $(python3 --version) | $(poetry --version) | ruff $(ruff --version)"
        '';
      };
    };
}
