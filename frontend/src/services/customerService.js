import apiClient from "./apiClient";

const API_URL = "/api/customer/";

export const getCustomers = async (token) => {
  const response = await apiClient.get(API_URL, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
