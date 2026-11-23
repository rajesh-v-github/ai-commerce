import apiClient from "./apiClient";

const API_URL = "/api/copilot/insights";
const ASSISTANT_API_URL = "/api/copilot/assistant";

export const getDashboardData = async (ticketNumber, token) => {
  console.time("Dashboard API");
  const response = await apiClient.post(
    API_URL,
    {
      ticket_number: ticketNumber.trim().toUpperCase(),
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
  console.timeEnd("Dashboard API");
  return response.data;
};

export const runAssistantFeature = async (request, token) => {
  const response = await apiClient.post(ASSISTANT_API_URL, request, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
