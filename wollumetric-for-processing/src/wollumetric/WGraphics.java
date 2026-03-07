package wollumetric;

import java.util.ArrayList;
import java.util.Collections;
import java.util.WeakHashMap;

import processing.core.*;
import processing.opengl.*;

public class WGraphics extends PGraphicsOpenGL {

	public Wollumetric wollumetric;
	public PShader sphereShader;
	public PShader boxShader;
	public PShader meshShader;
	public PImage mapData;

	private int voxelResolution = 64;
	private WeakHashMap<PShape, VoxelData> voxelCache = new WeakHashMap<>();

	/** Cached voxelisation of a PShape. */
	private static class VoxelData {
		PImage atlas;
		float[] bounds; // minX, minY, minZ, maxX, maxY, maxZ
		int resolution;
		int slicesPerRow;
		int atlasRows;
	}

	public WGraphics() {
		super();
	}

	public static void main(String[] args) {
	}

	// ------------------------------------------------------------------ //
	//  Voxel resolution
	// ------------------------------------------------------------------ //

	/**
	* Set the voxel grid resolution used when rendering PShape objects.
	* Higher values give more detail but take longer to compute.
	* Clears the voxel cache so shapes are re-voxelised on next draw.
	*
	* @param  res  grid resolution per axis (default 64)
	*/
	public void setVoxelResolution(int res) {
		this.voxelResolution = Math.max(4, res);
		voxelCache.clear();
	}

	/**
	* Force re-voxelisation of all cached shapes on the next draw call.
	*/
	public void clearVoxelCache() {
		voxelCache.clear();
	}

	// ------------------------------------------------------------------ //
	//  Sphere / Box  (unchanged)
	// ------------------------------------------------------------------ //

	/**
	* Draw a sphere.
	*
	* @param  r		radius
	*/

	@Override
	public void sphere(float r) {
		buildShape(sphereShader, r);
	}

	/**
	* Draw a box.
	*
	* @param  r		radius
	*/

	@Override
	public void box(float r) {
		buildShape(boxShader, r);
	}

	private void buildShape(PShader myShader, float r) {
		// wollumetric geometry
		myShader.set("xyzMax", wollumetric.size);
		myShader.set("screenSize", (float) width, (float) height);
		myShader.set("mapData", mapData);

		// styling and geo
		PStyle s = getStyle();
		colorCalc(s.fillColor);
		myShader.set("fill", calcR, calcG, calcB, calcA);
		//colorCalc(s.strokeColor);
		//myShader.set("shellColor", calcR, calcG, calcB, calcA);
		myShader.set("radius", r);
		//myShader.set("shellWeight", s.strokeWeight);

		// matrix transforms
		PMatrix3D invMatrix = modelviewInv.get();
		invMatrix.apply(camera);
		myShader.set("invMatrix", invMatrix);

		shader(myShader);

		pushMatrix();
		pushStyle();
			noStroke();
			fill(255, 255);
    		applyMatrix(invMatrix);
        	rect(0, 0, width, height);
        	resetShader();
    	popStyle();
    	popMatrix();
	}

	// ------------------------------------------------------------------ //
	//  PShape  (mesh / OBJ support)
	// ------------------------------------------------------------------ //

	/**
	* Draw a PShape (e.g. loaded with loadShape("model.obj")).
	* The shape is voxelised once and the result is cached.
	* Use translate / rotate / scale before calling this to position
	* the shape inside the volume.
	*
	* @param  shape  a PShape containing triangulated geometry
	*/
	@Override
	public void shape(PShape shape) {
		if (shape == null || !shape.isVisible()) return;
		if (meshShader == null) { super.shape(shape); return; }
		renderMeshShape(shape);
	}

	@Override
	public void shape(PShape shape, float x, float y) {
		if (shape == null || !shape.isVisible()) return;
		if (meshShader == null) { super.shape(shape, x, y); return; }
		pushMatrix();
		translate(x, y);
		renderMeshShape(shape);
		popMatrix();
	}

	@Override
	public void shape(PShape shape, float a, float b, float c, float d) {
		if (shape == null || !shape.isVisible()) return;
		if (meshShader == null) { super.shape(shape, a, b, c, d); return; }
		pushMatrix();
		float sw = shape.getWidth();
		float sh = shape.getHeight();
		if (shapeMode == CENTER) {
			translate(a - c / 2, b - d / 2);
			if (sw > 0 && sh > 0) scale(c / sw, d / sh);
		} else if (shapeMode == CORNERS) {
			translate(a, b);
			if (sw > 0 && sh > 0) scale((c - a) / sw, (d - b) / sh);
		} else { // CORNER
			translate(a, b);
			if (sw > 0 && sh > 0) scale(c / sw, d / sh);
		}
		renderMeshShape(shape);
		popMatrix();
	}

	// ------------------------------------------------------------------ //
	//  Internal – render a mesh via the voxel shader
	// ------------------------------------------------------------------ //

	private void renderMeshShape(PShape shape) {
		VoxelData data = getOrCreateVoxelData(shape);
		if (data == null) return; // no geometry found

		PShader myShader = meshShader;

		// wollumetric geometry
		myShader.set("xyzMax", wollumetric.size);
		myShader.set("screenSize", (float) width, (float) height);
		myShader.set("mapData", mapData);

		// styling
		PStyle s = getStyle();
		colorCalc(s.fillColor);
		myShader.set("fill", calcR, calcG, calcB, calcA);

		// voxel-mesh uniforms
		myShader.set("voxelData", data.atlas);
		myShader.set("voxelRes",
				(float) data.resolution,
				(float) data.resolution,
				(float) data.resolution);
		myShader.set("slicesPerRow", (float) data.slicesPerRow);
		myShader.set("atlasSize",
				(float) (data.slicesPerRow * data.resolution),
				(float) (data.atlasRows * data.resolution));
		myShader.set("meshMin",
				data.bounds[0], data.bounds[1], data.bounds[2]);
		myShader.set("meshMax",
				data.bounds[3], data.bounds[4], data.bounds[5]);

		// matrix transforms
		PMatrix3D invMatrix = modelviewInv.get();
		invMatrix.apply(camera);
		myShader.set("invMatrix", invMatrix);

		shader(myShader);

		pushMatrix();
		pushStyle();
			noStroke();
			fill(255, 255);
			applyMatrix(invMatrix);
			rect(0, 0, width, height);
			resetShader();
		popStyle();
		popMatrix();
	}

	// ------------------------------------------------------------------ //
	//  Voxelisation pipeline
	// ------------------------------------------------------------------ //

	private VoxelData getOrCreateVoxelData(PShape shape) {
		VoxelData cached = voxelCache.get(shape);
		if (cached != null) return cached;

		// 1. extract triangles
		ArrayList<float[]> triangles = new ArrayList<>();
		extractTriangles(shape, triangles);
		if (triangles.isEmpty()) return null;

		// 2. bounding box  (with small padding)
		float[] bounds = computeAABB(triangles);
		float padX = (bounds[3] - bounds[0]) * 0.02f;
		float padY = (bounds[4] - bounds[1]) * 0.02f;
		float padZ = (bounds[5] - bounds[2]) * 0.02f;
		// ensure non-zero padding for flat meshes
		float minPad = Math.max(padX, Math.max(padY, padZ));
		if (minPad < 1e-6f) minPad = 1.0f;
		if (padX < 1e-6f) padX = minPad;
		if (padY < 1e-6f) padY = minPad;
		if (padZ < 1e-6f) padZ = minPad;
		bounds[0] -= padX; bounds[1] -= padY; bounds[2] -= padZ;
		bounds[3] += padX; bounds[4] += padY; bounds[5] += padZ;

		// 3. voxelize
		int res = voxelResolution;
		boolean[][][] voxels = voxelize(triangles, bounds, res);

		// 4. pack into 2-D atlas
		int slicesPerRow = (int) Math.ceil(Math.sqrt(res));
		int atlasRows    = (int) Math.ceil((float) res / slicesPerRow);

		VoxelData data = new VoxelData();
		data.atlas = createVoxelAtlas(voxels, res, slicesPerRow, atlasRows);
		data.bounds = bounds;
		data.resolution = res;
		data.slicesPerRow = slicesPerRow;
		data.atlasRows = atlasRows;

		voxelCache.put(shape, data);
		return data;
	}

	// ---- triangle extraction ----------------------------------------- //

	private void extractTriangles(PShape shape, ArrayList<float[]> triangles) {
		int childCount = shape.getChildCount();
		if (childCount > 0) {
			for (int i = 0; i < childCount; i++) {
				extractTriangles(shape.getChild(i), triangles);
			}
			return;
		}

		int vc = shape.getVertexCount();
		if (vc < 3) return;

		int kind = shape.getKind();
		PVector a = new PVector(), b = new PVector(),
		        c = new PVector(), d = new PVector();

		switch (kind) {
			case TRIANGLE_STRIP:
				for (int i = 0; i + 2 < vc; i++) {
					shape.getVertex(i, a);
					shape.getVertex(i + 1, b);
					shape.getVertex(i + 2, c);
					if (i % 2 == 0)
						triangles.add(tri(a, b, c));
					else
						triangles.add(tri(b, a, c));
				}
				break;

			case TRIANGLE_FAN:
				shape.getVertex(0, a);
				for (int i = 1; i + 1 < vc; i++) {
					shape.getVertex(i, b);
					shape.getVertex(i + 1, c);
					triangles.add(tri(a, b, c));
				}
				break;

			case QUADS:
				for (int i = 0; i + 3 < vc; i += 4) {
					shape.getVertex(i, a);
					shape.getVertex(i + 1, b);
					shape.getVertex(i + 2, c);
					shape.getVertex(i + 3, d);
					triangles.add(tri(a, b, c));
					triangles.add(tri(a, c, d));
				}
				break;

			case QUAD_STRIP:
				for (int i = 0; i + 3 < vc; i += 2) {
					shape.getVertex(i, a);
					shape.getVertex(i + 1, b);
					shape.getVertex(i + 2, c);
					shape.getVertex(i + 3, d);
					triangles.add(tri(a, c, b));
					triangles.add(tri(c, d, b));
				}
				break;

			default: // TRIANGLES, POLYGON, or unknown — treat as triangles
				for (int i = 0; i + 2 < vc; i += 3) {
					shape.getVertex(i, a);
					shape.getVertex(i + 1, b);
					shape.getVertex(i + 2, c);
					triangles.add(tri(a, b, c));
				}
				break;
		}
	}

	private static float[] tri(PVector a, PVector b, PVector c) {
		return new float[]{a.x,a.y,a.z, b.x,b.y,b.z, c.x,c.y,c.z};
	}

	// ---- AABB -------------------------------------------------------- //

	private float[] computeAABB(ArrayList<float[]> triangles) {
		float minX = Float.MAX_VALUE, minY = Float.MAX_VALUE, minZ = Float.MAX_VALUE;
		float maxX = -Float.MAX_VALUE, maxY = -Float.MAX_VALUE, maxZ = -Float.MAX_VALUE;
		for (float[] t : triangles) {
			for (int i = 0; i < 9; i += 3) {
				if (t[i]     < minX) minX = t[i];
				if (t[i]     > maxX) maxX = t[i];
				if (t[i + 1] < minY) minY = t[i + 1];
				if (t[i + 1] > maxY) maxY = t[i + 1];
				if (t[i + 2] < minZ) minZ = t[i + 2];
				if (t[i + 2] > maxZ) maxZ = t[i + 2];
			}
		}
		return new float[]{minX, minY, minZ, maxX, maxY, maxZ};
	}

	// ---- scanline voxelisation --------------------------------------- //

	/**
	* Voxelises a triangle soup using scanline (ray along +X) even-odd
	* fill.  Result grid is indexed [x][y][z].
	*/
	private boolean[][][] voxelize(ArrayList<float[]> triangles,
	                               float[] bounds, int res) {
		boolean[][][] grid = new boolean[res][res][res];

		float minX = bounds[0], minY = bounds[1], minZ = bounds[2];
		float maxX = bounds[3], maxY = bounds[4], maxZ = bounds[5];
		float stepX = (maxX - minX) / res;
		float stepY = (maxY - minY) / res;
		float stepZ = (maxZ - minZ) / res;

		ArrayList<Float> hits = new ArrayList<>();

		for (int iy = 0; iy < res; iy++) {
			float rayY = minY + (iy + 0.5f) * stepY;
			for (int iz = 0; iz < res; iz++) {
				float rayZ = minZ + (iz + 0.5f) * stepZ;

				hits.clear();
				for (float[] t : triangles) {
					float hitX = rayTriangleIntersectX(rayY, rayZ, t);
					if (!Float.isNaN(hitX)) hits.add(hitX);
				}
				if (hits.isEmpty()) continue;

				Collections.sort(hits);

				// even-odd fill between pairs
				for (int p = 0; p + 1 < hits.size(); p += 2) {
					float x0 = hits.get(p);
					float x1 = hits.get(p + 1);
					int ix0 = Math.max(0,
							(int) Math.ceil((x0 - minX) / stepX - 0.5f));
					int ix1 = Math.min(res - 1,
							(int) Math.floor((x1 - minX) / stepX - 0.5f));
					for (int ix = ix0; ix <= ix1; ix++) {
						grid[ix][iy][iz] = true;
					}
				}
			}
		}
		return grid;
	}

	/**
	* Intersect a ray (parallel to +X, passing through (*, rayY, rayZ))
	* with a triangle.  Returns the X coordinate of the hit, or NaN.
	*/
	private float rayTriangleIntersectX(float rayY, float rayZ, float[] t) {
		float ax = t[0], ay = t[1], az = t[2];
		float bx = t[3], by = t[4], bz = t[5];
		float cx = t[6], cy = t[7], cz = t[8];

		// edge vectors projected onto YZ
		float v0y = cy - ay, v0z = cz - az;
		float v1y = by - ay, v1z = bz - az;
		float v2y = rayY - ay, v2z = rayZ - az;

		float dot00 = v0y * v0y + v0z * v0z;
		float dot01 = v0y * v1y + v0z * v1z;
		float dot02 = v0y * v2y + v0z * v2z;
		float dot11 = v1y * v1y + v1z * v1z;
		float dot12 = v1y * v2y + v1z * v2z;

		float denom = dot00 * dot11 - dot01 * dot01;
		if (Math.abs(denom) < 1e-10f) return Float.NaN;

		float inv = 1.0f / denom;
		float u = (dot11 * dot02 - dot01 * dot12) * inv;
		float v = (dot00 * dot12 - dot01 * dot02) * inv;

		if (u >= 0 && v >= 0 && u + v <= 1) {
			return ax + u * (cx - ax) + v * (bx - ax);
		}
		return Float.NaN;
	}

	// ---- atlas texture creation -------------------------------------- //

	private PImage createVoxelAtlas(boolean[][][] voxels, int res,
	                                int slicesPerRow, int atlasRows) {
		int atlasW = slicesPerRow * res;
		int atlasH = atlasRows * res;
		PImage atlas = ProcessingObject.pApplet.createImage(atlasW, atlasH, RGB);
		atlas.loadPixels();

		for (int i = 0; i < atlas.pixels.length; i++) {
			atlas.pixels[i] = 0xFF000000; // black
		}

		for (int iz = 0; iz < res; iz++) {
			int col = iz % slicesPerRow;
			int row = iz / slicesPerRow;
			for (int iy = 0; iy < res; iy++) {
				for (int ix = 0; ix < res; ix++) {
					if (voxels[ix][iy][iz]) {
						int px = col * res + ix;
						int py = row * res + iy;
						atlas.pixels[py * atlasW + px] = 0xFFFFFFFF; // white
					}
				}
			}
		}

		atlas.updatePixels();
		return atlas;
	}

}
