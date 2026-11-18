import { notFound } from 'next/navigation';
import { listCategories } from '@/features/catalogue/repository';
import { CatalogueView } from '@/features/catalogue/catalogue-view';
import type { SearchParams } from '@/features/catalogue/query';
import { canonical } from '@/lib/metadata';
type Props = { params: Promise<{ slug: string }>; searchParams: Promise<SearchParams> };
export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  const result = await listCategories();
  const categories = result.ok ? result.data : [];
  const c = categories.find((c) => c.slug === slug);
  return {
    title: c?.name ?? 'Category not found',
    description: c?.description,
    alternates: c ? canonical(`/categories/${c.slug}`) : undefined,
  };
}
export default async function CategoryPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const result = await listCategories();
  if (!result.ok) throw new Error('Catalogue unavailable');
  const categories = result.data;
  const category = categories.find((c) => c.slug === slug);
  if (!category) notFound();
  return <CatalogueView category={category} params={await searchParams} />;
}
