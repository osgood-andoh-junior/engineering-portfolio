import { TokenForm } from '@/features/account/token-form';
export const metadata = { title: 'Reset your password' };
export default function Page() {
  return (
    <div className="wrap information-page page-space">
      <div className="page-heading">
        <h1>Forgot your password?</h1>
        <p>Email delivery must be configured. We’ll report if the service is unavailable.</p>
      </div>
      <TokenForm mode="request-reset" />
    </div>
  );
}
