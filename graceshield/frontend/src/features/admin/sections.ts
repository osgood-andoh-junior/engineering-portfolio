export const sections = [
  'overview',
  'products',
  'categories',
  'inventory',
  'orders',
  'customers',
] as const;
export type AdminSection = (typeof sections)[number];
