import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getCurrentProfile,
  login as apiLogin,
  registerCustomer as apiRegister,
} from "../services/authService";
import {
  clearStoredAuth,
  getStoredRole,
  getStoredToken,
  getStoredUser,
  persistAuthTokenAndRole,
  persistAuthUser,
} from "../services/authStorage";
import { AuthContext } from "./authContextObject";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getStoredToken());
  const [role, setRole] = useState(() => getStoredRole());
  const [user, setUser] = useState(() => getStoredUser());
  const [profileLoading, setProfileLoading] = useState(() =>
    Boolean(getStoredToken()),
  );
  const [sessionExpired, setSessionExpired] = useState(false);

  const clearSession = useCallback(() => {
    clearStoredAuth();
    setToken("");
    setRole("");
    setUser(null);
  }, []);

  const refreshProfile = useCallback(
    async (explicitToken = "") => {
      const activeToken = explicitToken || getStoredToken();
      if (!activeToken) {
        setProfileLoading(false);
        return null;
      }
      try {
        setProfileLoading(true);
        const profile = await getCurrentProfile(activeToken);
        persistAuthUser(profile);
        setUser(profile);
        setRole(profile.role || "");
        return profile;
      } catch (error) {
        if (error.response?.status === 401) {
          clearSession();
        }
        return null;
      } finally {
        setProfileLoading(false);
      }
    },
    [clearSession],
  );

  useEffect(() => {
    if (!token) {
      return;
    }
    let active = true;
    const verifyTokenProfile = async () => {
      try {
        const profile = await getCurrentProfile(token);
        if (!active) {
          return;
        }
        persistAuthUser(profile);
        setUser(profile);
        setRole(profile.role || "");
      } catch (error) {
        if (active && error.response?.status === 401) {
          clearSession();
        }
      } finally {
        if (active) {
          setProfileLoading(false);
        }
      }
    };
    verifyTokenProfile();
    return () => {
      active = false;
    };
  }, [token, clearSession]);

  useEffect(() => {
    const onExpired = () => {
      setSessionExpired(true);
    };
    window.addEventListener("auth:session-expired", onExpired);
    return () => window.removeEventListener("auth:session-expired", onExpired);
  }, []);

  const loginUser = useCallback(async (username, password) => {
    const data = await apiLogin(username, password);
    persistAuthTokenAndRole(data.access_token, data.role);
    const profile = await getCurrentProfile(data.access_token);
    persistAuthUser(profile);
    setSessionExpired(false);
    setUser(profile);
    setRole(profile.role || data.role);
    setToken(data.access_token);
    return { ...data, profile };
  }, []);

  const registerUser = useCallback(async (payload) => {
    const data = await apiRegister(payload);
    persistAuthTokenAndRole(data.access_token, data.role);
    const profile = await getCurrentProfile(data.access_token);
    persistAuthUser(profile);
    setSessionExpired(false);
    setUser(profile);
    setRole(profile.role || data.role);
    setToken(data.access_token);
    return { ...data, profile };
  }, []);

  const syncLegacyLogin = useCallback(async () => {
    const storedToken = getStoredToken();
    const storedRole = getStoredRole();
    setSessionExpired(false);
    setToken(storedToken);
    setRole(storedRole);
    if (storedToken) {
      await refreshProfile(storedToken);
    }
  }, [refreshProfile]);

  const logoutUser = useCallback(() => {
    clearSession();
    setSessionExpired(false);
  }, [clearSession]);

  const dismissSessionExpired = useCallback(() => {
    clearSession();
    setSessionExpired(false);
  }, [clearSession]);

  const isExecutive = Boolean(token) && role === "support";

  const value = useMemo(
    () => ({
      token,
      role,
      user,
      loading: profileLoading,
      profileLoading,
      isAuthenticated: Boolean(token),
      isExecutive,
      isSupportExecutive: isExecutive,
      isCustomer: Boolean(token) && role === "customer",
      sessionExpired,
      loginUser,
      registerUser,
      logoutUser,
      refreshProfile,
      syncLegacyLogin,
      dismissSessionExpired,
      clearSessionExpired: dismissSessionExpired,
    }),
    [
      token,
      role,
      user,
      profileLoading,
      isExecutive,
      sessionExpired,
      loginUser,
      registerUser,
      logoutUser,
      refreshProfile,
      syncLegacyLogin,
      dismissSessionExpired,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
