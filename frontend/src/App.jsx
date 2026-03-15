import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
	MapContainer,
	TileLayer,
	CircleMarker,
	Polyline,
	useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "leaflet.heat";

import ChatWidget from "./components/ChatWidget";

const BASE_VESSELS = [
	// BAD VESSELS
	{
		name: "LUNA STAR",
		imo: "9284731",
		flag: "CM",
		type: "Crude Oil Tanker",
		status: "AIS Gap",
		lat: "26.32",
		lon: "56.21",
	},
	{
		name: "CASPIAN WAVE",
		imo: "9456012",
		flag: "PA",
		type: "Chemical Tanker",
		status: "Rendezvous",
		lat: "25.90",
		lon: "56.85",
	},
	{
		name: "NORTHERN DRIFT",
		imo: "9387120",
		flag: "MH",
		type: "LPG Tanker",
		status: "Route Deviation",
		lat: "25.45",
		lon: "57.20",
	},
	{
		name: "BLACK MARLIN",
		imo: "9612045",
		flag: "PA",
		type: "Crude Oil Tanker",
		status: "Dark Activity",
		lat: "26.05",
		lon: "56.55",
	},
	{
		name: "RED HORIZON",
		imo: "9601934",
		flag: "KH",
		type: "General Cargo",
		status: "Flag Hopping",
		lat: "26.10",
		lon: "55.80",
	},
	// GOOD VESSELS
	{
		name: "EVER GLORY",
		imo: "9812345",
		flag: "SG",
		type: "Container Ship",
		status: "Compliant",
		lat: "25.20",
		lon: "54.5",
	},
	{
		name: "MAERSK SENTINEL",
		imo: "9723410",
		flag: "DK",
		type: "Cargo",
		status: "Compliant",
		lat: "25.80",
		lon: "55.90",
	},
	{
		name: "PACIFIC RAY",
		imo: "9910284",
		flag: "JP",
		type: "Bulk Carrier",
		status: "Compliant",
		lat: "26.45",
		lon: "57.10",
	},
	{
		name: "NORDIC PRIDE",
		imo: "9456711",
		flag: "NO",
		type: "Oil Tanker",
		status: "Compliant",
		lat: "26.15",
		lon: "56.95",
	},
];

const PORT_SUGGESTIONS = [
	{ name: "Port of Fujairah", lat: 25.11, lon: 56.36 },
	{ name: "Port of Jebel Ali", lat: 25.01, lon: 55.06 },
	{ name: "Bandar Abbas", lat: 27.18, lon: 56.26 },
	{ name: "Muscat Port", lat: 23.62, lon: 58.56 },
];

// Timeline points will be generated below after helper function definition.

function seedFromId(id) {
	return id.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
}

function buildRecentTimelinePoints(hoursBack = 24, stepMinutes = 30) {
	const points = [];
	const now = Date.now();
	const stepMs = stepMinutes * 60 * 1000;
	const totalSteps = Math.floor((hoursBack * 60) / stepMinutes);
	const start = now - totalSteps * stepMs;
	for (let i = 0; i <= totalSteps; i += 1) {
		points.push(new Date(start + i * stepMs).toISOString());
	}
	return points;
}

const TIMELINE_POINTS = buildRecentTimelinePoints(24, 30);

// SAMPLE DATA: DIRECTION_OVERRIDES
// const DIRECTION_OVERRIDES = {
//   "9612045": { lat: -1, lon: 1 }, // BLACK MARLIN → southeast toward CASPIAN WAVE
// };
const DIRECTION_OVERRIDES = {
	9612045: { lat: -1, lon: 1 }, // BLACK MARLIN → southeast toward CASPIAN WAVE
};

function generateTrack(vessel) {
	const seed = seedFromId(vessel.imo);
	const baseLat = Number.parseFloat(vessel.lat);
	const baseLon = Number.parseFloat(vessel.lon);
	const override = DIRECTION_OVERRIDES[vessel.imo];
	const latDirection = override ? override.lat : seed % 2 === 0 ? 1 : -1;
	const lonDirection = override ? override.lon : seed % 3 === 0 ? -1 : 1;
	return TIMELINE_POINTS.map((ts, index) => {
		const drift = index / TIMELINE_POINTS.length;
		const latWave = Math.sin((index + seed) * 0.47) * 0.07;
		const lonWave = Math.cos((index + seed) * 0.41) * 0.08;
		return {
			ts,
			lat: baseLat + latWave + drift * 0.18 * latDirection,
			lon: baseLon + lonWave + drift * 0.2 * lonDirection,
		};
	});
}

function getTimeline(vessels) {
	const seen = new Set();
	for (const vessel of vessels) {
		for (const point of vessel.track || []) {
			seen.add(point.ts);
		}
	}
	return [...seen].sort((a, b) => new Date(a) - new Date(b));
}

function getPointAtOrBefore(track, targetTs) {
	if (!targetTs) return null;
	const target = new Date(targetTs).getTime();
	let latest = null;
	for (const point of track || []) {
		if (new Date(point.ts).getTime() <= target) latest = point;
	}
	return latest;
}

function getTrailUntil(track, targetTs) {
	if (!targetTs) return [];
	const target = new Date(targetTs).getTime();
	return (track || [])
		.filter((point) => new Date(point.ts).getTime() <= target)
		.map((point) => [point.lat, point.lon]);
}

const BADGE_STYLES = {
	compliant: "bg-[#16a34a]/20 text-[#16a34a]",
	"anomaly-detected": "bg-[#7f1d1d]/30 text-[#ef4444]",
	"ais-gap": "bg-[#991b1b]/20 text-[#ef4444]",
	"dark-activity": "bg-[#7f1d1d]/30 text-[#dc2626]",
	rendezvous: "bg-[#450a0a]/30 text-[#f87171]",
	"route-deviation": "bg-[#991b1b]/20 text-[#ef4444]",
	"flag-hopping": "bg-[#7f1d1d]/30 text-[#dc2626]",
};

// ── Heatmap: density-based danger zone engine ──────────
const THREAT_WEIGHT = {
	"Anomaly Detected": 0.48,
	"AIS Gap": 0.48,
	"Dark Activity": 0.48,
	Rendezvous: 0.36,
	"Route Deviation": 0.3,
	"Flag Hopping": 0.24,
	Compliant: 0.0,
};
const CELL = 0.055;
const DANGER_RADIUS = 0.22;
const GHOST_STEPS = 5;
const GHOST_INTERVAL = 0.4;
const GHOST_DECAY = 0.72;
const HEADING_FAN = [-15, 0, 15];

// Rough coastal polygons for land masking (point-in-polygon ray-cast)
// UAE + Oman southern coast, Iran northern coast, Musandam peninsula
const LAND_POLYGONS = [
	// UAE / Oman southern coastline (west to east)
	[
		[24.0, 51.5],
		[24.45, 54.35],
		[24.42, 54.5],
		[24.47, 54.65],
		[24.35, 54.75],
		[24.2, 54.8],
		[24.15, 55.15],
		[24.6, 55.4],
		[25.05, 55.1],
		[25.2, 55.2],
		[25.3, 55.3],
		[25.34, 55.4],
		[25.4, 55.52],
		[25.58, 56.2],
		[25.3, 56.35],
		[25.15, 56.38],
		[24.95, 56.6],
		[24.7, 56.65],
		[24.25, 56.55],
		[23.6, 58.55],
		[23.2, 58.8],
		[22.5, 59.8],
		[22.0, 59.8],
		[22.0, 51.5],
		[24.0, 51.5],
	],
	// Iran northern coastline
	[
		[27.1, 51.5],
		[26.9, 52.5],
		[26.6, 53.8],
		[26.55, 54.3],
		[26.3, 54.8],
		[26.15, 55.6],
		[26.55, 56.1],
		[26.95, 56.2],
		[27.1, 56.6],
		[27.2, 56.85],
		[26.65, 57.3],
		[26.4, 57.1],
		[26.3, 56.9],
		[26.1, 56.6],
		[25.85, 56.7],
		[25.75, 57.3],
		[25.45, 57.5],
		[25.3, 58.8],
		[25.6, 59.0],
		[25.8, 59.8],
		[30.0, 59.8],
		[30.0, 51.5],
		[27.1, 51.5],
	],
];

function pointInPolygon(lat, lon, polygon) {
	let inside = false;
	for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
		const [yi, xi] = polygon[i];
		const [yj, xj] = polygon[j];
		if (
			yi > lat !== yj > lat &&
			lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi
		) {
			inside = !inside;
		}
	}
	return inside;
}

function isLand(lat, lon) {
	for (const poly of LAND_POLYGONS) {
		if (pointInPolygon(lat, lon, poly)) return true;
	}
	return false;
}

function generateHeatmapPoints(vessels) {
	// 1. Collect threat sources: real positions + ghost projections
	const sources = [];
	for (const v of vessels) {
		const tw = THREAT_WEIGHT[v.status] ?? 0;
		if (tw === 0) continue;
		const lat = v.point.lat;
		const lon = v.point.lon;
		sources.push({ lat, lon, w: tw });

		// Infer heading from track
		const track = v.track || [];
		let heading = 0;
		if (track.length >= 2) {
			const p1 = track[track.length - 2];
			const p2 = track[track.length - 1];
			heading =
				((Math.atan2(p2.lon - p1.lon, p2.lat - p1.lat) * 180) / Math.PI + 360) %
				360;
		}
		const speed = 10;
		for (const offset of HEADING_FAN) {
			const rad = ((heading + offset) * Math.PI) / 180;
			const dLatH = speed / 60;
			const dLonH = speed / (60 * Math.cos((lat * Math.PI) / 180));
			let cLat = lat,
				cLon = lon,
				intensity = tw;
			for (let s = 0; s < GHOST_STEPS; s++) {
				cLat += dLatH * Math.cos(rad) * GHOST_INTERVAL;
				cLon += dLonH * Math.sin(rad) * GHOST_INTERVAL;
				intensity *= GHOST_DECAY;
				if (!isLand(cLat, cLon))
					sources.push({ lat: cLat, lon: cLon, w: intensity });
			}
		}

		// Historical track positions
		for (let i = 0; i < track.length; i++) {
			const age = (i + 1) / track.length;
			sources.push({ lat: track[i].lat, lon: track[i].lon, w: tw * age * 0.4 });
		}
	}

	// 2. Build grid — dynamically sized to cover all sources
	if (!sources.length) return [];
	const pad = DANGER_RADIUS + 0.1;
	const latMin = Math.min(...sources.map((s) => s.lat)) - pad;
	const latMax = Math.max(...sources.map((s) => s.lat)) + pad;
	const lonMin = Math.min(...sources.map((s) => s.lon)) - pad;
	const lonMax = Math.max(...sources.map((s) => s.lon)) + pad;
	const grid = {};
	const radiusSq = DANGER_RADIUS * DANGER_RADIUS;

	for (const src of sources) {
		const cellLatMin = Math.floor((src.lat - DANGER_RADIUS - latMin) / CELL);
		const cellLatMax = Math.ceil((src.lat + DANGER_RADIUS - latMin) / CELL);
		const cellLonMin = Math.floor((src.lon - DANGER_RADIUS - lonMin) / CELL);
		const cellLonMax = Math.ceil((src.lon + DANGER_RADIUS - lonMin) / CELL);

		for (let cy = cellLatMin; cy <= cellLatMax; cy++) {
			for (let cx = cellLonMin; cx <= cellLonMax; cx++) {
				const cellLat = latMin + cy * CELL + CELL / 2;
				const cellLon = lonMin + cx * CELL + CELL / 2;
				if (
					cellLat < latMin ||
					cellLat > latMax ||
					cellLon < lonMin ||
					cellLon > lonMax
				)
					continue;
				// Skip land cells
				if (isLand(cellLat, cellLon)) continue;
				const dLat = cellLat - src.lat;
				const dLon = cellLon - src.lon;
				const distSq = dLat * dLat + dLon * dLon;
				if (distSq > radiusSq) continue;
				const falloff = Math.exp((-3.0 * distSq) / radiusSq);
				const key = `${cy},${cx}`;
				grid[key] = (grid[key] || 0) + src.w * falloff;
			}
		}
	}

	// 3. Normalise and emit [lat, lon, intensity]
	const entries = Object.entries(grid);
	if (!entries.length) return [];
	const maxVal = Math.max(...entries.map(([, v]) => v));
	if (maxVal === 0) return [];

	const out = [];
	for (const [key, val] of entries) {
		const [cy, cx] = key.split(",").map(Number);
		const lat = latMin + cy * CELL + CELL / 2;
		const lon = lonMin + cx * CELL + CELL / 2;
		const norm = val / maxVal;
		if (norm < 0.03) continue;
		out.push([lat, lon, norm]);
	}
	return out;
}

function getHeatVisualsForZoom(zoom) {
	if (zoom <= 8) return { radius: 22, blur: 18 };
	if (zoom === 9) return { radius: 28, blur: 22 };
	if (zoom === 10) return { radius: 36, blur: 28 };
	if (zoom === 11) return { radius: 48, blur: 36 };
	if (zoom === 12) return { radius: 64, blur: 46 };
	if (zoom === 13) return { radius: 82, blur: 58 };
	return { radius: 104, blur: 72 };
}

function HeatLayer({ points }) {
	const map = useMap();
	const [zoom, setZoom] = useState(() => map.getZoom());

	useEffect(() => {
		const handleZoom = () => setZoom(map.getZoom());
		map.on("zoomend", handleZoom);
		return () => map.off("zoomend", handleZoom);
	}, [map]);

	useEffect(() => {
		if (!points.length) return;
		const { radius, blur } = getHeatVisualsForZoom(zoom);
		const heat = L.heatLayer(points, {
			radius,
			blur,
			max: 0.6,
			maxZoom: 12,
			minOpacity: 0.05,
			gradient: {
				0.15: "transparent",
				0.3: "rgba(12,20,69,0.3)",
				0.42: "#b45309",
				0.55: "#d97706",
				0.7: "#ea580c",
				0.85: "#dc2626",
				1.0: "#fef08a",
			},
		}).addTo(map);
		return () => map.removeLayer(heat);
	}, [map, points, zoom]);

	return null;
}

function getVesselHeading(vessel, currentTs) {
	const track = vessel.track || [];
	if (!currentTs || track.length < 2) return null;
	const target = new Date(currentTs).getTime();
	// Find the current point index
	let idx = -1;
	for (let i = 0; i < track.length; i++) {
		if (new Date(track[i].ts).getTime() <= target) idx = i;
	}
	// Use previous→current if available, otherwise current→next
	let p1, p2;
	if (idx > 0) {
		p1 = track[idx - 1];
		p2 = track[idx];
	} else if (idx === 0 && track.length > 1) {
		p1 = track[0];
		p2 = track[1];
	} else {
		return null;
	}
	const dy = p2.lat - p1.lat;
	const dx = p2.lon - p1.lon;
	return ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360;
}

function getVesselSpeed(vessel, currentTs) {
	const track = vessel.track || [];
	if (!currentTs || track.length < 2) return null;
	const target = new Date(currentTs).getTime();
	let idx = -1;
	for (let i = 0; i < track.length; i++) {
		if (new Date(track[i].ts).getTime() <= target) idx = i;
	}
	let p1, p2;
	if (idx > 0) {
		p1 = track[idx - 1];
		p2 = track[idx];
	} else if (idx === 0 && track.length > 1) {
		p1 = track[0];
		p2 = track[1];
	} else {
		return null;
	}
	// Haversine distance in nautical miles
	const R = 3440.065;
	const dLat = (p2.lat - p1.lat) * (Math.PI / 180);
	const dLon = (p2.lon - p1.lon) * (Math.PI / 180);
	const a =
		Math.sin(dLat / 2) ** 2 +
		Math.cos((p1.lat * Math.PI) / 180) *
			Math.cos((p2.lat * Math.PI) / 180) *
			Math.sin(dLon / 2) ** 2;
	const distance = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
	const timeHours = (new Date(p2.ts) - new Date(p1.ts)) / (1000 * 60 * 60);
	if (timeHours === 0) return 0;
	return distance / timeHours;
}

function headingToCompass(deg) {
	const dirs = [
		"N",
		"NNE",
		"NE",
		"ENE",
		"E",
		"ESE",
		"SE",
		"SSE",
		"S",
		"SSW",
		"SW",
		"WSW",
		"W",
		"WNW",
		"NW",
		"NNW",
	];
	return dirs[Math.round(deg / 22.5) % 16];
}

function countryCodeToFlagEmoji(countryCode) {
	if (!countryCode) return "🏳️";
	return countryCode
		.toUpperCase()
		.replace(/./g, (char) => String.fromCodePoint(127397 + char.charCodeAt()));
}

function App() {
	// State from both versions
	const [selectedVesselImo, setSelectedVesselImo] = useState(null);
	const [userGPS, setUserGPS] = useState(null);
	const [startPoint, setStartPoint] = useState(null);
	const [inputValue, setInputValue] = useState("");
	const [showDropdown, setShowDropdown] = useState(false);
	const [distance, setDistance] = useState(null);
	const [timeIndex, setTimeIndex] = useState(0);
	const [isPlaying, setIsPlaying] = useState(false);
	const [followLatest, setFollowLatest] = useState(true);
	const [showHeatmap, setShowHeatmap] = useState(false);
	const [vesselSummaries, setVesselSummaries] = useState({});
	const [vesselFlags, setVesselFlags] = useState({});
	const hasStartedSimulationRef = useRef(false);
	const [behaviorAnalysis, setBehaviorAnalysis] = useState({});

	// TanStack Query for Backend Integration
	const { data: simData } = useQuery({
		queryKey: ["simulation"],
		queryFn: async () => {
			try {
				if (!hasStartedSimulationRef.current) {
					const startRes = await fetch(
						"http://localhost:8000/api/v1/simulation/start",
						{
							method: "POST",
						},
					);
					const startData = await startRes.json();
					console.log("hi ", startData.vessel_prompt_results);
					setBehaviorAnalysis(startData.behavior_analysis || {});
					setVesselSummaries(startData.vessel_prompt_results || {});
					setVesselFlags(startData.vessel_flags || {});
					hasStartedSimulationRef.current = true;
				}
				const res = await fetch("http://localhost:8000/api/v1/simulation");
				const resData = await res.json();
				setBehaviorAnalysis(resData.behavior_analysis || {});
				if (res.status === 400) {
					// Simulation probably not started, start it
					const startRes = await fetch(
						"http://localhost:8000/api/v1/simulation/start",
						{
							method: "POST",
						},
					);
					const startData = await startRes.json();
					console.log("hi ", startData.vessel_prompt_results);
					setBehaviorAnalysis(startData.behavior_analysis || {});
					setVesselSummaries(startData.vessel_prompt_results || {});
					setVesselFlags(startData.vessel_flags || {});
					const retryRes = await fetch(
						"http://localhost:8000/api/v1/simulation",
					);
					return retryRes.json();
				}
				return resData;
			} catch (err) {
				console.error("Backend fetch error:", err);
				return { vessels: [] };
			}
		},
		refetchInterval: 1000,
	});

	const MOCK_VESSELS = useMemo(() => simData?.vessels || [], [simData]);

	const timeline = useMemo(() => getTimeline(MOCK_VESSELS), [MOCK_VESSELS]);
	// When following live, always pin to the last index synchronously
	// to avoid the 1-frame lag from useEffect that causes the slider to jump back.
	const effectiveTimeIndex =
		followLatest && timeline.length > 0
			? timeline.length - 1
			: Math.min(timeIndex, Math.max(timeline.length - 1, 0));
	const currentTs = timeline[effectiveTimeIndex] || null;

	// Nautical Distance Calculation
	const calculateDistance = (p1, p2) => {
		if (!p1 || !p2) return null;
		const R = 3440.065;
		const dLat = (p2.lat - p1.lat) * (Math.PI / 180);
		const dLon = (p2.lon - p1.lon) * (Math.PI / 180);
		const a =
			Math.sin(dLat / 2) ** 2 +
			Math.cos((p1.lat * Math.PI) / 180) *
				Math.cos((p2.lat * Math.PI) / 180) *
				Math.sin(dLon / 2) ** 2;
		return (R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(1);
	};

	useEffect(() => {
		if ("geolocation" in navigator) {
			navigator.geolocation.getCurrentPosition((pos) => {
				setUserGPS({ lat: pos.coords.latitude, lon: pos.coords.longitude });
			});
		}
	}, []);

	useEffect(() => {
		if (timeline.length === 0) return;
		const lastIndex = timeline.length - 1;
		if (followLatest) {
			// In live mode, pin the timeline to the newest sample as data streams in.
			setTimeIndex(lastIndex);
			return;
		}
		if (timeIndex > lastIndex) {
			setTimeIndex(lastIndex);
		}
	}, [timeline, followLatest, timeIndex]);

	useEffect(() => {
		if (!isPlaying || timeline.length < 2) return undefined;
		const timer = setInterval(() => {
			setTimeIndex((prev) => {
				const lastIndex = timeline.length - 1;
				if (prev >= lastIndex) {
					setIsPlaying(false);
					setFollowLatest(true);
					return lastIndex;
				}
				return prev + 1;
			});
		}, 900);
		return () => clearInterval(timer);
	}, [isPlaying, timeline.length]);

	const vesselsAtTime = useMemo(
		() =>
			MOCK_VESSELS.map((vessel) => {
				const point = getPointAtOrBefore(vessel.track, currentTs);
				if (vessel.mmsi == "2000016") {
					console.log(currentTs);
					console.log(point);
				}
				return point ? { ...vessel, point } : null;
			}).filter(Boolean),

		[currentTs, MOCK_VESSELS],
	);

	const heatmapPoints = useMemo(
		() => (showHeatmap ? generateHeatmapPoints(vesselsAtTime) : []),
		[vesselsAtTime, showHeatmap],
	);

	const selectedVesselDetails = useMemo(() => {
		if (!selectedVesselImo) return null;
		const base = MOCK_VESSELS.find((v) => v.imo === selectedVesselImo);
		if (!base) return null;
		const point = getPointAtOrBefore(base.track, currentTs);
		return point ? { ...base, point } : { ...base, point: null };
	}, [selectedVesselImo, currentTs, MOCK_VESSELS]);

	useEffect(() => {
		if (selectedVesselDetails?.point && startPoint) {
			setDistance(
				calculateDistance(startPoint, {
					lat: selectedVesselDetails.point.lat,
					lon: selectedVesselDetails.point.lon,
				}),
			);
		} else {
			setDistance(null);
		}
	}, [selectedVesselDetails, startPoint]);

	const formattedTime = currentTs
		? new Date(currentTs).toLocaleString()
		: "No time selected";

	return (
		<div className="flex flex-col min-h-screen bg-bg text-text">
			<header className="flex items-center gap-3.5 px-6 py-8 h-14 bg-surface border-b border-border">
				<span className="font-bold text-2xl tracking-[1px] text-accent">
					POPEYE
				</span>
			</header>

			<main className="flex-1 flex flex-col overflow-hidden">
				<section className="px-10 py-6 shrink-0">
					<div className="w-full h-130 rounded-lg overflow-hidden border border-border relative">
						<MapContainer
							center={[26.2, 56.5]}
							zoom={8}
							className="h-full w-full z-0"
						>
							<TileLayer
								url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
								attribution="&copy; OpenStreetMap"
							/>
							{showHeatmap && <HeatLayer points={heatmapPoints} />}

							{startPoint && selectedVesselDetails?.point && (
								<Polyline
									positions={[
										[startPoint.lat, startPoint.lon],
										[
											selectedVesselDetails.point.lat,
											selectedVesselDetails.point.lon,
										],
									]}
									pathOptions={{
										color: "#5b8def",
										weight: 2,
										dashArray: "5, 10",
									}}
								/>
							)}

							{vesselsAtTime.map((vessel) => {
								if (vessel.mmsi == "2000016") {
									console.log("hi");
								}
								const trail = getTrailUntil(vessel.track, currentTs);
								const isGood = vessel.status === "Compliant";
								const greenColor = "oklch(52.7% 0.154 150.069)";
								const redColor = "#ef4444";
								const heading =
									selectedVesselImo === vessel.imo
										? getVesselHeading(vessel, currentTs)
										: null;
								// Build a sleek direction indicator from vessel position
								const arrowLine = (() => {
									if (heading === null || !vessel.point) return null;
									const rad = (heading * Math.PI) / 180;
									const lat = vessel.point.lat;
									const lon = vessel.point.lon;
									// Tapered shaft: 3 segments getting progressively longer
									const segments = [0.03, 0.065, 0.1];
									const pts = segments.map((len) => [
										lat + len * Math.cos(rad),
										lon + len * Math.sin(rad),
									]);
									// Chevron arrowhead at the tip
									const tip = pts[2];
									const chevronBack = 0.025;
									const chevronSpread = 0.55; // radians (~32 degrees)
									const lWing = [
										tip[0] - chevronBack * Math.cos(rad - chevronSpread),
										tip[1] - chevronBack * Math.sin(rad - chevronSpread),
									];
									const rWing = [
										tip[0] - chevronBack * Math.cos(rad + chevronSpread),
										tip[1] - chevronBack * Math.sin(rad + chevronSpread),
									];
									return {
										shaft: [[lat, lon], ...pts],
										chevron: [lWing, tip, rWing],
									};
								})();

								return (
									<div key={vessel.imo}>
										{selectedVesselImo === vessel.imo && trail.length > 1 && (
											<Polyline
												positions={trail}
												pathOptions={{
													color: isGood ? greenColor : redColor,
													weight: 4,
													opacity: 0.8,
												}}
											/>
										)}
										{arrowLine && (
											<>
												{/* Glow layer */}
												<Polyline
													positions={arrowLine.shaft}
													pathOptions={{
														color: "#facc15",
														weight: 5,
														opacity: 0.1,
														lineCap: "round",
													}}
												/>
												{/* Main shaft */}
												<Polyline
													positions={arrowLine.shaft}
													pathOptions={{
														color: "#facc15",
														weight: 2,
														opacity: 0.45,
														lineCap: "round",
													}}
												/>
												{/* Chevron head - glow */}
												<Polyline
													positions={arrowLine.chevron}
													pathOptions={{
														color: "#facc15",
														weight: 5,
														opacity: 0.12,
														lineCap: "round",
														lineJoin: "round",
													}}
												/>
												{/* Chevron head */}
												<Polyline
													positions={arrowLine.chevron}
													pathOptions={{
														color: "#fde047",
														weight: 2.5,
														opacity: 0.5,
														lineCap: "round",
														lineJoin: "round",
													}}
												/>
											</>
										)}
										<CircleMarker
											center={[vessel.point.lat, vessel.point.lon]}
											radius={5}
											pathOptions={{
												color: isGood ? greenColor : redColor,
												fillColor: isGood ? greenColor : redColor,
												fillOpacity: 0.8,
												weight: selectedVesselImo === vessel.imo ? 3 : 1,
											}}
											eventHandlers={{
												click: () => setSelectedVesselImo(vessel.imo),
											}}
										/>
									</div>
								);
							})}
						</MapContainer>

						{/* Timeline Control */}
						<div
							className="absolute left-3 bottom-3 z-[1000] rounded-lg border border-border bg-surface/95 backdrop-blur-sm px-4 py-3 transition-[right] duration-300 ease-in-out"
							style={{
								right: selectedVesselDetails
									? "calc(20rem + 0.75rem)"
									: "0.75rem",
							}}
						>
							{" "}
							<div className="flex items-center gap-3">
								<button
									onClick={() => {
										setFollowLatest(false);
										setIsPlaying((prev) => !prev);
									}}
									className="h-9 px-3 rounded-md border border-border text-xs font-semibold hover:bg-white/[0.04]"
								>
									{isPlaying ? "PAUSE" : "PLAY"}
								</button>
								<button
									onClick={() => {
										setIsPlaying(false);
										setFollowLatest(true);
										if (timeline.length > 0) {
											setTimeIndex(timeline.length - 1);
										}
									}}
									className={`h-9 px-3 rounded-md border text-xs font-semibold ${
										followLatest
											? "border-red-400 text-red-300 bg-red-950/30"
											: "border-border hover:bg-white/[0.04]"
									}`}
								>
									LIVE
								</button>
								<input
									type="range"
									min={0}
									max={Math.max(timeline.length - 1, 0)}
									value={effectiveTimeIndex}
									onChange={(e) => {
										const nextIndex = Number(e.target.value);
										const lastIndex = Math.max(timeline.length - 1, 0);
										setTimeIndex(nextIndex);
										setIsPlaying(false);
										setFollowLatest(nextIndex >= lastIndex);
									}}
									className="w-full accent-accent"
								/>
								<span className="text-[11px] text-text-dim font-mono">
									{formattedTime}
								</span>
							</div>
						</div>

						{/* Heatmap Toggle */}
						<button
							onClick={() => setShowHeatmap((prev) => !prev)}
							className={`absolute top-3 z-[1001] flex items-center gap-2 px-4 py-2.5 rounded-lg border backdrop-blur-md text-xs font-bold tracking-wide transition-all duration-300 shadow-lg ${
								showHeatmap
									? "bg-orange-500 border-orange-400 text-white shadow-orange-500/30"
									: "bg-[#1e293b] border-[#334155] text-white hover:bg-[#334155]"
							} ${selectedVesselDetails ? "right-[21rem]" : "right-3"}`}
						>
							<span
								className={`w-2.5 h-2.5 rounded-full ${showHeatmap ? "bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)]" : "bg-gray-400"}`}
							/>
							HEATMAP
						</button>

						{/* Sidebar Panel */}
						<div
							className={`absolute top-0 right-0 h-full w-80 bg-surface/95 backdrop-blur-sm border-l border-border z-[1001] transition-transform duration-300 ${selectedVesselDetails ? "translate-x-0" : "translate-x-full"}`}
						>
							{selectedVesselDetails && (
								<div className="p-5 h-full overflow-y-auto">
									<div className="flex justify-between mb-5">
										<h3 className="text-lg font-bold">
											{selectedVesselDetails.name}
										</h3>
										<button
											onClick={() => setSelectedVesselImo(null)}
											className="text-text-dim hover:text-text text-xl"
										>
											&times;
										</button>
									</div>
									<div className="space-y-4">
										<div>
											<span className="text-[11px] uppercase text-text-dim tracking-wide">
												Status
											</span>
											<div className="mt-1">
												<span
													className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${BADGE_STYLES[selectedVesselDetails.status.replace(/\s/g, "-").toLowerCase()] || ""}`}
												>
													{selectedVesselDetails.status}
												</span>
											</div>
										</div>
										<div>
											<span className="text-[11px] uppercase text-text-dim tracking-wide">
												MMSI Number
											</span>
											<p className="font-mono text-sm mt-1">
												{selectedVesselDetails.imo}
											</p>
											<div className="mt-4">
												<h4 className="font-semibold text-sm mb-1">
													Agent Summary
												</h4>
												<pre className="whitespace-pre-wrap text-xs bg-gray-900/30 p-2 rounded">
													{vesselSummaries[selectedVesselDetails.mmsi]}
												</pre>
											</div>
											{behaviorAnalysis[selectedVesselDetails?.mmsi] && (
												<div className="mt-4">
													<h4 className="font-semibold text-sm mb-1">
														Behavior Analysis
													</h4>
													<pre className="whitespace-pre-wrap text-xs bg-gray-900/30 p-2 rounded">
														{behaviorAnalysis[selectedVesselDetails.mmsi]}
													</pre>
												</div>
											)}
										</div>
										<div>
											<span className="text-[11px] uppercase text-text-dim tracking-wide">
												Flag / Country
											</span>
											<div className="flex items-center gap-2 mt-1">
												<span style={{ fontSize: "1.5em" }}>
													{countryCodeToFlagEmoji(
														vesselFlags[selectedVesselDetails?.mmsi]
															?.toUpperCase()
															.slice(0, 2),
													)}
												</span>
												<span className="font-mono text-sm">
													{vesselFlags[selectedVesselDetails?.mmsi] ||
														"Unknown"}
												</span>
											</div>
										</div>
										<div>
											<span className="text-[11px] uppercase text-text-dim tracking-wide">
												Position
											</span>
											<p className="font-mono text-sm mt-1">
												{selectedVesselDetails.point
													? `${selectedVesselDetails.point.lat.toFixed(3)}°N, ${selectedVesselDetails.point.lon.toFixed(3)}°E`
													: "N/A"}
											</p>
										</div>
										{(() => {
											const h = getVesselHeading(
												selectedVesselDetails,
												currentTs,
											);
											const s = getVesselSpeed(
												selectedVesselDetails,
												currentTs,
											);
											if (h === null) return null;
											console.log(selectedVesselDetails);
											return (
												<div>
													<span className="text-[11px] uppercase text-text-dim tracking-wide">
														Heading
													</span>
													<p>
														Reported Heading:{" "}
														{selectedVesselDetails.latest_point.course}
													</p>
													<p>Actual Heading: </p>
													<div className="flex items-center gap-3 mt-1">
														<span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-white/[0.06] border border-border">
															<span
																style={{
																	transform: `rotate(${h}deg)`,
																	display: "inline-block",
																	fontSize: "16px",
																	lineHeight: 1,
																}}
															>
																↑
															</span>
														</span>
														<span className="font-mono text-sm">
															{h.toFixed(1)}° {headingToCompass(h)}
														</span>
													</div>
													<span className="text-[11px] uppercase text-text-dim tracking-wide">
														Speed
													</span>
													<p>
														Reported Speed:{" "}
														{selectedVesselDetails.latest_point.speed} knots
													</p>
													<p>Actual Speed</p>
													<div className="flex items-center gap-3 mt-1">
														<span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-white/[0.06] border border-border">
															<span
																style={{
																	transform: `rotate(${h}deg)`,
																	display: "inline-block",
																	fontSize: "16px",
																	lineHeight: 1,
																}}
															>
																↑
															</span>
														</span>
														<span className="font-mono text-sm">
															{s.toFixed(1)}
														</span>
													</div>
												</div>
											);
										})()}

										<div className="pt-2 relative">
											<div className="flex justify-between items-center mb-2">
												<span className="text-[11px] uppercase text-text-dim tracking-wide">
													Find route from
												</span>
												{distance && (
													<span className="text-[11px] font-mono text-accent animate-pulse">
														{distance} NM
													</span>
												)}
											</div>
											<div className="relative">
												<input
													type="text"
													value={inputValue}
													onChange={(e) => {
														setInputValue(e.target.value);
														setShowDropdown(true);
													}}
													onFocus={() => setShowDropdown(true)}
													placeholder="Search origin port..."
													className="w-full h-11 pl-5 pr-12 text-sm bg-bg border border-border rounded-full outline-none"
												/>
											</div>
											{showDropdown && (
												<div className="absolute left-0 right-0 mt-2 bg-surface border border-border rounded-xl shadow-2xl z-[1002] max-h-48 overflow-y-auto">
													{userGPS && (
														<button
															className="w-full px-4 py-3 text-left text-sm hover:bg-white/5 text-accent border-b border-border"
															onClick={() => {
																setStartPoint(userGPS);
																setInputValue("Your Location");
																setShowDropdown(false);
															}}
														>
															⊕ Use current location
														</button>
													)}
													{PORT_SUGGESTIONS.filter(
														(p) =>
															inputValue === "" ||
															inputValue === "Your Location" ||
															p.name
																.toLowerCase()
																.includes(inputValue.toLowerCase()),
													).map((port) => (
														<button
															key={port.name}
															className="w-full px-4 py-3 text-left text-sm hover:bg-white/5 flex flex-col border-b border-border/30 last:border-0"
															onClick={() => {
																setStartPoint(port);
																setInputValue(port.name);
																setShowDropdown(false);
															}}
														>
															<span className="font-medium">{port.name}</span>
															<span className="text-[10px] text-text-dim font-mono">
																{port.lat}, {port.lon}
															</span>
														</button>
													))}
												</div>
											)}
										</div>
									</div>
								</div>
							)}
						</div>
					</div>
				</section>

				<section className="px-10 pb-8 flex flex-col min-h-0 flex-1">
					<h2 className="text-[15px] font-semibold text-text mb-3">
						Flagged Vessels
					</h2>
					<div className="overflow-y-auto max-h-[300px] border border-border rounded-lg">
						<table className="w-full border-collapse text-[13px]">
							<thead className="sticky top-0 bg-surface z-10">
								<tr>
									{[
										"Vessel",
										"IMO",
										"Flag",
										"Type",
										"Status",
										"Lat",
										"Lon",
									].map((h) => (
										<th
											key={h}
											className="text-left px-3 py-2 font-semibold text-[11px] uppercase tracking-wide text-text-dim border-b border-border"
										>
											{h}
										</th>
									))}
								</tr>
							</thead>
							<tbody>
								{vesselsAtTime.map((v) => (
									<tr
										key={v.imo}
										className={`hover:bg-white/[0.02] cursor-pointer ${
											selectedVesselImo === v.imo
												? v.status === "Compliant"
													? "bg-[#16a34a]/20"
													: "bg-[#7f1d1d]/35"
												: ""
										}`}
										onClick={() => setSelectedVesselImo(v.imo)}
									>
										<td className="px-3 py-2.5 border-b border-border">
											{v.name}
										</td>
										<td className="px-3 py-2.5 border-b border-border font-mono">
											{v.imo}
										</td>
										<td className="px-3 py-2.5 border-b border-border">
											{v.flag}
										</td>
										<td className="px-3 py-2.5 border-b border-border">
											{v.type}
										</td>
										<td className="px-3 py-2.5 border-b border-border">
											<span
												className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${BADGE_STYLES[v.status.replace(/\s/g, "-").toLowerCase()] || ""}`}
											>
												{v.status}
											</span>
										</td>
										<td className="px-3 py-2.5 border-b border-border font-mono">
											{v.point.lat.toFixed(3)}
										</td>
										<td className="px-3 py-2.5 border-b border-border font-mono">
											{v.point.lon.toFixed(3)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</section>
			</main>
			<ChatWidget vessels={vesselsAtTime} heatmapPoints={heatmapPoints} />
		</div>
	);
}

export default App;
