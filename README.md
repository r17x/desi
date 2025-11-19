## How I build this project

1. I learn about development tools of www.pyedifice.org in [this flake](https://github.com/pyedifice/pyedifice/blob/master/flake.nix) and follow guides of [uv2nix](https://pyproject-nix.github.io/uv2nix/introduction.html)
2. I start with project development setup in [this ./flake.nix](./flake.nix)


## Prequisites

* [install nix](https://zero-to-nix.com/start/install/)


## Development

1. clone this project
2. go to project directory and run `nix develop` for load project dependencies in `nix-shell` (development environment)


## Run This Application

**Recomended** using nix - see [Prequisites](/#Prequisites)

```bash
nix run github:r17x/desi
```
