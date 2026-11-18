import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { listCategories } from '@/features/catalogue/repository';
import { CategoryIcon } from '@/components/ui/category-icon';
import { canonical } from '@/lib/metadata';
export const metadata = { title: 'Explore our categories', alternates: canonical('/categories') };
export default async function Categories() {
  const result = await listCategories();
  const categories = result.ok ? result.data : [];
  return (
    <div className="wrap page-space">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/">Home</Link>
        <span>/</span>
        <span>Categories</span>
      </nav>
      <div className="page-heading">
        <p className="eyebrow">SOMETHING FOR EVERY CHAPTER</p>
        <h1>A world of possibilities.</h1>
        <p>Eleven ways to find the little things that move your day forward.</p>
      </div>
      <div className="all-categories">
        {!result.ok && (
          <p role="alert">
            The category service is unavailable. Check the backend and database configuration.
          </p>
        )}
        {categories.map((c) => (
          <Link key={c.id} href={`/categories/${c.slug}`} className="category-card">
            <span className="category-icon" style={{ background: c.color }}>
              <CategoryIcon name={c.icon} size={34} />
            </span>
            <h2>{c.name}</h2>
            <p>{c.description}</p>
            <span className="text-link">
              Explore collection <ArrowUpRight size={17} />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
