import apiClient from "./apiClient";

const API_URL = "/api/orders/";

export const getOrders = async (token) => {
  const response = await apiClient.get(API_URL, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};

export const getOrderDetails = async (orderNumber, token) => {
  const response = await apiClient.get(
    `${API_URL}number/${encodeURIComponent(orderNumber)}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  return response.data;
};
