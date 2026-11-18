'use client';
import Link from 'next/link';
export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="wrap empty-state" role="alert">
      <h1>A little pause in your day.</h1>
      <p>We couldn’t load this page. Please try again.</p>
      <button className="button primary" onClick={reset}>
        Try again
      </button>
      <Link href="/" className="text-link">
        Back to home
      </Link>
    </div>
  );
}
