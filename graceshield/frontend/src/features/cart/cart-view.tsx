'use client';
import Link from 'next/link';
import Image from 'next/image';
import { ShoppingBag, Trash2, ArrowRight, ArrowLeft } from 'lucide-react';
import { useCart } from './cart-provider';
import { formatMoney } from '@/lib/formatting';
export function OrderSummary({ checkout = false }: { checkout?: boolean }) {
  const { subtotal, count, items } = useCart();
  return (
    <aside className="order-summary">
      <h2>Your summary</h2>
      {checkout && (
        <ul className="summary-items">
          {items.map((item) => {
            const product = item.product;
            return product ? (
              <li key={item.productId}>
                <span>
                  {product.name} <small>× {item.quantity}</small>
                </span>
                <strong>{formatMoney(product.price.amount * item.quantity)}</strong>
              </li>
            ) : null;
          })}
        </ul>
      )}
      <div>
        <span>Subtotal ({count} items)</span>
        <strong>{formatMoney(subtotal)}</strong>
      </div>
      <div>
        <span>Delivery</span>
        <span>Not calculated</span>
      </div>
      <div className="summary-total">
        <span>Subtotal</span>
        <strong>{formatMoney(subtotal)}</strong>
      </div>
      <p>
        Prices are calculated by the backend. Delivery eligibility and the final order total are
        validated during checkout preparation.
      </p>
      {!checkout && (
        <Link href="/checkout" className="button primary">
          Continue to checkout <ArrowRight size={17} />
        </Link>
      )}
      <div className="summary-note">Development environment · Live payments disabled</div>
    </aside>
  );
}
export function CartView() {
  const { items, ready, update, remove, error, busy, refresh, clear } = useCart();
  if (error)
    return (
      <div className="empty-state" role="alert">
        <h2>Your bag is temporarily unavailable.</h2>
        <p>{error}</p>
        <button className="button secondary" onClick={() => void refresh()}>
          Try again
        </button>
      </div>
    );
  if (!ready)
    return (
      <div className="empty-state" role="status">
        Restoring your bag…
      </div>
    );
  if (!items.length)
    return (
      <div className="empty-state">
        <ShoppingBag size={44} />
        <h2>A little room for possibility.</h2>
        <p>Your bag is empty. Let’s find your next everyday essential.</p>
        <Link href="/shop" className="button primary">
          Explore the collection <ArrowRight size={17} />
        </Link>
      </div>
    );
  return (
    <div className="cart-layout">
      <div>
        <div className="cart-table-head">
          <span>YOUR ESSENTIALS</span>
          <span>QUANTITY & TOTAL</span>
        </div>
        {items.map((item) => {
          const p = item.product;
          if (!p) return null;
          return (
            <article className="cart-row" key={item.variantId}>
              <Link href={`/products/${p.slug}`} className="cart-product-image">
                <Image src={p.images[0].src} alt={p.images[0].alt} width={120} height={120} />
              </Link>
              <div className="cart-item-copy">
                <span className="eyebrow">
                  {p.demonstration ? 'SAMPLE PRODUCT' : 'YOUR ESSENTIAL'}
                </span>
                {!item.valid && (
                  <p role="alert">
                    This item is unavailable or has insufficient stock. Remove it or reduce the
                    quantity.
                  </p>
                )}
                <h2>
                  <Link href={`/products/${p.slug}`}>{p.name}</Link>
                </h2>
                <p>{formatMoney(p.price)} each</p>
                <button
                  className="remove-link"
                  onClick={() => remove(item.variantId)}
                  aria-label={`Remove ${p.name}`}
                >
                  <Trash2 size={14} /> Remove
                </button>
              </div>
              <div className="cart-item-totals">
                <label className="sr-only" htmlFor={`qty-${item.variantId}`}>
                  Quantity for {p.name}
                </label>
                <select
                  id={`qty-${item.variantId}`}
                  disabled={busy}
                  value={item.quantity}
                  onChange={(e) => update(item.variantId, Number(e.target.value))}
                >
                  {Array.from({ length: 20 }, (_, i) => (
                    <option value={i + 1} key={i}>
                      {i + 1}
                    </option>
                  ))}
                </select>
                <strong>{formatMoney(p.price.amount * item.quantity)}</strong>
              </div>
            </article>
          );
        })}
        <Link href="/shop" className="text-link">
          <ArrowLeft size={16} /> Continue exploring
        </Link>
      </div>
      <div>
        <OrderSummary />
        <button className="button secondary" disabled={busy} onClick={clear}>
          Clear bag
        </button>
      </div>
    </div>
  );
}
