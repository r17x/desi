# Desi - Image Viewer and Effects

A desktop image processing application built with Python, PyEdifice, and PySide6. Apply real-time effects like hue, saturation, brightness, and sharpness to your images with an intuitive interface.

## Features

- **Batch Image Processing**: Load entire directories of images
- **Real-time Preview**: See effects applied instantly with adjustable quality modes
- **Image Effects**: 
  - Hue shift (-180° to +180°)
  - Saturation adjustment (0x to 4x)
  - Brightness/Value adjustment (0x to 4x)
  - Sharpness enhancement (0x to 4x)
- **Navigation**: Browse through multiple images with prev/next controls
- **Toggle View**: Compare original vs. processed images
- **Supported Formats**: PNG, JPG, JPEG, BMP, GIF, TIFF, WebP

## How I Build This Project

1. I learn about development tools of www.pyedifice.org in [this flake](https://github.com/pyedifice/pyedifice/blob/master/flake.nix) and follow guides of [uv2nix](https://pyproject-nix.github.io/uv2nix/introduction.html)
2. I start with project development setup in [this ./flake.nix](./flake.nix)
3. Just make it done - Read [Commits History](./commits/master/)

## Prerequisites

### With Nix (Recommended)

* [install nix](https://zero-to-nix.com/start/install/)

### Without Nix

* Python 3.12 or higher
* pip or [uv](https://docs.astral.sh/uv/) package manager

## Run This Application

### With Nix (Recommended)

```bash
nix run github:r17x/desi
```

### Without Nix

1. Clone the repository:
   ```bash
   git clone https://github.com/r17x/desi.git
   cd desi
   ```

2. Install dependencies:
   
   **Using uv:**
   ```bash
   uv sync
   uv run python src/main.py
   ```
   
   **Using pip:**
   ```bash
   pip install -r requirements.txt
   python src/main.py
   ```
   
   > **Note**: You may need to generate `requirements.txt` from `pyproject.toml`:
   > ```bash
   > pip install build
   > python -m build
   > ```

### With Hot Reload
```console

$ python -m edifice --inspect src/main.py Desi

```
## Development

### With Nix

1. Clone this project
2. Go to project directory and run `nix develop` to load project dependencies in `nix-shell` (development environment)
3. Run the application:
   ```bash
   python src/main.py
   ```

### Without Nix

1. Clone this project
2. Go to project directory
3. Install dependencies (see [Run This Application](#run-this-application) section)
4. Run the application:
   ```bash
   python src/main.py
   ```

## Project Structure

```
desi/
├── src/
│   └── main.py     # Main application with UI components
├── flake.nix       # Nix flake configuration
├── flake.lock      # Nix flake lock file
├── pyproject.toml  # Python project configuration
└── README.md       # This file
```

## Dependencies

- [**pyedifice**](https://pyedifice.github.io/): Declarative UI framework
    - **PySide6**: Qt6 bindings for Python
        - **watchdog**: File system event monitoring (hot reload - development mode)
- **Pillow**: Image processing library

## Usage

1. **Select Source Directory**: Click "Pick Source Dir" to choose a folder containing images
2. **Adjust Effects**: Use sliders to modify hue, saturation, value, and sharpness
3. **Preview Changes**: Toggle "Show Original" to compare before/after
4. **Navigate Images**: Use "Prev" and "Next" buttons to browse through images
5. **Select Output Directory**: Click "Pick Output Dir" to choose where to save processed images
6. **Save**: Click "Save Processed" to export the edited images

## Technical Details

The application uses:
- **Async Processing**: Non-blocking image loading and effect application
- **Debounced Updates**: Smooth slider interaction with 150ms debounce
- **Quality Modes**: Fast (768px), Low (1024px), and HQ (1280px) preview rendering
- **HSV Color Space**: For accurate hue/saturation adjustments
- **Pillow Effects**: ImageEnhance for professional-grade sharpness control
