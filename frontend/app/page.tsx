'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getPeople, getStats, Person } from '../lib/api';
import { PageTitle, PersonAvatar, PersonTile, Shell } from './components';

export default function Home() {
  const [people, setPeople] = useState<Person[]>([]);
  const [stats, setStats] = useState({ people: 0, agents: 0, dates: 0, rankings: 0 });
  const [error, setError] = useState('');
  useEffect(() => {
    Promise.all([getPeople(), getStats()]).then(([profiles, counts]) => { setPeople(profiles); setStats(counts); })
      .catch(() => setError('API unavailable. Start the backend to load the simulation.'));
  }, []);
  const modes = new Set(people.map(person => person.source_type === 'fixture' ? 'fixture' : 'public'));
  const modeLabel = !people.length ? 'SIMULATION NOT RUN' : modes.size > 1 ? 'FIXTURE + PUBLIC-PROFILE SIMULATIONS' : modes.has('fixture') ? 'FIXTURE MODE' : 'PUBLIC-PROFILE SIMULATION';

  return <Shell><section className="content">
    <PageTitle eyebrow="AI ENGINEERING ASSESSMENT" title="AI Compatibility Simulation" detail="Profile-grounded AI agents exchange simulated messages; compatibility scores describe only that generated exchange." />
    <div className="simulation-notice"><b>{modeLabel}</b><p>Public-profile records are not represented as participants or endorsers. Fixture profiles are fictional demos. Rankings do not describe real people's dating preferences.</p></div>
    <div className="hero-band"><div className="hero-copy"><span className="live-label"><i /> SIMULATION WORKSPACE</span>
      <h2>Compatibility is a simulation, not a claim.</h2>
      <p>AI agents are generated from normalized profile information and converse only with each other. No messages are sent to the people described by public profiles.</p>
      <div className="hero-actions"><Link className="button button-primary" href="/people">Explore profiles <span>↗</span></Link><Link className="button button-outline" href="/analyze">Analyze a Profile ✦</Link><Link className="button button-outline" href="/rankings">View simulation rankings</Link></div>
    </div><div className="orbit-scene"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-center"><span>↔</span></div>
      <div className="orbit-person orbit-left"><PersonAvatar person={people[0] || { name: 'AI Agent A' } as Person} /></div>
      <div className="orbit-person orbit-right"><PersonAvatar person={people[1] || { name: 'AI Agent B' } as Person} /></div><div className="orbit-caption">AGENT A · AGENT B · SIMULATED EXCHANGE</div>
    </div></div>
    <div className="stats-grid">{[['PROFILES', stats.people, 'Fixture and public-profile records'], ['AI AGENTS', stats.agents, 'Profile-based simulations'], ['EXCHANGES', stats.dates, 'Saved AI conversations'], ['RANKINGS', stats.rankings, 'Simulation scores']].map(([label, value, sub]) => <div className="stat" key={label as string}><div>{label}</div><strong>{value}</strong><small>{sub}</small></div>)}</div>
    <div className="section-heading"><div><div className="eyebrow">PROFILE RECORDS</div><h2>Simulation profiles</h2></div><Link href="/people" className="text-link">Browse profiles <span>→</span></Link></div>
    {error && <div className="notice">{error}</div>}
    <div className="people-grid">{people.slice(0, 4).map(person => <PersonTile key={person.id} person={person} />)}</div>
  </section></Shell>;
}
