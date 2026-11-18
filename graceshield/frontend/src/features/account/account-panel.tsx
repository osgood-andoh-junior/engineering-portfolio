'use client';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';
import {
  api,
  ApiError,
  userSchema,
  orderSchema,
  messageSchema,
  errorMessage,
  type CustomerProfile,
  type Order,
} from '@/lib/api';
import { formatMoney } from '@/lib/formatting';
export function AccountPanel({ ordersOnly = false }: { ordersOnly?: boolean }) {
  const [user, setUser] = useState<CustomerProfile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState('');
  const [message, setMessage] = useState('');
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    setFailure('');
    try {
      setUser(await api('/auth/me', userSchema));
      if (ordersOnly)
        setOrders(
          (
            await api(
              `/orders?page=${page}`,
              z.object({ orders: z.array(orderSchema), page: z.number() }),
            )
          ).orders,
        );
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setUser(null);
      else setFailure(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [ordersOnly, page]);
  useEffect(() => {
    queueMicrotask(() => void load());
  }, [load]);
  const action = async (path: string) => {
    setBusy(true);
    setFailure('');
    try {
      setMessage((await api(path, messageSchema, { method: 'POST' })).message);
      if (path === '/auth/logout') {
        setUser(null);
        window.dispatchEvent(new Event('graceshield-auth'));
      }
    } catch (e) {
      setFailure(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  if (loading) return <p role="status">Loading your account…</p>;
  if (!user)
    return (
      <div className="empty-state">
        <h2>Sign in to your account.</h2>
        <p>{failure || 'Your profile and orders are protected by your account session.'}</p>
        <Link href="/login" className="button primary">
          Sign in
        </Link>
        <Link href="/register" className="text-link">
          Create an account
        </Link>
      </div>
    );
  return (
    <div>
      {failure && (
        <p role="alert" className="field-error">
          {failure}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {ordersOnly ? (
        <>
          <div className="account-grid">
            {orders.map((order) => (
              <article className="content-card" key={order.id}>
                <p className="eyebrow">{order.reference}</p>
                <h2>{order.status.replaceAll('_', ' ')}</h2>
                <p>
                  {formatMoney(order.total)} ·{' '}
                  {new Date(order.createdAt).toLocaleDateString('en-GH')}
                </p>
                <ul>
                  {order.items.map((line, i) => (
                    <li key={i}>
                      {line.name} × {line.quantity} · {formatMoney(line.unitPrice * line.quantity)}
                    </li>
                  ))}
                </ul>
                {order.status === 'pending_payment' && (
                  <>
                    <p>
                      No payment has been taken. Reservation expires{' '}
                      {new Date(order.expiresAt).toLocaleString('en-GH')}.
                    </p>
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        try {
                          await api(`/orders/${order.id}/cancel`, orderSchema, { method: 'POST' });
                          await load();
                        } catch (e) {
                          setFailure(errorMessage(e));
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Cancel pending order
                    </button>
                  </>
                )}
              </article>
            ))}
          </div>
          {!orders.length && <p>No orders on this page.</p>}
          <div className="pagination">
            <button
              className="button secondary"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span>Page {page}</span>
            <button
              className="button secondary"
              disabled={orders.length < 20}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <section className="content-card">
          <h2>Welcome, {user.name}.</h2>
          <p>{user.email}</p>
          <p>Email: {user.verified ? 'verified' : 'verification required'}</p>
          {!user.verified && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => void action('/auth/verification/request')}
            >
              Request verification email
            </button>
          )}
          <div className="info-links">
            <Link className="button primary" href="/account/orders">
              View your orders
            </Link>
            {user.roles.includes('admin') && (
              <Link className="button secondary" href="/admin">
                Administration
              </Link>
            )}
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => void action('/auth/logout')}
            >
              Sign out
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
