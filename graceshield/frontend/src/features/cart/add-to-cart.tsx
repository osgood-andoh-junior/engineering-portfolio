'use client';
import { Plus, ShoppingBag } from 'lucide-react';
import { useState } from 'react';
import { useCart } from './cart-provider';
import type { Product } from '@/features/catalogue/types';
export function AddToCart({ product, compact = false }: { product: Product; compact?: boolean }) {
  const { add, ready, busy, error } = useCart();
  const [variantId, setVariantId] = useState(product.variantId ?? '');
  const [quantity, setQuantity] = useState(1);
  const unavailable = product.availability === 'unavailable';
  return (
    <div className={compact ? 'quick-add' : 'purchase-controls'}>
      {!compact && product.variants && product.variants.length > 1 && (
        <label className="quantity-label">
          Option
          <select
            aria-label="Product option"
            value={variantId}
            onChange={(e) => setVariantId(e.target.value)}
          >
            {product.variants.map((v) => (
              <option key={v.id} value={v.id} disabled={!v.available}>
                {v.name}
                {!v.available ? ' — out of stock' : ''}
              </option>
            ))}
          </select>
        </label>
      )}
      {!compact && (
        <label className="quantity-label">
          Quantity
          <select
            aria-label="Quantity"
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
          >
            {Array.from({ length: 20 }, (_, i) => (
              <option key={i} value={i + 1}>
                {i + 1}
              </option>
            ))}
          </select>
        </label>
      )}
      <button
        className={compact ? 'add-circle' : 'button primary'}
        disabled={!ready || busy || unavailable || !!error}
        aria-label={compact ? `Add ${product.name} to bag` : undefined}
        onClick={() => add(product.id, quantity, variantId)}
      >
        {compact ? (
          <Plus size={19} />
        ) : (
          <>
            <ShoppingBag size={18} />
            {unavailable ? 'Currently unavailable' : 'Add to bag'}
          </>
        )}
      </button>
    </div>
  );
}
