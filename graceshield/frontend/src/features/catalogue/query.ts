import type { CatalogueQuery } from './types';
export type SearchParams = Record<string, string | string[] | undefined>;
export function first(value: string | string[] | undefined) {
  return typeof value === 'string' ? value : '';
}
export function parseQuery(params: SearchParams, fixedCategory?: string): CatalogueQuery {
  const minor = (value: string) =>
    /^\d{1,6}(\.\d{1,2})?$/.test(value) ? Math.round(Number(value) * 100) : undefined;
  const category = fixedCategory ?? first(params.category);
  return {
    q: first(params.q).slice(0, 120),
    category: /^[0-9a-f-]{36}$/i.test(category) ? category : undefined,
    min: minor(first(params.min)),
    max: minor(first(params.max)),
    sort: first(params.sort),
    page: /^\d{1,6}$/.test(first(params.page)) ? Number(first(params.page)) : 1,
  };
}
export function pageHref(params: SearchParams, page: number, pathname: string) {
  const next = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (typeof value === 'string') next.set(key, value);
  });
  next.set('page', String(page));
  return `${pathname}?${next}`;
}
