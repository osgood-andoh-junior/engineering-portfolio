import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft, Info } from 'lucide-react';
import { listCategories } from '@/features/catalogue/repository';
import { productRepository } from '@/features/catalogue/repository';
import { Gallery } from '@/features/products/gallery';
import { AddToCart } from '@/features/cart/add-to-cart';
import { ProductCard } from '@/components/ui/product-card';
import { formatMoney } from '@/lib/formatting';
import { canonical } from '@/lib/metadata';
type Props = { params: Promise<{ slug: string }> };
export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  const result = await productRepository.findBySlug(slug);
  return {
    title: result.ok && result.data ? result.data.name : 'Product not found',
    alternates: result.ok && result.data ? canonical(`/products/${result.data.slug}`) : undefined,
  };
}
export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const result = await productRepository.findBySlug(slug);
  if (!result.ok) throw new Error('Catalogue unavailable');
  if (!result.data) notFound();
  const p = result.data;
  const [categoryResult, relatedResult] = await Promise.all([
    listCategories(),
    productRepository.list({}),
  ]);
  const categories = categoryResult.ok ? categoryResult.data : [];
  const products = relatedResult.ok ? relatedResult.data.products : [];
  const c = categories.find((c) => c.id === p.categoryId);
  return (
    <div className="wrap page-space">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/shop">Shop</Link>
        <span>/</span>
        <Link href={`/categories/${c?.slug}`}>{c?.name}</Link>
        <span>/</span>
        <span>{p.name}</span>
      </nav>
      <div className="product-detail">
        <Gallery images={p.images} />
        <div className="product-description">
          <p className="eyebrow">{c?.name}</p>
          <h1>{p.name}</h1>
          <p className="detail-price">{formatMoney(p.price)}</p>
          <span className="availability">
            {p.availability === 'available'
              ? 'Available to add to your bag'
              : 'Currently unavailable'}
          </span>
          <p>{p.description}</p>
          <AddToCart product={p} />
          <div className="notice">
            <Info size={19} />
            <p>
              Development environment. Seeded products are illustrative. Live payments are disabled.
            </p>
          </div>
          <div className="product-details-list">
            <h2>The little details</h2>
            <ul>
              {p.details.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
          <Link className="text-link" href="/shop">
            <ArrowLeft size={15} /> Back to the collection
          </Link>
        </div>
      </div>
      <section className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">KEEP EXPLORING</p>
            <h2>A few more possibilities.</h2>
          </div>
        </div>
        <div className="product-grid">
          {products
            .filter((item) => item.id !== p.id)
            .slice(0, 4)
            .map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
        </div>
      </section>
    </div>
  );
}
