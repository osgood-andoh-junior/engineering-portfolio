'use client';
import { createContext, useContext, useEffect, useCallback, useState, type ReactNode } from 'react';
import { z } from 'zod';
import { api, errorMessage } from '@/lib/api';
import { productSchema } from '@/features/catalogue/api-schemas';
import type { Product } from '@/features/catalogue/types';
type CartContext = {
  items: {
    productId: string;
    variantId: string;
    quantity: number;
    product: Product;
    valid: boolean;
    lineTotal: number;
  }[];
  ready: boolean;
  message: string;
  subtotal: number;
  count: number;
  error: string;
  busy: boolean;
  refresh: () => Promise<void>;
  clear: () => void;
  add: (id: string, quantity: number, variantId?: string) => void;
  update: (id: string, quantity: number) => void;
  remove: (id: string) => void;
};
const Context = createContext<CartContext | null>(null);
export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<z.infer<typeof cartSchema>>({
    items: [],
    subtotal: 0,
    count: 0,
    currency: 'GHS',
  });
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      await api('/auth/session', z.object({ csrf: z.string() }));
      setCart(await api('/cart', cartSchema));
      setError('');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setReady(true);
      setBusy(false);
    }
  }, []);
  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) void refresh();
    });
    const changed = () => void refresh();
    window.addEventListener('graceshield-auth', changed);
    return () => {
      active = false;
      window.removeEventListener('graceshield-auth', changed);
    };
  }, [refresh]);
  const mutate = async (path: string, method: string, body?: object) => {
    if (busy) return;
    setBusy(true);
    try {
      setCart(
        await api(path, cartSchema, { method, body: body ? JSON.stringify(body) : undefined }),
      );
      setError('');
      setMessage('Your bag has been updated. Prices are calculated by GraceShield.');
    } catch (e) {
      setError(errorMessage(e));
      setMessage(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const add = (_id: string, quantity: number, variantId?: string) => {
    if (!variantId) {
      setMessage('Select an available product variant.');
      return;
    }
    void mutate('/cart/items', 'POST', { variant_id: variantId, quantity });
  };
  const update = (id: string, quantity: number) => {
    const item = cart.items.find((i) => i.variantId === id || i.productId === id);
    if (item)
      void mutate(`/cart/items/${item.variantId}`, 'PUT', { variant_id: item.variantId, quantity });
  };
  const remove = (id: string) => {
    const item = cart.items.find((i) => i.variantId === id || i.productId === id);
    if (item) void mutate(`/cart/items/${item.variantId}`, 'DELETE');
  };
  return (
    <Context.Provider
      value={{
        items: cart.items,
        ready,
        message,
        subtotal: cart.subtotal,
        count: cart.count,
        error,
        busy,
        refresh,
        clear: () => {
          void mutate('/cart', 'DELETE');
        },
        add,
        update,
        remove,
      }}
    >
      {children}
      <div className="cart-announcement" role="status" aria-live="polite">
        {message}
      </div>
    </Context.Provider>
  );
}
export const cartSchema = z.object({
  items: z.array(
    z.object({
      productId: z.string().uuid(),
      variantId: z.string().uuid(),
      quantity: z.number().int().min(1).max(20),
      product: productSchema,
      valid: z.boolean(),
      lineTotal: z.number().int().nonnegative(),
    }),
  ),
  subtotal: z.number().int().nonnegative(),
  count: z.number().int().nonnegative(),
  currency: z.literal('GHS'),
});
export function useCart() {
  const value = useContext(Context);
  if (!value) throw new Error('CartProvider is required');
  return value;
}
