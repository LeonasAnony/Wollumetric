# Wollumetric - Python Scripts

Tools for designing string layouts and generating wiremap files.

**Dependencies:** Python 3, NumPy, Matplotlib, SciPy

---

## Workflow

The scripts run in sequence - each step feeds into the next:

```
createPoints.py  →  _points.npy
                        ↓
               createStrings.py  →  _strings.npy
                                        ↓
                                  strings2txt.py  →  _strings.txt
```

### 1. Generate string positions

```bash
python createPoints.py
```

Interactive prompts for number of strings, structure dimensions, throw ratio, and algorithm.
Outputs a `_points.npy` file into `../wiremaps/`.

**Algorithms:** `regular`, `semi`, `x`, `xz`, `prime`, `golden`, `radius`

The `radius` algorithm produces the best results - it uses a KDTree to iteratively swap points that are too close, achieving an even spatial distribution.

### 2. Add projected heights

```bash
python createStrings.py ../wiremaps/<name>_points.npy
```

Computes the projected height of each string based on its depth and the projector frustum.
Outputs `_strings.npy`.

### 3. Convert to text format

```bash
python strings2txt.py ../wiremaps/<name>_strings.npy
```

Converts the NumPy array to a whitespace-delimited text file (`_strings.txt`) - the universal wiremap format consumed by the Processing library, and the browser visualizer.

---

## Analysis & Visualization

```bash
# Scatter plot of a point layout
python visualizePoints.py ../wiremaps/<name>_points.npy

# Viewability analysis - how many strings are visible from each angle (360°)
python analyzeViewability.py ../wiremaps/<name>_points.npy
```

## Map Texture (for TouchDesigner)

```bash
python createMapTexture.py ../wiremaps/<name>_strings.txt
```

Generates a PNG where each pixel encodes the 3D world position of the corresponding projector pixel. Prints the `uVolumeSize` uniform values needed by the GLSL shader.
