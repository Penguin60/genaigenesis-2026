import { useState, useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const MOCK_VESSELS = [
  // BAD VESSELS
  { name: "LUNA STAR", imo: "9284731", flag: "CM", type: "Crude Oil Tanker", status: "AIS Gap", lat: "26.32", lon: "56.21" },
  { name: "CASPIAN WAVE", imo: "9456012", flag: "PA", type: "Chemical Tanker", status: "Rendezvous", lat: "25.90", lon: "56.85" },
  { name: "NORTHERN DRIFT", imo: "9387120", flag: "MH", type: "LPG Tanker", status: "Route Deviation", lat: "25.45", lon: "57.20" },
  { name: "BLACK MARLIN", imo: "9612045", flag: "PA", type: "Crude Oil Tanker", status: "Dark Activity", lat: "26.05", lon: "56.55" },
  { name: "RED HORIZON", imo: "9601934", flag: "KH", type: "General Cargo", status: "Flag Hopping", lat: "26.10", lon: "55.80" },

  // GOOD VESSELS
  { name: "EVER GLORY", imo: "9812345", flag: "SG", type: "Container Ship", status: "Compliant", lat: "25.20", lon: "55.50" },
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

const BADGE_STYLES = {
  // good status
  "compliant": "bg-[#16a34a]/20 text-[#16a34a]",

  // bad status (shades of red, depending on what kind of activity is going on)
  "ais-gap": "bg-[#991b1b]/20 text-[#ef4444]", 
  "dark-activity": "bg-[#7f1d1d]/30 text-[#dc2626]",
  "rendezvous": "bg-[#450a0a]/30 text-[#f87171]",
  "route-deviation": "bg-[#991b1b]/20 text-[#ef4444]",
  "flag-hopping": "bg-[#7f1d1d]/30 text-[#dc2626]",
};

function App() {
  const [selectedVessel, setSelectedVessel] = useState(null);
  const [userGPS, setUserGPS] = useState(null);
  const [startPoint, setStartPoint] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [distance, setDistance] = useState(null);

  // Get User GPS location
  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setUserGPS({ lat: pos.coords.latitude, lon: pos.coords.longitude });
      });
    }
  }, []);

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
    if (selectedVessel && startPoint) {
      setDistance(calculateDistance(startPoint, { lat: parseFloat(selectedVessel.lat), lon: parseFloat(selectedVessel.lon) }));
    } else {
      setDistance(null);
    }
  }, [selectedVessel, startPoint]);

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
              <TileLayer 
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" 
                attribution='&copy; OpenStreetMap'
              />
              {startPoint && selectedVessel && (
                <Polyline 
                  positions={[[startPoint.lat, startPoint.lon], [parseFloat(selectedVessel.lat), parseFloat(selectedVessel.lon)]]}
                  pathOptions={{ color: '#5b8def', weight: 2, dashArray: '5, 10' }}
                />
              )}
              {MOCK_VESSELS.map((v) => (
                <CircleMarker
                  key={v.imo}
                  center={[parseFloat(v.lat), parseFloat(v.lon)]}
                  radius={5}
                  pathOptions={{
                    color: selectedVessel?.imo === v.imo ? "#fff" : "#dc2626",
                    fillColor: "#ef4444",
                    fillOpacity: 0.9,
                    weight: selectedVessel?.imo === v.imo ? 3 : 2,
                  }}
                  eventHandlers={{ click: () => setSelectedVessel(v) }}
                />
              ))}
              
            </MapContainer>

            {/* Sidebar Panel */}
            <div className={`absolute top-0 right-0 h-full w-80 bg-surface/95 backdrop-blur-sm border-l border-border z-[1001] transition-transform duration-300 ${selectedVessel ? "translate-x-0" : "translate-x-full"}`}>
              {selectedVessel && (
                <div className="p-5 h-full overflow-y-auto">
                  <div className="flex justify-between mb-5">
                    <h3 className="text-lg font-bold">{selectedVessel.name}</h3>
                    <button onClick={() => setSelectedVessel(null)} className="text-text-dim hover:text-text text-xl">&times;</button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <span className="text-[11px] uppercase text-text-dim tracking-wide">Status</span>
                      <div className="mt-1">
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${BADGE_STYLES[selectedVessel.status.replace(/\s/g, "-").toLowerCase()] || ""}`}>
                          {selectedVessel.status}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="text-[11px] uppercase text-text-dim tracking-wide">IMO Number</span>
                      <p className="font-mono text-sm mt-1">{selectedVessel.imo}</p>
                    </div>
                    <div>
                      <span className="text-[11px] uppercase text-text-dim tracking-wide">Flag State</span>
                      <p className="text-sm mt-1">{selectedVessel.flag}</p>
                    </div>
                    <div>
                      <span className="text-[11px] uppercase text-text-dim tracking-wide">Vessel Type</span>
                      <p className="text-sm mt-1">{selectedVessel.type}</p>
                    </div>
                    <div>
                      <span className="text-[11px] uppercase text-text-dim tracking-wide">Position</span>
                      <p className="font-mono text-sm mt-1">{selectedVessel.lat}°N, {selectedVessel.lon}°E</p>
                    </div>

                    {/* Search / Route Origin */}
                    <div className="pt-2 relative">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-[11px] uppercase text-text-dim tracking-wide">Find route from</span>
                        {distance && <span className="text-[11px] font-mono text-accent animate-pulse">{distance} NM</span>}
                      </div>
                      <div className="relative">
                        <input
                          type="text"
                          value={inputValue}
                          onChange={(e) => { setInputValue(e.target.value); setShowDropdown(true); }}
                          onFocus={() => setShowDropdown(true)}
                          placeholder="Search origin port..."
                          className="w-full h-11 pl-5 pr-12 text-sm bg-bg border border-border rounded-full text-text placeholder:text-text-dim focus:ring-1 focus:ring-accent outline-none"
                        />
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center">
                          {inputValue ? (
                            <button onClick={() => { setInputValue(""); setStartPoint(null); setShowDropdown(false); }} className="p-2 text-text-dim hover:text-text">&times;</button>
                          ) : (
                            <div className="p-2 text-accent">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                            </div>
                          )}
                        </div>
                      </div>

                      {showDropdown && (
                        <div className="absolute left-0 right-0 mt-2 bg-surface border border-border rounded-xl shadow-2xl z-[1002] overflow-hidden max-h-48 overflow-y-auto">
                          {userGPS && (
                            <button 
                              className="w-full px-4 py-3 text-left text-sm hover:bg-white/5 flex items-center gap-3 border-b border-border text-accent"
                              onClick={() => { setStartPoint(userGPS); setInputValue("Your Location"); setShowDropdown(false); }}
                            >
                              ⊕ Use current location
                            </button>
                          )}
                          {PORT_SUGGESTIONS.filter(p => p.name.toLowerCase().includes(inputValue.toLowerCase())).map(port => (
                            <button 
                              key={port.name}
                              className="w-full px-4 py-3 text-left text-sm hover:bg-white/5 flex flex-col border-b border-border/30 last:border-0"
                              onClick={() => { setStartPoint(port); setInputValue(port.name); setShowDropdown(false); }}
                            >
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

        {/* Flagged Vessels Table - Integrated with Scrolling and Lat/Lon */}
        <section className="px-10 pb-8 flex flex-col min-h-0 flex-1">
          <h2 className="text-[15px] font-semibold text-text mb-3 shrink-0">Flagged Vessels</h2>
          <div className="overflow-y-auto max-h-[300px] border border-border rounded-lg">
            <table className="w-full border-collapse text-[13px]">
              <thead className="sticky top-0 bg-surface z-10">
                <tr>
                  {["Vessel", "IMO", "Flag", "Type", "Status", "Lat", "Lon"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 font-semibold text-[11px] uppercase tracking-wide text-text-dim border-b border-border">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MOCK_VESSELS.map((v) => {
                  const badgeKey = v.status.replace(/\s/g, "-").toLowerCase();
                  return (
                    <tr
                      key={v.imo}
                      className={`hover:bg-white/[0.02] cursor-pointer ${selectedVessel?.imo === v.imo ? "bg-white/[0.04]" : ""}`}
                      onClick={() => setSelectedVessel(selectedVessel?.imo === v.imo ? null : v)}
                    >
                      <td className="px-3 py-2.5 border-b border-border whitespace-nowrap">{v.name}</td>
                      <td className="px-3 py-2.5 border-b border-border whitespace-nowrap font-mono text-xs">{v.imo}</td>
                      <td className="px-3 py-2.5 border-b border-border whitespace-nowrap">{v.flag}</td>
                      <td className="px-3 py-2.5 border-b border-border whitespace-nowrap">{v.type}</td>
                      <td className="px-3 py-2.5 border-b border-border whitespace-nowrap">
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${BADGE_STYLES[badgeKey] || ""}`}>
                          {v.status}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 border-b border-border whitespace-nowrap font-mono text-xs">{v.lat}</td>
                      <td className="px-3 py-2.5 border-b border-border whitespace-nowrap font-mono text-xs">{v.lon}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;