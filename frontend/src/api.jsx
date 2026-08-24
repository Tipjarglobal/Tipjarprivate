import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const api = axios.create({
  baseURL: BACKEND_URL ? `${BACKEND_URL}/api` : "/api",
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const apiErr = (error) => {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || "Request failed";
};

export const fileUrl = (filePath) => {
  if (!filePath) return "";
  if (filePath.startsWith("http")) return filePath;
  return `${BACKEND_URL ? BACKEND_URL : ""}${filePath.startsWith("/") ? "" : "/"}${filePath}`;
};

export default api;
