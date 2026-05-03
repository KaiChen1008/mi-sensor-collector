import axios from "axios";

const api = axios.create({ baseURL: "/api" });

// Sensors
export const getSensors = () => api.get("/sensors").then((r) => r.data);
export const createSensor = (data) => api.post("/sensors", data).then((r) => r.data);
export const updateSensor = (id, data) => api.patch(`/sensors/${id}`, data).then((r) => r.data);
export const deleteSensor = (id) => api.delete(`/sensors/${id}`);
export const scanBLE = () => api.get("/sensors/scan").then((r) => r.data);
export const triggerRead = (id) => api.post(`/sensors/${id}/read`).then((r) => r.data);

// Readings
export const getLatestReadings = () => api.get("/readings/latest").then((r) => r.data);
export const getReadings = (params) => api.get("/readings", { params }).then((r) => r.data);

// Alert rules
export const getAlertRules = () => api.get("/alert-rules").then((r) => r.data);
export const createAlertRule = (data) => api.post("/alert-rules", data).then((r) => r.data);
export const updateAlertRule = (id, data) => api.patch(`/alert-rules/${id}`, data).then((r) => r.data);
export const deleteAlertRule = (id) => api.delete(`/alert-rules/${id}`);
export const testAlertRule = (id) => api.post(`/alert-rules/${id}/test`).then((r) => r.data);

// Alert logs
export const getAlertLogs = (params) => api.get("/alert-rules/logs", { params }).then((r) => r.data);
