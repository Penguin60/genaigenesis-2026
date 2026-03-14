import sys
import os
import math

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.navigation import NavigationService


def run_test():
		nav = NavigationService(grid_size=100)

		start = {"lat": 24.0, "lon": 50.0}
		end = {"lat": 24.0, "lon": 56.0}

		vessels_blocked = [
				{"lat": 24.0, "lon": 53.0, "status": "Suspicious"}
		]

		vessels_clean = [
				{"lat": 22.5, "lon": 52.5, "status": "Compliant"}
		]

		print("\n--- Running Navigation Tests ---")

		path_clean = nav.solve_astar(start, end, vessels_clean)
		path_blocked = nav.solve_astar(start, end, vessels_blocked)

		print(f"Clean path nodes: {len(path_clean)}")
		print(f"Blocked path nodes: {len(path_blocked)}")

		# TEST 1: Ensure both paths exist
		if not path_clean:
				print("FAIL: No path found in clean scenario")
				return

		if not path_blocked:
				print("FAIL: No path found when vessel present")
				return

		print("PASS: Both scenarios produced valid paths")

		# TEST 2: Ensure routes differ
		if path_clean != path_blocked:
				print("PASS: Path changed to avoid suspicious vessel")
		else:
				print("WARNING: Paths are identical")

		# TEST 3: Verify vessel safety zone avoided
		vessel = vessels_blocked[0]
		bx, by = nav.lat_lon_to_grid(vessel["lat"], vessel["lon"])

		safety_radius = 3
		violation = False

		for node in path_blocked:
				dx = node[0] - bx
				dy = node[1] - by
				dist = math.sqrt(dx**2 + dy**2)

				if dist <= safety_radius:
						violation = True
						break

		if violation:
				print("FAIL: Path entered vessel safety zone")
		else:
				print("PASS: Path avoided vessel safety zone")

		# TEST 4: Show example nodes for debugging
		print("\nSample path nodes:")
		print("Clean path (first 10):", path_clean[:10])
		print("Blocked path (first 10):", path_blocked[:10])

		print("\n--- Test Complete ---")


if __name__ == "__main__":
		run_test()