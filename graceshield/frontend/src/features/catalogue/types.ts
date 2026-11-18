export type Money = { amount: number; currency: 'GHS' };
export type Category = {
  id: string;
  slug: string;
  name: string;
  shortName: string;
  icon: string;
  description: string;
  color: string;
};
export type ProductImage = { src: string; alt: string };
export type InventoryAvailability = 'available' | 'unavailable';
export type Product = {
  id: string;
  slug: string;
  name: string;
  categoryId: string;
  price: Money;
  images: ProductImage[];
  description: string;
  details: string[];
  availability: InventoryAvailability;
  featured: boolean;
  demonstration?: boolean;
  categoryName?: string;
  variantId?: string | null;
  variants?: { id: string; name: string; sku: string; available: number }[];
};
export type CatalogueQuery = {
  q?: string;
  category?: string;
  min?: number;
  max?: number;
  sort?: string;
  page?: number;
};
export type ProductPage = { products: Product[]; total: number; page: number; pages: number };
export type Result<T> = { ok: true; data: T } | { ok: false; error: 'unavailable' };
export interface ProductRepository {
  list(query: CatalogueQuery): Promise<Result<ProductPage>>;
  findBySlug(slug: string): Promise<Result<Product | null>>;
}
