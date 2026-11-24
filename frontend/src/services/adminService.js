import apiClient from "./apiClient";

export const fetchAdminOverview = async (days = 14) => {
  const response = await apiClient.get("/api/admin/dashboard", {
    params: { days },
  });
  return response.data;
};

export const fetchAdminProducts = async (params = {}) => {
  const response = await apiClient.get("/api/admin/products", {
    params: {
      search: params.search,
      category: params.category,
      stock_filter: params.stock_filter || params.stock_status || "all",
      sort: params.sort || params.sort_by || "id_asc",
    },
  });
  return response.data;
};

export const createAdminProduct = async (payload) => {
  const response = await apiClient.post("/api/admin/products", payload);
  return response.data;
};

export const updateAdminProduct = async (productId, payload) => {
  const response = await apiClient.put(
    `/api/admin/products/${productId}`,
    payload,
  );
  return response.data;
};

export const adjustAdminInventory = async (productId, payload) => {
  const response = await apiClient.patch(
    `/api/admin/products/${productId}/inventory`,
    payload,
  );
  return response.data;
};

export const deleteAdminProduct = async (
  productId,
  deactivateOnly = false,
) => {
  const response = await apiClient.delete(`/api/admin/products/${productId}`, {
    params: { deactivate_only: deactivateOnly },
  });
  return response.data;
};

export const uploadAdminProductImage = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post(
    "/api/admin/products/upload-image",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
  return response.data;
};

export const fetchAdminAiStatus = async () => {
  const response = await apiClient.get("/api/admin/ai/status");
  return response.data;
};

export const generateAiProductDescription = async (payload) => {
  const response = await apiClient.post(
    "/api/admin/products/generate-description",
    payload,
  );
  return response.data;
};

export const fetchAdminOrders = async (params = {}) => {
  const response = await apiClient.get("/api/admin/orders", { params });
  return response.data;
};

export const fetchAdminOrderDetail = async (orderId) => {
  const response = await apiClient.get(`/api/admin/orders/${orderId}`);
  return response.data;
};

export const updateAdminOrderStatus = async (orderId, payload) => {
  const response = await apiClient.patch(
    `/api/admin/orders/${orderId}/status`,
    payload,
  );
  return response.data;
};

export const fetchAdminCustomers = async (params = {}) => {
  const response = await apiClient.get("/api/admin/customers", {
    params: {
      search: params.search,
      filter_by: params.filter_by || params.status_filter || "all",
    },
  });
  return response.data;
};

export const createAdminCustomer = async (payload) => {
  const response = await apiClient.post("/api/admin/customers", payload);
  return response.data;
};

export const fetchAdminCustomerDetail = async (customerId) => {
  const response = await apiClient.get(`/api/admin/customers/${customerId}`);
  return response.data;
};

export const updateAdminCustomer = async (customerId, payload) => {
  const response = await apiClient.put(
    `/api/admin/customers/${customerId}`,
    payload,
  );
  return response.data;
};
