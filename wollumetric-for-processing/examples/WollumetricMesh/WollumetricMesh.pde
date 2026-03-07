/*
  Mesh / OBJ shape demo for Wollumetric displays.
  Place an .obj file (e.g. "model.obj") in the data/ folder.
  Set the size() to match your projector resolution.

  The PShape is voxelised once on first draw and cached.
  Use translate / rotate / scale to position and orient the
  shape inside the volume, just like sphere() or box().

  Call thisWollumetric.getGfx().setVoxelResolution(n) to
  change the voxel grid resolution (default 64).
  Call thisWollumetric.getGfx().clearVoxelCache() to force
  re-voxelisation after modifying a shape at runtime.
*/

import wollumetric.*;

public Wollumetric thisWollumetric;
PShape model;

void setup() {
  size(1920, 1200, "wollumetric.WGraphics");
  thisWollumetric = new Wollumetric("wollumetricConfig.json", this);

  // Load any .obj file placed in the data/ folder
  model = loadShape("wirecube.obj");

  // Optional: increase voxel resolution for finer detail
//  thisWollumetric.getGfx().setVoxelResolution(128);
}

public void draw() {
  background(0);

  // Centre of the volume
  translate(thisWollumetric.size.x / 2,
            thisWollumetric.size.y / 2,
            thisWollumetric.size.z / 2);

  // You can still mix in built-in primitives
  translate(10, 0, 0);
  fill(255, 0, 0);
  sphere(4);

  translate(-15, 0, 0);

  // Slowly rotate so you can see all sides
  rotateY(float(millis()) / 4000.0);

  // Draw the loaded mesh
  fill(0, 200, 255);
  scale(4);
  shape(model);
}
