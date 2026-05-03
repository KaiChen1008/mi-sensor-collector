import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";

function formatTick(ts) {
  return format(new Date(ts), "HH:mm");
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="text-gray-500 mb-1">{format(new Date(label), "MM/dd HH:mm")}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value}
          {p.dataKey === "temperature" ? "°C" : "%"}
        </p>
      ))}
    </div>
  );
}

export default function SensorChart({ readings }) {
  if (!readings?.length) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
        No readings yet
      </div>
    );
  }

  const data = [...readings]
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    .map((r) => ({
      timestamp: r.timestamp,
      temperature: parseFloat(r.temperature.toFixed(1)),
      humidity: parseFloat(r.humidity.toFixed(1)),
    }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 12, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatTick}
          tick={{ fontSize: 11 }}
          minTickGap={40}
        />
        <YAxis yAxisId="temp" domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
        <YAxis yAxisId="hum" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} />
        <Tooltip content={<CustomTooltip />} />
        <Legend iconType="circle" iconSize={8} />
        <Line
          yAxisId="temp"
          type="monotone"
          dataKey="temperature"
          name="Temp (°C)"
          stroke="#ef4444"
          dot={false}
          strokeWidth={2}
        />
        <Line
          yAxisId="hum"
          type="monotone"
          dataKey="humidity"
          name="Humidity (%)"
          stroke="#3b82f6"
          dot={false}
          strokeWidth={2}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
