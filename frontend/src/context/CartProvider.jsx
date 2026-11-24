import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  clearSavedCart,
  getSavedCart,
  syncSavedCart,
  validateStoreCart,
} from "../services/storeService";
import { useAuth } from "./authContextObject";
import { CartContext } from "./cartContextObject";

const CART_STORAGE_KEY = "soranogear_cart_v1";

function loadStoredCart() {
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (item) =>
        item &&
        Number.isInteger(Number(item.product_id)) &&
        Number(item.quantity) > 0,
    );
  } catch {
    return [];
  }
}

export function CartProvider({ children }) {
  const { isAuthenticated, token } = useAuth();
  const [items, setItems] = useState(() => loadStoredCart());
  const [cartSummary, setCartSummary] = useState(null);
  const [validating, setValidating] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const mergedTokenRef = useRef("");

  useEffect(() => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    } catch {
      // Ignore storage quota issues
    }
  }, [items]);

  const refreshValidation = useCallback(async (targetItems) => {
    if (!targetItems || targetItems.length === 0) {
      setCartSummary({
        items: [],
        item_count: 0,
        subtotal_amount: 0,
        shipping_amount: 0,
        included_gst_amount: 0,
        total_amount: 0,
        free_shipping_threshold: 1999,
        amount_to_free_shipping: 1999,
        warnings: [],
        valid_for_checkout: false,
      });
      return null;
    }

    try {
      setValidating(true);
      const payload = targetItems.map((i) => ({
        product_id: Number(i.product_id),
        quantity: Number(i.quantity),
      }));
      const summary = await validateStoreCart(payload);
      setCartSummary(summary);
      return summary;
    } catch (error) {
      console.error("Cart validation failed", error);
      return null;
    } finally {
      setValidating(false);
    }
  }, []);

  // Merge local guest cart with server-saved cart upon login
  useEffect(() => {
    if (!isAuthenticated || !token || mergedTokenRef.current === token) {
      return;
    }
    mergedTokenRef.current = token;

    let active = true;
    const hydrateAuthenticatedCart = async () => {
      try {
        const serverCart = await getSavedCart();
        if (!active) {
          return;
        }
        const localItems = loadStoredCart();
        const combinedMap = new Map();

        for (const serverLine of serverCart.items || []) {
          if (serverLine.quantity > 0) {
            combinedMap.set(serverLine.product_id, {
              product_id: serverLine.product_id,
              quantity: serverLine.quantity,
              product: serverLine.product,
            });
          }
        }
        for (const localLine of localItems) {
          const existing = combinedMap.get(localLine.product_id);
          combinedMap.set(localLine.product_id, {
            product_id: localLine.product_id,
            quantity: existing
              ? Math.max(existing.quantity, localLine.quantity)
              : localLine.quantity,
            product: localLine.product || existing?.product || null,
          });
        }

        const mergedList = Array.from(combinedMap.values());
        setItems(mergedList);
        if (mergedList.length > 0) {
          const synced = await syncSavedCart(
            mergedList.map((i) => ({
              product_id: i.product_id,
              quantity: i.quantity,
            })),
          );
          if (active) {
            setCartSummary(synced);
          }
        } else if (active) {
          setCartSummary(serverCart);
        }
      } catch (error) {
        console.error("Unable to sync saved cart", error);
      }
    };

    hydrateAuthenticatedCart();
    return () => {
      active = false;
    };
  }, [isAuthenticated, token]);

  useEffect(() => {
    let active = true;
    const validateAsync = async () => {
      if (!items || items.length === 0) {
        await Promise.resolve();
        if (active) {
          setCartSummary({
            items: [],
            item_count: 0,
            subtotal_amount: 0,
            shipping_amount: 0,
            included_gst_amount: 0,
            total_amount: 0,
            free_shipping_threshold: 1999,
            amount_to_free_shipping: 1999,
            warnings: [],
            valid_for_checkout: false,
          });
        }
        return;
      }
      try {
        const payload = items.map((i) => ({
          product_id: Number(i.product_id),
          quantity: Number(i.quantity),
        }));
        const summary = await validateStoreCart(payload);
        if (active) {
          setCartSummary(summary);
        }
      } catch (error) {
        console.error("Cart validation failed", error);
      }
    };
    validateAsync();
    return () => {
      active = false;
    };
  }, [items]);

  const persistServerIfAuthenticated = useCallback(
    async (nextItems) => {
      if (!isAuthenticated) {
        return;
      }
      try {
        const synced = await syncSavedCart(
          nextItems.map((i) => ({
            product_id: Number(i.product_id),
            quantity: Number(i.quantity),
          })),
        );
        setCartSummary(synced);
      } catch (error) {
        console.error("Failed syncing cart to server", error);
      }
    },
    [isAuthenticated],
  );

  const addItem = useCallback(
    (product, quantityToAdd = 1, openDrawerAfter = true) => {
      const availableStock = Number(product.stock ?? 0);
      if (availableStock <= 0) {
        return { added: false, reason: "Out of stock" };
      }
      let capped = false;
      setItems((prev) => {
        const existingIndex = prev.findIndex(
          (i) => Number(i.product_id) === Number(product.id),
        );
        let next;
        if (existingIndex >= 0) {
          const currentQty = Number(prev[existingIndex].quantity);
          const desired = currentQty + Number(quantityToAdd);
          const finalQty = Math.min(desired, availableStock);
          capped = desired > availableStock;
          next = prev.map((line, idx) =>
            idx === existingIndex
              ? { ...line, quantity: finalQty, product }
              : line,
          );
        } else {
          const finalQty = Math.min(Number(quantityToAdd), availableStock);
          capped = Number(quantityToAdd) > availableStock;
          next = [
            ...prev,
            { product_id: product.id, quantity: finalQty, product },
          ];
        }
        persistServerIfAuthenticated(next);
        return next;
      });
      if (openDrawerAfter) {
        setDrawerOpen(true);
      }
      return { added: true, capped };
    },
    [persistServerIfAuthenticated],
  );

  const updateQuantity = useCallback(
    (productId, nextQuantity) => {
      const qty = Number(nextQuantity);
      setItems((prev) => {
        let next;
        if (qty <= 0) {
          next = prev.filter((i) => Number(i.product_id) !== Number(productId));
        } else {
          next = prev.map((i) => {
            if (Number(i.product_id) !== Number(productId)) {
              return i;
            }
            const maxStock = i.product?.stock != null ? Number(i.product.stock) : 999;
            return { ...i, quantity: Math.min(qty, Math.max(1, maxStock)) };
          });
        }
        persistServerIfAuthenticated(next);
        return next;
      });
    },
    [persistServerIfAuthenticated],
  );

  const removeItem = useCallback(
    (productId) => {
      setItems((prev) => {
        const next = prev.filter(
          (i) => Number(i.product_id) !== Number(productId),
        );
        persistServerIfAuthenticated(next);
        return next;
      });
    },
    [persistServerIfAuthenticated],
  );

  const clearCart = useCallback(async () => {
    setItems([]);
    try {
      localStorage.removeItem(CART_STORAGE_KEY);
    } catch {
      // Ignore storage restriction errors
    }
    if (isAuthenticated) {
      try {
        await clearSavedCart();
      } catch {
        // Ignore clear error
      }
    }
  }, [isAuthenticated]);

  const enrichedLines = useMemo(() => {
    if (cartSummary?.items?.length || items.length === 0) {
      return cartSummary?.items || [];
    }
    return items.map((i) => ({
      product_id: i.product_id,
      product: i.product || { id: i.product_id, name: "Loading...", price: 0, stock: i.quantity },
      quantity: i.quantity,
      available_stock: i.product?.stock ?? i.quantity,
      unit_price: Number(i.product?.price || 0),
      line_total: Number(i.product?.price || 0) * i.quantity,
    }));
  }, [cartSummary, items]);

  const itemCount = useMemo(
    () => items.reduce((acc, i) => acc + Number(i.quantity || 0), 0),
    [items],
  );

  const subtotal =
    cartSummary?.subtotal_amount ??
    enrichedLines.reduce((acc, l) => acc + l.line_total, 0);
  const shipping =
    cartSummary?.shipping_amount ?? (subtotal === 0 || subtotal >= 1999 ? 0 : 99);
  const includedGst =
    cartSummary?.included_gst_amount ?? Math.round((subtotal * 0.18) / 1.18);
  const total = cartSummary?.total_amount ?? subtotal + shipping;
  const warnings = useMemo(
    () => cartSummary?.warnings || [],
    [cartSummary],
  );

  const value = useMemo(
    () => ({
      items,
      lines: enrichedLines,
      itemCount,
      subtotal,
      shipping,
      includedGst,
      total,
      freeShippingThreshold: cartSummary?.free_shipping_threshold ?? 1999,
      amountToFreeShipping:
        cartSummary?.amount_to_free_shipping ?? Math.max(0, 1999 - subtotal),
      warnings,
      validating,
      drawerOpen,
      setDrawerOpen,
      addItem,
      updateQuantity,
      removeItem,
      clearCart,
      refreshValidation: () => refreshValidation(items),
    }),
    [
      items,
      enrichedLines,
      itemCount,
      subtotal,
      shipping,
      includedGst,
      total,
      cartSummary,
      warnings,
      validating,
      drawerOpen,
      addItem,
      updateQuantity,
      removeItem,
      clearCart,
      refreshValidation,
    ],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}
