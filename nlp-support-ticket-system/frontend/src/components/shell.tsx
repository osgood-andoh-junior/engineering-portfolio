"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
const links = [["/", "Dashboard", "◫"], ["/tickets", "Tickets", "≡"], ["/classify", "Classify Ticket", "↗"], ["/training", "Training", "⚙"], ["/models", "Models", "◈"], ["/experiments", "Experiments", "⌘"]];
export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return <div className="app-shell"><aside className="sidebar">
    <Link href="/" className="brand"><span className="brand-mark">ti</span><span>Ticket intelligence<small>NLP LABORATORY</small></span></Link>
    <div className="nav-label">WORKSPACE</div><nav aria-label="Main navigation">{links.map(([href, label, icon]) => <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined} className={pathname === href ? "nav-item active" : "nav-item"}><span aria-hidden="true">{icon}</span>{label}</Link>)}</nav>
    <div className="sidebar-note"><span className="status-dot" /> Learning environment<p>Your experiments.<br />Your implementations.</p><small>V1 · LOCAL WORKSPACE</small></div>
  </aside><div className="workspace"><header className="topbar"><span>Workspace <span className="separator">/</span> <strong>NLP Support-Ticket Intelligence</strong></span><span className="pill">Multiclass classification</span></header><main id="main">{children}</main><footer>Built for learning. Powered by your models.<span>6 categories · 6 experiments</span></footer></div></div>;
}
