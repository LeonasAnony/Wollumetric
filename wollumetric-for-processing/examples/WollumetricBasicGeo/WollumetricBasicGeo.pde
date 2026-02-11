/*
  Basic geometry demo for Lumarca / Wollumetric displays.
  Set the size() to match your projector resolution.
  With 640 strings, 1920 pixels wide gives 3 pixels per string.
*/

import wollumetric.*;

public Wollumetric thisWollumetric;

void setup() {
  size(1920, 1200, "wollumetric.WGraphics");
  thisWollumetric = new Wollumetric("wollumetricConfig.json", this);
}

public void draw() {
  background(0);
  translate(thisWollumetric.size.x / 2, thisWollumetric.size.y / 2, thisWollumetric.size.z / 2);
  fill(255, 0, 0);
  sphere(5);
  translate(10, 0, 0);
  rotateX(float(millis()) / 3000.0 );
  fill(0, 255, 0);
  box(3);
}
