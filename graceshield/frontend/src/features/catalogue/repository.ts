import { cache } from 'react';
import { z } from 'zod';
import { serverApi } from '@/lib/server-api';
import { categorySchema, productPageSchema, productSchema } from './api-schemas';
import type { ProductRepository, Result, Category } from './types';
export const listCategories = cache(async (): Promise<Result<Category[]>> => {
  const result = await serverApi('/categories', z.array(categorySchema));
  return result.data ? { ok: true, data: result.data } : { ok: false, error: 'unavailable' };
});
export const productRepository: ProductRepository = {
  async list(query) {
    const params = new URLSearchParams();
    if (query.q) params.set('q', query.q);
    if (query.category) params.set('category', query.category);
    if (query.min !== undefined) params.set('min_minor', String(query.min));
    if (query.max !== undefined) params.set('max_minor', String(query.max));
    if (query.sort && ['price-asc', 'price-desc', 'name'].includes(query.sort))
      params.set('sort', query.sort);
    if (query.page) params.set('page', String(query.page));
    const result = await serverApi(`/products?${params}`, productPageSchema);
    return result.data ? { ok: true, data: result.data } : { ok: false, error: 'unavailable' };
  },
  async findBySlug(slug) {
    const result = await serverApi(`/products/${encodeURIComponent(slug)}`, productSchema);
    return result.data
      ? { ok: true, data: result.data }
      : result.status === 404
        ? { ok: true, data: null }
        : { ok: false, error: 'unavailable' };
  },
};
