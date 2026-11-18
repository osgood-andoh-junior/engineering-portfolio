import { z } from 'zod';
export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
    public code = 'network_error',
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  schema: z.ZodType<T>,
  options: RequestInit = {},
): Promise<T> {
  try {
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    if (options.method && !['GET', 'HEAD'].includes(options.method)) {
      const response = await fetch('/api/v1/auth/session', {
        credentials: 'same-origin',
        cache: 'no-store',
      });
      if (!response.ok)
        throw new ApiError(
          'The account service is unavailable. Please try again.',
          response.status,
        );
      const session = z.object({ csrf: z.string().min(20) }).parse(await response.json());
      headers.set('X-CSRF-Token', session.csrf);
    }
    const response = await fetch(`/api/v1${path}`, {
      ...options,
      headers,
      credentials: 'same-origin',
      cache: 'no-store',
      signal: options.signal ?? AbortSignal.timeout(15000),
    });
    const data: unknown = await response.json();
    if (!response.ok) {
      const error = z
        .object({ error: z.object({ message: z.string(), code: z.string() }) })
        .safeParse(data);
      throw new ApiError(
        error.success ? error.data.error.message : 'The service could not complete this request.',
        response.status,
        error.success ? error.data.error.code : 'service_error',
      );
    }
    return schema.parse(data);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      'The service is unavailable or returned an invalid response. Please try again.',
    );
  }
}
export const messageSchema = z.object({ message: z.string() });
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.email(),
  name: z.string(),
  verified: z.boolean(),
  roles: z.array(z.string()),
});
export type CustomerProfile = z.infer<typeof userSchema>;
export const orderSchema = z.object({
  id: z.string().uuid(),
  reference: z.string(),
  status: z.enum([
    'pending_payment',
    'paid',
    'processing',
    'shipped',
    'delivered',
    'cancelled',
    'refunded',
  ]),
  subtotal: z.number().int().nonnegative(),
  shipping: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
  currency: z.literal('GHS'),
  expiresAt: z.string(),
  createdAt: z.string(),
  items: z.array(
    z.object({
      name: z.string(),
      quantity: z.number().int().positive(),
      unitPrice: z.number().int().nonnegative(),
      sku: z.string(),
    }),
  ),
  paymentAvailable: z.literal(false),
  nextSteps: z.string(),
});
export type Order = z.infer<typeof orderSchema>;
export function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : 'Something went wrong. Please try again.';
}
