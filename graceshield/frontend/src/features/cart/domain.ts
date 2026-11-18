import { z } from 'zod';
import type { Product } from '@/features/catalogue/types';
export const MAX_QUANTITY = 20;
export const CART_KEY = 'graceshield.cart.v1';
export type CartItem = { productId: string; quantity: number };
export type Cart = CartItem[];
export type CartAction =
  | { type: 'add'; productId: string; quantity: number }
  | { type: 'quantity'; productId: string; quantity: number }
  | { type: 'remove'; productId: string }
  | { type: 'restore'; items: Cart };
const quantity = z.number().int().min(1).max(MAX_QUANTITY);
const storageSchema = z.object({
  version: z.literal(1),
  items: z.array(z.object({ productId: z.string().min(1).max(80), quantity })).max(100),
});
export function restoreCart(
  raw: string | null,
  catalogue: Product[],
): { items: Cart; recovered: boolean } {
  if (!raw) return { items: [], recovered: false };
  try {
    const parsed = storageSchema.parse(JSON.parse(raw));
    const items: Cart = [];
    for (const item of parsed.items) {
      if (!catalogue.some((p) => p.id === item.productId && p.availability === 'available'))
        continue;
      const previous = items.find((i) => i.productId === item.productId);
      if (previous) previous.quantity = Math.min(MAX_QUANTITY, previous.quantity + item.quantity);
      else items.push({ ...item });
    }
    return { items, recovered: JSON.stringify(items) !== JSON.stringify(parsed.items) };
  } catch {
    return { items: [], recovered: true };
  }
}
export function cartReducer(state: Cart, action: CartAction): Cart {
  if (action.type === 'restore') return action.items;
  if (action.type === 'remove') return state.filter((i) => i.productId !== action.productId);
  if (!quantity.safeParse(action.quantity).success) return state;
  const found = state.find((i) => i.productId === action.productId);
  if (action.type === 'quantity')
    return state.map((i) =>
      i.productId === action.productId ? { ...i, quantity: action.quantity } : i,
    );
  return found
    ? state.map((i) =>
        i.productId === action.productId
          ? { ...i, quantity: Math.min(MAX_QUANTITY, i.quantity + action.quantity) }
          : i,
      )
    : [...state, { productId: action.productId, quantity: action.quantity }];
}
export function cartSubtotal(cart: Cart, catalogue: Product[]): number {
  return cart.reduce(
    (sum, item) =>
      sum + (catalogue.find((p) => p.id === item.productId)?.price.amount ?? 0) * item.quantity,
    0,
  );
}
