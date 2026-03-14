import heapq
import math

class NavigationService:
		def __init__(self, grid_size=100):
				self.grid_size = grid_size

		def get_distance(self, p1, p2):
				return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

		def solve_astar(self, start, end, vessels):
				# "Blocked" coordinates based on 'bad' status
				blocked = set()
				for v in vessels:
						if v.get('status') != 'Compliant':
								bx, by = self.lat_lon_to_grid(v['lat'], v['lon'])
								blocked.add((bx, by))

				start_node = self.lat_lon_to_grid(start['lat'], start['lon'])
				end_node = self.lat_lon_to_grid(end['lat'], end['lon'])

				open_list = []
				heapq.heappush(open_list, (0, start_node))
				came_from = {}
				g_score = {start_node: 0}

				while open_list:
						current = heapq.heappop(open_list)[1]

						if current == end_node:
								return self.reconstruct_path(came_from, current)
						for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
								neighbor = (current[0] + dx, current[1] + dy)

								if 0 <= neighbor[0] < self.grid_size and 0 <= neighbor[1] < self.grid_size:
										if neighbor in blocked: continue

										tentative_g = g_score[current] + self.get_distance(current, neighbor)

										if tentative_g < g_score.get(neighbor, float('inf')):
												came_from[neighbor] = current
												g_score[neighbor] = tentative_g
												f_score = tentative_g + self.get_distance(neighbor, end_node)
												heapq.heappush(open_list, (f_score, neighbor))
				return []

		def lat_lon_to_grid(self, lat, lon):
				x = int(((lon + 180) / 360) * self.grid_size)
				y = int(((90 - lat) / 180) * self.grid_size)
				return (x, y)

		def reconstruct_path(self, came_from, current):
				path = [current]
				while current in came_from:
						current = came_from[current]
						path.append(current)
				return path[::-1]