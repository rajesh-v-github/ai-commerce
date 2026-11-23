import apiClient from "./apiClient";

const API_URL = "/api/dashboard/overview";

export const getOverview = async (token) => {
  const response = await apiClient.get(API_URL, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};
