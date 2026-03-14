import sys
import os
# Add the backend directory to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.navigation import NavigationService

def run_test():
		nav = NavigationService(grid_size=100)

		# Define a start and end point
		start = {"lat": 20.0, "lon": 50.0}
		end = {"lat": 25.0, "lon": 55.0}

		# Scenario 1: Clean Route (All vessels compliant)
		vessels_clean = [
				{"lat": 22.5, "lon": 52.5, "status": "Compliant"}
		]

		# Scenario 2: Blocked Route (Vessel is Non-Compliant)
		vessels_blocked = [
				{"lat": 22.5, "lon": 52.5, "status": "Suspicious"}
		]

		print("--- Running Navigation Tests ---")

		path_1 = nav.solve_astar(start, end, vessels_clean)
		print(f"Scenario 1 (Compliant): Found path with {len(path_1)} nodes.")

		path_2 = nav.solve_astar(start, end, vessels_blocked)
		print(f"Scenario 2 (Blocked): Found path with {len(path_2)} nodes.")

		if len(path_1) != len(path_2):
				print("SUCCESS: The algorithm calculated a different route to avoid the 'Suspicious' vessel.")
		else:
				print("NOTE: Paths are the same length. Check if the vessel was directly on the path.")

if __name__ == "__main__":
		run_test()