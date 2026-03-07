### Generate a Wollumetric map texture from a wiremap _strings.txt file.
### The map texture encodes the 3D world-space position of each projector
### pixel as RGB.
###
### Usage:
### 	python createMapTexture.py path/to/wiremap_strings.txt

import sys
import os
import numpy as np
from PIL import Image

print("Wollumetric Map Texture Generator")

# get command line argument for path to _strings.txt file
arg_path = str(sys.argv[1]) if len(sys.argv) > 1 else ""

if arg_path == "":
	print("No path to _strings.txt file provided as command line argument.")
	exit()

# Read wiremap: each line is "angle x z height"
with open(arg_path, "r") as f:
	wiremap_lines = [line.strip().split() for line in f if line.strip()]

num_strings = len(wiremap_lines)
print(f"Loaded {num_strings} strings from {arg_path}")

# Parse filename for display parameters
# e.g. "radius-480-48x30-2.2-170.0_strings.txt"
file_name = os.path.basename(arg_path)
params_part = file_name.split("_")[0]
params = params_part.split("-")
max_x = float(params[2].split("x")[0])
max_z = float(params[2].split("x")[1])
throw_ratio = float(params[3])
print(f"From filename: maxX={max_x}, maxZ={max_z}, throwRatio={throw_ratio}")

# Screen resolution
screen_width = int(input("Enter screen width in pixels (default: 1920): ") or 1920)
screen_height = int(input("Enter screen height in pixels (default: 1200): ") or 1200)

# Derived geometry (matches Wollumetric.java constructor)
near_depth = throw_ratio * max_x
far_depth = near_depth + max_z
size_x = max_x * far_depth / near_depth   # far-plane X extent
size_y = size_x * (screen_height / screen_width)  # far-plane Y extent
size_z = max_z

print(f"Volume size: x={size_x:.4f}, y={size_y:.4f}, z={size_z:.4f}")

# Pixels per string slice (integer division, matches Java)
px_per_slice = screen_width // num_strings
print(f"Pixels per slice: {px_per_slice}")

# Build map texture (RGB uint8, black = no string)
map_img = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

# Precompute row indices for vectorized inner loop
rows = np.arange(screen_height)

for i, parts in enumerate(wiremap_lines):
	x_raw = float(parts[1])
	z_raw = float(parts[2])
	proj_height = float(parts[3])

	# Volume-space coordinates (matches Wollumetric.java)
	line_x = x_raw + size_x / 2.0
	line_z = z_raw

	# Encode position as color (matches Line.renderMap)
	# Java: (int) PApplet.map(value, 0, max, 0, 255) — truncates to int
	x_color = int(line_x / size_x * 255)
	z_color = int(line_z / size_z * 255)

	# Map each pixel row to world Y
	# row 0 = top of image = top of string (max projected height)
	# row H = bottom of image = base of string (Y = 0)
	y_world = proj_height * (1.0 - rows / screen_height)

	# Only encode pixels where the string is within the display volume
	valid = (y_world >= 0) & (y_world <= size_y)

	# Y encoding: 16-bit intent mapped to green channel
	# Java: yColor = map(y, 0, sizeY, 0, 255*255); yColor1 = floor(yColor/255)
	y_color_full = (y_world / size_y) * 255.0 * 255.0
	y_color = np.floor(y_color_full / 255.0).astype(np.int32)
	y_color = np.clip(y_color, 0, 255).astype(np.uint8)

	# Fill the slice columns for valid rows
	col_start = px_per_slice * i
	col_end = col_start + px_per_slice
	valid_rows = np.where(valid)[0]
	map_img[valid_rows, col_start:col_end, 0] = x_color
	map_img[valid_rows, col_start:col_end, 1] = y_color[valid_rows, np.newaxis]
	map_img[valid_rows, col_start:col_end, 2] = z_color

	if (i + 1) % 100 == 0:
		print(f"\rProcessing string {i + 1}/{num_strings}...", end="", flush=True)

print(f"\rProcessed {num_strings} strings.                ")

# Save PNG
save_path = arg_path.replace("_strings.txt", f"_map_{screen_width}x{screen_height}.png")
img = Image.fromarray(map_img, 'RGB')
img.save(save_path)

print(f"Saved map texture ({screen_width}x{screen_height}) to {save_path}")
print()
print("=== Shader Uniforms ===")
print(f"  uVolumeSize = ({size_x:.4f}, {size_y:.4f}, {size_z:.4f})")
print(f"  Resolution  = {screen_width} x {screen_height}")
print(f"  Strings     = {num_strings}")
print(f"  Px/Slice    = {px_per_slice}")
