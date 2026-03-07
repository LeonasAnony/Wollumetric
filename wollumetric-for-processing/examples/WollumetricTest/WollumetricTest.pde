/*
  Wollumetric Test - Vertical Line Editor
  
  Controls:
    LEFT/RIGHT arrows    - Move selected line horizontally
    UP/DOWN arrows        - Switch selected line for editing
    1, 2, 3, 4           - Set line width (1-4 px)
    r, g, b, w           - Set line color (Red, Green, Blue, White)
    Shift + R, G, B, W   - Scanner mode: 10px segment bouncing vertically
    A                     - Add a new line and select it
*/

// Each entry: [xPos, strokeWeight, r, g, b, mode, yPos, yDir]
// mode: 0 = full line, 1 = scanner (10px segment)
ArrayList<int[]> lines;
int selectedLine = 0;
int moveSpeed = 1;
int scanSpeed = 5;
boolean movingLeft = false;
boolean movingRight = false;

void setup() {
  size(1920, 1200, P2D);
  frameRate(10);
  lines = new ArrayList<int[]>();
  // Start with one white line in the center
  //                    x,         sw, r,   g,   b,   mode, yPos,      yDir
  lines.add(new int[]{ width / 2, 1,  255, 255, 255, 0,    height / 2, 1 });
}

void draw() {
  background(0);

  // Continuous movement while arrow keys are held
  int[] cur = lines.get(selectedLine);
  if (movingLeft)  cur[0] = max(0, cur[0] - moveSpeed);
  if (movingRight) cur[0] = min(width - 1, cur[0] + moveSpeed);

  for (int i = 0; i < lines.size(); i++) {
    int[] l = lines.get(i);
    stroke(l[2], l[3], l[4]);
    strokeWeight(l[1]);
    if (l[5] == 0) {
      // Full vertical line
      line(l[0], 0, l[0], height);
    } else {
      // Scanner: 50px segment bouncing up and down
      line(l[0], l[6], l[0], l[6] + 50);
      l[6] += scanSpeed * l[7];
      if (l[6] + 50 >= height) { l[6] = height - 50; l[7] = -1; }
      if (l[6] <= 0)           { l[6] = 0;          l[7] = 1;  }
    }
  }

  // Draw selection indicator for the active line
  int[] sel = lines.get(selectedLine);
  noStroke();
  fill(sel[2], sel[3], sel[4], 150);
  triangle(sel[0] - 6, 10, sel[0] + 6, 10, sel[0], 20);

  // HUD
  fill(200);
  noStroke();
  textSize(12);
  textAlign(LEFT, TOP);
//  String mode = sel[5] == 0 ? "full" : "scan";
  text("x:" + sel[0]
       + "  w:" + sel[1] + "px"
       + "  color:(" + sel[2] + "," + sel[3] + "," + sel[4] + ")", 8, 8);
}

void keyPressed() {
  int[] sel = lines.get(selectedLine);

  if (keyCode == LEFT) {
    movingLeft = true;
  } else if (keyCode == RIGHT) {
    movingRight = true;
  } else if (keyCode == UP) {
    selectedLine = (selectedLine - 1 + lines.size()) % lines.size();
  } else if (keyCode == DOWN) {
    selectedLine = (selectedLine + 1) % lines.size();
  }

  if (key == '1') sel[1] = 1;
  if (key == '2') sel[1] = 2;
  if (key == '3') sel[1] = 3;
  if (key == '4') sel[1] = 4;

  // Lowercase = set color (full line mode)
  if (key == 'r') { sel[2] = 255; sel[3] = 0;   sel[4] = 0;   sel[5] = 0; }
  if (key == 'g') { sel[2] = 0;   sel[3] = 255; sel[4] = 0;   sel[5] = 0; }
  if (key == 'b') { sel[2] = 0;   sel[3] = 0;   sel[4] = 255; sel[5] = 0; }
  if (key == 'w') { sel[2] = 255; sel[3] = 255; sel[4] = 255; sel[5] = 0; }
  if (key == 'o') { sel[2] = 0;   sel[3] = 0;   sel[4] = 0;   sel[5] = 0; }

  // Shift + color = scanner mode (10px bouncing segment)
  if (key == 'R') { sel[2] = 255; sel[3] = 0;   sel[4] = 0;   sel[5] = 1; }
  if (key == 'G') { sel[2] = 0;   sel[3] = 255; sel[4] = 0;   sel[5] = 1; }
  if (key == 'B') { sel[2] = 0;   sel[3] = 0;   sel[4] = 255; sel[5] = 1; }
  if (key == 'W') { sel[2] = 255; sel[3] = 255; sel[4] = 255; sel[5] = 1; }

  if (key == 'a' || key == 'A') {
    lines.add(new int[]{ width / 2, 1, 255, 255, 255, 0, height / 2, 1 });
    selectedLine = lines.size() - 1;
  }
}

void keyReleased() {
  if (keyCode == LEFT)  movingLeft = false;
  if (keyCode == RIGHT) movingRight = false;
}
