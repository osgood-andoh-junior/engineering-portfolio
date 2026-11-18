import { AdminPanel } from '@/features/admin/admin-panel';
export const metadata = { title: 'Administration' };
export default function Page() {
  return (
    <div className="wrap page-space">
      <div className="page-heading">
        <p className="eyebrow">GRACESHIELD ADMINISTRATION</p>
        <h1>Store overview.</h1>
        <p>Metrics reflect stored records. Demonstration orders are development records.</p>
      </div>
      <AdminPanel />
    </div>
  );
}
