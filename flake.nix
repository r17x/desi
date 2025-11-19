{
  description = "Desi - Desktop App with Python";

  outputs =
    inputs:
    inputs.flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];

      perSystem =
        {
          self',
          pkgs,
          lib,
          system,
          ...
        }:
        {

          # ship it
          packages.default = pkgs.writeShellApplication {
            name = "desi";
            runtimeInputs = [
              (pkgs.pythonSet.mkVirtualEnv "desi-env" pkgs.workspace.deps.default)
            ];
            text = "python ${inputs.self.outPath}/src/main.py";
          };

          _module.args.pkgs = import inputs.nixpkgs {
            inherit system;
            overlays = [
              (final: prev: {
                # building
                mkApplication = (prev.callPackage inputs.pyproject-nix.build.util { }).mkApplication;
                # pinned python with python 3.12
                python = prev.python312;
                pythonBase = prev.callPackage inputs.pyproject-nix.build.packages {
                  python = prev.python312;
                  stdenv = lib.optionals pkgs.stdenv.isDarwin pkgs.stdenv.override {
                    targetPlatform = pkgs.stdenv.targetPlatform // {
                      # Sets MacOS SDK version to 15.1 which implies Darwin version 24.
                      # See https://en.wikipedia.org/wiki/MacOS_version_history#Releases for more background on version numbers.
                      darwinSdkVersion = "15.1";
                    };
                  };
                };
                pythonSet = final.pythonBase.overrideScope (
                  lib.composeManyExtensions [
                    inputs.pyproject-build-systems.overlays.wheel
                    (final.workspace.mkPyprojectOverlay {
                      sourcePreference = "wheel";
                    })
                  ]
                );
                workspace = inputs.uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
              })
            ];
          };

          devShells.default =
            let
              inherit (pkgs) pythonSet;
              editableOverlay = pkgs.workspace.mkEditablePyprojectOverlay {
                # Use environment variable pointing to editable root directory
                root = "$REPO_ROOT";
                # Optional: Only enable editable for these packages
                # members = [ "desi" ];
              };

              editablePythonSet = pythonSet.overrideScope editableOverlay;

              virtualenv = editablePythonSet.mkVirtualEnv "desi-env" pkgs.workspace.deps.all;
            in

            pkgs.mkShell {
              nativeBuildInputs = [
                pkgs.qt6.full
              ];
              packages = [
                virtualenv
                pkgs.uv
              ];
              env = {
                UV_NO_SYNC = "1";
                UV_PYTHON = editablePythonSet.python.interpreter;
                UV_PYTHON_DOWNLOADS = "never";
              };
              shellHook = ''
                # Undo dependency propagation by nixpkgs.
                unset PYTHONPATH

                # Get repository root using git. This is expanded at runtime by the editable `.pth` machinery.
                export REPO_ROOT=$(git rev-parse --show-toplevel)
              '';
            };
        };
    };

  inputs = {
    # utilities for Flake
    flake-parts.url = "github:hercules-ci/flake-parts";

    ## -- nixpkgs
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nixpkgs.follows = "nixpkgs-unstable";

    ## -- python related

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

  };
}
