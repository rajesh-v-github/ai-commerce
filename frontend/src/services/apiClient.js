import axios from "axios";
import { getStoredToken } from "./authStorage";

function setHeaderValue(headers, name, value) {
  if (headers && typeof headers.set === "function") {
    headers.set(name, value);
  } else if (headers) {
    headers[name] = value;
  }
}

function readHeaderValue(headers, name) {
  if (!headers) {
    return "";
  }
  if (typeof headers.get === "function") {
    return headers.get(name) || "";
  }
  return headers[name] || headers[name.toLowerCase()] || "";
}

const apiClient = axios.create();

apiClient.interceptors.request.use((config) => {
  config.headers = config.headers || {};

  const existingAuth = readHeaderValue(config.headers, "Authorization");
  const explicitBearer = existingAuth.startsWith("Bearer ")
    ? existingAuth.slice(7).trim()
    : "";
  const rawToken = explicitBearer || getStoredToken();

  if (rawToken && rawToken !== "null" && rawToken !== "undefined") {
    setHeaderValue(config.headers, "Authorization", `Bearer ${rawToken}`);
    // Proxy-resilient companion header in case an edge preview proxy strips Authorization
    setHeaderValue(config.headers, "X-Auth-Token", rawToken);
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const hadAuthHeader = Boolean(
      readHeaderValue(error.config?.headers, "Authorization") ||
        readHeaderValue(error.config?.headers, "X-Auth-Token"),
    );
    if (error.response?.status === 401 && hadAuthHeader) {
      window.dispatchEvent(new Event("auth:session-expired"));
    }

    return Promise.reject(error);
  },
);

export default apiClient;
