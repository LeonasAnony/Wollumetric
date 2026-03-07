import sys
import matplotlib.pyplot as plt
import numpy as np

print("Wollumetric Point Distribution Visualizer")

# get command line argument for path to .npy file
arg_path = str(sys.argv[1]) if len(sys.argv) > 1 else ""

if arg_path == "":
	print("No path to .npy file provided as command line argument.")
	exit()

# [[angle, x, z], ...]
points = np.load(arg_path)
print(f"Loaded {len(points)} points with shape {np.shape(points)}")

# Get params from file name - e.g. optimized-480-48x30-2.2-166.0_points.npy
file_name = arg_path.split("/")[-1]
size = file_name.split("-")[2]
width, depth = map(int, size.split("x"))
throw_ratio = float(file_name.split("-")[3])
print(f"Extracted parameters from file name: width={width}, depth={depth}, throw_ratio={throw_ratio}")

visualize = str(input("Edit parameters? (y/N) ") or "n")
if visualize.lower() == "y":
	width = int(input(f"Enter the width of the projection ({width}): ") or width)
	depth = int(input(f"Enter the depth of the projection ({depth}): ") or depth)
	throw_ratio = float(input(f"Enter the throw ratio ({throw_ratio}): ") or throw_ratio)

angle_arr = np.array([point[0] for point in points])
x_arr = np.array([point[1] for point in points])
z_arr = np.array([point[2] for point in points])

distance = (throw_ratio * width)	# Abstand zur Projektionsebene

# creating subplot and figure
fig = plt.figure()
ax = fig.add_subplot(111)
scatter, = ax.plot(x_arr, z_arr, ".")
x_max = ((distance + depth) / throw_ratio) / 2
ax.set_xlim([-(x_max+1), x_max+1])

# setting labels
plt.xlabel("Width")
plt.ylabel("Depth")
plt.title(f"Wollumetric - {file_name}")
plt.show()
