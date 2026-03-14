import { useState } from "react";
import { MapContainer, TileLayer, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const MOCK_VESSELS = [
  { name: "LUNA STAR", imo: "9284731", flag: "CM", type: "Crude Oil Tanker", status: "AIS Gap", lat: "26.32", lon: "56.21" },
  { name: "ORIENT PEARL", imo: "9310284", flag: "TG", type: "Bulk Carrier", status: "Flag Change", lat: "26.58", lon: "56.48" },
  { name: "CASPIAN WAVE", imo: "9456012", flag: "PA", type: "Chemical Tanker", status: "Rendezvous", lat: "25.90", lon: "56.85" },
  { name: "ATLAS VOYAGER", imo: "9523841", flag: "LR", type: "Oil Tanker", status: "AIS Gap", lat: "26.75", lon: "56.10" },
  { name: "NORTHERN DRIFT", imo: "9387120", flag: "MH", type: "LPG Tanker", status: "Route Deviation", lat: "25.45", lon: "57.20" },
  { name: "RED HORIZON", imo: "9601934", flag: "KH", type: "General Cargo", status: "Flag Change", lat: "26.10", lon: "55.80" },
  { name: "SILVANA", imo: "9478561", flag: "GN", type: "Crude Oil Tanker", status: "AIS Gap", lat: "26.50", lon: "56.70" },
  { name: "ZENITH FORTUNE", imo: "9534209", flag: "PA", type: "Bulk Carrier", status: "Rendezvous", lat: "25.70", lon: "57.05" },
  { name: "BLACK MARLIN", imo: "9612045", flag: "PA", type: "Crude Oil Tanker", status: "AIS Gap", lat: "26.05", lon: "56.55" },
  { name: "GULF SPIRIT", imo: "9345678", flag: "MH", type: "Oil Tanker", status: "Flag Change", lat: "26.88", lon: "56.32" },
  { name: "IRON PHOENIX", imo: "9498321", flag: "LR", type: "Bulk Carrier", status: "Route Deviation", lat: "25.62", lon: "57.40" },
  { name: "JADE EMPRESS", imo: "9567012", flag: "TG", type: "Chemical Tanker", status: "Rendezvous", lat: "26.42", lon: "55.95" },
  { name: "KARACHI SUN", imo: "9623410", flag: "CM", type: "LPG Tanker", status: "AIS Gap", lat: "25.38", lon: "56.78" },
  { name: "MERIDIAN STAR", imo: "9701234", flag: "GN", type: "General Cargo", status: "Flag Change", lat: "26.68", lon: "56.90" },
  { name: "NIGHT HERON", imo: "9415678", flag: "KH", type: "Crude Oil Tanker", status: "Route Deviation", lat: "25.85", lon: "57.15" },
  { name: "OMAN BREEZE", imo: "9389012", flag: "PA", type: "Oil Tanker", status: "AIS Gap", lat: "26.20", lon: "56.05" },
  { name: "PACIFIC DAWN", imo: "9543210", flag: "MH", type: "Chemical Tanker", status: "Rendezvous", lat: "25.55", lon: "56.42" },
  { name: "ROYAL CREST", imo: "9678901", flag: "LR", type: "Bulk Carrier", status: "Flag Change", lat: "26.95", lon: "56.60" },
  { name: "STORM PETREL", imo: "9456789", flag: "TG", type: "LPG Tanker", status: "Route Deviation", lat: "25.72", lon: "57.30" },
  { name: "TITAN GLORY", imo: "9512345", flag: "CM", type: "Crude Oil Tanker", status: "AIS Gap", lat: "26.15", lon: "56.38" },
];

const BADGE_STYLES = {
  "ais-gap": "bg-badge-red-bg text-badge-red",
  "flag-change": "bg-badge-amber-bg text-badge-amber",
  "rendezvous": "bg-badge-purple-bg text-badge-purple",
  "route-deviation": "bg-badge-blue-bg text-badge-blue",
};

function App() {
  const [selectedVessel, setSelectedVessel] = useState(null);

  return (
    <div className="flex flex-col min-h-screen">
      <header className="flex items-center gap-3.5 px-6 py-8 h-14 bg-surface border-b border-border">
        <span className="font-bold text-4xl tracking-[3px] text-accent">VANGUARD</span>
        <span className="text-xl text-text-dim">Shadow Fleet Monitor</span>
      </header>

      <main className="flex-1 flex flex-col overflow-hidden">
        <section className="px-10 py-6 shrink-0">
          <div className="w-full h-130 rounded-lg overflow-hidden border border-border relative">
             {/* Map here, later add functionality to do the separate from destination */}
            <MapContainer center={[26.2, 56.5]} zoom={8} className="h-full w-full">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
              />
              {MOCK_VESSELS.map((v) => (
                <CircleMarker
                  key={v.imo}
                  center={[parseFloat(v.lat), parseFloat(v.lon)]}
                  radius={8}
                  pathOptions={{
                    color: selectedVessel?.imo === v.imo ? "#fff" : "#dc2626",
                    fillColor: "#ef4444",
                    fillOpacity: 0.9,
                    weight: selectedVessel?.imo === v.imo ? 3 : 2,
                  }}
                  eventHandlers={{
                    click: () => setSelectedVessel(selectedVessel?.imo === v.imo ? null : v),
                  }}
                />
              ))}
            </MapContainer>

            {/* Side panel */}
            <div
              className={`absolute top-0 right-0 h-full w-80 bg-surface/95 backdrop-blur-sm border-l border-border z-[1000] transition-transform duration-300 ease-in-out ${
                selectedVessel ? "translate-x-0" : "translate-x-full"
              }`}
            >
              {selectedVessel && (
                <div className="p-5 h-full overflow-y-auto">
                  <div className="flex items-center justify-between mb-5">
                    <h3 className="text-lg font-bold text-text">{selectedVessel.name}</h3>
                    <button
                      onClick={() => setSelectedVessel(null)}
                      className="text-text-dim hover:text-text text-xl leading-none cursor-pointer"
                    >
                      &times;
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <span className="text-[11px] uppercase tracking-wide text-text-dim">Status</span>
                      <div className="mt-1">
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${BADGE_STYLES[selectedVessel.status.replace(/\s/g, "-").toLowerCase()] || ""}`}>
                          {selectedVessel.status}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[11px] uppercase tracking-wide text-text-dim">IMO Number</span>
                      <p className="text-text font-mono text-sm mt-1">{selectedVessel.imo}</p>
                    </div>

                    <div>
                      <span className="text-[11px] uppercase tracking-wide text-text-dim">Flag State</span>
                      <p className="text-text text-sm mt-1">{selectedVessel.flag}</p>
                    </div>

                    <div>
                      <span className="text-[11px] uppercase tracking-wide text-text-dim">Vessel Type</span>
                      <p className="text-text text-sm mt-1">{selectedVessel.type}</p>
                    </div>

                    <div>
                      <span className="text-[11px] uppercase tracking-wide text-text-dim">Position</span>
                      <p className="text-text font-mono text-sm mt-1">
                        {selectedVessel.lat}°N, {selectedVessel.lon}°E
                      </p>
                    </div>
                    {/* add for search directions to */}
                    <div className="pt-2">
                      {/* Label is just text-dim to match the other labels */}
                      <span className="text-[11px] uppercase tracking-wide text-text-dim">Find route</span>

                      <div className="relative mt-2">
                        {/* The Input field, styled like a search bar, dark theme */}
                        <input
                          type="text"
                          placeholder="Enter destination port or coordinates..."
                          className="w-full h-11 pl-5 pr-12 text-sm bg-bg border border-border rounded-full text-text placeholder:text-text-dim focus:ring-1 focus:ring-accent focus:border-accent transition-all duration-200"
                        />

                        {/* The Search/Direction icon, positioned inside the right of the bar */}
                        <button className="absolute right-1.5 top-1/2 -translate-y-1/2 h-8 w-8 flex items-center justify-center rounded-full text-accent hover:bg-white/[0.04]">
                          {/* This is a simple SVG for a Search icon, matching your CSS theme */}
                          <svg 
                            viewBox="0 0 24 24" 
                            className="h-5 w-5" 
                            fill="none" 
                            stroke="currentColor" 
                            strokeWidth="2.5"
                          >
                            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    {/*  */}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

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
