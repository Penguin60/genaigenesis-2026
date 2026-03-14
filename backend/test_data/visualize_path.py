import sys
import os
import matplotlib.pyplot as plt
import numpy as np

# Add the backend directory to the path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.navigation import NavigationService

def run_visual_test():
		# Initialize the navigation service with a 100x100 grid
		nav = NavigationService(grid_size=100)

		# Define a start point (bottom-left) and an end point (top-right)
		start = {"lat": 21.0, "lon": 48.0}
		end = {"lat": 28.0, "lon": 58.0}

		# Define landmass (a rectangular area)
		landmass = [
				{"lat": lat, "lon": lon}
				for lat in np.arange(23.0, 26.0, 0.2)
				for lon in np.arange(52.0, 55.0, 0.2)
		]

		# Define vessels to avoid (non-compliant status triggers avoidance)
		vessels_to_avoid = [
				{"lat": 24.0, "lon": 50.0, "status": "Suspicious"},
				{"lat": 26.0, "lon": 56.0, "status": "Non-Compliant"}
		]

		# Calculate the path that avoids vessels and landmass
		path = nav.solve_astar(start, end, vessels_to_avoid, landmass_points=landmass)

		# Convert the grid path back to lat/lon for visualization
		lat_lon_path = []
		if path:
				lat_lon_path = [nav.grid_to_lat_lon(p[0], p[1]) for p in path]

		# --- Matplotlib Plotting ---
		plt.figure(figsize=(10, 8))

		# Create the grid for visualization
		grid_display = np.zeros((nav.grid_size, nav.grid_size))

		# Mark landmass (value 1)
		if landmass:
				for lp in landmass:
						bx, by = nav.lat_lon_to_grid(lp['lat'], lp['lon'])
						grid_display[by, bx] = 1

		# Mark blocked circles around non-compliant vessels (value 2)
		# This approximates the internal logic for visualization
		safety_radius_grid = 3 
		for v in vessels_to_avoid:
				vx, vy = nav.lat_lon_to_grid(v['lat'], v['lon'])
				for dx in range(-safety_radius_grid, safety_radius_grid + 1):
						for dy in range(-safety_radius_grid, safety_radius_grid + 1):
								if np.sqrt(dx**2 + dy**2) <= safety_radius_grid:
										nx, ny = vx + dx, vy + dy
										if 0 <= nx < nav.grid_size and 0 <= ny < nav.grid_size:
												grid_display[ny, nx] = 2

		# Plot the grid with land and vessel zones
		# flipud is needed as imshow puts (0,0) at the top-left by default
		plt.imshow(np.flipud(grid_display), extent=[nav.LON_MIN, nav.LON_MAX, nav.LAT_MIN, nav.LAT_MAX], cmap='viridis', aspect='equal')

		# Create a custom legend for the grid colors
		from matplotlib.patches import Patch
		legend_elements = [Patch(facecolor=plt.cm.viridis(0.0), label='Safe Water'),
											 Patch(facecolor=plt.cm.viridis(0.5), label='Landmass'),
											 Patch(facecolor=plt.cm.viridis(1.0), label='Vessel Zone')]
		plt.legend(handles=legend_elements, loc='upper left')

		# Plot the path (as lat/lon line)
		if lat_lon_path:
				path_lons = [p['lon'] for p in lat_lon_path]
				path_lats = [p['lat'] for p in lat_lon_path]
				plt.plot(path_lons, path_lats, color='white', linewidth=3, label='Safe Route', marker='o', markersize=3)

		# Plot start and end points
		plt.scatter([start['lon']], [start['lat']], color='green', s=150, label='Start Point', edgecolors='black', zorder=5)
		plt.scatter([end['lon']], [end['lat']], color='blue', s=150, label='End Point', edgecolors='black', zorder=5)

		# Plot actual vessel locations
		for v in vessels_to_avoid:
				plt.scatter(v['lon'], v['lat'], color='red', marker='X', s=100, edgecolors='black', zorder=5)

		plt.xlabel('Longitude')
		plt.ylabel('Latitude')
		plt.title('A* Pathfinding Visualization (Avoiding Vessels & Landmass)')

		# Combine legends
		handles, labels = plt.gca().get_legend_handles_labels()
		# Add the grid legend elements
		handles.extend(legend_elements)
		labels.extend(['Safe Water Zone', 'Landmass Zone', 'Vessel Avoidance Zone'])

		# Remove duplicates
		by_label = dict(zip(labels, handles))
		plt.legend(by_label.values(), by_label.keys(), loc='best')

		plt.grid(True, linestyle='--', alpha=0.5)

		# Set plot limits based on navigation service bounds
		plt.xlim(nav.LON_MIN, nav.LON_MAX)
		plt.ylim(nav.LAT_MIN, nav.LAT_MAX)

		plt.tight_layout()
		plt.show()

if __name__ == "__main__":
		try:
				run_visual_test()
		except ImportError as e:
				print(f"Error: Missing required library. Please install it using: pip install matplotlib numpy. Specific error: {e}")
		except Exception as e:
				print(f"An unexpected error occurred: {e}")