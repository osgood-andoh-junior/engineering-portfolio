import { siteOrigin } from './config';
export function canonical(path: string) {
  return siteOrigin ? { canonical: new URL(path, siteOrigin).href } : undefined;
}
