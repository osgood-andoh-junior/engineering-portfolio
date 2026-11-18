import 'server-only';
import { z } from 'zod';
export async function serverApi<T>(
  path: string,
  schema: z.ZodType<T>,
): Promise<{ status: number; data: T | null }> {
  const origin = process.env.API_INTERNAL_URL ?? 'http://127.0.0.1:8000';
  if (!z.url().safeParse(origin).success || !['http:', 'https:'].includes(new URL(origin).protocol))
    throw new Error('API_INTERNAL_URL must be an HTTP(S) origin');
  try {
    const response = await fetch(`${origin}/api/v1${path}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) return { status: response.status, data: null };
    const parsed = schema.safeParse(await response.json());
    return {
      status: parsed.success ? response.status : 502,
      data: parsed.success ? parsed.data : null,
    };
  } catch {
    return { status: 503, data: null };
  }
}
