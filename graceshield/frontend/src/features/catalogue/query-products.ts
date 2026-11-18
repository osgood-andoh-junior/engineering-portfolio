import type { CatalogueQuery, Product, ProductPage } from './types';
export const PAGE_SIZE = 8;
export function queryProducts(source: Product[], query: CatalogueQuery): ProductPage {
  const needle = (query.q ?? '').trim().toLowerCase().slice(0, 120);
  const selected = source.filter(
    (p) =>
      (!needle || `${p.name} ${p.description}`.toLowerCase().includes(needle)) &&
      (!query.category || p.categoryId === query.category) &&
      (query.min === undefined || p.price.amount >= query.min) &&
      (query.max === undefined || p.price.amount <= query.max),
  );
  if (query.sort === 'price-asc') selected.sort((a, b) => a.price.amount - b.price.amount);
  if (query.sort === 'price-desc') selected.sort((a, b) => b.price.amount - a.price.amount);
  if (query.sort === 'name') selected.sort((a, b) => a.name.localeCompare(b.name));
  const pages = Math.max(1, Math.ceil(selected.length / PAGE_SIZE));
  const page = Math.min(pages, Math.max(1, Math.floor(query.page || 1)));
  return {
    products: selected.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    total: selected.length,
    page,
    pages,
  };
}
