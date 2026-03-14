const MOCK_VESSELS = [
  { name: "LUNA STAR", imo: "9284731", flag: "CM", type: "Crude Oil Tanker", status: "AIS Gap", lat: "33.52", lon: "-118.44" },
  { name: "ORIENT PEARL", imo: "9310284", flag: "TG", type: "Bulk Carrier", status: "Flag Change", lat: "34.01", lon: "-119.12" },
  { name: "CASPIAN WAVE", imo: "9456012", flag: "PA", type: "Chemical Tanker", status: "Rendezvous", lat: "32.87", lon: "-117.89" },
  { name: "ATLAS VOYAGER", imo: "9523841", flag: "LR", type: "Oil Tanker", status: "AIS Gap", lat: "33.91", lon: "-118.67" },
  { name: "NORTHERN DRIFT", imo: "9387120", flag: "MH", type: "LPG Tanker", status: "Route Deviation", lat: "34.22", lon: "-120.01" },
  { name: "RED HORIZON", imo: "9601934", flag: "KH", type: "General Cargo", status: "Flag Change", lat: "33.10", lon: "-117.30" },
  { name: "SILVANA", imo: "9478561", flag: "GN", type: "Crude Oil Tanker", status: "AIS Gap", lat: "32.65", lon: "-118.90" },
  { name: "ZENITH FORTUNE", imo: "9534209", flag: "PA", type: "Bulk Carrier", status: "Rendezvous", lat: "34.55", lon: "-119.78" },
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
      <header className="flex items-center gap-3.5 px-6 h-14 bg-surface border-b border-border">
        <span className="font-bold text-xl tracking-[3px] text-accent">VANGUARD</span>
        <span className="text-sm text-text-dim">Shadow Fleet Monitor</span>
      </header>

      <main className="flex-1 flex flex-col overflow-y-auto">
        <section className="px-10 py-6">
          <div className="w-full h-[480px] bg-surface border border-border rounded-lg flex items-center justify-center text-text-dim text-sm">
            Map View
          </div>
        </section>

        <section className="px-10 pb-8">
          <h2 className="text-[15px] font-semibold text-text mb-3">Flagged Vessels</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px]">
              <thead>
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
