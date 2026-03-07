### Wollumetric Viewability Analyzer
### 
### Analyzes the visibility of points from different viewing angles on a 2D plane.
### For each viewing angle (-180° to 180°), counts how many points are visible
### (not fully occluded by other points in front of them).
### 
### Usage:
### 	python analyzeViewability.py ../wiremaps/file1_points.npy ../wiremaps/file2_points.npy ...

import sys
import numpy as np
import matplotlib.pyplot as plt

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
		  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]


def add_interval(intervals: list, new_start: float, new_end: float) -> list:
	"""
	Insert a new interval into a sorted, non-overlapping interval list and merge.
	Returns the updated merged list.
	"""
	result = []
	i = 0
	n = len(intervals)

	# Copy intervals entirely before the new one
	while i < n and intervals[i][1] < new_start:
		result.append(intervals[i])
		i += 1

	# Merge all overlapping intervals with the new one
	merge_start = new_start
	merge_end = new_end
	while i < n and intervals[i][0] <= new_end:
		merge_start = min(merge_start, intervals[i][0])
		merge_end = max(merge_end, intervals[i][1])
		i += 1
	result.append((merge_start, merge_end))

	# Copy remaining intervals after the merged region
	while i < n:
		result.append(intervals[i])
		i += 1

	return result


def is_fully_covered(start: float, end: float, intervals: list) -> bool:
	"""
	Check if the range [start, end] is fully covered by the union of
	sorted, non-overlapping intervals.
	"""
	current = start
	for iv_start, iv_end in intervals:
		if iv_start > current:
			return False  # gap before this interval
		if iv_end >= end:
			return True
		if iv_end > current:
			current = iv_end
	return current >= end


def compute_visibility(points_x: np.ndarray, points_z: np.ndarray,
					   viewer_angle_deg: float, viewer_distance: float,
					   point_diameter: float) -> int:
	"""
	Compute the number of visible points from a given viewing angle.

	The viewer is placed at `viewer_distance` from the center of the point cloud,
	looking inward. A point is considered visible if any part of it is not fully
	occluded by closer points.

	Args:
		points_x:         x coordinates of all points
		points_z:         z coordinates of all points
		viewer_angle_deg: viewing angle in degrees (0° = front, looking in +z)
		viewer_distance:  distance from center of point cloud to viewer
		point_diameter:   diameter of each point (same units as coordinates)

	Returns:
		Count of visible points
	"""
	theta = np.radians(viewer_angle_deg)
	sin_t = np.sin(theta)
	cos_t = np.cos(theta)

	# Center of the point cloud bounding box
	cx = (np.min(points_x) + np.max(points_x)) / 2.0
	cz = (np.min(points_z) + np.max(points_z)) / 2.0

	# Viewer position (rotates around the center)
	# At 0°: viewer is at (cx, cz - distance), looking in +z direction
	vx = cx + viewer_distance * sin_t
	vz = cz - viewer_distance * cos_t

	# Vectors from viewer to each point
	dx = points_x - vx
	dz = points_z - vz

	# Viewing direction (from viewer toward center): (-sin(θ), cos(θ))
	# Perpendicular (screen axis): (cos(θ), sin(θ))
	depths = dx * (-sin_t) + dz * cos_t       # distance along viewing direction
	screen_pos = dx * cos_t + dz * sin_t       # position on the screen axis

	# Only consider points in front of the viewer
	valid_mask = depths > 0
	if not np.any(valid_mask):
		return 0

	valid_depths = depths[valid_mask]
	valid_screen = screen_pos[valid_mask]

	# Sort by depth (front to back)
	order = np.argsort(valid_depths)

	visible_count = 0
	blocked_intervals = []  # sorted, non-overlapping angular intervals

	for i in order:
		d = valid_depths[i]
		s = valid_screen[i]

		# Angular extent of this point as seen from the viewer
		ang_center = np.arctan2(s, d)
		ang_half = np.arctan(point_diameter / (2.0 * d))
		p_start = ang_center - ang_half
		p_end = ang_center + ang_half

		# A point is visible if its angular range is NOT fully covered
		if not is_fully_covered(p_start, p_end, blocked_intervals):
			visible_count += 1

		# Every point (visible or not) blocks the view behind it
		blocked_intervals = add_interval(blocked_intervals, p_start, p_end)

	return visible_count


def main():
	print("Wollumetric Viewability Analyzer")

	# get command line arguments for paths to .npy files
	arg_paths = sys.argv[1:] if len(sys.argv) > 1 else []

	if len(arg_paths) == 0:
		print("No path to .npy file(s) provided as command line argument.")
		exit()

	print(f"Files to analyze: {len(arg_paths)}")
	for p in arg_paths:
		print(f"  - {p.split('/')[-1]}")

	# ---- Shared parameters ---- #
	# Try to extract defaults from the first file
	first_file = arg_paths[0].split("/")[-1]
	try:
		parts = first_file.split("_")[0].split("-")
		size = parts[2]
		width, depth = map(int, size.split("x"))
		throw_ratio = float(parts[3])
		auto_distance = round(throw_ratio * width + depth / 2, 1)
		print(f"\nFrom filename: width={width}, depth={depth}, "
			  f"throw_ratio={throw_ratio}, distance={auto_distance}")
	except (IndexError, ValueError):
		auto_distance = 100.0
		print("\nCould not parse filename — using default distance=100.0")

	viewer_distance = float(input(f"Enter viewing distance ({auto_distance}): ") or auto_distance)
	point_diameter = float(input("Enter point diameter (0.1): ") or 0.1)
	resolution = float(input("Enter angular resolution in degrees (1.0): ") or 1.0)
	plot_mode = str(input("Enter Plot mode ([polar], line): ") or "polar").strip().lower()
	avg_window = int(input("Enter averaging window in samples (1 = off): ") or 1)

	# ---- Compute angles ---- #
	angles = np.arange(-180, 180, resolution)
	angles = angles[angles <= 180.0]
	total = len(angles)

	# ---- Process each file ---- #
	results = []  # list of (file_name, num_points, visible_counts)

	for file_idx, arg_path in enumerate(arg_paths):
		points = np.load(arg_path)
		file_name = arg_path.split("/")[-1]
		print(f"\n[{file_idx + 1}/{len(arg_paths)}] {file_name}")
		print(f"  Loaded {len(points)} points  (shape {points.shape})")

		points_x = points[:, 1]
		points_z = points[:, 2]

		visible_counts = np.zeros(total, dtype=int)

		print(f"  Computing visibility for {total} angles...")
		for i, angle in enumerate(angles):
			visible_counts[i] = compute_visibility(
				points_x, points_z, angle, viewer_distance, point_diameter
			)
			if (i + 1) % max(1, total // 20) == 0 or i == total - 1:
				print(f"\r  Progress: {i + 1}/{total}  "
					  f"({100 * (i + 1) / total:.0f}%)", end="", flush=True)

		results.append((file_name, len(points), visible_counts))

	# ---- Apply averaging ---- #
	if avg_window > 1:
		for i, (file_name, num_points, visible_counts) in enumerate(results):
			# Circular moving average: pad by wrapping around
			padded = np.concatenate([visible_counts[-(avg_window // 2):],
									 visible_counts,
									 visible_counts[:avg_window // 2]])
			kernel = np.ones(avg_window) / avg_window
			smoothed = np.convolve(padded, kernel, mode="valid")
			# Trim to original length in case of even window
			smoothed = smoothed[:len(visible_counts)]
			results[i] = (file_name, num_points, smoothed)

	print(f"\n\nResults:")
	for r in results:
		print(f" - {r[0]}: {r[1]} points, {np.max(r[2]):.1f} max visible, {np.min(r[2]):.1f} min visible, {np.mean(r[2]):.1f} avg visible")

	# ---- Plot ---- #
	points = max(r[1] for r in results)
	min_points = min(r[2].min() for r in results)
	max_points = max(r[2].max() for r in results)

	if plot_mode == "polar":
		fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
		angles_rad = np.radians(angles)

		for idx, (file_name, num_points, visible_counts) in enumerate(results):
			color = COLORS[idx % len(COLORS)]
			angles_rad_closed = np.append(angles_rad, angles_rad[0])
			visible_closed = np.append(visible_counts, visible_counts[0])

			label = file_name.replace("_points.npy", "")
			ax.plot(angles_rad_closed, visible_closed, linewidth=1.2, color=color, label=label)
			ax.fill(angles_rad_closed, visible_closed, alpha=0.08, color=color)

		# Reference circle for max point count
		ref_angles = np.linspace(0, 2 * np.pi, 360)
		ax.plot(ref_angles, np.full_like(ref_angles, points),
				color="red", linestyle="--", alpha=0.5, label=f"Total ({points})")

		ax.set_rorigin(min_points * 0.95)
		ax.set_rmin(min_points * 0.95)
		ax.set_rmax(max_points * 1.05)
		ax.set_theta_zero_location("S")  # 0° at bottom (front view)
		ax.set_theta_direction(-1)        # clockwise
		ax.set_rlabel_position(45)
		ax.set_title(
			f"Wollumetric Viewability\n"
			f"Distance: {viewer_distance},  Point Ø: {point_diameter}",
			pad=20
		)
		ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)

	else:  # line graph
		fig, ax = plt.subplots(figsize=(12, 6))

		for idx, (file_name, num_points, visible_counts) in enumerate(results):
			color = COLORS[idx % len(COLORS)]
			label = file_name.replace("_points.npy", "")
			ax.plot(angles, visible_counts, linewidth=1.2, color=color, label=label)

		ax.axhline(y=points, color="red", linestyle="--", alpha=0.5,
				   label=f"Total ({points})")

		ax.set_xlabel("Viewing Angle (°)")
		ax.set_ylabel("Visible Points")
		ax.set_title(
			f"Wollumetric Viewability\n"
			f"Distance: {viewer_distance},  Point Ø: {point_diameter}"
		)
		ax.set_xlim(-180, 180)
		ax.set_xticks(np.arange(-180, 181, 30))
		ax.set_ylim(min_points * 0.95, max_points * 1.05)
		ax.grid(True, alpha=0.3)
		ax.legend(fontsize=8)

	plt.tight_layout()
	plt.show()


if __name__ == "__main__":
	main()
