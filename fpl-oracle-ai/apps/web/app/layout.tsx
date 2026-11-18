import type { Metadata } from 'next';
import { Providers } from '@/components/providers';
import './globals.css';
export const metadata: Metadata = {title:'FPL Oracle AI · Football intelligence',description:'Evidence-led FPL predictions, coaching intelligence and squad optimization.'};
export default function Layout({children}:{children:React.ReactNode}) {return <html lang="en"><body><Providers>{children}</Providers></body></html>}
