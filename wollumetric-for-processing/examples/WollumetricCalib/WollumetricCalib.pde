/*
  Calibration routine for Lumarca / Wollumetric displays.
  Set the size() to match your projector resolution.

  Strings closest to the projector are Red.
  Strings furthest from the projector are Blue.
  Strings in between are Green.
*/

import wollumetric.*;

public Wollumetric thisWollumetric;

 void setup() {
  size(1920, 1200, "wollumetric.WGraphics");
  thisWollumetric = new Wollumetric("wollumetricConfig.json", this);
}

public void draw() {
  background(0);

  for (int i = 0; i < thisWollumetric.getLineCount(); i++) {
    Line l = thisWollumetric.getLine(i);
    if (l.z < thisWollumetric.size.z * .33333) {
      fill(255, 0, 0);
    } else if (l.z < thisWollumetric.size.z * .6666) {
      fill(0, 255, 0);
    } else {
      fill(0, 0, 255);
    }
    l.draw(0, thisWollumetric.size.y);
  }
}
