### Convert a wiremap from _strings.npy to .txt format
### Usage: python strings2txt.py path/to/wiremap_strings.npy
### .npy format: [[angle, x, z, height], ...]
### .txt format: angle x z height

import sys
import numpy as np

# get command line argument for path to .npy file
arg_path = str(sys.argv[1]) if len(sys.argv) > 1 else ""

if arg_path == "":
	print("No path to .npy file provided as command line argument.")
	exit()

# [[angle, x, z, height], ...]
points = np.load(arg_path)

print(f"Loaded {len(points)} points with shape {np.shape(points)}")

# convert to .txt format: angle x z height
txt_path = arg_path.replace(".npy", ".txt")
with open(txt_path, "w") as f:
	for point in points:
		f.write(f"{point[0]} {point[1]} {point[2]} {point[3]}\n")

print(f"Saved points to {txt_path}")