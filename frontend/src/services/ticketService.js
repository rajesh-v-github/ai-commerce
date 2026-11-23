import apiClient from "./apiClient";

const API_URL = "/api/tickets/";

export const getTickets = async (token) => {
  const response = await apiClient.get(API_URL, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};

export const createTicket = async (ticket, token) => {
  const response = await apiClient.post(API_URL, ticket, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
