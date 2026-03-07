/*
  Wollumetric Calibration Tool

  Displays all strings from the wiremap file as vertical colored lines.
  Adjust width and offset per line, then save calibration.

  Controls:
    UP / DOWN      - Select previous / next line
    LEFT / RIGHT   - Shift selected line position by 1 px (hold-able)
    + / =          - Increase line width
    - / _          - Decrease line width
    S              - Save calibration file
*/

int numLines;
int pxPerSlice;
int defaultWidth;
int selectedLine = 0;

int[] lineWidths;
int[] lineOffsets;
float[] lineDepths;
float minDepth, maxDepth;

String configFile = "wollumetricConfig.json";
String wiremapFile;
String calibFileName;

boolean shiftPressed = false;
int movingSelection = 0; // 0 = none, -1 = left, 1 = right
boolean highlightLine = false;


void setup() {
  size(1920, 1200, P2D);
  colorMode(HSB, 360, 100, 100);

  // Read config
  JSONObject config = loadJSONObject(dataPath(configFile));
  wiremapFile = config.getString("wiremapFile");

  // Derive calibration file name
  if (wiremapFile.endsWith("_strings.txt")) {
    calibFileName = wiremapFile.substring(0, wiremapFile.length() - "_strings.txt".length()) + "_calib.txt";
  } else {
    calibFileName = wiremapFile + "_calib.txt";
  }

  // Load wiremap to count lines and read depths
  String[] rawLines = loadStrings(dataPath(wiremapFile));
  numLines = 0;
  for (String s : rawLines) {
    if (s.trim().length() > 0) numLines++;
  }

  pxPerSlice  = width / numLines;
  defaultWidth = pxPerSlice;

  lineWidths  = new int[numLines];
  lineOffsets = new int[numLines];
  lineDepths  = new float[numLines];

  int idx = 0;
  minDepth = Float.MAX_VALUE;
  maxDepth = Float.MIN_VALUE;
  for (String s : rawLines) {
    if (s.trim().length() == 0) continue;
    String[] parts = s.trim().split("\\s+");
    float z = Float.parseFloat(parts[2]);
    lineDepths[idx] = z;
    if (z < minDepth) minDepth = z;
    if (z > maxDepth) maxDepth = z;
    idx++;
  }

  for (int i = 0; i < numLines; i++) {
    lineWidths[i]  = defaultWidth;
    lineOffsets[i] = 0;
  }

  // Load existing calibration if present
  loadCalibration();
}

void draw() {
  background(0);

  // Handle continuous selection movement
  if (movingSelection != 0) {
    selectedLine = (selectedLine + movingSelection + numLines) % numLines;
  }

  // Draw all lines
  for (int i = 0; i < numLines; i++) {
    float hue = map(lineDepths[i], minDepth, maxDepth, 180, 360);
    if (i == selectedLine) {
      fill(hue, 100, 100);
    } else if (highlightLine) {
      fill(hue, 0, 0);
    } else {
      fill(hue, 100, 60);
    }
    noStroke();
    int slotX = pxPerSlice * i;
    rect(slotX + lineOffsets[i], 0, lineWidths[i], height);
  }

  // Selection indicator triangle
  int selX = pxPerSlice * selectedLine + lineOffsets[selectedLine];
  int selCx = selX + lineWidths[selectedLine] / 2;
  fill(0, 0, 100);
  noStroke();
  triangle(selCx - 6, 10, selCx + 6, 10, selCx, 22);

  // HUD
  int maxOff = pxPerSlice - lineWidths[selectedLine];
  textSize(14);
  textAlign(LEFT, TOP);
  text("Line " + (selectedLine + 1) + "/" + numLines
    + "  width:" + lineWidths[selectedLine] + "/" + defaultWidth + "px"
    + "  offset:" + lineOffsets[selectedLine] + "/" + maxOff + "px"
    + "  |  [s]ave [h]ighlight [+/-]width  [\u2190\u2192]offset  [(shift)+\u2191\u2193]select", 10, 30);
  text(wiremapFile, 10, 50);
}

void keyPressed() {
  if (keyCode == SHIFT) {
    shiftPressed = true;
  }

  if (keyCode == UP) {
    if (shiftPressed) {
      movingSelection = -1;
    } else {
      selectedLine = (selectedLine - 1 + numLines) % numLines;
    }
  } else if (keyCode == DOWN) {
    if (shiftPressed) {
      movingSelection = 1;
    } else {
      selectedLine = (selectedLine + 1) % numLines;
    }
  } else if (keyCode == LEFT) {
    lineOffsets[selectedLine] = max(0, lineOffsets[selectedLine] - 1);
  } else if (keyCode == RIGHT) {
    int maxOff = pxPerSlice - lineWidths[selectedLine];
    lineOffsets[selectedLine] = min(maxOff, lineOffsets[selectedLine] + 1);
  }

  if (key == '+') {
    lineWidths[selectedLine] = min(defaultWidth, lineWidths[selectedLine] + 1);
    // Clamp offset so line stays in its slot
    int maxOff = pxPerSlice - lineWidths[selectedLine];
    lineOffsets[selectedLine] = min(lineOffsets[selectedLine], maxOff);
  }
  if (key == '-') {
    lineWidths[selectedLine] = max(1, lineWidths[selectedLine] - 1);
  }

  if (key == 's') {
    saveCalibration();
  }

  if (key == 'h') {
    if (highlightLine) {
      highlightLine = false;
    } else {
      highlightLine = true;
    }
  }
}

void keyReleased() {
  if (keyCode == UP || keyCode == DOWN) {
    movingSelection = 0;
  }
  if (keyCode == SHIFT) {
    shiftPressed = false;
  }
}

void saveCalibration() {
  String[] out = new String[numLines];
  for (int i = 0; i < numLines; i++) {
    out[i] = lineWidths[i] + " " + lineOffsets[i];
  }
  saveStrings(dataPath(calibFileName), out);
  println("Calibration saved to data/" + calibFileName);
}

void loadCalibration() {
  File f = new File(dataPath(calibFileName));
  if (f.exists()) {
    String[] cal = loadStrings(dataPath(calibFileName));
    for (int i = 0; i < min(cal.length, numLines); i++) {
      String[] parts = cal[i].trim().split("\\s+");
      if (parts.length >= 2) {
        lineWidths[i]  = Integer.parseInt(parts[0]);
        lineOffsets[i] = Integer.parseInt(parts[1]);
      }
    }
    println("Loaded calibration from data/" + calibFileName);
  }
}
