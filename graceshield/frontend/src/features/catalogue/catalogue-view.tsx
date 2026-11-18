import Link from 'next/link';
import { Search, SlidersHorizontal, ArrowLeft, ArrowRight } from 'lucide-react';
import { listCategories } from './repository';
import { productRepository } from './repository';
import { first, pageHref, parseQuery, type SearchParams } from './query';
import { ProductCard } from '@/components/ui/product-card';
import type { Category } from './types';
export async function CatalogueView({
  params,
  category,
}: {
  params: SearchParams;
  category?: Category;
}) {
  const categoryResult = await listCategories();
  const categories = categoryResult.ok ? categoryResult.data : [];
  const query = parseQuery(params, category?.id);
  const result = await productRepository.list(query);
  const pathname = category ? `/categories/${category.slug}` : '/shop';
  return (
    <div className="wrap page-space">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/">Home</Link>
        <span>/</span>
        {category ? (
          <>
            <Link href="/categories">Categories</Link>
            <span>/</span>
            <span>{category.name}</span>
          </>
        ) : (
          <span>Shop all</span>
        )}
      </nav>
      <div className="page-heading">
        <p className="eyebrow">THE GRACESHIELD COLLECTION</p>
        <h1>{category?.name ?? 'Everyday essentials. Endless possibilities.'}</h1>
        <p>
          {category?.description ??
            'Something for every page, every project and every new beginning.'}
        </p>
      </div>
      <div className="catalogue-layout">
        <aside className="filters">
          <h2>
            <SlidersHorizontal size={17} /> Refine your collection
          </h2>
          <form action={pathname} key={JSON.stringify(params)}>
            <label>
              Search
              <div className="filter-search">
                <Search size={16} />
                <input
                  name="q"
                  type="search"
                  maxLength={120}
                  defaultValue={first(params.q)}
                  placeholder="Find an essential"
                />
              </div>
            </label>
            {!category && (
              <label>
                Category
                <select name="category" defaultValue={query.category ?? ''}>
                  <option value="">All categories</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <fieldset>
              <legend>Sample price (GHS)</legend>
              <div className="price-fields">
                <label>
                  <span>From</span>
                  <input
                    name="min"
                    type="number"
                    min="0"
                    max="999999"
                    step="0.01"
                    defaultValue={first(params.min)}
                    placeholder="0"
                  />
                </label>
                <label>
                  <span>To</span>
                  <input
                    name="max"
                    type="number"
                    min="0"
                    max="999999"
                    step="0.01"
                    defaultValue={first(params.max)}
                    placeholder="Any"
                  />
                </label>
              </div>
            </fieldset>
            <label>
              Sort by
              <select name="sort" defaultValue={query.sort ?? ''}>
                <option value="">Featured collection</option>
                <option value="price-asc">Price: low to high</option>
                <option value="price-desc">Price: high to low</option>
                <option value="name">Name: A to Z</option>
              </select>
            </label>
            <button className="button primary" type="submit">
              Apply filters <ArrowRight size={16} />
            </button>
            <Link className="reset-link" href={pathname}>
              Reset filters
            </Link>
          </form>
          <div className="filter-help">
            <strong>A note on this collection</strong>
            <p>
              Prices and availability are supplied by the backend. Seeded demonstration items are
              labeled SAMPLE.
            </p>
          </div>
        </aside>
        <div className="catalogue-results">
          {!result.ok ? (
            <div role="alert" className="empty-state">
              <h2>Collection unavailable</h2>
              <p>Please refresh to try again.</p>
            </div>
          ) : (
            <>
              <div className="results-heading">
                <span>
                  {result.data.total} {result.data.total === 1 ? 'essential' : 'essentials'}
                  {query.q && <> matching “{query.q}”</>}
                </span>
                <span>DEVELOPMENT CATALOGUE</span>
              </div>
              {result.data.total ? (
                <div className="product-grid catalogue-products">
                  {result.data.products.map((p) => (
                    <ProductCard key={p.id} product={p} />
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <Search size={38} />
                  <h2>No essentials found</h2>
                  <p>Try a different search or a wider price range.</p>
                  <Link href={pathname} className="button secondary">
                    Clear filters
                  </Link>
                </div>
              )}
              {result.data.pages > 1 && (
                <nav className="pagination" aria-label="Catalogue pages">
                  {result.data.page > 1 && (
                    <Link
                      aria-label="Previous page"
                      href={pageHref(params, result.data.page - 1, pathname)}
                    >
                      <ArrowLeft size={17} />
                    </Link>
                  )}
                  {Array.from({ length: result.data.pages }, (_, i) => (
                    <Link
                      aria-label={`Page ${i + 1}`}
                      aria-current={result.data.page === i + 1 ? 'page' : undefined}
                      key={i}
                      href={pageHref(params, i + 1, pathname)}
                    >
                      {i + 1}
                    </Link>
                  ))}
                  {result.data.page < result.data.pages && (
                    <Link
                      aria-label="Next page"
                      href={pageHref(params, result.data.page + 1, pathname)}
                    >
                      <ArrowRight size={17} />
                    </Link>
                  )}
                </nav>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
