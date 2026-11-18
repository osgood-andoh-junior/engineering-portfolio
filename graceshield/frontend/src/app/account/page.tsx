import { AccountPanel } from '@/features/account/account-panel';
export const metadata = { title: 'Your account' };
export default function Page() {
  return (
    <div className="wrap page-space">
      <div className="page-heading">
        <p className="eyebrow">YOUR GRACESHIELD</p>
        <h1>Your account.</h1>
      </div>
      <AccountPanel ordersOnly={false} />
    </div>
  );
}
