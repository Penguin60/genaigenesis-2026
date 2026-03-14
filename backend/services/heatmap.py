"""
Heatmap Service — generates density heatmap data for vessel activity.

Accounts for shadow fleet behaviour: vessels that go dark (disable AIS)
are projected forward using their last known heading and speed, creating
"ghost" positions that inflate the heat around likely locations.

All logic is self-contained in this file.

Usage:
    from services.heatmap import HeatmapService

    service = HeatmapService()
    points  = service.generate(vessels)
    # returns list of [lat, lon, intensity] suitable for Leaflet.heat
"""

import math
from typing import Any, Dict, List, Optional, Tuple

# ── Tunables ─────────────────────────────────────────────────────────
GRID_RESOLUTION   = 0.05          # degrees per cell (~5.5 km)
GHOST_STEPS       = 6             # how many future positions to project for dark vessels
GHOST_INTERVAL_H  = 0.5           # hours between each ghost step
GHOST_DECAY       = 0.85          # intensity multiplier per ghost step (uncertainty grows)
SPEED_FALLBACK    = 10.0          # knots – default if vessel has no speed field
HEADING_SPREAD    = 15.0          # degrees ± fan for heading uncertainty
HEADING_FAN_RAYS  = 3             # 1 centre + 2 side rays
KERNEL_RADIUS     = 2             # grid cells for Gaussian-like smoothing
STATUS_WEIGHTS: Dict[str, float] = {
    "AIS Gap":         1.0,
    "Dark Activity":   1.0,
    "Rendezvous":      0.85,
    "Route Deviation": 0.75,
    "Flag Hopping":    0.70,
    "Compliant":       0.15,
}
# ────────────────────────────────────────────────────────────────────


class HeatmapService:
    """Builds a weighted lat/lon/intensity list for front-end heat layers."""

    # ── public API ──────────────────────────────────────────────────
    def generate(
        self,
        vessels: List[Dict[str, Any]],
        bounds: Optional[Dict[str, float]] = None,
    ) -> List[List[float]]:
        """
        Parameters
        ----------
        vessels : list of dicts, each containing at minimum:
            - lat, lon          (float or str)
            - status            (str)
            Optional but used when present:
            - heading           (float, degrees true north)
            - speed             (float, knots)
            - track             (list of {lat, lon, ts} breadcrumbs)
        bounds : optional dict {lat_min, lat_max, lon_min, lon_max}
            restricts output to a viewport.  Defaults to the Persian-Gulf
            focus area used elsewhere in the backend.

        Returns
        -------
        List of [lat, lon, intensity] triples, intensity ∈ (0, 1].
        """
        if bounds is None:
            bounds = {"lat_min": 20.0, "lat_max": 30.0,
                      "lon_min": 45.0, "lon_max": 60.0}

        raw_points: List[Tuple[float, float, float]] = []

        for v in vessels:
            base_weight = STATUS_WEIGHTS.get(v.get("status", ""), 0.3)
            lat = float(v["lat"])
            lon = float(v["lon"])

            # 1. Actual known position
            raw_points.append((lat, lon, base_weight))

            # 2. If the vessel has a track, add historical breadcrumbs
            #    (older points get less weight)
            track = v.get("track", [])
            if track:
                n = len(track)
                for i, pt in enumerate(track):
                    age_factor = (i + 1) / n  # older → smaller
                    raw_points.append((
                        float(pt["lat"]),
                        float(pt["lon"]),
                        base_weight * age_factor * 0.5,
                    ))

            # 3. Ghost projection for dark / suspicious vessels
            if v.get("status") not in ("Compliant",):
                heading = self._infer_heading(v)
                speed   = float(v.get("speed", SPEED_FALLBACK))
                ghosts  = self._project_ghosts(lat, lon, heading, speed, base_weight)
                raw_points.extend(ghosts)

        # 4. Bin into grid, smooth, normalise
        grid = self._bin_to_grid(raw_points, bounds)
        grid = self._smooth(grid)
        output = self._normalise_and_flatten(grid, bounds)

        return output

    # ── ghost projection ────────────────────────────────────────────
    @staticmethod
    def _knots_to_deg_per_h(knots: float, lat: float) -> Tuple[float, float]:
        """Convert speed in knots to approximate degrees/hour."""
        nm_per_deg_lat = 60.0
        nm_per_deg_lon = 60.0 * math.cos(math.radians(lat))
        deg_lat_per_h = knots / nm_per_deg_lat
        deg_lon_per_h = knots / nm_per_deg_lon if nm_per_deg_lon else 0.0
        return deg_lat_per_h, deg_lon_per_h

    def _project_ghosts(
        self,
        lat: float,
        lon: float,
        heading: float,
        speed: float,
        base_weight: float,
    ) -> List[Tuple[float, float, float]]:
        """
        Fan out HEADING_FAN_RAYS rays around the heading ± HEADING_SPREAD,
        placing GHOST_STEPS positions along each ray with decaying intensity.
        """
        ghosts: List[Tuple[float, float, float]] = []
        angles = [heading + HEADING_SPREAD * (r / max(HEADING_FAN_RAYS // 2, 1))
                  for r in range(-(HEADING_FAN_RAYS // 2), HEADING_FAN_RAYS // 2 + 1)]

        for angle in angles:
            rad = math.radians(angle)
            dlat_h, dlon_h = self._knots_to_deg_per_h(speed, lat)
            intensity = base_weight
            cur_lat, cur_lon = lat, lon

            for _ in range(GHOST_STEPS):
                # heading: 0 = north, 90 = east
                cur_lat += dlat_h * math.cos(rad) * GHOST_INTERVAL_H
                cur_lon += dlon_h * math.sin(rad) * GHOST_INTERVAL_H
                intensity *= GHOST_DECAY
                ghosts.append((cur_lat, cur_lon, intensity))

        return ghosts

    # ── heading inference ───────────────────────────────────────────
    @staticmethod
    def _infer_heading(vessel: Dict[str, Any]) -> float:
        """
        Best-effort heading:
        1. Explicit `heading` field
        2. Derive from last two track points
        3. Fall back to 0 (north)
        """
        if "heading" in vessel and vessel["heading"] is not None:
            return float(vessel["heading"])

        track = vessel.get("track", [])
        if len(track) >= 2:
            p1 = track[-2]
            p2 = track[-1]
            dy = float(p2["lat"]) - float(p1["lat"])
            dx = float(p2["lon"]) - float(p1["lon"])
            heading = math.degrees(math.atan2(dx, dy)) % 360
            return heading

        return 0.0

    # ── grid binning ────────────────────────────────────────────────
    @staticmethod
    def _bin_to_grid(
        points: List[Tuple[float, float, float]],
        bounds: Dict[str, float],
    ) -> Dict[Tuple[int, int], float]:
        grid: Dict[Tuple[int, int], float] = {}
        for lat, lon, w in points:
            if not (bounds["lat_min"] <= lat <= bounds["lat_max"] and
                    bounds["lon_min"] <= lon <= bounds["lon_max"]):
                continue
            gx = int((lon - bounds["lon_min"]) / GRID_RESOLUTION)
            gy = int((lat - bounds["lat_min"]) / GRID_RESOLUTION)
            grid[(gx, gy)] = grid.get((gx, gy), 0.0) + w
        return grid

    # ── Gaussian-ish smoothing ──────────────────────────────────────
    @staticmethod
    def _smooth(grid: Dict[Tuple[int, int], float]) -> Dict[Tuple[int, int], float]:
        smoothed: Dict[Tuple[int, int], float] = {}
        for (gx, gy), w in grid.items():
            for dx in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1):
                for dy in range(-KERNEL_RADIUS, KERNEL_RADIUS + 1):
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > KERNEL_RADIUS:
                        continue
                    # Gaussian-like falloff
                    falloff = math.exp(-0.5 * (dist / max(KERNEL_RADIUS * 0.5, 0.1)) ** 2)
                    key = (gx + dx, gy + dy)
                    smoothed[key] = smoothed.get(key, 0.0) + w * falloff
        return smoothed

    # ── normalise & flatten ─────────────────────────────────────────
    @staticmethod
    def _normalise_and_flatten(
        grid: Dict[Tuple[int, int], float],
        bounds: Dict[str, float],
    ) -> List[List[float]]:
        if not grid:
            return []

        max_val = max(grid.values())
        if max_val == 0:
            return []

        result: List[List[float]] = []
        for (gx, gy), w in grid.items():
            lat = bounds["lat_min"] + gy * GRID_RESOLUTION + GRID_RESOLUTION / 2
            lon = bounds["lon_min"] + gx * GRID_RESOLUTION + GRID_RESOLUTION / 2
            intensity = round(w / max_val, 4)
            if intensity < 0.01:
                continue
            result.append([round(lat, 5), round(lon, 5), intensity])

        return result
