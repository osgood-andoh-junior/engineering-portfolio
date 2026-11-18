'use client';
import Link from 'next/link';
import { LockKeyhole } from 'lucide-react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api, errorMessage, messageSchema, userSchema } from '@/lib/api';
export function AccountForm({ registration = false }: { registration?: boolean }) {
  const router = useRouter();
  const [message, setMessage] = useState('');
  const [failure, setFailure] = useState('');
  const schema = z.object({
    name: registration ? z.string().trim().min(2, 'Enter your name.') : z.string(),
    email: z.email('Enter a valid email address.'),
    password: z.string().min(12, 'Use at least 12 characters.').max(128),
  });
  type Fields = z.infer<typeof schema>;
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Fields>({ resolver: zodResolver(schema), defaultValues: { name: '' } });
  return (
    <div className="auth-card">
      <LockKeyhole size={28} />
      <p className="eyebrow">YOUR GRACESHIELD</p>
      <h1>{registration ? 'A new chapter starts here.' : 'Welcome back.'}</h1>
      <p>
        {registration
          ? 'Your future account for everyday essentials.'
          : 'Your essentials, all in one place.'}
      </p>
      <div className="notice">
        <p>
          Accounts use the configured local backend and managed development database. Use a unique
          development password. Email verification is required for checkout.
        </p>
      </div>
      <form
        noValidate
        onSubmit={handleSubmit(async (data) => {
          setFailure('');
          setMessage('');
          try {
            if (registration) {
              const result = await api('/auth/register', messageSchema, {
                method: 'POST',
                body: JSON.stringify(data),
              });
              setMessage(result.message);
            } else {
              await api('/auth/login', userSchema, {
                method: 'POST',
                body: JSON.stringify({ email: data.email, password: data.password }),
              });
              window.dispatchEvent(new Event('graceshield-auth'));
              router.push('/account');
              router.refresh();
            }
          } catch (e) {
            setFailure(errorMessage(e));
          }
        })}
      >
        <fieldset disabled={isSubmitting}>
          {registration && (
            <label className="form-field">
              Full name
              <input autoComplete="name" {...register('name')} aria-invalid={!!errors.name} />
            </label>
          )}
          <label className="form-field">
            Email address
            <input
              type="email"
              autoComplete="email"
              {...register('email')}
              aria-invalid={!!errors.email}
            />
          </label>
          <label className="form-field">
            Password
            <input
              type="password"
              autoComplete={registration ? 'new-password' : 'current-password'}
              {...register('password')}
              aria-invalid={!!errors.password}
            />
          </label>
          <button className="button primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Please wait…' : registration ? 'Create account' : 'Sign in'}
          </button>
          {Object.entries(errors).map(([name, error]) => (
            <p key={name} className="field-error" role="alert">
              {error.message}
            </p>
          ))}
          {failure && (
            <p className="field-error" role="alert">
              {failure}
            </p>
          )}
          {message && <p role="status">{message}</p>}
        </fieldset>
      </form>
      <p className="small">
        {registration ? 'Already exploring?' : 'New to GraceShield?'}{' '}
        <Link href={registration ? '/login' : '/register'}>
          {registration ? 'Sign in' : 'Create an account'}
        </Link>
      </p>
      {!registration && (
        <Link className="text-link" href="/forgot-password">
          Forgot your password?
        </Link>
      )}
      <Link href="/shop" className="text-link">
        Explore the collection ↗
      </Link>
    </div>
  );
}
