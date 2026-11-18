import { AccountForm } from '@/features/account/account-form';
import { canonical } from '@/lib/metadata';
export const metadata = { title: 'Sign in preview', alternates: canonical('/login') };
export default function Login() {
  return (
    <div className="wrap auth-page">
      <AccountForm />
    </div>
  );
}
