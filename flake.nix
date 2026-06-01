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
          export POETRY_VIRTUALENVS_PREFER_ACTIVE_PYTHON=true
          export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"
          echo "sask dev shell: $(python3 --version) | $(poetry --version) | ruff $(ruff --version)"
        '';
      };
    };
}
