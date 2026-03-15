"""
Wollumetric GPU Voxelizer — Triangle Data Extractor
TouchDesigner Script TOP Callback

Extracts triangle vertex data from a SOP and packs it into a small
RGBA32F texture consumed by wollumetric_gpu_voxelizer.glsl.  The GLSL
shader performs scanline even-odd voxelisation on the GPU, producing
an RGBA atlas identical in layout to the CPU voxeliser.

Pipeline:
  [SOP] → [Script TOP: this] → [GLSL TOP: voxelizer] → [GLSL TOP: renderer]

Requirements:
  - numpy  (ships with TouchDesigner)

Setup in TouchDesigner:
  1. Create a Text DAT and paste this script into it.
  2. Create a Script TOP.
  3. On the Script TOP's "Script" page, set "Callbacks DAT" to your Text DAT.
  4. Click "Setup Parameters" on the Script TOP.
  5. Set "SOP Path" to the operator path of your scene SOP.
  6. Wire the Script TOP output into the GLSL voxelizer TOP's input 0.

Output texture format:
  Width  = numTriangles (1 if none)
  Height = 6
  RGBA32F
  Row 0–2: vertex A / B / C positions  (x, y, z, 0)
  Row 3–5: vertex A / B / C colours    (r, g, b, 1)

Metadata is exposed as custom output parameters on the Script TOP so
that downstream GLSL TOPs can reference them in uniform expressions:
    op('tri_data').par.Voxelresout
    op('tri_data').par.Slicesperrowout
    op('tri_data').par.Atlaswidthout   /  Atlasheightout
    op('tri_data').par.Meshminxout     /  Meshminyout  /  Meshminzout
    op('tri_data').par.Meshmaxxout     /  Meshmaxyout  /  Meshmaxzout
    op('tri_data').par.Numtrianglesout
"""

import numpy as np
import math


# ═══════════════════════════════════════════════════════════════════════
#  Script TOP callbacks
# ═══════════════════════════════════════════════════════════════════════

def onSetupParameters(scriptOp):
	"""Create custom parameters when the user clicks Setup Parameters."""
	page = scriptOp.appendCustomPage('Wollumetric')

	p = page.appendStr('Sop', label='SOP Path')[0]
	p.default = ''

	p = page.appendInt('Resolution', label='Voxel Resolution')[0]
	p.default = 64
	p.clampMin = True
	p.min = 4
	p.max = 256

	# ── Output parameters (set during cook, read by GLSL TOPs) ────────
	out = scriptOp.appendCustomPage('Output')

	p = out.appendFloat('Voxelresout', label='Voxel Res')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Slicesperrowout', label='Slices/Row')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Atlaswidthout', label='Atlas Width')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Atlasheightout', label='Atlas Height')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Meshminxout', label='Mesh Min X')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Meshminyout', label='Mesh Min Y')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Meshminzout', label='Mesh Min Z')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Meshmaxxout', label='Mesh Max X')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Meshmaxyout', label='Mesh Max Y')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Meshmaxzout', label='Mesh Max Z')[0]
	p.default = 0
	p.readOnly = True

	p = out.appendFloat('Numtrianglesout', label='Num Triangles')[0]
	p.default = 0
	p.readOnly = True


# Alias for older TouchDesigner versions
setupParameters = onSetupParameters


def onCook(scriptOp):
	"""Main cook — extract triangle data and output as RGBA32F texture."""

	# ── Read parameters ────────────────────────────────────────────────
	res = max(4, int(_par(scriptOp, 'Resolution', 64)))
	sop_path = str(_par(scriptOp, 'Sop', ''))

	# Atlas layout (always valid, even with no triangles)
	spr = math.ceil(math.sqrt(res))
	ar = math.ceil(res / spr)
	aw = spr * res
	ah = ar * res

	if not sop_path:
		_output_empty(scriptOp, res, spr, aw, ah)
		return

	sop = op(sop_path)  # type: ignore
	if sop is None:
		debug(f"[wollumetric] SOP '{sop_path}' not found")  # type: ignore
		_output_empty(scriptOp, res, spr, aw, ah)
		return

	if sop.numPoints == 0:
		debug("[wollumetric] SOP has no geometry")  # type: ignore
		_output_empty(scriptOp, res, spr, aw, ah)
		return

	# ── Bulk-extract point positions + colours ─────────────────────────
	n_pts = sop.numPoints
	has_cd = any(a.name == 'Cd' for a in sop.pointAttribs)

	if has_cd:
		raw = [(pt.P.x, pt.P.y, pt.P.z, pt.Cd[0], pt.Cd[1], pt.Cd[2])
		       for pt in sop.points]
		data = np.array(raw, dtype=np.float64)
		positions = data[:, :3]
		colors_arr = data[:, 3:].astype(np.float32)
	else:
		positions = np.array([(pt.P.x, pt.P.y, pt.P.z)
		                      for pt in sop.points], dtype=np.float64)
		colors_arr = np.ones((n_pts, 3), dtype=np.float32)

	# ── Build triangle index list (fan-triangulate polygons) ───────────
	tri_indices = []
	for prim in sop.prims:
		pt_idx = [v.point.index for v in prim]
		n = len(pt_idx)
		if n >= 3:
			for j in range(1, n - 1):
				tri_indices.append((pt_idx[0], pt_idx[j], pt_idx[j + 1]))

	if not tri_indices:
		debug("[wollumetric] SOP has no polygon primitives")  # type: ignore
		_output_empty(scriptOp, res, spr, aw, ah)
		return

	tri_idx = np.array(tri_indices, dtype=np.int32)
	num_tris = len(tri_idx)

	# ── Bounding box with padding ──────────────────────────────────────
	mins = positions.min(axis=0)
	maxs = positions.max(axis=0)
	extent = maxs - mins
	pad = extent * 0.02
	min_pad = max(pad.max(), 0.001)
	pad = np.maximum(pad, min_pad)
	mins = mins - pad
	maxs = maxs + pad

	# ── Pack triangle data into RGBA32F texture ────────────────────────
	#  Shape: (height=6, width=numTriangles, channels=4)
	#  Row 0: vertex A position  (x, y, z, 0)
	#  Row 1: vertex B position  (x, y, z, 0)
	#  Row 2: vertex C position  (x, y, z, 0)
	#  Row 3: vertex A colour    (r, g, b, 1)
	#  Row 4: vertex B colour    (r, g, b, 1)
	#  Row 5: vertex C colour    (r, g, b, 1)
	tri_tex = np.zeros((6, num_tris, 4), dtype=np.float32)

	tri_tex[0, :, :3] = positions[tri_idx[:, 0]].astype(np.float32)
	tri_tex[1, :, :3] = positions[tri_idx[:, 1]].astype(np.float32)
	tri_tex[2, :, :3] = positions[tri_idx[:, 2]].astype(np.float32)

	tri_tex[3, :, :3] = colors_arr[tri_idx[:, 0]]
	tri_tex[3, :, 3] = 1.0
	tri_tex[4, :, :3] = colors_arr[tri_idx[:, 1]]
	tri_tex[4, :, 3] = 1.0
	tri_tex[5, :, :3] = colors_arr[tri_idx[:, 2]]
	tri_tex[5, :, 3] = 1.0

	scriptOp.copyNumpyArray(tri_tex)

	# ── Set output parameters ──────────────────────────────────────────
	_set_par(scriptOp, 'Voxelresout', float(res))
	_set_par(scriptOp, 'Slicesperrowout', float(spr))
	_set_par(scriptOp, 'Atlaswidthout', float(aw))
	_set_par(scriptOp, 'Atlasheightout', float(ah))
	_set_par(scriptOp, 'Meshminxout', float(mins[0]))
	_set_par(scriptOp, 'Meshminyout', float(mins[1]))
	_set_par(scriptOp, 'Meshminzout', float(mins[2]))
	_set_par(scriptOp, 'Meshmaxxout', float(maxs[0]))
	_set_par(scriptOp, 'Meshmaxyout', float(maxs[1]))
	_set_par(scriptOp, 'Meshmaxzout', float(maxs[2]))
	_set_par(scriptOp, 'Numtrianglesout', float(num_tris))

	debug(  # type: ignore
		f"[wollumetric] {num_tris} triangles → "
		f"GPU voxeliser {res}³ → {aw}×{ah} atlas"
	)


# Alias for older TouchDesigner versions
cook = onCook


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _output_empty(scriptOp, res, spr, aw, ah):
	"""Output a minimal texture and zero-triangle metadata."""
	tri_tex = np.zeros((6, 1, 4), dtype=np.float32)
	scriptOp.copyNumpyArray(tri_tex)
	_set_par(scriptOp, 'Voxelresout', float(res))
	_set_par(scriptOp, 'Slicesperrowout', float(spr))
	_set_par(scriptOp, 'Atlaswidthout', float(aw))
	_set_par(scriptOp, 'Atlasheightout', float(ah))
	_set_par(scriptOp, 'Meshminxout', 0.0)
	_set_par(scriptOp, 'Meshminyout', 0.0)
	_set_par(scriptOp, 'Meshminzout', 0.0)
	_set_par(scriptOp, 'Meshmaxxout', 0.0)
	_set_par(scriptOp, 'Meshmaxyout', 0.0)
	_set_par(scriptOp, 'Meshmaxzout', 0.0)
	_set_par(scriptOp, 'Numtrianglesout', 0.0)


def _par(scriptOp, name, default):
	"""Safely read a custom parameter value, returning *default* if missing."""
	if hasattr(scriptOp.par, name):
		return getattr(scriptOp.par, name).eval()
	return default


def _set_par(scriptOp, name, value):
	"""Safely set a custom parameter value (no-op if parameter is missing)."""
	if hasattr(scriptOp.par, name):
		getattr(scriptOp.par, name).val = value
