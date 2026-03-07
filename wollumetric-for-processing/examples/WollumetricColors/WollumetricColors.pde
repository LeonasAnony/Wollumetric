/*
  Color spectrum demo for Wollumetric displays.
  Set the size() to match your projector resolution.

  X-axis  -> Hue        (0–360)
  Y-axis  -> Saturation (0–100%)
  Z-axis  -> Brightness (0–100%)
*/

import wollumetric.*;

public Wollumetric thisWollumetric;

void setup() {
  size(1920, 1200, "wollumetric.WGraphics");
  colorMode(HSB, 360, 100, 100);
  thisWollumetric = new Wollumetric("wollumetricConfig.json", this);
}

public void draw() {
  background(0);

  int segments = 100;
  float segmentHeight = thisWollumetric.size.y / segments;

  for (int i = 0; i < thisWollumetric.getLineCount(); i++) {
    Line l = thisWollumetric.getLine(i);

    float hue = map(l.x, 0, thisWollumetric.size.x, 0, 360);
    float bri = map(l.z, 0, thisWollumetric.size.z, 100, 20);

    for (int s = 0; s < segments; s++) {
      float sat = map(s, 0, segments - 1, 1, 100);
      fill(hue, sat, bri);
      l.draw(s * segmentHeight, (s + 1) * segmentHeight);
    }
  }

  translate(thisWollumetric.size.x / 2, thisWollumetric.size.y / 2, thisWollumetric.size.z / 2);
  fill(0, 255, 0);
  box(5);
}
