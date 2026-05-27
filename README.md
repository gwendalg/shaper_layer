
This script processes SVG files exported from tools like Fusion 360 with the Shaper Origin Add-In to generate layered cut files based on depth.

## Visual Overview

### 1. Input SVG
For instance, let's consider the following desgin: ![design](./examples/png/systainer_base_bottom_fusion.png)
The generated SVG ![genrated SVG](./examples/png/systainer_plunge_bottom_bottom.png) contains paths with the `shaper:cutDepth` attribute.

### 2. Processing
Shapes are filtered, attributes cleaned, and paths merged.

### 3. Output SVGs
One file per depth, containing all shapes intended to be cut at or below that level:
- 4mm depth: ![4mm](./examples/png/systainer_plunge_bottom_bottom_0-4cm.png)
- 6mm depth: ![6mm](./examples/png/systainer_plunge_bottom_bottom_0-6cm.png)
- 12mm depth: ![12mm](./examples/png/systainer_plunge_bottom_bottom_1-2cm.png)
- 22mm depth: ![22mm](./examples/png/systainer_plunge_bottom_bottom_2-2cm.png)
- ~1in depth: ![1in](./examples/png/systainer_plunge_bottom_bottom_2-5225cm.png)

## Requirements

- inkscape
- Python 3
- `lxml` library

Install dependencies:
```bash
pip install lxml
```

## Usage

Run the script by passing the path to your source SVG filem it will generate the files in the same directory.

```bash
python3 process_svg.py my_layout.svg
```
