import { formatDistanceToNow } from "date-fns";

function Gauge({ value, max, unit, label, color }) {
  const pct = max ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-2xl font-bold" style={{ color }}>
        {value != null ? `${value}${unit}` : "—"}
      </span>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div
          className="h-1.5 rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs text-gray-500">{label}</span>
    </div>
  );
}

function BatteryBadge({ value }) {
  if (value == null) return null;
  const color = value > 50 ? "text-green-600" : value > 20 ? "text-yellow-600" : "text-red-600";
  return (
    <span className={`text-xs font-medium ${color}`}>
      Battery {value}%
    </span>
  );
}

function RefreshIcon({ spinning }) {
  return (
    <svg
      className={`w-4 h-4 ${spinning ? "animate-spin" : ""}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M23 4v6h-6" />
      <path d="M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
    </svg>
  );
}

export default function SensorCard({ sensor, onRefresh, isRefreshing }) {
  const { sensor_id, sensor_name, sensor_location, temperature, humidity, battery, timestamp } =
    sensor;

  const timeAgo = timestamp
    ? formatDistanceToNow(new Date(timestamp), { addSuffix: true })
    : "never";

  const isStale = timestamp
    ? Date.now() - new Date(timestamp).getTime() > 7 * 60 * 1000
    : true;

  return (
    <div
      className={`bg-white rounded-xl shadow-sm border p-5 flex flex-col gap-4 ${isStale ? "border-yellow-200" : "border-gray-200"}`}
    >
      <div className="flex justify-between items-start">
        <div>
          <h2 className="font-semibold text-gray-800">{sensor_name}</h2>
          {sensor_location && <p className="text-sm text-gray-500">{sensor_location}</p>}
        </div>
        <div className="flex items-center gap-2">
          <BatteryBadge value={battery} />
          {onRefresh && (
            <button
              onClick={() => onRefresh(sensor_id)}
              disabled={isRefreshing}
              title="Fetch now"
              className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 disabled:opacity-40 transition-colors"
            >
              <RefreshIcon spinning={isRefreshing} />
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Gauge value={temperature} max={50} unit="°C" label="Temperature" color="#ef4444" />
        <Gauge value={humidity} max={100} unit="%" label="Humidity" color="#3b82f6" />
      </div>

      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>Updated {timeAgo}</span>
        {isStale && <span className="text-yellow-500 font-medium">No recent data</span>}
      </div>
    </div>
  );
}
