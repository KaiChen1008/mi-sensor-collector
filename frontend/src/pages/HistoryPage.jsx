import { useEffect, useState } from "react";
import { getSensors, getReadings } from "../api/client";
import SensorChart from "../components/SensorChart";

const RANGES = [
  { label: "Last 2 h", hours: 2 },
  { label: "Last 12 h", hours: 12 },
  { label: "Last 24 h", hours: 24 },
  { label: "Last 7 d", hours: 24 * 7 },
];

export default function HistoryPage() {
  const [sensors, setSensors] = useState([]);
  const [selected, setSelected] = useState(null);
  const [range, setRange] = useState(RANGES[1]);
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getSensors().then((s) => {
      setSensors(s);
      if (s.length) setSelected(s[0]);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    const start = new Date(Date.now() - range.hours * 3600 * 1000).toISOString();
    setLoading(true);
    getReadings({ sensor_id: selected.id, start, limit: 500 })
      .then(setReadings)
      .finally(() => setLoading(false));
  }, [selected, range]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">History</h1>
        <p className="text-sm text-gray-500">Sensor readings over time</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="flex gap-2">
          {sensors.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelected(s)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                selected?.id === s.id
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-200 hover:border-blue-300"
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>

        <div className="flex gap-2 ml-auto">
          {RANGES.map((r) => (
            <button
              key={r.label}
              onClick={() => setRange(r)}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                range.label === r.label
                  ? "bg-gray-800 text-white border-gray-800"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {selected ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="font-semibold text-gray-700 mb-4">
            {selected.name}
            {selected.location && (
              <span className="text-gray-400 font-normal ml-2">· {selected.location}</span>
            )}
            <span className="text-gray-400 font-normal ml-2">· {range.label}</span>
          </h2>
          {loading ? (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              Loading…
            </div>
          ) : (
            <SensorChart readings={readings} />
          )}
          <div className="mt-4 grid grid-cols-3 gap-4 text-center text-sm">
            {readings.length > 0 && (
              <>
                <Stat
                  label="Avg Temp"
                  value={avg(readings, "temperature").toFixed(1) + "°C"}
                />
                <Stat
                  label="Avg Humidity"
                  value={avg(readings, "humidity").toFixed(1) + "%"}
                />
                <Stat label="Readings" value={readings.length} />
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center text-gray-400 text-sm">
          No sensors available. Add a sensor first.
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-lg font-semibold text-gray-800">{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

function avg(readings, key) {
  const vals = readings.map((r) => r[key]).filter((v) => v != null);
  if (!vals.length) return 0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}
