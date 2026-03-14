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

function App() {
  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">VANGUARD</span>
        <span className="subtitle">Shadow Fleet Monitor</span>
      </header>

      <main className="content">
        <section className="map-section">
          <div className="map-placeholder">Map View</div>
        </section>

        <section className="table-section">
          <h2>Flagged Vessels</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Vessel</th>
                  <th>IMO</th>
                  <th>Flag</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Lat</th>
                  <th>Lon</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_VESSELS.map((v) => (
                  <tr key={v.imo}>
                    <td>{v.name}</td>
                    <td className="mono">{v.imo}</td>
                    <td>{v.flag}</td>
                    <td>{v.type}</td>
                    <td><span className={`badge ${v.status.replace(/\s/g, "-").toLowerCase()}`}>{v.status}</span></td>
                    <td className="mono">{v.lat}</td>
                    <td className="mono">{v.lon}</td>
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
