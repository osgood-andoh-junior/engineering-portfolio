import { z } from 'zod';
export const categorySchema = z.object({
  id: z.string().uuid(),
  slug: z.string(),
  name: z.string(),
  shortName: z.string(),
  description: z.string(),
  icon: z.string(),
  color: z.string().regex(/^#[a-fA-F0-9]{6}$/),
});
export const productSchema = z.object({
  id: z.string().uuid(),
  slug: z.string(),
  name: z.string(),
  categoryId: z.string().uuid(),
  categoryName: z.string().optional(),
  price: z.object({ amount: z.number().int().nonnegative(), currency: z.literal('GHS') }),
  images: z
    .array(
      z.object({
        path: z.string().regex(/^\/images\/[a-zA-Z0-9_-]+\.(svg|png|webp|jpg)$/),
        alt: z.string(),
      }),
    )
    .transform((imgs) => imgs.map((img) => ({ src: img.path, alt: img.alt }))),
  description: z.string(),
  details: z.array(z.string()),
  availability: z.enum(['available', 'unavailable']),
  featured: z.boolean(),
  demonstration: z.boolean(),
  variantId: z.string().uuid().nullable(),
  variants: z.array(
    z.object({
      id: z.string().uuid(),
      name: z.string(),
      sku: z.string(),
      available: z.number().int().nonnegative(),
    }),
  ),
});
export const productPageSchema = z.object({
  products: z.array(productSchema),
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  pages: z.number().int().positive(),
});
