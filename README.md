# Wollumetric

A toolkit for building and driving a **wiremap volumetric display** - a physical installation where hundreds of vertical strings are illuminated by a single projector to create true 3D images visible from multiple angles.

<!-- TODO: add hero photo/gif of the display in action -->
![Wollumetric Display](docs/hero.jpg)

---

## How It Works

Two (Plexiglas) plates suspend strings at varying depths inside the volume created by them. A projector shines onto the strings from one side. Because each string sits at a known position on the rays from the projector, it can selectively light individual strings and on them vertical points in space - creating a volumetric display.

<!-- TODO: add diagram showing projector → strings → viewer -->

This project provides everything needed to **design** the string layout using Python scripts, **preview** it in a browser, and **render** 3D content onto the display using either [Processing](https://processing.org/) or [TouchDesigner](https://derivative.ca/).

---

## Inspiration

The initial idea came from [this video](https://www.youtube.com/watch?v=wrfBjRp61iY), which proved too complex to replicate. That led to discovering [Lumarca](https://www.madparker.com/work/art/lumarca) by Matt Parker and Albert Hwang.

The paper ["Projection Volumetric Display using Passive Optical Scatterers"](https://cave.cs.columbia.edu/Statics/publications/pdfs/Nayar_TR06.pdf) (Columbia University) helped in understanding even point distributions and viewability analysis.

The Processing library is adapted from Albert Hwang's [lumarca-for-processing](https://github.com/Albert/lumarca-for-processing), extended with mesh rendering and per-string calibration.

The Python scripts for wiremap generation, the browser visualizer, and the TouchDesigner implementation are original work.

---

## Project Structure

```
Wollumetric/
├── py-scripts/              Python tools for designing string layouts
│   ├── createPoints.py      Generate string positions (multiple algorithms)
│   ├── createStrings.py     Add projected heights to points
│   ├── strings2txt.py       Convert .npy → .txt wiremap format
│   ├── visualizePoints.py   Plot point distributions (matplotlib)
│   ├── analyzeViewability.py  Visibility analysis from all viewing angles
│   └── createMapTexture.py  Generate map texture PNG for TouchDesigner
│
├── visualizer/              Browser-based 3D wiremap preview (Three.js)
│   └── index.html           Drag & drop a _strings.txt to visualize
│
├── wollumetric-for-processing/   Processing library for real-time rendering
│   ├── src/wollumetric/     Library source (Java + GLSL shaders)
│   ├── examples/            Example sketches
│   └── resources/           Build configuration
│
└── touchdesigner/           TouchDesigner voxel rendering pipeline
    ├── wollumetric_voxelizer.py   Script TOP - voxelises SOPs
    ├── wollumetric_render.glsl    GLSL TOP - renders the wiremap image
    └── README.md                  Detailed setup guide
```

---

## Workflow

### 1. Design the String Layout

```bash
mkdir wiremaps
cd py-scripts

# Generate 480 string positions in a 48×30cm structure, throw ratio 2.2
python createPoints.py
# → saves  <name>_points.npy

# Add projected heights
python createStrings.py ../wiremaps/<name>_points.npy
# → saves  <name>_strings.npy

# Convert to text format
python strings2txt.py ../wiremaps/<name>_strings.npy
# → saves  <name>_strings.txt
```

Available layout algorithms: `regular`, `semi`, `x`, `xz`, `prime`, `golden`, `radius`.

The `radius` algorithm uses a KDTree to iteratively even out the spatial distribution.

### 2. Analyze & Preview

```bash
# Scatter plot of point positions
python visualizePoints.py ../wiremaps/<name>_points.npy

# Viewability analysis (how many strings visible from each angle)
python analyzeViewability.py ../wiremaps/<name>_points.npy
```

Open `visualizer/index.html` in a browser and drag in a `_strings.txt` file for an interactive 3D preview.

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
# → saves  <name>_map_1920x1200.png
# → prints uVolumeSize values for the shader
```

A TouchDesigner SOP render Component Wollumetric.tox is in the releases, it can be used for displaying any SOPs as wiremap content.

Alternatively you can manually set up a File In TOP → GLSL TOP ← Script TOP pipeline.
See [wollumetric-for-touchdesigner/README.md](wollumetric-for-touchdesigner/README.md) for that.

---

## Wiremap File Format

Each line in a `_strings.txt` file describes one vertical string:

```
angle  x  z  height
```

| Field | Description |
|-------|-------------|
| `angle` | Horizontal angle from projector center (radians) |
| `x` | World-space X position |
| `z` | World-space Z depth (0 = near/projector side) |
| `height` | Projected height on the string |

---

## Requirements

| Component | Dependencies |
|-----------|-------------|
| py-scripts | Python 3, NumPy, Matplotlib, SciPy (for `radius` algorithm) |
| Processing library | Processing 4.x (Java 17+, OpenGL 3.2+) |
| TouchDesigner pipeline | TouchDesigner, SciPy |
| Visualizer | Any modern browser |

---

## License

This project is licensed under the [GPL-3.0](LICENSE).

The processing library is released under the [GPL-3.0](wollumetric-for-processing/LICENSE) as well, with modifications to Albert Hwang's original work [here](https://github.com/Albert/lumarca-for-processing).

The Processing library build template is based on work by Elie Zananiri and Andreas Schlegel.
