import { vi } from 'vitest';
import { products } from '@/data/mock/catalogue';
export const productId = '00000000-0000-4000-8000-000000000001';
export const variantId = '00000000-0000-4000-8000-000000000002';
export const categoryId = '00000000-0000-4000-8000-000000000003';
export const testProduct = {
  ...products[0],
  id: productId,
  categoryId,
  variantId,
  demonstration: true,
  variants: [{ id: variantId, name: 'Standard', sku: 'TEST-NOTEBOOK', available: 30 }],
};
export const rawProduct = {
  ...testProduct,
  images: testProduct.images.map((image) => ({ path: image.src, alt: image.alt })),
};
export function installApiFixture(initialQuantity = 0) {
  let quantity = initialQuantity;
  const cart = () => ({
    items: quantity
      ? [
          {
            productId,
            variantId,
            quantity,
            product: rawProduct,
            valid: true,
            lineTotal: 4500 * quantity,
          },
        ]
      : [],
    subtotal: 4500 * quantity,
    count: quantity,
    currency: 'GHS',
  });
  const transport = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
    const url = String(input);
    let data: unknown;
    let status = 200;
    if (url.endsWith('/auth/session')) data = { csrf: 'test-csrf-token-for-request-validation' };
    else if (url.includes('/cart')) {
      const method = options?.method ?? 'GET';
      if (
        method !== 'GET' &&
        new Headers(options?.headers).get('X-CSRF-Token') !==
          'test-csrf-token-for-request-validation'
      ) {
        data = { error: { code: 'csrf_failed', message: 'CSRF rejected' } };
        status = 403;
      } else {
        if (method === 'POST') quantity += JSON.parse(String(options?.body)).quantity;
        if (method === 'PUT') quantity = JSON.parse(String(options?.body)).quantity;
        if (method === 'DELETE') quantity = 0;
        data = cart();
      }
    } else {
      data = { error: { code: 'unavailable', message: 'Service unavailable' } };
      status = 503;
    }
    return new Response(JSON.stringify(data), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  vi.stubGlobal('fetch', transport);
  return transport;
}
