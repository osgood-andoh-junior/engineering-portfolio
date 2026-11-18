import { notFound } from 'next/navigation';
import { AdminPanel } from '@/features/admin/admin-panel';
import { sections } from '@/features/admin/sections';
export const metadata = { title: 'Store management' };
export default async function Page({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!sections.includes(section as (typeof sections)[number])) notFound();
  return (
    <div className="wrap page-space">
      <div className="page-heading">
        <p className="eyebrow">GRACESHIELD ADMINISTRATION</p>
        <h1>{section.charAt(0).toUpperCase() + section.slice(1)}.</h1>
      </div>
      <AdminPanel section={section as (typeof sections)[number]} />
    </div>
  );
}
