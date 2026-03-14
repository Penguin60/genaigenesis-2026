import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
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
  return (
    <div className="flex flex-col min-h-screen">
      <header className="flex items-center gap-3.5 px-6 py-8 h-14 bg-surface border-b border-border">
        <span className="font-bold text-4xl tracking-[3px] text-accent">VANGUARD</span>
        <span className="text-xl text-text-dim">Shadow Fleet Monitor</span>
      </header>

      <main className="flex-1 flex flex-col overflow-hidden">
        <section className="px-10 py-6 shrink-0">
          <div className="w-full h-130 rounded-lg overflow-hidden border border-border">
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
                  pathOptions={{ color: "#dc2626", fillColor: "#ef4444", fillOpacity: 0.9, weight: 2 }}
                >
                  <Popup>
                    <strong>{v.name}</strong><br />
                    IMO: {v.imo}<br />
                    {v.type} — {v.status}
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
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
                    <tr key={v.imo} className="hover:bg-white/[0.02]">
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
