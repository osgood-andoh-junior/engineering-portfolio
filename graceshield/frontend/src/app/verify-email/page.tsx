import { TokenForm } from '@/features/account/token-form';
export const metadata = { title: 'Verify your email', referrer: 'no-referrer' as const };
export default function Page() {
  return (
    <div className="wrap information-page page-space">
      <div className="page-heading">
        <h1>Verify your email.</h1>
        <p>Confirm the single-use link sent to your address.</p>
      </div>
      <TokenForm mode="verify" />
    </div>
  );
}
