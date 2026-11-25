export const FALLBACK_PRODUCT_IMAGE = "/product-images/fallback-product.svg";

export function formatINR(amount) {
  const numeric = Number(amount || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: numeric % 1 === 0 ? 0 : 2,
  }).format(numeric);
}

export function formatDateTime(isoString) {
  if (!isoString) {
    return "—";
  }
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatShortDate(isoString) {
  if (!isoString) {
    return "—";
  }
  const date = new Date(
    isoString.length === 10 ? `${isoString}T00:00:00` : isoString,
  );
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }
  return new Intl.DateTimeFormat("en-IN", {
    month: "short",
    day: "numeric",
  }).format(date);
}

export function handleProductImageError(event) {
  const img = event.currentTarget;
  if (img.dataset.fallbackApplied === "true") {
    return;
  }
  img.dataset.fallbackApplied = "true";
  img.src = FALLBACK_PRODUCT_IMAGE;
}

export function formatPaymentMethodLabel(method) {
  switch ((method || "").toUpperCase()) {
    case "MOCK_CARD":
      return "Mock Card (POC)";
    case "MOCK_UPI":
      return "Mock UPI (POC)";
    case "MOCK_COD":
      return "Cash on Delivery (POC)";
    default:
      return method || "Mock Payment (POC)";
  }
}
