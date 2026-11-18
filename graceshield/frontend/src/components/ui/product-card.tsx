import Link from 'next/link';
import Image from 'next/image';
import type { Product } from '@/features/catalogue/types';
import { formatMoney } from '@/lib/formatting';
import { AddToCart } from '@/features/cart/add-to-cart';
export function ProductCard({ product }: { product: Product }) {
  return (
    <article className="product-card">
      <Link href={`/products/${product.slug}`} className="product-image">
        {product.demonstration !== false && <span className="sample-tag">SAMPLE</span>}
        <Image src={product.images[0].src} alt={product.images[0].alt} width={360} height={300} />
        <span className="product-discover">Take a closer look ↗</span>
      </Link>
      <div className="product-info">
        <p className="product-category">{product.categoryName ?? 'Everyday essentials'}</p>
        <h3>
          <Link href={`/products/${product.slug}`}>{product.name}</Link>
        </h3>
        <div className="product-bottom">
          <span>{formatMoney(product.price)}</span>
          <AddToCart product={product} compact />
        </div>
      </div>
    </article>
  );
}
