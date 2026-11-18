import { describe, it, expect } from 'vitest';
import { categories, products } from '@/data/mock/catalogue';
import { queryProducts } from './query-products';
import { parseQuery } from './query';
import { formatMoney } from '@/lib/formatting';
describe('catalogue', () => {
  it('has exactly eleven categories and unique stable product IDs/slugs', () => {
    expect(categories).toHaveLength(11);
    expect(new Set(products.map((p) => p.id)).size).toBe(products.length);
    expect(new Set(products.map((p) => p.slug)).size).toBe(products.length);
    for (const p of products) {
      expect(categories.some((c) => c.id === p.categoryId)).toBe(true);
      expect(Number.isInteger(p.price.amount)).toBe(true);
    }
  });
  it('searches case-insensitively and composes category/price filters', () => {
    const page = queryProducts(products, {
      q: 'NOTEBOOK',
      category: 'paper',
      min: 4000,
      max: 5000,
    });
    expect(page.products.map((p) => p.id)).toEqual(['p01']);
  });
  it('sorts by price in both directions and by name', () => {
    expect(queryProducts(products, { sort: 'price-asc' }).products[0].id).toBe('p18');
    expect(queryProducts(products, { sort: 'price-desc' }).products[0].id).toBe('p03');
    expect(queryProducts(products, { sort: 'name' }).products[0].name).toBe('A4 Copy Paper');
  });
  it('paginates deterministically and clamps invalid pages', () => {
    expect(queryProducts(products, { page: 2 }).products[0].id).toBe('p09');
    expect(queryProducts(products, { page: 99 }).page).toBe(3);
    expect(queryProducts(products, { page: -4 }).page).toBe(1);
    expect(queryProducts(products, { q: 'nothing-matches' })).toMatchObject({
      total: 0,
      pages: 1,
      page: 1,
    });
  });
  it('parses untrusted URL values and converts decimal prices to pesewas', () => {
    expect(
      parseQuery({
        category: 'invalid',
        q: ['a', 'b'],
        min: '12.35',
        max: 'NaN',
        page: 'Infinity',
      }),
    ).toMatchObject({ category: undefined, q: '', min: 1235, max: undefined, page: 1 });
    expect(parseQuery({ min: '-5', max: '1e9' })).toMatchObject({ min: undefined, max: undefined });
  });
  it('formats Ghana Cedi precisely for display', () => {
    expect(formatMoney(12345).replace(/\s/g, ' ')).toBe('GHS 123.45');
    expect(formatMoney(0)).toContain('0.00');
  });
});
