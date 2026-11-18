'use client';
import Link from 'next/link';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Info, LockKeyhole, Check } from 'lucide-react';
import { checkoutSchema, regions, type CheckoutDraft } from './schema';
import { useCart } from '@/features/cart/cart-provider';
import { OrderSummary } from '@/features/cart/cart-view';
import { api, orderSchema, errorMessage, type Order } from '@/lib/api';
export function CheckoutForm() {
  const { items, ready, error, refresh } = useCart();
  const [order, setOrder] = useState<Order | null>(null);
  const [failure, setFailure] = useState('');
  const [submissionKey] = useState(() => crypto.randomUUID());
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CheckoutDraft>({ resolver: zodResolver(checkoutSchema) });
  if (order)
    return (
      <div className="empty-state" role="status">
        <h2>Order prepared — pending payment.</h2>
        <p>Reference: {order.reference}</p>
        <p>{order.nextSteps}</p>
        <p>Reservation expires: {new Date(order.expiresAt).toLocaleString('en-GH')}</p>
        <Link className="button primary" href="/account/orders">
          View your orders
        </Link>
      </div>
    );
  if (error)
    return (
      <div className="empty-state" role="alert">
        <p>{error}</p>
        <button className="button secondary" onClick={() => void refresh()}>
          Try again
        </button>
      </div>
    );
  if (!ready) return <p role="status">Restoring your bag…</p>;
  if (!items.length)
    return (
      <div className="empty-state">
        <h2>Start with a little inspiration.</h2>
        <p>Add an available product to prepare checkout.</p>
        <Link className="button primary" href="/shop">
          Explore the collection
        </Link>
      </div>
    );
  const field = (name: keyof CheckoutDraft, label: string, autocomplete: string, type = 'text') => (
    <div className="form-field">
      <label htmlFor={`checkout-${name}`}>{label}</label>
      <input
        id={`checkout-${name}`}
        type={type}
        autoComplete={autocomplete}
        {...register(name)}
        aria-invalid={!!errors[name]}
        aria-describedby={errors[name] ? `${name}-error` : undefined}
      />
      {errors[name] && (
        <span className="field-error" id={`${name}-error`} role="alert">
          {errors[name]?.message}
        </span>
      )}
    </div>
  );
  return (
    <div className="cart-layout checkout-layout">
      <div>
        <div className="notice">
          <Info size={20} />
          <p>
            <strong>Local development.</strong> Preparing an order sends the details below to your
            configured backend. Use test details with demonstration stock. Email verification and
            configured delivery pricing are required. Live payments are disabled.
          </p>
        </div>
        <form
          className="checkout-form"
          onSubmit={handleSubmit(async (data) => {
            setFailure('');
            try {
              setOrder(
                await api('/checkout/prepare', orderSchema, {
                  method: 'POST',
                  headers: { 'Idempotency-Key': submissionKey },
                  body: JSON.stringify(data),
                }),
              );
              await refresh();
            } catch (e) {
              setFailure(errorMessage(e));
            }
          })}
          noValidate
        >
          <h2>
            <span>01</span> Your details
          </h2>
          <div className="form-grid">
            {field('firstName', 'First name', 'given-name')}
            {field('lastName', 'Last name', 'family-name')}
            {field('email', 'Email address', 'email', 'email')}
            {field('phone', 'Phone number', 'tel', 'tel')}
          </div>
          <h2>
            <span>02</span> Delivery address
          </h2>
          {field('address', 'Street address or GhanaPost GPS address', 'street-address')}
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="checkout-region">Region</label>
              <select
                id="checkout-region"
                {...register('region')}
                aria-invalid={!!errors.region}
                aria-describedby={errors.region ? 'region-error' : undefined}
              >
                <option value="">Select a region</option>
                {regions.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
              {errors.region && (
                <span role="alert" id="region-error" className="field-error">
                  {errors.region.message}
                </span>
              )}
            </div>
            {field('city', 'City or town', 'address-level2')}
          </div>
          <div className="service-placeholder">
            <h3>Shipping options</h3>
            <p>
              The backend validates coverage and calculates the configured delivery fee before
              creating an order. Unconfigured delivery prevents order creation.
            </p>
          </div>
          <h2>
            <span>03</span> Payment
          </h2>
          <div className="service-placeholder">
            <LockKeyhole size={21} />
            <div>
              <h3>Payments are unavailable</h3>
              <p>No payment information is collected in this preview.</p>
            </div>
          </div>
          <button
            className="button primary"
            type="submit"
            disabled={isSubmitting || items.some((i) => !i.valid)}
          >
            {isSubmitting ? 'Preparing…' : 'Prepare pending-payment order'} <Check size={16} />
          </button>
          {failure && (
            <p className="field-error" role="alert">
              {failure}
            </p>
          )}
          <button className="button primary place-order" type="button" disabled>
            Pay now — unavailable
          </button>
        </form>
      </div>
      <OrderSummary checkout />
    </div>
  );
}
