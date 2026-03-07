"""
Wollumetric SOP Voxelizer — TouchDesigner Script TOP

Converts any SOP geometry into a coloured 2D atlas texture for the
Wollumetric GLSL renderer.  Each voxel stores RGBA: RGB = surface colour
(from Cd attribute, white if absent), A = occupancy (1.0 = inside).

Supported geometry types:
  - Polygons (3+ vertices) — triangulated, surface-rasterised + flood-filled
  - Lines (2-vertex prims) — rasterised into voxel grid
  - Point clouds (no prims) — each point marks a single voxel

Requirements:
  - numpy  (ships with TouchDesigner)
  - scipy  (install: python -m pip install scipy)

Setup in TouchDesigner:
  1. Create a Text DAT and paste this script into it.
  2. Create a Script TOP.
  3. On the Script TOP's "Script" page, set "Callbacks DAT" to your Text DAT.
  4. Click "Setup Parameters" on the Script TOP.
  5. Set "SOP Path" to the operator path of your scene SOP.
  6. Wire the Script TOP output into the GLSL TOP's second input (index 1).

Metadata is exposed as custom output parameters on the Script TOP so
that downstream operators (e.g. GLSL TOP uniform expressions) get
proper cook-dependency tracking.  Reference them like:
    op('voxelizer').par.Voxelresout
    op('voxelizer').par.Slicesperrowout
    op('voxelizer').par.Atlaswidthout   /  Atlasheightout
    op('voxelizer').par.Meshminxout     /  Meshminyout  /  Meshminzout
    op('voxelizer').par.Meshmaxxout     /  Meshmaxyout  /  Meshmaxzout
"""

import numpy as np
import math
from scipy.ndimage import binary_fill_holes, distance_transform_edt


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

	# ── Output parameters (set during cook, read by GLSL TOP) ─────────
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


# Aliases for older TouchDesigner versions
setupParameters = onSetupParameters


def onCook(scriptOp):
	"""Main cook — voxelise the SOP and output a coloured RGBA atlas."""

	# ── Read parameters ────────────────────────────────────────────────
	res = max(4, int(_par(scriptOp, 'Resolution', 64)))
	sop_path = str(_par(scriptOp, 'Sop', ''))

	if not sop_path:
		return

	sop = op(sop_path) # type: ignore
	if sop is None:
		debug(f"[wollumetric] SOP '{sop_path}' not found") # type: ignore
		return

	if sop.numPrims == 0 and sop.numPoints == 0:
		debug("[wollumetric] SOP has no geometry") # type: ignore
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

	# ── Build triangle + line index arrays ─────────────────────────────
	tri_indices = []
	line_indices = []

	for prim in sop.prims:
		pt_idx = [v.point.index for v in prim]
		n = len(pt_idx)
		if n >= 3:
			for j in range(1, n - 1):
				tri_indices.append((pt_idx[0], pt_idx[j], pt_idx[j + 1]))
		elif n == 2:
			line_indices.append((pt_idx[0], pt_idx[1]))

	# ── Bounding box with padding ──────────────────────────────────────
	mins = positions.min(axis=0)
	maxs = positions.max(axis=0)
	extent = maxs - mins
	pad = extent * 0.02
	min_pad = max(pad.max(), 0.001)
	pad = np.maximum(pad, min_pad)
	mins = mins - pad
	maxs = maxs + pad
	step = (maxs - mins) / res

	# ── Surface voxelisation ───────────────────────────────────────────
	grid = np.zeros((res, res, res, 4), dtype=np.float32)

	if tri_indices:
		tri_idx = np.array(tri_indices, dtype=np.int32)   # (T, 3)
		A_all = positions[tri_idx[:, 0]]   # (T, 3)
		B_all = positions[tri_idx[:, 1]]
		C_all = positions[tri_idx[:, 2]]
		cA_all = colors_arr[tri_idx[:, 0]]
		cB_all = colors_arr[tri_idx[:, 1]]
		cC_all = colors_arr[tri_idx[:, 2]]

		# Edge lengths in voxel units → sample density per triangle
		inv_step = 1.0 / step
		edge_ab = np.linalg.norm((B_all - A_all) * inv_step, axis=1)
		edge_ac = np.linalg.norm((C_all - A_all) * inv_step, axis=1)
		edge_bc = np.linalg.norm((C_all - B_all) * inv_step, axis=1)
		edge_max = np.maximum(edge_ab, np.maximum(edge_ac, edge_bc))

		# Sample count per triangle, capped for performance
		n_samp = np.clip((edge_max * 2.0).astype(np.int32), 3, 80)

		surface = np.zeros((res, res, res), dtype=bool)
		color_grid = np.zeros((res, res, res, 3), dtype=np.float32)

		# Batch triangles by sample count → fully vectorised
		valid_tri = edge_max >= 0.01
		if valid_tri.any():
			A_v = A_all[valid_tri]; B_v = B_all[valid_tri]; C_v = C_all[valid_tri]
			cA_v = cA_all[valid_tri]; cB_v = cB_all[valid_tri]; cC_v = cC_all[valid_tri]
			n_samp_v = n_samp[valid_tri]

			for ns_val in np.unique(n_samp_v):
				ns = int(ns_val)
				u_lin = np.linspace(0, 1, ns)
				UU, VV = np.meshgrid(u_lin, u_lin, indexing='ij')
				bm = (UU + VV) <= 1.0
				u_b = UU[bm].astype(np.float64)
				v_b = VV[bm].astype(np.float64)
				w_b = 1.0 - u_b - v_b
				S = len(u_b)

				grp = n_samp_v == ns_val
				A_g = A_v[grp]; B_g = B_v[grp]; C_g = C_v[grp]
				cA_g = cA_v[grp]; cB_g = cB_v[grp]; cC_g = cC_v[grp]

				# Process in memory-safe chunks (~48 MB per chunk)
				chunk = max(1, 2_000_000 // S)
				for ci in range(0, len(A_g), chunk):
					sl = slice(ci, min(ci + chunk, len(A_g)))
					# (chunk, S, 3) world-space sample positions
					pts = (w_b[None, :, None] * A_g[sl, None, :]
					     + u_b[None, :, None] * B_g[sl, None, :]
					     + v_b[None, :, None] * C_g[sl, None, :])
					vi = np.floor((pts.reshape(-1, 3) - mins) * inv_step).astype(np.int32)
					ok = np.all((vi >= 0) & (vi < res), axis=1)
					vi = vi[ok]
					cols = (w_b[None, :, None] * cA_g[sl, None, :]
					      + u_b[None, :, None] * cB_g[sl, None, :]
					      + v_b[None, :, None] * cC_g[sl, None, :]).reshape(-1, 3)[ok].astype(np.float32)
					surface[vi[:, 0], vi[:, 1], vi[:, 2]] = True
					color_grid[vi[:, 0], vi[:, 1], vi[:, 2]] = cols

		# ── Flood fill to find solid interior ──────────────────────────
		interior = _flood_fill_interior(surface)

		# ── Assemble colour grid ───────────────────────────────────────
		grid[surface, :3] = color_grid[surface]
		grid[surface, 3] = 1.0

		# Propagate surface colours inward so each interior voxel
		# inherits the colour of its nearest surface voxel.
		interior_only = interior & ~surface
		if interior_only.any():
			_propagate_color(surface, color_grid, grid, interior_only)

	# ── Rasterise line primitives (vectorised) ─────────────────────────
	if line_indices:
		inv_step = 1.0 / step
		line_idx = np.array(line_indices, dtype=np.int32)
		p0s = positions[line_idx[:, 0]]
		p1s = positions[line_idx[:, 1]]
		c0s = colors_arr[line_idx[:, 0]]
		c1s = colors_arr[line_idx[:, 1]]
		lengths = np.linalg.norm(p1s - p0s, axis=1)
		max_steps = max(1, int(lengths.max() / step.min() * 2))
		t = np.linspace(0, 1, max_steps + 1)
		# (L, max_steps+1, 3) sample positions + colours
		pts = p0s[:, None, :] + t[None, :, None] * (p1s - p0s)[:, None, :]
		cols = c0s[:, None, :] + t[None, :, None] * (c1s - c0s)[:, None, :]
		vi = np.floor((pts.reshape(-1, 3) - mins) * inv_step).astype(np.int32)
		ok = np.all((vi >= 0) & (vi < res), axis=1)
		vi = vi[ok]
		cols_v = cols.reshape(-1, 3)[ok].astype(np.float32)
		if len(vi) > 0:
			grid[vi[:, 0], vi[:, 1], vi[:, 2], :3] = cols_v
			grid[vi[:, 0], vi[:, 1], vi[:, 2], 3] = 1.0

	# ── Point-cloud fallback ──────────────────────────────────────────
	if grid[:, :, :, 3].max() < 0.5 and n_pts > 0:
		inv_step = 1.0 / step
		vi = np.floor((positions - mins) * inv_step).astype(np.int32)
		valid = np.all((vi >= 0) & (vi < res), axis=1)
		vi = vi[valid]
		cols = colors_arr[valid]
		if len(vi) > 0:
			grid[vi[:, 0], vi[:, 1], vi[:, 2], :3] = cols
			grid[vi[:, 0], vi[:, 1], vi[:, 2], 3] = 1.0

	# ── Pack into 2D RGBA atlas (vectorised) ───────────────────────────
	spr = math.ceil(math.sqrt(res))
	ar = math.ceil(res / spr)
	aw = spr * res
	ah = ar * res

	# Transpose [X,Y,Z,C] → [Y,X,Z,C], pad Z to fill atlas grid,
	# then reshape+transpose to pack slices into 2D tile layout.
	grid_yx = np.ascontiguousarray(grid.transpose(1, 0, 2, 3))
	n_slices = spr * ar
	if n_slices > res:
		grid_yx = np.pad(grid_yx, ((0, 0), (0, 0), (0, n_slices - res), (0, 0)))
	atlas = np.ascontiguousarray(
		grid_yx.reshape(res, res, ar, spr, 4)
		.transpose(2, 0, 3, 1, 4)
	).reshape(ah, aw, 4)

	# ── Write output ───────────────────────────────────────────────────
	scriptOp.copyNumpyArray(atlas)

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

	scriptOp.store('voxelRes', res)
	scriptOp.store('slicesPerRow', spr)
	scriptOp.store('atlasSize', (aw, ah))
	scriptOp.store('meshMin', tuple(mins.tolist()))
	scriptOp.store('meshMax', tuple(maxs.tolist()))

	n_filled = int((grid[:, :, :, 3] > 0.5).sum())
	debug( # type: ignore
		f"[wollumetric] {len(tri_indices)} tris → "
		f"{res}³ grid ({n_filled} filled) → {aw}×{ah} atlas"
	)


# Alias for older TouchDesigner versions
cook = onCook


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _flood_fill_interior(surface):
	"""Return a boolean mask of all voxels inside the closed surface."""
	return binary_fill_holes(surface) | surface


def _propagate_color(surface, color_grid, grid, interior_only):
	"""Assign each interior voxel the colour of its nearest surface voxel."""
	_, nearest = distance_transform_edt(~surface, return_indices=True)
	nn_color = color_grid[nearest[0], nearest[1], nearest[2]]
	grid[interior_only, :3] = nn_color[interior_only]
	grid[interior_only, 3] = 1.0


def _par(scriptOp, name, default):
	"""Safely read a custom parameter value, returning *default* if missing."""
	if hasattr(scriptOp.par, name):
		return getattr(scriptOp.par, name).eval()
	return default


def _set_par(scriptOp, name, value):
	"""Safely set a custom parameter value (no-op if parameter is missing)."""
	if hasattr(scriptOp.par, name):
		getattr(scriptOp.par, name).val = value
