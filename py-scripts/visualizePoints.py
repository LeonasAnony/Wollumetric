import sys
import matplotlib.pyplot as plt
import numpy as np

# get command line argument for path to .npy file
arg_path = str(sys.argv[1]) if len(sys.argv) > 1 else ""

if arg_path == "":
	print("No path to .npy file provided as command line argument.")
	exit()

# [[angle, x, z], ...]
points = np.load(arg_path)

print(f"Loaded {len(points)} points with shape {np.shape(points)}")
visualize = str(input("Do you want to visualize the points? (Y/n) ") or "y")
if visualize.lower() != "y":
	exit()

depth = int(input("Enter the depth of the projection (default: 20): ") or 20)
width = int(input("Enter the width of the projection (default: 32): ") or 32)
throw_ratio = float(input("Enter the throw ratio (default: 1.6): ") or 1.6)

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
plt.title("Wollumetric Point Distribution")
plt.show()
