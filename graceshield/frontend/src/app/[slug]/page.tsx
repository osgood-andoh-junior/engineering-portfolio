import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowUpRight } from 'lucide-react';
import { information, faqs } from '@/data/information';
import { canonical } from '@/lib/metadata';
type Props = { params: Promise<{ slug: string }> };
export const dynamicParams = false;
export function generateStaticParams() {
  return [...Object.keys(information), 'faq'].map((slug) => ({ slug }));
}
export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  return {
    alternates: information[slug] || slug === 'faq' ? canonical(`/${slug}`) : undefined,
    title:
      slug === 'faq'
        ? 'Frequently asked questions'
        : (information[slug]?.eyebrow ?? 'Page not found'),
  };
}
export default async function InfoPage({ params }: Props) {
  const { slug } = await params;
  if (slug === 'faq')
    return (
      <div className="wrap information-page page-space">
        <div className="page-heading">
          <p className="eyebrow">A LITTLE HELP ALONG THE WAY</p>
          <h1>
            Good questions.
            <br />
            Clear answers.
          </h1>
          <p>Everything you need to know about this GraceShield preview.</p>
        </div>
        <div className="faq-list">
          {faqs.map(([q, a]) => (
            <details key={q}>
              <summary>{q}</summary>
              <p>{a}</p>
            </details>
          ))}
        </div>
        <Link href="/contact" className="text-link">
          Contact information <ArrowUpRight size={16} />
        </Link>
      </div>
    );
  const page = information[slug];
  if (!page) notFound();
  return (
    <div className="wrap information-page page-space">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/">Home</Link>
        <span>/</span>
        <span>{page.eyebrow}</span>
      </nav>
      <div className="page-heading">
        <p className="eyebrow">{page.eyebrow}</p>
        <h1>{page.title}</h1>
        <p>{page.intro}</p>
      </div>
      <div className="information-body">
        {page.sections.map((s) => (
          <section key={s.heading}>
            <h2>{s.heading}</h2>
            <p>{s.body}</p>
          </section>
        ))}
      </div>
      <div className="info-links">
        <Link href="/shop" className="button primary">
          Explore the collection <ArrowUpRight size={16} />
        </Link>
        <Link href="/faq" className="text-link">
          Visit our FAQs <ArrowUpRight size={16} />
        </Link>
      </div>
    </div>
  );
}
