import apiClient from "./apiClient";

const API_URL = "/api/orders/customer/username";

export const getCustomerOrders = async (username, token) => {
  const response = await apiClient.get(`${API_URL}/${username}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
