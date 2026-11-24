import axios from "axios";
import apiClient from "./apiClient";

export const getStoreProducts = async (params = {}) => {
  const response = await axios.get("/api/store/products", { params });
  return response.data;
};

export const getStoreCategories = async () => {
  const response = await axios.get("/api/store/categories");
  return response.data;
};

export const getStoreProductDetail = async (productId) => {
  const response = await axios.get(`/api/store/products/${productId}`);
  return response.data;
};

export const validateStoreCart = async (items) => {
  const response = await axios.post("/api/store/cart/validate", { items });
  return response.data;
};

export const getSavedCart = async () => {
  const response = await apiClient.get("/api/store/cart");
  return response.data;
};

export const syncSavedCart = async (items) => {
  const response = await apiClient.put("/api/store/cart", { items });
  return response.data;
};

export const clearSavedCart = async () => {
  const response = await apiClient.delete("/api/store/cart");
  return response.data;
};

export const submitStoreCheckout = async (payload) => {
  const response = await apiClient.post("/api/store/checkout", payload);
  return response.data;
};

export const getOrderConfirmation = async (orderNumber, ref = "") => {
  const response = await apiClient.get(
    `/api/store/orders/confirmation/${encodeURIComponent(orderNumber)}`,
    {
      params: ref ? { ref } : {},
    },
  );
  return response.data;
};

export const getMyOrders = async () => {
  const response = await apiClient.get("/api/orders/my");
  return response.data;
};

export const getMyOrderDetail = async (orderNumber) => {
  const response = await apiClient.get(
    `/api/orders/my/${encodeURIComponent(orderNumber)}`,
  );
  return response.data;
};
