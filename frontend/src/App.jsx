                    import { useEffect, useMemo, useState } from "react";
                    import { MapContainer, TileLayer, CircleMarker, Polyline, useMap } from "react-leaflet";
                    import "leaflet/dist/leaflet.css";
                    import L from "leaflet";
                    import "leaflet.heat";

                    const BASE_VESSELS = [
                      // BAD VESSELS
                      { name: "LUNA STAR", imo: "9284731", flag: "CM", type: "Crude Oil Tanker", status: "AIS Gap", lat: "26.32", lon: "56.21" },
                      { name: "CASPIAN WAVE", imo: "9456012", flag: "PA", type: "Chemical Tanker", status: "Rendezvous", lat: "25.90", lon: "56.85" },
                      { name: "NORTHERN DRIFT", imo: "9387120", flag: "MH", type: "LPG Tanker", status: "Route Deviation", lat: "25.45", lon: "57.20" },
                      { name: "BLACK MARLIN", imo: "9612045", flag: "PA", type: "Crude Oil Tanker", status: "Dark Activity", lat: "26.05", lon: "56.55" },
                      { name: "RED HORIZON", imo: "9601934", flag: "KH", type: "General Cargo", status: "Flag Hopping", lat: "26.10", lon: "55.80" },
                      // GOOD VESSELS
                      { name: "EVER GLORY", imo: "9812345", flag: "SG", type: "Container Ship", status: "Compliant", lat: "25.20", lon: "54.5" },
                      { name: "MAERSK SENTINEL", imo: "9723410", flag: "DK", type: "Cargo", status: "Compliant", lat: "25.80", lon: "55.90" },
                      { name: "PACIFIC RAY", imo: "9910284", flag: "JP", type: "Bulk Carrier", status: "Compliant", lat: "26.45", lon: "57.10" },
                      { name: "NORDIC PRIDE", imo: "9456711", flag: "NO", type: "Oil Tanker", status: "Compliant", lat: "26.15", lon: "56.95" }
                    ];

                    const PORT_SUGGESTIONS = [
                      { name: "Port of Fujairah", lat: 25.11, lon: 56.36 },
                      { name: "Port of Jebel Ali", lat: 25.01, lon: 55.06 },
                      { name: "Bandar Abbas", lat: 27.18, lon: 56.26 },
                      { name: "Muscat Port", lat: 23.62, lon: 58.56 },
                    ];

                    const TIMELINE_POINTS = [
                      "2026-03-13T18:00:00Z", "2026-03-13T18:30:00Z", "2026-03-13T19:00:00Z", "2026-03-13T19:30:00Z",
                      "2026-03-13T20:00:00Z", "2026-03-13T20:30:00Z", "2026-03-13T21:00:00Z", "2026-03-13T21:30:00Z",
                      "2026-03-13T22:00:00Z", "2026-03-13T22:30:00Z", "2026-03-13T23:00:00Z",
                    ];

                    function seedFromId(id) { return id.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0); }

                    // Override directions: make BLACK MARLIN head toward CASPIAN WAVE (southeast)
                    const DIRECTION_OVERRIDES = {
                      "9612045": { lat: -1, lon: 1 }, // BLACK MARLIN → southeast toward CASPIAN WAVE
                    };

                    function generateTrack(vessel) {
                      const seed = seedFromId(vessel.imo);
                      const baseLat = Number.parseFloat(vessel.lat);
                      const baseLon = Number.parseFloat(vessel.lon);
                      const override = DIRECTION_OVERRIDES[vessel.imo];
                      const latDirection = override ? override.lat : (seed % 2 === 0 ? 1 : -1);
                      const lonDirection = override ? override.lon : (seed % 3 === 0 ? -1 : 1);
                      return TIMELINE_POINTS.map((ts, index) => {
                        const drift = index / TIMELINE_POINTS.length;
                        const latWave = Math.sin((index + seed) * 0.47) * 0.07;
                        const lonWave = Math.cos((index + seed) * 0.41) * 0.08;
                        return { ts, lat: baseLat + latWave + drift * 0.18 * latDirection, lon: baseLon + lonWave + drift * 0.2 * lonDirection };
                      });
                    }

                    const MOCK_VESSELS = BASE_VESSELS.map((vessel) => ({ ...vessel, track: generateTrack(vessel) }));

                    function getTimeline(vessels) {
                      const seen = new Set();
                      for (const vessel of vessels) { for (const point of vessel.track || []) { seen.add(point.ts); } }
                      return [...seen].sort((a, b) => new Date(a) - new Date(b));
                    }

                    function getPointAtOrBefore(track, targetTs) {
                      if (!targetTs) return null;
                      const target = new Date(targetTs).getTime();
                      let latest = null;
                      for (const point of track || []) { if (new Date(point.ts).getTime() <= target) latest = point; }
                      return latest;
                    }

                    function getTrailUntil(track, targetTs) {
                      if (!targetTs) return [];
                      const target = new Date(targetTs).getTime();
                      return (track || []).filter((point) => new Date(point.ts).getTime() <= target).map((point) => [point.lat, point.lon]);
                    }

                    const BADGE_STYLES = {
                      "compliant": "bg-[#16a34a]/20 text-[#16a34a]",
                      "ais-gap": "bg-[#991b1b]/20 text-[#ef4444]", 
                      "dark-activity": "bg-[#7f1d1d]/30 text-[#dc2626]",
                      "rendezvous": "bg-[#450a0a]/30 text-[#f87171]",
                      "route-deviation": "bg-[#991b1b]/20 text-[#ef4444]",
                      "flag-hopping": "bg-[#7f1d1d]/30 text-[#dc2626]",
                    };

                    // ── Heatmap: density-based danger zone engine ──────────
                    const THREAT_WEIGHT = {
                      "AIS Gap": 0.48, "Dark Activity": 0.48, "Rendezvous": 0.36,
                      "Route Deviation": 0.3, "Flag Hopping": 0.24, "Compliant": 0.0,
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
                        [24.0, 51.5], [24.45, 54.35], [24.42, 54.50], [24.47, 54.65],
                        [24.35, 54.75], [24.20, 54.80], [24.15, 55.15], [24.60, 55.40],
                        [25.05, 55.10], [25.20, 55.20], [25.30, 55.30], [25.34, 55.40],
                        [25.40, 55.52], [25.58, 56.20], [25.30, 56.35], [25.15, 56.38],
                        [24.95, 56.60], [24.70, 56.65], [24.25, 56.55], [23.60, 58.55],
                        [23.20, 58.80], [22.50, 59.80], [22.0, 59.80], [22.0, 51.5],
                        [24.0, 51.5],
                      ],
                      // Iran northern coastline
                      [
                        [27.10, 51.5], [26.90, 52.50], [26.60, 53.80], [26.55, 54.30],
                        [26.30, 54.80], [26.15, 55.60], [26.55, 56.10], [26.95, 56.20],
                        [27.10, 56.60], [27.20, 56.85], [26.65, 57.30], [26.40, 57.10],
                        [26.30, 56.90], [26.10, 56.60], [25.85, 56.70], [25.75, 57.30],
                        [25.45, 57.50], [25.30, 58.80], [25.60, 59.00], [25.80, 59.80],
                        [30.0, 59.80], [30.0, 51.5], [27.10, 51.5],
                      ],
                    ];

                    function pointInPolygon(lat, lon, polygon) {
                      let inside = false;
                      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
                        const [yi, xi] = polygon[i];
                        const [yj, xj] = polygon[j];
                        if (((yi > lat) !== (yj > lat)) && (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)) {
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
                          heading = (Math.atan2(p2.lon - p1.lon, p2.lat - p1.lat) * 180 / Math.PI + 360) % 360;
                        }
                        const speed = 10;
                        for (const offset of HEADING_FAN) {
                          const rad = (heading + offset) * Math.PI / 180;
                          const dLatH = speed / 60;
                          const dLonH = speed / (60 * Math.cos(lat * Math.PI / 180));
                          let cLat = lat, cLon = lon, intensity = tw;
                          for (let s = 0; s < GHOST_STEPS; s++) {
                            cLat += dLatH * Math.cos(rad) * GHOST_INTERVAL;
                            cLon += dLonH * Math.sin(rad) * GHOST_INTERVAL;
                            intensity *= GHOST_DECAY;
                            if (!isLand(cLat, cLon)) sources.push({ lat: cLat, lon: cLon, w: intensity });
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
                      const latMin = Math.min(...sources.map(s => s.lat)) - pad;
                      const latMax = Math.max(...sources.map(s => s.lat)) + pad;
                      const lonMin = Math.min(...sources.map(s => s.lon)) - pad;
                      const lonMax = Math.max(...sources.map(s => s.lon)) + pad;
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
                            if (cellLat < latMin || cellLat > latMax || cellLon < lonMin || cellLon > lonMax) continue;
                            // Skip land cells
                            if (isLand(cellLat, cellLon)) continue;
                            const dLat = cellLat - src.lat;
                            const dLon = cellLon - src.lon;
                            const distSq = dLat * dLat + dLon * dLon;
                            if (distSq > radiusSq) continue;
                            const falloff = Math.exp(-3.0 * distSq / radiusSq);
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

                    function HeatLayer({ points }) {
                      const map = useMap();
                      useEffect(() => {
                        if (!points.length) return;
                        const heat = L.heatLayer(points, {
                          radius: 22,
                          blur: 18,
                          max: 0.5,
                          maxZoom: 12,
                          minOpacity: 0.04,
                          gradient: { 0.15: "transparent", 0.3: "rgba(12,20,69,0.3)", 0.42: "#b45309", 0.55: "#d97706", 0.7: "#ea580c", 0.85: "#dc2626", 1.0: "#fef08a" },
                        }).addTo(map);
                        return () => map.removeLayer(heat);
                      }, [map, points]);
                      return null;
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
                      const [showHeatmap, setShowHeatmap] = useState(false);

                      const timeline = useMemo(() => getTimeline(MOCK_VESSELS), []);
                      const currentTs = timeline[timeIndex] || null;

                      // Nautical Distance Calculation
                      const calculateDistance = (p1, p2) => {
                        if (!p1 || !p2) return null;
                        const R = 3440.065; 
                        const dLat = (p2.lat - p1.lat) * (Math.PI / 180);
                        const dLon = (p2.lon - p1.lon) * (Math.PI / 180);
                        const a = Math.sin(dLat / 2) ** 2 + Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
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
                        if (!isPlaying || timeline.length < 2) return undefined;
                        const timer = setInterval(() => {
                          setTimeIndex((prev) => (prev >= timeline.length - 1 ? 0 : prev + 1));
                        }, 900);
                        return () => clearInterval(timer);
                      }, [isPlaying, timeline.length]);

                      const vesselsAtTime = useMemo(() => 
                        MOCK_VESSELS.map((vessel) => {
                          const point = getPointAtOrBefore(vessel.track, currentTs);
                          return point ? { ...vessel, point } : null;
                        }).filter(Boolean), [currentTs]
                      );

                      const heatmapPoints = useMemo(() => showHeatmap ? generateHeatmapPoints(vesselsAtTime) : [], [vesselsAtTime, showHeatmap]);

                      const selectedVesselDetails = useMemo(() => {
                        if (!selectedVesselImo) return null;
                        const base = MOCK_VESSELS.find((v) => v.imo === selectedVesselImo);
                        if (!base) return null;
                        const point = getPointAtOrBefore(base.track, currentTs);
                        return point ? { ...base, point } : { ...base, point: null };
                      }, [selectedVesselImo, currentTs]);

                      useEffect(() => {
                        if (selectedVesselDetails?.point && startPoint) {
                          setDistance(calculateDistance(startPoint, { lat: selectedVesselDetails.point.lat, lon: selectedVesselDetails.point.lon }));
                        } else {
                          setDistance(null);
                        }
                      }, [selectedVesselDetails, startPoint]);

                      const formattedTime = currentTs ? new Date(currentTs).toLocaleString() : "No time selected";

                      return (
                        <div className="flex flex-col min-h-screen bg-bg text-text">
                          <header className="flex items-center gap-3.5 px-6 py-8 h-14 bg-surface border-b border-border">
                            <span className="font-bold text-4xl tracking-[3px] text-accent">VANGUARD</span>
                            <span className="text-xl text-text-dim">Shadow Fleet Monitor</span>
                          </header>

                          <main className="flex-1 flex flex-col overflow-hidden">
                            <section className="px-10 py-6 shrink-0">
                              <div className="w-full h-130 rounded-lg overflow-hidden border border-border relative">
                                <MapContainer center={[26.2, 56.5]} zoom={8} className="h-full w-full z-0">
                                  <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution='&copy; OpenStreetMap' />
                                  {showHeatmap && <HeatLayer points={heatmapPoints} />}

                                  {startPoint && selectedVesselDetails?.point && (
                                    <Polyline 
                                      positions={[[startPoint.lat, startPoint.lon], [selectedVesselDetails.point.lat, selectedVesselDetails.point.lon]]}
                                      pathOptions={{ color: '#5b8def', weight: 2, dashArray: '5, 10' }}
                                    />
                                  )}

                                  {vesselsAtTime.map((vessel) => {
                                    const trail = getTrailUntil(vessel.track, currentTs);
                                    const isGood = vessel.status === "Compliant";
                                    const greenColor = "oklch(52.7% 0.154 150.069)";
                                    const redColor = "#ef4444";

                                    return (
                                      <div key={vessel.imo}>
                                        {selectedVesselImo === vessel.imo && trail.length > 1 && (
                                          <Polyline positions={trail} pathOptions={{ color: "#f8fafc", weight: 4, opacity: 0.65 }} />
                                        )}
                                        <CircleMarker
                                          center={[vessel.point.lat, vessel.point.lon]}
                                          radius={5}
                                          pathOptions={{
                                            color: selectedVesselImo === vessel.imo ? "#ffffff" : (isGood ? greenColor : redColor),
                                            fillColor: isGood ? greenColor : redColor,
                                            fillOpacity: 0.8,
                                            weight: selectedVesselImo === vessel.imo ? 3 : 1,
                                          }}
                                          eventHandlers={{ click: () => setSelectedVesselImo(vessel.imo) }}
                                        />
                                      </div>
                                    );
                                  })}
                                </MapContainer>

                                {/* Timeline Control */}
                                <div className="absolute left-3 right-3 bottom-3 z-[1000] rounded-lg border border-border bg-surface/95 backdrop-blur-sm px-4 py-3">
                                  <div className="flex items-center gap-3">
                                    <button onClick={() => setIsPlaying((prev) => !prev)} className="h-9 px-3 rounded-md border border-border text-xs font-semibold hover:bg-white/[0.04]">
                                      {isPlaying ? "PAUSE" : "PLAY"}
                                    </button>
                                    <input type="range" min={0} max={Math.max(timeline.length - 1, 0)} value={timeIndex} onChange={(e) => setTimeIndex(Number(e.target.value))} className="w-full accent-accent" />
                                    <span className="text-[11px] text-text-dim font-mono">{formattedTime}</span>
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
                                  <span className={`w-2.5 h-2.5 rounded-full ${showHeatmap ? "bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)]" : "bg-gray-400"}`} />
                                  HEATMAP
                                </button>

                                {/* Sidebar Panel */}
                                <div className={`absolute top-0 right-0 h-full w-80 bg-surface/95 backdrop-blur-sm border-l border-border z-[1001] transition-transform duration-300 ${selectedVesselDetails ? "translate-x-0" : "translate-x-full"}`}>
                                  {selectedVesselDetails && (
                                    <div className="p-5 h-full overflow-y-auto">
                                      <div className="flex justify-between mb-5">
                                        <h3 className="text-lg font-bold">{selectedVesselDetails.name}</h3>
                                        <button onClick={() => setSelectedVesselImo(null)} className="text-text-dim hover:text-text text-xl">&times;</button>
                                      </div>
                                      <div className="space-y-4">
                                        <div>
                                          <span className="text-[11px] uppercase text-text-dim tracking-wide">Status</span>
                                          <div className="mt-1">
                                            <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${BADGE_STYLES[selectedVesselDetails.status.replace(/\s/g, "-").toLowerCase()] || ""}`}>
                                              {selectedVesselDetails.status}
                                            </span>
                                          </div>
                                        </div>
                                        <div>
                                          <span className="text-[11px] uppercase text-text-dim tracking-wide">IMO Number</span>
                                          <p className="font-mono text-sm mt-1">{selectedVesselDetails.imo}</p>
                                        </div>
                                        <div>
                                          <span className="text-[11px] uppercase text-text-dim tracking-wide">Position</span>
                                          <p className="font-mono text-sm mt-1">
                                            {selectedVesselDetails.point ? `${selectedVesselDetails.point.lat.toFixed(3)}°N, ${selectedVesselDetails.point.lon.toFixed(3)}°E` : "N/A"}
                                          </p>
                                        </div>

                                        <div className="pt-2 relative">
                                          <div className="flex justify-between items-center mb-2">
                                            <span className="text-[11px] uppercase text-text-dim tracking-wide">Find route from</span>
                                            {distance && <span className="text-[11px] font-mono text-accent animate-pulse">{distance} NM</span>}
                                          </div>
                                          <div className="relative">
                                            <input type="text" value={inputValue} onChange={(e) => { setInputValue(e.target.value); setShowDropdown(true); }} onFocus={() => setShowDropdown(true)} placeholder="Search origin port..." className="w-full h-11 pl-5 pr-12 text-sm bg-bg border border-border rounded-full outline-none" />
                                          </div>
                                          {showDropdown && (
                                            <div className="absolute left-0 right-0 mt-2 bg-surface border border-border rounded-xl shadow-2xl z-[1002] max-h-48 overflow-y-auto">
                                              {userGPS && (
                                                <button className="w-full px-4 py-3 text-left text-sm hover:bg-white/5 text-accent border-b border-border" onClick={() => { setStartPoint(userGPS); setInputValue("Your Location"); setShowDropdown(false); }}>
                                                  ⊕ Use current location
                                                </button>
                                              )}
                                              {PORT_SUGGESTIONS.filter(p => inputValue === "" || inputValue === "Your Location" || p.name.toLowerCase().includes(inputValue.toLowerCase())).map(port => (
                                                <button key={port.name} className="w-full px-4 py-3 text-left text-sm hover:bg-white/5 flex flex-col border-b border-border/30 last:border-0" onClick={() => { setStartPoint(port); setInputValue(port.name); setShowDropdown(false); }}>
                                                  <span className="font-medium">{port.name}</span>
                                                  <span className="text-[10px] text-text-dim font-mono">{port.lat}, {port.lon}</span>
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
                              <h2 className="text-[15px] font-semibold text-text mb-3">Flagged Vessels</h2>
                              <div className="overflow-y-auto max-h-[300px] border border-border rounded-lg">
                                <table className="w-full border-collapse text-[13px]">
                                  <thead className="sticky top-0 bg-surface z-10">
                                    <tr>{["Vessel", "IMO", "Flag", "Type", "Status", "Lat", "Lon"].map((h) => (<th key={h} className="text-left px-3 py-2 font-semibold text-[11px] uppercase tracking-wide text-text-dim border-b border-border">{h}</th>))}</tr>
                                  </thead>
                                  <tbody>
                                    {vesselsAtTime.map((v) => (
                                      <tr key={v.imo} className={`hover:bg-white/[0.02] cursor-pointer ${selectedVesselImo === v.imo ? "bg-white/[0.04]" : ""}`} onClick={() => setSelectedVesselImo(v.imo)}>
                                        <td className="px-3 py-2.5 border-b border-border">{v.name}</td>
                                        <td className="px-3 py-2.5 border-b border-border font-mono">{v.imo}</td>
                                        <td className="px-3 py-2.5 border-b border-border">{v.flag}</td>
                                        <td className="px-3 py-2.5 border-b border-border">{v.type}</td>
                                        <td className="px-3 py-2.5 border-b border-border">
                                          <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${BADGE_STYLES[v.status.replace(/\s/g, "-").toLowerCase()] || ""}`}>{v.status}</span>
                                        </td>
                                        <td className="px-3 py-2.5 border-b border-border font-mono">{v.point.lat.toFixed(3)}</td>
                                        <td className="px-3 py-2.5 border-b border-border font-mono">{v.point.lon.toFixed(3)}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </section>
                          </main>
                        </div>
                      );
                    }

                    export default App;