import { useEffect, useState } from "react";
import {
  getAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  testAlertRule,
  getAlertLogs,
} from "../api/client";
import AlertRuleList from "../components/AlertRuleList";
import AlertRuleForm from "../components/AlertRuleForm";
import { formatDistanceToNow } from "date-fns";

export default function AlertRulesPage() {
  const [rules, setRules] = useState([]);
  const [logs, setLogs] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editRule, setEditRule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const load = async () => {
    const [r, l] = await Promise.all([getAlertRules(), getAlertLogs({ limit: 20 })]);
    setRules(r);
    setLogs(l);
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async (data) => {
    setLoading(true);
    try {
      if (editRule) {
        await updateAlertRule(editRule.id, data);
        showToast("Rule updated");
      } else {
        await createAlertRule(data);
        showToast("Rule created");
      }
      setShowForm(false);
      setEditRule(null);
      load();
    } catch (e) {
      showToast(e.response?.data?.detail || "Save failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (rule) => {
    setEditRule(rule);
    setShowForm(true);
  };

  const handleDelete = async (rule) => {
    if (!confirm(`Delete rule "${rule.name}"?`)) return;
    await deleteAlertRule(rule.id);
    load();
  };

  const handleTest = async (rule) => {
    try {
      await testAlertRule(rule.id);
      showToast("Test notification sent");
    } catch (e) {
      showToast(e.response?.data?.detail || "Test failed", "error");
    }
  };

  const handleToggle = async (rule) => {
    await updateAlertRule(rule.id, { is_active: !rule.is_active });
    load();
  };

  const cancel = () => {
    setShowForm(false);
    setEditRule(null);
  };

  return (
    <div className="space-y-8">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-2.5 rounded-lg shadow-lg text-sm text-white ${
            toast.type === "error" ? "bg-red-500" : "bg-green-500"
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alert Rules</h1>
          <p className="text-sm text-gray-500">
            Get notified when sensor values cross thresholds
          </p>
        </div>
        {!showForm && (
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            + New Rule
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4">
            {editRule ? "Edit Rule" : "New Alert Rule"}
          </h2>
          <AlertRuleForm
            initial={editRule}
            onSubmit={handleSubmit}
            onCancel={cancel}
            loading={loading}
          />
        </div>
      )}

      <AlertRuleList
        rules={rules}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onTest={handleTest}
        onToggle={handleToggle}
      />

      {logs.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Recent Alert Logs</h2>
          <div className="space-y-2">
            {logs.map((log) => (
              <div
                key={log.id}
                className={`rounded-lg border px-4 py-2.5 text-sm flex flex-wrap gap-x-4 gap-y-1 items-center ${
                  log.notification_sent
                    ? "bg-green-50 border-green-200"
                    : "bg-red-50 border-red-200"
                }`}
              >
                <span className="font-medium">
                  {log.notification_sent ? "Sent" : "Failed"}
                </span>
                <span className="text-gray-600">Rule #{log.rule_id}</span>
                <span className="text-gray-600">Sensor #{log.sensor_id}</span>
                <span className="text-gray-600">Value: {log.metric_value}</span>
                <span className="text-gray-400 ml-auto text-xs">
                  {formatDistanceToNow(new Date(log.triggered_at), { addSuffix: true })}
                </span>
                {log.error_message && (
                  <span className="w-full text-red-600 text-xs">{log.error_message}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
