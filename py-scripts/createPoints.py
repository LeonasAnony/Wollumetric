import matplotlib.pyplot as plt
import math
import numpy as np
from scipy.spatial import KDTree

SAVE_PATH = "../wiremaps/"


# ---- Helper Functions ---- #
def calculate_neighbor_distance(flat_array, width) -> float:
		"""
		Berechnet die durchschnittliche Distanz zu den k nächsten Nachbarn.
		Nutzt KDTree für effiziente Nachbarschaftssuche.
		Höherer Score = besser (größere Distanzen).
		"""
		# Erstelle 2D-Punkte: (index, y-wert)
		# Dies berücksichtigt sowohl Position in der Sequenz als auch y-Wert
		points = np.column_stack([np.interp(np.arange(len(flat_array)), (0, len(flat_array)-1), (0, width-1)).round(2), flat_array])
		
		# Baue KDTree für effiziente k-nächste-Nachbarn Suche
		tree = KDTree(points)
		
		# Finde k+1 nächste Nachbarn (inkl. Punkt selbst)
		distances, _ = tree.query(points, k=2)
		
		# Zweite Spalte = Distanz zum nächsten Nachbarn
		avg_distance = np.mean(distances[:, 1:])
		
		return avg_distance


def optimize_z_sequence(array: np.ndarray, points: int, width: int, temperature: float = 0.00001, iterations: int = 50000):
	"""
	Optimiert die Reihenfolge der z-Werte über alle Spalten hinweg.
	Gibt ein 2D-Array zurück mit shape (width, depth).
	"""
	# Initialisiere mit zufälliger Permutation pro Spalte
	best_sequence = array
	best_score = calculate_neighbor_distance(best_sequence, width)
	
	cooling_rate = 0.999
	score_check = 0
	
	for iteration in range(iterations):
		# Wähle zufällige Spalte und tausche zwei z-Werte darin
		i, j = np.random.choice(points, 2, replace=False)
		
		# Erstelle Kandidat
		candidate = best_sequence.copy()
		candidate[i], candidate[j] = candidate[j], candidate[i]
		
		score = calculate_neighbor_distance(candidate, width)
		
		# Simulated Annealing: Akzeptiere auch schlechtere Lösungen mit Wahrscheinlichkeit
		delta = score - best_score
		if (delta + np.random.random() * temperature) > 0:
			best_sequence = candidate
			best_score = score
		
		temperature *= cooling_rate
		
		if iteration % 100 == 0:
			print(f'\rIteration: {iteration}, Current Score: {best_score:.4f}, Temperature: {temperature:.6f}        ', end="", flush=True)
			if round(best_score, 4) == score_check:
				break
			score_check = round(best_score, 4)

	print()
	return best_sequence


def optimize_z_sequence2(array: np.ndarray, points: int, distance: int, x_angels: np.ndarray, target_radius: float = 90, start_radius: float = 80, max_iterations: int = 100000):
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
	z_high_res = np.linspace(0, depth, points * 100)	# 0 -> depth, 100xpoints Werte
	
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
	# ---- Configuration ---- #
	WIDTH = int(input("Enter the width of the projection (default: 32): ") or 32)
	DEPTH = int(input("Enter the depth of the projection (default: 20): ") or 20)
	THROW_RATIO = float(input("Enter the throw ratio (default: 1.6): ") or 1.6)
	ALGORITHM = str(input("Enter the algorithm (default: optimized): ") or "optimized")  # "regular", "semi-regular", "x-dithered", "xz-dithered", "prime-permuted", "optimized"
	PRIME = int(input("Enter the prime number (default: 59): ") or 59)
	TARGET_RADIUS = float(input("Enter the target radius (default: 94.0): ") or 94.0)
	START_RADIUS = float(input("Enter the start radius (default: 90.0): ") or 90.0)
	MAX_ITERATIONS = int(input("Enter the max iterations (default: 100_000_000): ") or 100_000_000)

	print("\nGenerating points...")

	points = DEPTH * WIDTH                                            # Gesamtanzahl Punkte
	distance = (THROW_RATIO * WIDTH)                                # Abstand zur Projektionsebene
	x_max_angle = math.atan((WIDTH/2) / distance)                # Maximaler Halb-Winkel in Radiant
	x_angels = np.linspace(-(x_max_angle), (x_max_angle), num=points)    # X-Winkel für alle Punkte

	#base_arr = np.linspace(0, depth, points)                                     # Gleichmäßig verteilte z-Werte (Baseline)
	base_arr = create_trapez_distributed_array(points, DEPTH, WIDTH, distance, THROW_RATIO)

	match ALGORITHM:
		case "regular":
			z_arr = base_arr
		case "semi-regular":
			z_arr = np.repeat([np.arange(DEPTH)], WIDTH, axis=0).flatten()
		case "x-dithered":
			depth_arr = np.arange(DEPTH)
			x_dithered = np.array([])
			for i in range(WIDTH):
				x_dithered = np.append(x_dithered, np.random.permutation(depth_arr))
			z_arr = x_dithered.flatten()
		case "xy-dithered":
			depth_arr = np.arange(DEPTH)
			x_dithered = np.array([])
			for i in range(WIDTH):
				x_dithered = np.append(x_dithered, np.random.permutation(depth_arr))
			x_dithered = x_dithered.flatten()
			z_arr = (x_dithered+np.random.uniform(-0.5, 0.5, points)).clip(0, points-1).round(2)
		case "prime-permuted":
			prime_permuted = np.argsort([(i  * PRIME) % points for i in np.interp(base_arr, (0, DEPTH), (0, points))])
			z_arr = np.interp(prime_permuted, (0, points), (0, DEPTH)).round(2)
		case "optimized":
			z_arr = optimize_z_sequence(base_arr, points, WIDTH, iterations=100000)
			z_arr = optimize_z_sequence2(z_arr, points, distance, x_angels, target_radius=TARGET_RADIUS, start_radius=START_RADIUS, max_iterations=MAX_ITERATIONS)


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

		np.save(f"{SAVE_PATH}{ALGORITHM}-{WIDTH}x{DEPTH}-{THROW_RATIO}{'-'+str(PRIME) if ALGORITHM == 'prime-permuted' else ''}{'-'+str(TARGET_RADIUS) if ALGORITHM == 'optimized' else ''}_points.npy", result)
		print("Points saved successfully!")