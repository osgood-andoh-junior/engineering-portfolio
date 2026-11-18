import { TokenForm } from '@/features/account/token-form';
export const metadata = { title: 'Set a new password', referrer: 'no-referrer' as const };
export default function Page() {
  return (
    <div className="wrap information-page page-space">
      <div className="page-heading">
        <h1>A fresh start.</h1>
        <p>
          Use a unique password with 12–128 characters. Resetting invalidates existing sessions.
        </p>
      </div>
      <TokenForm mode="reset" />
    </div>
  );
}
