### Adds Height info to a wiremap file based on a projetor resolution
### Usage: python createStrings.py path/to/wiremap.npy
### input .npy format: [[angle, x, z], ...]
### output .npy format: [[angle, x, z, height], ...]

import sys
import numpy as np

# get command line argument for path to .npy file
arg_path = str(sys.argv[1]) if len(sys.argv) > 1 else ""

if arg_path == "":
	print("No path to .npy file provided as command line argument.")
	exit()

# [[angle, x, z], ...]
points = np.load(arg_path)

print(f"Loaded {len(points)} points with shape {np.shape(points)}")

# Add height (y) info
width = int(input("Enter the width of the projection (default: 32): ") or 32)
throw_ratio = float(input("Enter the throw ratio (default: 1.6): ") or 1.6)
screen_width = int(input("Enter the screen width in pixels (default: 1920): ") or 1920)
screen_height = int(input("Enter the screen height in pixels (default: 1200): ") or 1200)
max_y = width * (screen_height / screen_width)
distance = width * throw_ratio

# Calculate height (y) = (max_y / distance) * (z + distance)
heights = (max_y / distance) * (points[:, 2] + distance)
heights = heights.round(4)  # Round to 4 decimal places

# Combine with original points: [[angle, x, z, height], ...]
points_with_height = np.hstack((points, heights.reshape(-1, 1)))

# Save new array
save_path = arg_path.replace("_points.npy", "_strings.npy")
np.save(save_path, points_with_height)
print(f"Saved points with height to {save_path}")