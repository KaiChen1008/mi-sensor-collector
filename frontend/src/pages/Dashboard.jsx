import { useEffect, useState, useCallback } from "react";
import { getLatestReadings, triggerRead } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";
import SensorCard from "../components/SensorCard";

export default function Dashboard() {
  const [sensors, setSensors] = useState([]);
  const [wsStatus, setWsStatus] = useState("connecting");
  const [refreshing, setRefreshing] = useState(new Set());

  const load = useCallback(async () => {
    try {
      const data = await getLatestReadings();
      setSensors(data);
    } catch {
      // ignore on initial load failure
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === "reading") {
      setWsStatus("live");
      setSensors((prev) => {
        const idx = prev.findIndex((s) => s.sensor_id === msg.sensor_id);
        const updated = {
          sensor_id: msg.sensor_id,
          sensor_name: msg.sensor_name,
          sensor_location: msg.sensor_location,
          temperature: msg.temperature,
          humidity: msg.humidity,
          battery: msg.battery,
          timestamp: msg.timestamp,
        };
        if (idx === -1) return [...prev, updated];
        const next = [...prev];
        next[idx] = updated;
        return next;
      });
    }
  }, []);

  useWebSocket(handleWsMessage);

  const handleRefresh = useCallback(async (sensorId) => {
    setRefreshing((prev) => new Set([...prev, sensorId]));
    try {
      await triggerRead(sensorId);
    } catch {
      // ignore — data arrives via WebSocket when ready
    } finally {
      setRefreshing((prev) => {
        const next = new Set(prev);
        next.delete(sensorId);
        return next;
      });
    }
  }, []);

  const handleRefreshAll = useCallback(async () => {
    await Promise.all(sensors.map((s) => handleRefresh(s.sensor_id)));
  }, [sensors, handleRefresh]);

  const isAnyRefreshing = refreshing.size > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Live sensor overview</p>
        </div>
        <div className="flex items-center gap-3">
          {sensors.length > 0 && (
            <button
              onClick={handleRefreshAll}
              disabled={isAnyRefreshing}
              className="btn-secondary flex items-center gap-1.5 text-sm disabled:opacity-50"
            >
              <svg
                className={`w-4 h-4 ${isAnyRefreshing ? "animate-spin" : ""}`}
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
              Fetch All
            </button>
          )}
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              wsStatus === "live"
                ? "bg-green-50 text-green-700"
                : "bg-yellow-50 text-yellow-700"
            }`}
          >
            {wsStatus === "live" ? "Live" : "Connecting…"}
          </span>
        </div>
      </div>

      {sensors.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500 text-sm">
            No sensors registered yet. Go to{" "}
            <a href="/sensors" className="text-blue-600 underline">
              Sensors
            </a>{" "}
            to add one.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sensors.map((s) => (
            <SensorCard
              key={s.sensor_id}
              sensor={s}
              onRefresh={handleRefresh}
              isRefreshing={refreshing.has(s.sensor_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
