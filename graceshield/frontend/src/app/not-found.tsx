import Link from 'next/link';
import { BookOpen } from 'lucide-react';
export default function NotFound() {
  return (
    <div className="wrap empty-state not-found">
      <BookOpen size={48} />
      <p className="eyebrow">404 · A PAGE YET TO BE WRITTEN</p>
      <h1>This chapter is missing.</h1>
      <p>We couldn’t find that page. Let’s turn back to something familiar.</p>
      <Link href="/" className="button primary">
        Back to the beginning ↗
      </Link>
    </div>
  );
}
