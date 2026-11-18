import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Sparkles,
  Layers3,
  HeartHandshake,
} from 'lucide-react';
import { listCategories } from '@/features/catalogue/repository';
import { productRepository } from '@/features/catalogue/repository';
import { ProductCard } from '@/components/ui/product-card';
import { CategoryIcon } from '@/components/ui/category-icon';
import { canonical } from '@/lib/metadata';
export const metadata = { alternates: canonical('/') };
export default async function Home() {
  const [result, categoryResult] = await Promise.all([
    productRepository.list({}),
    listCategories(),
  ]);
  const categories = categoryResult.ok ? categoryResult.data : [];
  return (
    <>
      <section className="hero wrap">
        <div className="hero-copy">
          <p className="eyebrow">
            <span /> LITTLE ESSENTIALS. BIG POSSIBILITIES.
          </p>
          <h1>
            For every
            <br />
            brighter <span>chapter.</span>
          </h1>
          <p className="hero-description">
            From the first page to the next big idea.
            <br />
            Discover books, stationery and everyday essentials
            <br className="desktop-only" /> for learning, working and creating.
          </p>
          <div className="hero-actions">
            <Link href="/shop" className="button primary">
              Explore the collection <ArrowUpRight size={18} />
            </Link>
            <Link href="/about" className="text-link">
              Our story <ArrowRight size={16} />
            </Link>
          </div>
          <div className="hero-footnote">
            <span className="mini-shield">
              <BookOpen size={16} />
            </span>
            <span>A little inspiration for school, work & everything in between.</span>
          </div>
        </div>
        <div className="hero-art">
          <div className="hero-art-label">
            <span>THE EVERYDAY COLLECTION</span>
            <span>01 / GRACESHIELD</span>
          </div>
          <Image
            src="/images/hero.svg"
            alt="Illustrated collection of a navy notebook, pencils and school essentials on a warm ivory desk"
            width={700}
            height={570}
            priority
          />
          <div className="art-caption">
            <span>
              Good things start
              <br />
              <strong>with a fresh page.</strong>
            </span>
            <span className="art-arrow">
              <ArrowUpRight size={27} />
            </span>
          </div>
          <span className="art-sample">ILLUSTRATIVE COLLECTION</span>
        </div>
      </section>
      <section className="values-strip">
        <div className="wrap values-grid">
          <div>
            <BookOpen />
            <span>
              <strong>For curious minds</strong>
              <small>Learning starts with possibility</small>
            </span>
          </div>
          <div>
            <Layers3 />
            <span>
              <strong>Everyday, thoughtfully chosen</strong>
              <small>School, work and creative moments</small>
            </span>
          </div>
          <div>
            <HeartHandshake />
            <span>
              <strong>Rooted in Ghana</strong>
              <small>Made for our everyday journeys</small>
            </span>
          </div>
        </div>
      </section>
      <section className="wrap section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">FIND YOUR EVERYDAY</p>
            <h2>A world of possibilities.</h2>
          </div>
          <Link href="/categories" className="text-link">
            All 11 categories <ArrowUpRight size={17} />
          </Link>
        </div>
        <div className="category-preview">
          {categories.slice(0, 6).map((c) => (
            <Link className="category-tile" href={`/categories/${c.slug}`} key={c.id}>
              <span className="category-icon" style={{ background: c.color }}>
                <CategoryIcon name={c.icon} size={31} />
              </span>
              <h3>{c.shortName}</h3>
              <span className="category-explore">
                Explore <ArrowRight size={13} />
              </span>
            </Link>
          ))}
        </div>
      </section>
      <section className="wrap collection-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">SMALL THINGS, EVERYDAY JOY</p>
            <h2>Meet your new essentials.</h2>
          </div>
          <Link href="/shop" className="text-link">
            Explore all products <ArrowUpRight size={17} />
          </Link>
        </div>
        <p className="demo-note">
          Development catalogue. Any seeded demonstration products are marked SAMPLE.
        </p>
        <div className="product-grid">
          {result.ok ? (
            result.data.products.slice(0, 4).map((p) => <ProductCard key={p.id} product={p} />)
          ) : (
            <p role="alert">The sample collection could not be loaded. Please try again.</p>
          )}
        </div>
      </section>
      <section className="wrap editorial-grid">
        <Link className="editorial-card school-edit" href="/categories/school-supplies">
          <div>
            <p className="eyebrow">READY FOR WHAT’S NEXT</p>
            <h2>
              Big dreams.
              <br />
              Little essentials.
            </h2>
            <p>A fresh start for every school day.</p>
            <span className="text-link">
              Explore school supplies <ArrowUpRight size={17} />
            </span>
          </div>
          <Image
            src="/images/backpack.svg"
            alt="Illustration of a school backpack"
            width={300}
            height={300}
          />
        </Link>
        <Link className="editorial-card creative-edit" href="/categories/arts-crafts">
          <div>
            <p className="eyebrow">LET IDEAS TAKE COLOUR</p>
            <h2>
              A little more
              <br />
              imagination.
            </h2>
            <p>Make something that’s all you.</p>
            <span className="text-link">
              Discover arts & crafts <ArrowUpRight size={17} />
            </span>
          </div>
          <Image
            src="/images/pencils.svg"
            alt="Illustration of colourful pencils"
            width={300}
            height={300}
          />
        </Link>
      </section>
      <section className="story-strip wrap">
        <span className="story-spark">
          <Sparkles size={27} />
        </span>
        <p>
          For the learner. The thinker. The everyday creator.
          <br />
          <strong>There’s a little GraceShield in every new beginning.</strong>
        </p>
        <Link href="/about" className="text-link">
          Get to know us <ArrowUpRight size={17} />
        </Link>
      </section>
    </>
  );
}
