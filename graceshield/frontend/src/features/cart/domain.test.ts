import { describe, it, expect } from 'vitest';
import { cartReducer, cartSubtotal, restoreCart } from './domain';
import { products } from '@/data/mock/catalogue';
describe('cart domain', () => {
  it('adds immutably, merges quantities and caps at twenty', () => {
    const state = [{ productId: 'p01', quantity: 18 }];
    const next = cartReducer(state, { type: 'add', productId: 'p01', quantity: 5 });
    expect(next).toEqual([{ productId: 'p01', quantity: 20 }]);
    expect(state[0].quantity).toBe(18);
  });
  it.each([0, -1, 21, 1.5, NaN, Infinity])('rejects invalid quantity %s', (quantity) => {
    const state = [{ productId: 'p01', quantity: 2 }];
    expect(cartReducer(state, { type: 'quantity', productId: 'p01', quantity })).toBe(state);
  });
  it('updates and removes individual lines', () => {
    const state = [
      { productId: 'p01', quantity: 2 },
      { productId: 'p02', quantity: 1 },
    ];
    expect(
      cartReducer(state, { type: 'quantity', productId: 'p01', quantity: 3 })[0].quantity,
    ).toBe(3);
    expect(cartReducer(state, { type: 'remove', productId: 'p01' })).toEqual([state[1]]);
  });
  it('calculates integer pesewa subtotals', () => {
    expect(
      cartSubtotal(
        [
          { productId: 'p01', quantity: 3 },
          { productId: 'p02', quantity: 2 },
        ],
        products,
      ),
    ).toBe(17100);
    expect(cartSubtotal([{ productId: 'missing', quantity: 2 }], products)).toBe(0);
  });
  it.each([
    'bad json',
    '{}',
    '{"version":2,"items":[]}',
    '{"version":1,"items":[{"productId":"p01","quantity":-2}]}',
  ])('recovers corrupt data safely', (raw) => {
    expect(restoreCart(raw, products)).toEqual({ items: [], recovered: true });
  });
  it('removes missing and unavailable products, merges duplicate IDs', () => {
    const restored = restoreCart(
      JSON.stringify({
        version: 1,
        items: [
          { productId: 'p01', quantity: 13 },
          { productId: 'p01', quantity: 10 },
          { productId: 'missing', quantity: 1 },
          { productId: 'p17', quantity: 1 },
        ],
      }),
      products,
    );
    expect(restored).toEqual({ items: [{ productId: 'p01', quantity: 20 }], recovered: true });
  });
  it('handles absent and valid storage', () => {
    expect(restoreCart(null, products)).toEqual({ items: [], recovered: false });
    expect(
      restoreCart('{"version":1,"items":[{"productId":"p02","quantity":2}]}', products).recovered,
    ).toBe(false);
  });
});
