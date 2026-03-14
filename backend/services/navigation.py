import heapq
import math


class NavigationService:
		def __init__(self, grid_size=100):
				self.grid_size = grid_size

				# Geographic bounds (Persian Gulf focus area)
				self.LAT_MIN = 20.0
				self.LAT_MAX = 30.0
				self.LON_MIN = 45.0
				self.LON_MAX = 60.0

		def get_distance(self, p1, p2):
				"""Euclidean distance used for both movement cost and heuristic"""
				return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

		def solve_astar(self, start, end, vessels):
				blocked = set()
				safety_radius = 3

				# Create blocked zones around suspicious vessels
				for vessel in vessels:
						if vessel.get("status") != "Compliant":
								bx, by = self.lat_lon_to_grid(vessel["lat"], vessel["lon"])
								for dx in range(-safety_radius, safety_radius + 1):
										for dy in range(-safety_radius, safety_radius + 1):
												if math.sqrt(dx**2 + dy**2) <= safety_radius:
														nx = bx + dx
														ny = by + dy

														if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
																blocked.add((nx, ny))

				start_node = self.lat_lon_to_grid(start["lat"], start["lon"])
				end_node = self.lat_lon_to_grid(end["lat"], end["lon"])

				open_list = []
				heapq.heappush(open_list, (0, start_node))

				came_from = {}
				g_score = {start_node: 0}

				while open_list:
						current = heapq.heappop(open_list)[1]

						if current == end_node:
								return self.reconstruct_path(came_from, current)
						for dx, dy in [
								(0, 1), (0, -1), (1, 0), (-1, 0),
								(1, 1), (1, -1), (-1, 1), (-1, -1)
						]:
								neighbor = (current[0] + dx, current[1] + dy)

								if not (0 <= neighbor[0] < self.grid_size and
												0 <= neighbor[1] < self.grid_size):
										continue

								if neighbor in blocked:
										continue

								move_cost = self.get_distance(current, neighbor)
								tentative_g = g_score[current] + move_cost

								if tentative_g < g_score.get(neighbor, float("inf")):
										came_from[neighbor] = current
										g_score[neighbor] = tentative_g
										f_score = tentative_g + self.get_distance(neighbor, end_node)

										heapq.heappush(open_list, (f_score, neighbor))
				return []

		def lat_lon_to_grid(self, lat, lon):
				x = int(
						((lon - self.LON_MIN) / (self.LON_MAX - self.LON_MIN))
						* (self.grid_size - 1)
				)
				y = int(
						((self.LAT_MAX - lat) / (self.LAT_MAX - self.LAT_MIN))
						* (self.grid_size - 1)
				)

				x = max(0, min(x, self.grid_size - 1))
				y = max(0, min(y, self.grid_size - 1))
				return (x, y)

		def grid_to_lat_lon(self, x, y):
				lon = (
						(x / (self.grid_size - 1))
						* (self.LON_MAX - self.LON_MIN)
						+ self.LON_MIN
				)

				lat = (
						self.LAT_MAX
						- (y / (self.grid_size - 1))
						* (self.LAT_MAX - self.LAT_MIN)
				)

				return {
						"lat": round(lat, 6),
						"lon": round(lon, 6)
				}

		def reconstruct_path(self, came_from, current):
				path = [current]
				while current in came_from:
						current = came_from[current]
						path.append(current)

				path.reverse()
				return path

		def convert_path_to_geo(self, grid_path):
				"""Convert grid path to geographic coordinates"""
				geo_path = []

				for x, y in grid_path:
						geo_path.append(self.grid_to_lat_lon(x, y))

				return geo_path