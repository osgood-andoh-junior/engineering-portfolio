import { CatalogueView } from '@/features/catalogue/catalogue-view';
import type { SearchParams } from '@/features/catalogue/query';
import { canonical } from '@/lib/metadata';
export const metadata = {
  alternates: canonical('/shop'),
  title: 'Shop the collection',
  description:
    'Explore demonstration books, stationery and school essentials. Search and filter sample products.',
};
export default async function Shop({ searchParams }: { searchParams: Promise<SearchParams> }) {
  return <CatalogueView params={await searchParams} />;
}
