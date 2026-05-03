import { useState, useEffect } from "react";
import { getSensors } from "../api/client";

const METRICS = ["temperature", "humidity", "battery"];
const OPERATORS = [">", "<", ">=", "<=", "==", "!="];
const CHANNELS = ["email", "telegram", "line"];

const CHANNEL_HELP = {
  email: "Recipient email address",
  telegram: "Telegram chat ID (e.g. 123456789)",
  line: "LINE Notify access token",
};

const DEFAULT_FORM = {
  name: "",
  sensor_id: "",
  metric: "temperature",
  operator: ">",
  threshold: "",
  channel: "email",
  channel_target: "",
  cooldown_minutes: 30,
};

export default function AlertRuleForm({ initial, onSubmit, onCancel, loading }) {
  const [form, setForm] = useState(initial || DEFAULT_FORM);
  const [sensors, setSensors] = useState([]);

  useEffect(() => {
    getSensors().then(setSensors).catch(() => {});
  }, []);

  const set = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      sensor_id: form.sensor_id ? Number(form.sensor_id) : null,
      threshold: parseFloat(form.threshold),
      cooldown_minutes: parseInt(form.cooldown_minutes, 10),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <label className="label">Rule name</label>
          <input
            className="input"
            required
            value={form.name}
            onChange={set("name")}
            placeholder="e.g. High humidity alert"
          />
        </div>

        <div>
          <label className="label">Sensor (leave empty for all)</label>
          <select className="input" value={form.sensor_id} onChange={set("sensor_id")}>
            <option value="">All sensors</option>
            {sensors.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} {s.location ? `(${s.location})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">Metric</label>
          <select className="input" value={form.metric} onChange={set("metric")}>
            {METRICS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">Operator</label>
          <select className="input" value={form.operator} onChange={set("operator")}>
            {OPERATORS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">
            Threshold
            {form.metric === "temperature" && " (°C)"}
            {form.metric === "humidity" && " (%)"}
            {form.metric === "battery" && " (%)"}
          </label>
          <input
            className="input"
            type="number"
            step="0.1"
            required
            value={form.threshold}
            onChange={set("threshold")}
            placeholder="e.g. 60"
          />
        </div>

        <div>
          <label className="label">Notification channel</label>
          <select className="input" value={form.channel} onChange={set("channel")}>
            {CHANNELS.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <label className="label">{CHANNEL_HELP[form.channel]}</label>
          <input
            className="input"
            required
            value={form.channel_target}
            onChange={set("channel_target")}
            placeholder={CHANNEL_HELP[form.channel]}
          />
        </div>

        <div>
          <label className="label">Cooldown (minutes)</label>
          <input
            className="input"
            type="number"
            min="1"
            required
            value={form.cooldown_minutes}
            onChange={set("cooldown_minutes")}
          />
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Saving…" : "Save rule"}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
