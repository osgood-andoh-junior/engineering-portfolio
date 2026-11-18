'use client';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';
import { api, userSchema, orderSchema, errorMessage, messageSchema } from '@/lib/api';
import { categorySchema, productSchema } from '@/features/catalogue/api-schemas';
import { formatMoney } from '@/lib/formatting';

import { sections } from './sections';
type Section = (typeof sections)[number];
type Row = Record<string, unknown>;
const schemas: Record<Exclude<Section, 'overview'>, z.ZodType<Row[]>> = {
  products: z.array(productSchema.extend({ status: z.enum(['draft', 'published', 'archived']) })),
  categories: z.array(categorySchema.extend({ archived: z.boolean() })),
  inventory: z.array(
    z.object({
      variantId: z.string().uuid(),
      sku: z.string(),
      quantity: z.number().int(),
      reserved: z.number().int(),
      available: z.number().int(),
      lowStockThreshold: z.number().int(),
    }),
  ),
  orders: z.array(orderSchema),
  customers: z.array(userSchema),
};
const columns: Record<Exclude<Section, 'overview'>, string[]> = {
  products: ['name', 'status', 'price', 'demonstration'],
  categories: ['name', 'slug', 'archived'],
  inventory: ['sku', 'quantity', 'reserved', 'available', 'lowStockThreshold'],
  orders: ['reference', 'status', 'total', 'createdAt'],
  customers: ['name', 'email', 'verified', 'roles'],
};
const value = (row: Row | null, key: string) => {
  const v = row?.[key];
  return typeof v === 'string' || typeof v === 'number' ? String(v) : '';
};
function cell(row: Row, key: string) {
  const v = row[key];
  if (key === 'price') {
    const p = z.object({ amount: z.number() }).safeParse(v);
    return p.success ? formatMoney(p.data.amount) : '—';
  }
  if (key === 'total' && typeof v === 'number') return formatMoney(v);
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  return typeof v === 'string' || typeof v === 'number' ? String(v) : '—';
}
export function AdminPanel({ section = 'overview' }: { section?: Section }) {
  const [authorized, setAuthorized] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [overview, setOverview] = useState<Record<string, number>>({});
  const [categories, setCategories] = useState<z.infer<typeof categorySchema>[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const [message, setMessage] = useState('');
  const [page, setPage] = useState(1);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const user = await api('/auth/me', userSchema);
      if (!user.verified || !user.roles.includes('admin'))
        throw new Error('Administrator permission and a verified account are required.');
      setAuthorized(true);
      if (section === 'overview') {
        const data = await api(
          '/admin/overview',
          z.object({
            customers: z.number(),
            products: z.number(),
            orders: z.number(),
            verifiedSalesMinor: z.number(),
            lowStockVariants: z.number(),
            currency: z.literal('GHS'),
          }),
        );
        setOverview({
          Customers: data.customers,
          Products: data.products,
          Orders: data.orders,
          'Verified sales (pesewas)': data.verifiedSalesMinor,
          'Low-stock variants': data.lowStockVariants,
        });
      } else {
        setRows(await api(`/admin/${section}?page=${page}`, schemas[section]));
        if (section === 'products')
          setCategories(await api('/categories', z.array(categorySchema)));
      }
      setFailure('');
    } catch (e) {
      setFailure(e instanceof Error ? e.message : errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [section, page]);
  useEffect(() => {
    queueMicrotask(() => void load());
  }, [load]);
  const mutate = async (
    path: string,
    body?: object,
    method = 'POST',
    schema: z.ZodType<unknown> = z.unknown(),
  ) => {
    setBusy(true);
    setFailure('');
    try {
      await api(path, schema, { method, body: body ? JSON.stringify(body) : undefined });
      setMessage('Change saved.');
      setSelected(null);
      await load();
    } catch (e) {
      setFailure(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const textField = (
    label: string,
    name: string,
    defaultValue = '',
    type = 'text',
    required = true,
  ) => (
    <label className="form-field">
      {label}
      <input
        name={name}
        type={type}
        defaultValue={defaultValue}
        required={required}
        min={type === 'number' ? '0' : undefined}
      />
    </label>
  );
  if (loading && !authorized) return <p role="status">Checking administrator access…</p>;
  if (!authorized)
    return (
      <div className="empty-state">
        <h2>Administrator access required.</h2>
        <p role="alert">{failure}</p>
        <Link className="button primary" href="/login">
          Sign in
        </Link>
      </div>
    );
  return (
    <div>
      <nav className="admin-nav" aria-label="Administration">
        {sections.map((s) => (
          <Link
            key={s}
            aria-current={section === s ? 'page' : undefined}
            href={s === 'overview' ? '/admin' : `/admin/${s}`}
          >
            {s}
          </Link>
        ))}
      </nav>
      {failure && (
        <p className="field-error" role="alert">
          {failure}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {loading && <p role="status">Refreshing records…</p>}
      {section === 'overview' ? (
        <div className="account-grid">
          {Object.entries(overview).map(([label, n]) => (
            <section className="content-card" key={label}>
              <p>{label}</p>
              <h2>{n.toLocaleString('en-GH')}</h2>
            </section>
          ))}
        </div>
      ) : (
        <>
          {(section === 'products' || section === 'categories') && (
            <details className="admin-editor" open={!!selected}>
              <summary>{selected ? 'Edit record' : 'Add a record'}</summary>
              <form
                key={value(selected, 'id') || 'new'}
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const id = value(selected, 'id');
                  if (section === 'categories') {
                    void mutate(
                      `/admin/categories${id ? `/${id}` : ''}`,
                      {
                        name: f.get('name'),
                        slug: f.get('slug'),
                        description: f.get('description'),
                        icon: f.get('icon'),
                        color: f.get('color'),
                      },
                      id ? 'PUT' : 'POST',
                      categorySchema,
                    );
                  } else {
                    void mutate(
                      `/admin/products${id ? `/${id}` : ''}`,
                      {
                        name: f.get('name'),
                        slug: f.get('slug'),
                        description: f.get('description'),
                        category_id: f.get('category_id'),
                        price_minor: Number(f.get('price_minor')),
                        sku: f.get('sku'),
                        status: f.get('status'),
                        demonstration: f.get('demonstration') === 'on',
                        images: [{ path: f.get('image'), alt: f.get('alt') }],
                      },
                      id ? 'PUT' : 'POST',
                      productSchema,
                    );
                  }
                }}
              >
                <div className="form-grid">
                  {textField('Name', 'name', value(selected, 'name'))}
                  {textField('Slug', 'slug', value(selected, 'slug'))}
                </div>
                {textField('Description', 'description', value(selected, 'description'))}
                {section === 'categories' ? (
                  <div className="form-grid">
                    {textField('Icon name', 'icon', value(selected, 'icon') || 'book')}
                    {textField('Colour', 'color', value(selected, 'color') || '#eaf0f8', 'color')}
                  </div>
                ) : (
                  <>
                    <div className="form-grid">
                      <label className="form-field">
                        Category
                        <select
                          name="category_id"
                          required
                          defaultValue={value(selected, 'categoryId')}
                        >
                          {categories.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="form-field">
                        Publication status
                        <select name="status" defaultValue={value(selected, 'status') || 'draft'}>
                          <option>draft</option>
                          <option>published</option>
                          <option>archived</option>
                        </select>
                      </label>
                      {textField(
                        'Price (integer pesewas)',
                        'price_minor',
                        z.object({ amount: z.number() }).safeParse(selected?.price).success
                          ? String(z.object({ amount: z.number() }).parse(selected?.price).amount)
                          : '0',
                        'number',
                      )}
                      {textField(
                        'SKU',
                        'sku',
                        Array.isArray(selected?.variants)
                          ? String((selected.variants[0] as { sku?: string })?.sku ?? '')
                          : '',
                      )}
                      {textField(
                        'Approved image path',
                        'image',
                        Array.isArray(selected?.images)
                          ? String(
                              (selected.images[0] as { src?: string })?.src ??
                                '/images/notebook.svg',
                            )
                          : '/images/notebook.svg',
                      )}
                      {textField(
                        'Image description',
                        'alt',
                        value(selected, 'name') || 'Product illustration',
                      )}
                    </div>
                    <label className="form-field">
                      <span>
                        <input
                          name="demonstration"
                          type="checkbox"
                          defaultChecked={selected?.demonstration === true}
                        />{' '}
                        Demonstration stock
                      </span>
                    </label>
                  </>
                )}
                <button className="button primary" disabled={busy}>
                  {busy ? 'Saving…' : selected ? 'Save changes' : 'Create record'}
                </button>
                {selected && (
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => setSelected(null)}
                  >
                    Cancel edit
                  </button>
                )}
              </form>
            </details>
          )}
          <div className="admin-table-wrap">
            <table className="admin-table">
              <caption>
                {section} · page {page}
              </caption>
              <thead>
                <tr>
                  {columns[section].map((c) => (
                    <th scope="col" key={c}>
                      {c.replaceAll('_', ' ')}
                    </th>
                  ))}
                  {section !== 'customers' && <th scope="col">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={value(row, 'id') || value(row, 'variantId') || i}>
                    {columns[section].map((c) => (
                      <td key={c}>{cell(row, c)}</td>
                    ))}
                    {section !== 'customers' && (
                      <td>
                        {(section === 'products' || section === 'categories') && (
                          <>
                            <button
                              className="button secondary"
                              disabled={busy}
                              onClick={() => setSelected(row)}
                            >
                              Edit
                            </button>
                            <button
                              className="button secondary"
                              disabled={busy || row.status === 'archived' || row.archived === true}
                              onClick={() =>
                                void mutate(
                                  `/admin/${section}/${value(row, 'id')}`,
                                  undefined,
                                  'DELETE',
                                  messageSchema,
                                )
                              }
                            >
                              Archive
                            </button>
                          </>
                        )}
                        {section === 'inventory' && (
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              const f = new FormData(e.currentTarget);
                              void mutate(`/admin/inventory/${value(row, 'variantId')}/adjust`, {
                                delta: Number(f.get('delta')),
                                reason: f.get('reason'),
                                low_stock_threshold: Number(f.get('threshold')),
                              });
                            }}
                          >
                            <label>
                              Stock adjustment
                              <input
                                name="delta"
                                aria-label={`Stock adjustment for ${value(row, 'sku')}`}
                                type="number"
                                required
                                defaultValue="0"
                              />
                            </label>
                            <label>
                              Reason
                              <input
                                name="reason"
                                aria-label={`Adjustment reason for ${value(row, 'sku')}`}
                                required
                                minLength={5}
                              />
                            </label>
                            <label>
                              Low stock threshold
                              <input
                                name="threshold"
                                type="number"
                                min="0"
                                defaultValue={value(row, 'lowStockThreshold')}
                                required
                              />
                            </label>
                            <button className="button secondary" disabled={busy}>
                              Apply adjustment
                            </button>
                          </form>
                        )}
                        {section === 'orders' && (
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              const f = new FormData(e.currentTarget);
                              void mutate(
                                `/admin/orders/${value(row, 'id')}/status`,
                                { status: f.get('status') },
                                'POST',
                                orderSchema,
                              );
                            }}
                          >
                            <label>
                              Next status
                              <select
                                name="status"
                                aria-label={`Next status for ${value(row, 'reference')}`}
                              >
                                <option value="processing">processing</option>
                                <option value="shipped">shipped</option>
                                <option value="delivered">delivered</option>
                                <option value="cancelled">cancelled</option>
                              </select>
                            </label>
                            <button className="button secondary" disabled={busy}>
                              Update status
                            </button>
                          </form>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && <p>No records on this page.</p>}
          </div>
          {section === 'products' && (
            <details className="admin-editor">
              <summary>Add a product option</summary>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  void mutate(
                    `/admin/products/${f.get('product')}/variants`,
                    { name: f.get('name'), sku: f.get('sku') },
                    'POST',
                    productSchema,
                  );
                }}
              >
                <label className="form-field">
                  Product
                  <select name="product" required>
                    {rows.map((r) => (
                      <option value={value(r, 'id')} key={value(r, 'id')}>
                        {value(r, 'name')}
                      </option>
                    ))}
                  </select>
                </label>
                {textField('Option name', 'name')}
                {textField('SKU', 'sku')}
                <button className="button primary" disabled={busy}>
                  Add option
                </button>
              </form>
            </details>
          )}
          <div className="pagination">
            <button
              className="button secondary"
              disabled={page === 1 || section === 'categories'}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span>Page {page}</span>
            <button
              className="button secondary"
              disabled={
                rows.length < (section === 'inventory' ? 50 : 20) || section === 'categories'
              }
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
