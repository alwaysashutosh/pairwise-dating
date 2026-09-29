'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { Person } from '../lib/api';

const nav = [['/', 'Overview'], ['/people', 'Profiles'], ['/rankings', 'Rankings'], ['/analyze', 'Analyze Profile']];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return <div className="shell"><aside className="sidebar">
    <Link className="brand" href="/"><span className="brand-mark">P</span><span>Pairwise<small>AI COMPATIBILITY SIMULATION</small></span></Link>
    <div className="nav-label">WORKSPACE</div><nav>{nav.map(([href, label]) => <Link key={href} className={`nav-link ${path === href || href !== '/' && path.startsWith(href) ? 'active' : ''}`} href={href}>{label}</Link>)}</nav>
    <div className="sidebar-foot"><span className="status-dot" /> SIMULATION ENVIRONMENT <span className="version">v1.0</span></div>
  </aside><main className="main"><header className="topbar"><div className="breadcrumb">AI COMPATIBILITY SIMULATION / <b>{path === '/' ? 'OVERVIEW' : path.split('/')[1]?.toUpperCase()}</b></div><div className="top-state"><span className="status-dot" /> SIMULATED AGENTS</div></header>{children}</main></div>;
}

export function PersonAvatar({ person, size = 'normal' }: { person: Person; size?: 'normal' | 'large' }) {
  const colors = ['sage', 'rose', 'gold', 'blue'];
  const color = colors[(person.name.charCodeAt(0) + person.name.length) % colors.length];
  return <div className={`avatar ${color} ${size === 'large' ? 'avatar-large' : ''}`} aria-label={`Initials for ${person.name}`}><span>{person.name.split(' ').map(n => n[0]).slice(0, 2).join('')}</span></div>;
}

export function PersonTile({ person, score }: { person: Person; score?: number }) {
  const fixture = person.source_type === 'fixture';
  return <article className="person-tile"><div className="tile-top"><PersonAvatar person={person} /><span className={`source-tag ${fixture ? 'fixture' : ''}`}>{fixture ? 'FIXTURE MODE' : 'PUBLIC-PROFILE SIMULATION'}</span></div>
    <h3>{person.name}</h3><p className="role">{person.profession || 'Analysis pending'}</p><p className="tile-summary">{person.profile_summary}</p>
    <div className="tile-bottom"><span>{person.profile?.interests?.slice(0, 2).join(' · ') || 'No profile signals'}</span>{score !== undefined && <b>{Math.round(score)}%</b>}</div>
    <Link className="tile-link" href={`/people/${person.id}`}>View profile <span>↗</span></Link></article>;
}

export function PageTitle({ eyebrow, title, detail, children }: { eyebrow: string; title: string; detail?: string; children?: React.ReactNode }) {
  return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{detail && <p>{detail}</p>}</div>{children}</div>;
}
