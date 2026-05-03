import { useEffect, useState } from "react";
import {
  getSensors,
  createSensor,
  updateSensor,
  deleteSensor,
  scanBLE,
  triggerRead,
} from "../api/client";

function SensorFormModal({ initial, onSave, onClose }) {
  const [form, setForm] = useState(
    initial || { name: "", ble_address: "", location: "" }
  );
  const set = (f) => (e) => setForm((p) => ({ ...p, [f]: e.target.value }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="text-lg font-semibold">
          {initial ? "Edit Sensor" : "Add Sensor"}
        </h2>
        <div className="space-y-3">
          <div>
            <label className="label">Name</label>
            <input className="input" value={form.name} onChange={set("name")} required />
          </div>
          <div>
            <label className="label">BLE Address</label>
            <input
              className="input font-mono"
              value={form.ble_address}
              onChange={set("ble_address")}
              placeholder="AA:BB:CC:DD:EE:FF or UUID"
              required
            />
          </div>
          <div>
            <label className="label">Location (optional)</label>
            <input
              className="input"
              value={form.location}
              onChange={set("location")}
              placeholder="e.g. Bedroom"
            />
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button className="btn-primary" onClick={() => onSave(form)}>
            Save
          </button>
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SensorsPage() {
  const [sensors, setSensors] = useState([]);
  const [discovered, setDiscovered] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [editTarget, setEditTarget] = useState(null); // null | {} | sensor
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = async () => {
    setSensors(await getSensors());
  };

  useEffect(() => { load(); }, []);

  const handleScan = async () => {
    setScanning(true);
    setDiscovered([]);
    try {
      const devices = await scanBLE();
      setDiscovered(devices);
    } catch (e) {
      showToast(e.response?.data?.detail || "Scan failed", "error");
    } finally {
      setScanning(false);
    }
  };

  const handleSave = async (form) => {
    try {
      if (editTarget?.id) {
        await updateSensor(editTarget.id, {
          name: form.name,
          location: form.location,
        });
        showToast("Sensor updated");
      } else {
        await createSensor(form);
        showToast("Sensor added");
      }
      setEditTarget(null);
      load();
    } catch (e) {
      showToast(e.response?.data?.detail || "Save failed", "error");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this sensor and all its readings?")) return;
    await deleteSensor(id);
    load();
  };

  const handleTriggerRead = async (id) => {
    try {
      await triggerRead(id);
      showToast("Read triggered");
    } catch (e) {
      showToast(e.response?.data?.detail || "Failed", "error");
    }
  };

  return (
    <div className="space-y-6">
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
          <h1 className="text-2xl font-bold text-gray-900">Sensors</h1>
          <p className="text-sm text-gray-500">Manage your Mi sensor devices</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={handleScan} disabled={scanning}>
            {scanning ? "Scanning…" : "Scan BLE"}
          </button>
          <button className="btn-primary" onClick={() => setEditTarget({})}>
            + Add Sensor
          </button>
        </div>
      </div>

      {discovered.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm font-medium text-blue-800 mb-3">
            Discovered devices — click to pre-fill address:
          </p>
          <div className="space-y-2">
            {discovered.map((d) => (
              <div
                key={d.address}
                className="flex items-center justify-between bg-white rounded-lg border border-blue-100 px-4 py-2.5 cursor-pointer hover:bg-blue-50"
                onClick={() =>
                  setEditTarget({
                    name: d.name || "LYWSD03MMC",
                    ble_address: d.address,
                    location: "",
                  })
                }
              >
                <div>
                  <span className="font-mono text-sm">{d.address}</span>
                  {d.name && (
                    <span className="text-xs text-gray-500 ml-2">{d.name}</span>
                  )}
                </div>
                {d.rssi != null && (
                  <span className="text-xs text-gray-400">RSSI {d.rssi}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {sensors.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center text-gray-400 text-sm">
          No sensors added yet. Scan for BLE devices or add one manually.
        </div>
      ) : (
        <div className="space-y-3">
          {sensors.map((s) => (
            <div
              key={s.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col sm:flex-row sm:items-center gap-3"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">{s.name}</span>
                  {!s.is_active && (
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                      Inactive
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-0.5 space-x-3">
                  <span className="font-mono">{s.ble_address}</span>
                  {s.location && <span>{s.location}</span>}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => handleTriggerRead(s.id)}
                  className="btn-xs btn-secondary"
                >
                  Read now
                </button>
                <button
                  onClick={() => setEditTarget(s)}
                  className="btn-xs btn-secondary"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(s.id)}
                  className="btn-xs btn-danger"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {editTarget !== null && (
        <SensorFormModal
          initial={editTarget.id ? editTarget : editTarget.ble_address ? editTarget : null}
          onSave={handleSave}
          onClose={() => setEditTarget(null)}
        />
      )}
    </div>
  );
}
