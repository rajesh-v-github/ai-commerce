// In-memory + safe localStorage session store so authentication works both in
// standard browser tabs and inside strict cross-origin preview iframes.
const memoryStore = {
  token: "",
  role: "",
  user: null,
};

function safeGetItem(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore third-party iframe storage restrictions; memoryStore remains active
  }
}

function safeRemoveItem(key) {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Ignore storage restriction errors
  }
}

export function getStoredToken() {
  if (memoryStore.token) {
    return memoryStore.token;
  }
  const fromStorage = safeGetItem("token") || "";
  memoryStore.token = fromStorage;
  return fromStorage;
}

export function getStoredRole() {
  if (memoryStore.role) {
    return memoryStore.role;
  }
  const fromStorage = safeGetItem("role") || "";
  memoryStore.role = fromStorage;
  return fromStorage;
}

export function getStoredUser() {
  if (memoryStore.user) {
    return memoryStore.user;
  }
  const raw = safeGetItem("sorano_user");
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw);
    memoryStore.user = parsed;
    return parsed;
  } catch {
    return null;
  }
}

export function persistAuthTokenAndRole(token, role) {
  memoryStore.token = token || "";
  memoryStore.role = role || "";
  if (token) {
    safeSetItem("token", token);
  } else {
    safeRemoveItem("token");
  }
  if (role) {
    safeSetItem("role", role);
  } else {
    safeRemoveItem("role");
  }
}

export function persistAuthUser(user) {
  memoryStore.user = user || null;
  if (user) {
    if (user.role) {
      memoryStore.role = user.role;
      safeSetItem("role", user.role);
    }
    safeSetItem("sorano_user", JSON.stringify(user));
  } else {
    safeRemoveItem("sorano_user");
  }
}

export function clearStoredAuth() {
  memoryStore.token = "";
  memoryStore.role = "";
  memoryStore.user = null;
  safeRemoveItem("token");
  safeRemoveItem("role");
  safeRemoveItem("sorano_user");
}
