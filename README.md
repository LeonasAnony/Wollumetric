# Wollumetric

A toolkit for building and driving a **volumetric display** - a physical installation where hundreds of vertical strings are illuminated by a single projector to create true 3D images.

<!-- TODO: add hero photo/gif of the display in action -->

---

## How It Works

Two (Plexiglas) plates suspend vertical strings at varying depths between them. A projector shines onto the strings from one side. Because each string sits at a known position on the rays from the projector, it can selectively light individual strings and on them vertical points in space - creating a volumetric display.

<!-- TODO: add diagram showing projector → strings → viewer -->

This project provides everything needed to **generate** the string layout using Python scripts, **preview** it in a browser, **construct** the physical display using Fusion 360, and **render** 3D content onto the display using either [Processing](https://processing.org/) or [TouchDesigner](https://derivative.ca/).

---

## Inspiration

The initial idea came from [this video](https://www.youtube.com/watch?v=wrfBjRp61iY), which proved too complex to replicate. That led to discovering [Lumarca](https://www.madparker.com/work/art/lumarca) by Matt Parker and Albert Hwang.

The paper ["Projection Volumetric Display using Passive Optical Scatterers"](https://cave.cs.columbia.edu/Statics/publications/pdfs/Nayar_TR06.pdf) (Columbia University) helped in understanding even point distributions and viewability analysis.

The Processing library is adapted from Albert Hwang's [lumarca-for-processing](https://github.com/Albert/lumarca-for-processing), extended with mesh rendering and per-string calibration.

The Python scripts for wiremap generation, the browser visualizer, the Fusion 360 Addin, and the TouchDesigner implementation are original work.

---

## Project Structure

```
Wollumetric/
├── py-scripts/                   Python tools for designing string layouts
│   ├── createPoints.py           Generate string positions (multiple algorithms)
│   ├── createStrings.py          Add projected heights to points
│   ├── strings2txt.py            Convert .npy to .txt wiremap format
│   ├── visualizePoints.py        Plot point distributions (matplotlib)
│   ├── analyzeViewability.py     Visibility analysis from all viewing angles
│   └── createMapTexture.py       Generate map texture PNG for TouchDesigner
│
├── visualizer/                   Browser-based 3D wiremap preview (Three.js)
│   └── index.html                Drag & drop a _strings.txt to visualize
│
├── wollumetric-for-processing/   Processing library for real-time rendering
│   ├── src/wollumetric/          Library source (Java + GLSL shaders)
│   ├── examples/                 Example sketches
│   └── resources/                Build configuration
│
├── touchdesigner/                TouchDesigner voxel rendering pipeline
│   ├── wollumetric_voxelizer.py  Script TOP - voxelises SOPs
│   ├── wollumetric_render.glsl   GLSL TOP - renders the wiremap image
│   └── README.md                 Detailed setup guide
│
└── AddIns/Wollumetric/           Fusion 360 AddIn for manufacturing
    └── commands/
        ├── loadPoints/           Import _points.npy into a sketch
        ├── createAxes/           Construction axes at each point
        └── createCircles/        Hole footprints at each point
```

---

## Workflow

### 1. Design the String Layout

```bash
mkdir wiremaps
cd py-scripts

# Generate 480 string positions in a 48×30cm structure, throw ratio 2.2
python createPoints.py
# > outputs <name>_points.npy

# Add projected heights
python createStrings.py ../wiremaps/<name>_points.npy
# > outputs <name>_strings.npy

# Convert to text format
python strings2txt.py ../wiremaps/<name>_strings.npy
# > outputs <name>_strings.txt
```

Available layout algorithms: `regular`, `semi`, `x`, `xz`, `prime`, `golden`, `radius`.

The `radius` algorithm uses a KDTree to iteratively even out the spatial distribution.

### 2. Analyze & Preview

```bash
# Scatter plot of point positions
python visualizePoints.py ../wiremaps/<name>_points.npy

# Viewability analysis (how many strings visible from each angle)
python analyzeViewability.py ../wiremaps/<name>_points.npy

# Browser-based 3D preview (drag & drop the _strings.txt)
python -m http.server 8000 -d visualizer
# > open http://localhost:8000 in a browser
```

<!-- TODO: add screenshot of the visualizer -->

### 3. Render Content

#### Option A: Processing

Place the `_strings.txt` and a `wollumetricConfig.json` in your sketch's `data/` folder:

```json
{
  "wiremapFile": "radius-480-48x30-2.2-170.0_strings.txt",
  "version": "2.0.0"
}
```

Then switch the renderer:

```java
import wollumetric.*;

Wollumetric w;

void setup() {
  size(1920, 1200, Wollumetric.RENDERER);
  w = new Wollumetric("wollumetricConfig.json", this);
}
```

See [wollumetric-for-processing/README.md](wollumetric-for-processing/README.md) for the complete setup guide and example sketches.

#### Option B: TouchDesigner

```bash
# Generate the map texture for your projector resolution
python py-scripts/createMapTexture.py wiremaps/<name>_strings.txt
# > outputs <name>_map_1920x1200.png
# > prints uVolumeSize values for the shader
```

A TouchDesigner SOP render Component `Wollumetric.tox` is in the releases, it can be used for displaying any SOPs as wiremap content. In the Components `Wolllumetric` Parameter Tab, set the output `Resolution`, the `mapTexture` to the generated map PNG, and paste the printed `uVolumeSize` values. The Parameter `Voxel Resolution` controls the density of the voxelisation, and thus the rendering quality.

Alternatively you can manually set up the render network.

See [wollumetric-for-touchdesigner/README.md](wollumetric-for-touchdesigner/README.md) for more details and manual setup instructions.

### 4. Manufacturing (Fusion 360)

The Fusion 360 AddIn in `AddIns/Wollumetric/` helps with manufacturing the display structure. It bridges from the `_points.npy` file to a CAD Fusion sketch.

1. **Load Points** — imports a `_points.npy` file as sketch points on the active sketch.
2. **Create Axes** — generates construction axis perpendicular to the surface at each point (to translate the points to an angled surface).
3. **Create Circles** — creates circles of a specified diameter at each point.

Install by copying the `AddIns/Wollumetric` folder into your Fusion 360 AddIns directory.

---

## Wiremap File Format

Each line in a `_strings.txt` file describes one vertical string:

```
angle  x  z  height
```

| Field | Description |
|-------|-------------|
| `angle` | Horizontal angle from projector center (radians) |
| `x` | World-space X position (<0 = left, >0 = right) |
| `z` | World-space Z depth (0 = near/projector side) |
| `height` | Projected height on the string |

---

## Requirements

| Component | Dependencies |
|-----------|-------------|
| py-scripts | Python 3, NumPy, Matplotlib, SciPy |
| Processing library | Processing 4.x (Java 17+, OpenGL 3.2+) |
| TouchDesigner pipeline | TouchDesigner, SciPy |
| Fusion 360 AddIn | Fusion 360, NumPy |
| Visualizer | Python 3, Browser |

---

## License

This project is licensed under the [GPL-3.0](LICENSE).

The processing library is released under the [GPL-3.0](wollumetric-for-processing/LICENSE) as well, with modifications to Albert Hwang's original work [here](https://github.com/Albert/lumarca-for-processing).

The Processing library build template is based on work by Elie Zananiri and Andreas Schlegel.
