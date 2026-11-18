import { z } from 'zod';
const origin = z.url().refine((value) => ['https:', 'http:'].includes(new URL(value).protocol));
const configured = process.env.NEXT_PUBLIC_SITE_URL;
if (configured && !origin.safeParse(configured).success)
  throw new Error('NEXT_PUBLIC_SITE_URL must be an absolute HTTP(S) URL');
export const siteOrigin = configured ? new URL(configured) : undefined;
