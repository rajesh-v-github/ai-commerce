import axios from "axios";
import apiClient from "./apiClient";

const LOGIN_URL = "/api/auth/login";
const REGISTER_URL = "/api/auth/register";
const ME_URL = "/api/auth/me";

export const login = async (username, password) => {
  const response = await axios.post(LOGIN_URL, {
    username,
    password,
  });

  return response.data;
};

export const registerCustomer = async (payload) => {
  const response = await axios.post(REGISTER_URL, payload);
  return response.data;
};

export const getCurrentProfile = async (explicitToken = "") => {
  const headers = explicitToken
    ? {
        Authorization: `Bearer ${explicitToken}`,
        "X-Auth-Token": explicitToken,
      }
    : undefined;
  const response = await apiClient.get(ME_URL, headers ? { headers } : undefined);
  return response.data;
};

export const updateCurrentProfile = async (payload) => {
  const response = await apiClient.put(ME_URL, payload);
  return response.data;
};
