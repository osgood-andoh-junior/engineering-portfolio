import Link from 'next/link';
import { ArrowUpRight } from 'lucide-react';
import { Brand } from './brand';
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="wrap footer-grid">
        <div className="footer-brand">
          <Brand />
          <p>
            Thoughtful essentials for learning,
            <br />
            creating and everyday possibilities.
          </p>
          <span className="footer-note">Made with Ghana in mind.</span>
        </div>
        <div>
          <h2>Explore</h2>
          <Link href="/shop">Shop all</Link>
          <Link href="/categories">Our categories</Link>
          <Link href="/about">Our story</Link>
          <Link href="/account">My account</Link>
        </div>
        <div>
          <h2>We’re here to help</h2>
          <Link href="/contact">Contact us</Link>
          <Link href="/faq">Frequently asked questions</Link>
          <Link href="/delivery">Delivery information</Link>
          <Link href="/returns">Returns & refunds</Link>
        </div>
        <div className="footer-invitation">
          <h2>A new chapter is coming.</h2>
          <p>Explore the preview. Discover what GraceShield could bring to your day.</p>
          <Link href="/shop">
            Find your essentials <ArrowUpRight size={16} />
          </Link>
          <small>Demonstration only. Shopping services are not live.</small>
        </div>
      </div>
      <div className="wrap footer-bottom">
        <span>© {new Date().getFullYear()} GraceShield. Frontend preview.</span>
        <div>
          <Link href="/privacy">Privacy policy</Link>
          <Link href="/terms">Terms & conditions</Link>
        </div>
        <span>Ghana · GHS</span>
      </div>
    </footer>
  );
}
