import { formatDistanceToNow } from "date-fns";

const CHANNEL_ICONS = { email: "✉️", telegram: "✈️", line: "💬" };

export default function AlertRuleList({ rules, onEdit, onDelete, onTest, onToggle }) {
  if (!rules.length) {
    return (
      <p className="text-gray-400 text-sm text-center py-8">
        No alert rules yet. Create one to get started.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {rules.map((rule) => (
        <div
          key={rule.id}
          className={`bg-white rounded-xl border shadow-sm p-4 flex flex-col sm:flex-row sm:items-center gap-3 ${
            rule.is_active ? "border-gray-200" : "border-gray-100 opacity-60"
          }`}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-gray-800">{rule.name}</span>
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {rule.metric} {rule.operator} {rule.threshold}
                {rule.metric === "temperature" ? "°C" : "%"}
              </span>
              <span className="text-xs text-gray-500">
                {CHANNEL_ICONS[rule.channel]} {rule.channel}
              </span>
            </div>
            <div className="text-xs text-gray-400 mt-1 flex gap-3 flex-wrap">
              <span>Cooldown: {rule.cooldown_minutes} min</span>
              {rule.sensor_id ? (
                <span>Sensor #{rule.sensor_id}</span>
              ) : (
                <span>All sensors</span>
              )}
              {rule.last_triggered_at && (
                <span>
                  Last fired:{" "}
                  {formatDistanceToNow(new Date(rule.last_triggered_at), { addSuffix: true })}
                </span>
              )}
            </div>
          </div>

          <div className="flex gap-2 shrink-0">
            <button
              onClick={() => onToggle(rule)}
              className={`btn-xs ${rule.is_active ? "btn-secondary" : "btn-primary"}`}
            >
              {rule.is_active ? "Disable" : "Enable"}
            </button>
            <button onClick={() => onTest(rule)} className="btn-xs btn-secondary">
              Test
            </button>
            <button onClick={() => onEdit(rule)} className="btn-xs btn-secondary">
              Edit
            </button>
            <button onClick={() => onDelete(rule)} className="btn-xs btn-danger">
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
