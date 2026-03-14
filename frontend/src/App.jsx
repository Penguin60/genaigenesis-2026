                    import { useEffect, useMemo, useState } from "react";
                    import { MapContainer, TileLayer, CircleMarker, Polyline } from "react-leaflet";
                    import "leaflet/dist/leaflet.css";

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

                    function generateTrack(vessel) {
                      const seed = seedFromId(vessel.imo);
                      const baseLat = Number.parseFloat(vessel.lat);
                      const baseLon = Number.parseFloat(vessel.lon);
                      const latDirection = seed % 2 === 0 ? 1 : -1;
                      const lonDirection = seed % 3 === 0 ? -1 : 1;
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