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

export default function SensorCard({ sensor }) {
  const { sensor_name, sensor_location, temperature, humidity, battery, timestamp } = sensor;

  const timeAgo = timestamp
    ? formatDistanceToNow(new Date(timestamp), { addSuffix: true })
    : "never";

  const isStale = timestamp
    ? Date.now() - new Date(timestamp).getTime() > 5 * 60 * 1000
    : true;

  return (
    <div className={`bg-white rounded-xl shadow-sm border p-5 flex flex-col gap-4 ${isStale ? "border-yellow-200" : "border-gray-200"}`}>
      <div className="flex justify-between items-start">
        <div>
          <h2 className="font-semibold text-gray-800">{sensor_name}</h2>
          {sensor_location && (
            <p className="text-sm text-gray-500">{sensor_location}</p>
          )}
        </div>
        <BatteryBadge value={battery} />
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
