import matplotlib.pyplot as plt
import math
import numpy as np
from scipy.spatial import KDTree

SAVE_PATH = "../wiremaps/"


# ---- Helper Functions ---- #
def create_quasirandom_permutation(n: int) -> np.ndarray:
	"""
	Creates a quasi-random permutation using the golden ratio.
	The resulting permutation maps sequential angle indices to well-separated
	depth ranks, producing a 2D distribution with no alignment artifacts.
	This is based on the same principle as phyllotaxis / sunflower spirals.
	"""
	phi = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.618
	v = np.mod(np.arange(n) * phi, 1.0)
	return np.argsort(v)


def optimize_z_sequence_radius(array: np.ndarray, points: int, distance: int, x_angels: np.ndarray, target_radius: float = 90, start_radius: float = 80, max_iterations: int = 100000):
	"""
	Optimiert die Reihenfolge der z-Werte durch Radius-basierte Suche.
	Tauscht Punkte die näher als min_radius zueinander sind, bis keine
	Verletzungen mehr existieren.
	"""
	best_sequence = array.copy()

	rand_violations = np.random.randint(points, size=max_iterations)
	rand_swap = np.random.randint(points, size=max_iterations)
	rand_choose = np.random.randint(2, size=max_iterations)

	radius = start_radius
	
	last_violations = []
	swap_point = 0
	swap_with = 0
	stagnation_limit = 10
	last_violations_counts = []
	valid_violations = 0
	skip = True
	for iteration in range(max_iterations):
		# KDTree mit aktuellen Punkten bauen
		x_positions = np.tan(x_angels) * (distance + best_sequence)
		points_2d = np.column_stack([x_positions, best_sequence])
		tree = KDTree(points_2d)
		violations = tree.query_pairs(r=radius/100)

		# Wenn keine Verletzungen: fertig!
		if len(violations) == 0:
			if radius >= target_radius:
				break
			radius = round(radius + 0.01, 2)
			valid_violations = 0
			last_violations_counts.clear()
			if stagnation_limit > 15:
				stagnation_limit -= 10
			elif stagnation_limit > 10:
				stagnation_limit -= 5
			skip = True
			continue

		if len(violations) <= (max(len(last_violations), valid_violations)) or skip:
			if len(violations) < len(last_violations) and stagnation_limit > 10:
				stagnation_limit -= 5
				last_violations_counts.clear()
			last_violations = violations
			skip = False
		else:
			if (iteration - 1) % 4 == 0:
				if swap_point < swap_with:
					best_sequence = np.insert(best_sequence, swap_point, best_sequence[swap_with-1])
					best_sequence = np.delete(best_sequence, swap_with)
				else:
					best_sequence = np.insert(best_sequence, swap_point+1, best_sequence[swap_with])
					best_sequence = np.delete(best_sequence, swap_with)
			else:
				best_sequence[swap_point], best_sequence[swap_with] = best_sequence[swap_with], best_sequence[swap_point]
			violations = last_violations


		if iteration % 1000 == 0:
			print(f'\rIteration: {iteration}, Violations: {len(violations)}, Radius: {radius}/{target_radius}, Stagnation: {last_violations_counts.count(len(violations))}/{stagnation_limit * 10}        ', end="", flush=True)


		if iteration % 100 == 0:
			last_violations_counts.append(len(violations))
			if last_violations_counts.count(len(violations)) > stagnation_limit * 10:
				valid_violations = len(violations) + 1
				last_violations_counts.clear()
				if stagnation_limit < 45:
					stagnation_limit += 10
				elif stagnation_limit < 50:
					stagnation_limit += 5
			else:
				valid_violations = 0
		
		# Wähle eine zufällige Verletzung
		i, j = list(violations)[rand_violations[iteration] % len(violations)]
		
		# Finde einen zufälligen Tauschpartner für einen der beiden Punkte
		swap_point = i if rand_choose[iteration] == 0 else j
		swap_with = rand_swap[iteration]

		if swap_with == swap_point:
			swap_with = (swap_with + 1) % points

		if iteration % 4 == 0:
			# Einfügen
			best_sequence = np.insert(best_sequence, swap_with, best_sequence[swap_point])
			# Entfernen
			if swap_with < swap_point:
				best_sequence = np.delete(best_sequence, swap_point + 1)
			else:
				best_sequence = np.delete(best_sequence, swap_point)
		else:
			# Tausche
			best_sequence[swap_point], best_sequence[swap_with] = best_sequence[swap_with], best_sequence[swap_point]
	else:
		if max_iterations % 4 == 0:
			if swap_point < swap_with:
				best_sequence = np.insert(best_sequence, swap_point, best_sequence[swap_with-1])
				best_sequence = np.delete(best_sequence, swap_with)
			else:
				best_sequence = np.insert(best_sequence, swap_point+1, best_sequence[swap_with])
				best_sequence = np.delete(best_sequence, swap_with)
		else:
			best_sequence[swap_point], best_sequence[swap_with] = best_sequence[swap_with], best_sequence[swap_point]
		violations = last_violations
		print(f"\nMax iterations ({max_iterations}) reached. {len(violations)} violations remaining. Radius: {radius}/{target_radius}")
	
	print()
	return best_sequence


def create_trapez_distributed_array(points, depth, width, distance, throw_ratio):
	"""
	Erstellt ein Array mit n=points Werten, von 0 bis depth, die proportional zur Trapezbreite verteilt sind.
	Größere Abstände bei z=0 (kurze Seite), kleinere Abstände bei z=depth (lange Seite).
	"""
	# Hochauflösende z-Samples
	z_high_res = np.linspace(0, depth, points * 1000)	# 0 -> depth, 1000xpoints Werte
	
	# Breite an jeder z-Position
	widths = (distance + z_high_res) / throw_ratio		# w(z) = (distance + z) / throw_ratio
	widths = widths / width								# w(z) = ((distance + z) / width)
	
	# Kumulative Summe (entspricht "Anzahl Punkte bis hier")
	cum_widths = np.cumsum(widths)
	
	# Gleichmäßig verteilte Ziel-Positionen
	targets = np.linspace(0, cum_widths[-1], points)
	
	# Finde z-Werte durch Interpolation
	base_arr = np.interp(targets, cum_widths, z_high_res)
	
	return base_arr


# ---- Main Execution ---- #
if __name__ == "__main__":
	print("Wollumetric Point Distribution Generator")
	# ---- Configuration ---- #
	POINTS = int(input("Enter the total number of points (default: 640): ") or 640)
	WIDTH = int(input("Enter the width of the projection (default: 64): ") or 64)
	DEPTH = int(input("Enter the depth of the projection (default: 40): ") or 40)
	THROW_RATIO = float(input("Enter the throw ratio (default: 2.2): ") or 2.2)
	ALGORITHM = str(input("Enter the algorithm (regular, semi, x, xz, prime, golden, [radius]): ") or "radius")
	if ALGORITHM == "prime":
		PRIME = int(input("Enter the prime number (default: 59): ") or 59)
	elif ALGORITHM == "radius":
		TARGET_RADIUS = float(input("Enter the target radius (default: 160.0): ") or 160.0)
		START_RADIUS = float(input("Enter the start radius (default: 100.0): ") or 100.0)
		MAX_ITERATIONS = int(input("Enter the max iterations (default: 100_000_000): ") or 100_000_000)

	print("\nGenerating points...")

	distance = (THROW_RATIO * WIDTH)									# Abstand zur Projektionsebene
	x_max_angle = math.atan((WIDTH/2) / distance)						# Maximaler Halb-Winkel in Radiant
	x_angels = np.linspace(-(x_max_angle), (x_max_angle), num=POINTS)	# X-Winkel für alle Punkte

	#base_arr = np.linspace(0, depth, points)                                     # Gleichmäßig verteilte z-Werte (Baseline)
	base_arr = create_trapez_distributed_array(POINTS, DEPTH, WIDTH, distance, THROW_RATIO)

	match ALGORITHM:
		case "regular":
			z_arr = base_arr
		case "semi":
			z_arr = np.repeat([np.arange(POINTS//(WIDTH/2))], WIDTH//2, axis=0).flatten()
		case "x":
			depth_arr = np.arange(POINTS//(WIDTH/2))
			x_dithered = np.array([])
			for i in range(WIDTH//2):
				x_dithered = np.append(x_dithered, np.random.permutation(depth_arr))
			z_arr = x_dithered.flatten()
		case "xz":
			depth_arr = np.arange(POINTS//(WIDTH/2))
			x_dithered = np.array([])
			for i in range(WIDTH//2):
				x_dithered = np.append(x_dithered, np.random.permutation(depth_arr))
			x_dithered = x_dithered.flatten()
			z_arr = (x_dithered+np.random.uniform(-0.5, 0.5, POINTS)).clip(0, POINTS-1).round(2)
		case "prime":
			prime_permuted = np.argsort([(i  * PRIME) % POINTS for i in np.interp(base_arr, (0, DEPTH), (0, POINTS))])
			z_arr = np.interp(prime_permuted, (0, POINTS), (0, DEPTH)).round(2)
		case "golden":
			permutation = create_quasirandom_permutation(POINTS)
			z_arr = base_arr[permutation]
		case "radius":
			permutation = create_quasirandom_permutation(POINTS)
			z_arr = base_arr[permutation]
			z_arr = optimize_z_sequence_radius(z_arr, POINTS, distance, x_angels, target_radius=TARGET_RADIUS, start_radius=START_RADIUS, max_iterations=MAX_ITERATIONS)


	print("\nPoints generated!")

	# Calculate x positions
	x_positions = np.tan(x_angels) * (distance + z_arr)

	visualize = str(input("Do you want to visualize the points? (Y/n) ") or "y")
	if visualize.lower() == "y":
		# creating subplot and figure
		fig = plt.figure()
		ax = fig.add_subplot(111)
		scatter, = ax.plot(x_positions, z_arr, ".")
		x_max = ((distance + DEPTH) / THROW_RATIO) / 2
		ax.set_xlim([-(x_max+1), x_max+1])

		# setting labels
		plt.xlabel("Width")
		plt.ylabel("Depth")
		plt.title("Wollumetric Point Distribution")
		plt.show()

	save = str(input("Do you want to save the points? (Y/n) ") or "y")
	if save.lower() == "y":
		result = np.column_stack([x_angels.round(4), np.column_stack([x_positions.round(4), z_arr.round(4)])])

		np.save(f"{SAVE_PATH}{ALGORITHM}-{POINTS}-{WIDTH}x{DEPTH}-{THROW_RATIO}{'-'+str(PRIME) if ALGORITHM == 'prime' else ''}{'-'+str(TARGET_RADIUS) if ALGORITHM == 'radius' else ''}_points.npy", result)
		print("Points saved successfully!")