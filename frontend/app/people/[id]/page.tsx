'use client';

import Link from 'next/link';
import { use } from 'react';
import { useEffect, useState } from 'react';
import { getPerson, getRankings, Person, Ranking } from '../../../lib/api';
import { PageTitle, PersonAvatar, Shell } from '../../components';

export default function ProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [person, setPerson] = useState<Person | null>(null);
  const [matches, setMatches] = useState<Ranking[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    getPerson(id).then(setPerson).catch(() => setError('Profile not found.'));
    getRankings(id).then(setMatches).catch(() => {});
  }, [id]);

  return <Shell><section className="content">
    {error && <div className="notice">{error}</div>}
    {person && <>
      <PageTitle eyebrow="AI COMPATIBILITY SIMULATION" title={person.name} detail={person.profession || 'Profile analysis pending'}>
        <span className={`source-tag ${person.source_type === 'fixture' ? 'fixture' : ''}`}>{person.source_type === 'fixture' ? 'FIXTURE MODE' : 'PUBLIC-PROFILE SIMULATION'}</span>
      </PageTitle>
      {person.simulation_notice && <div className="simulation-notice">{person.simulation_notice}</div>}
      <div className="profile-head"><PersonAvatar person={person} size="large" />
        <div className="profile-head-copy"><h2>{person.name}</h2><p>{person.profile_summary}</p>
          <div className="source-links">
            {person.linkedin_url ? <a href={person.linkedin_url} target="_blank" rel="noreferrer">LinkedIn ↗</a> : <span>LinkedIn unavailable</span>}
            {person.instagram_url ? <a href={person.instagram_url} target="_blank" rel="noreferrer">Instagram ↗</a> : <span>Instagram unavailable</span>}
          </div>
        </div>
        <div className="agent-status"><span className="status-dot" /> SIMULATION {person.profile ? 'READY' : 'PENDING'}<small>{person.simulation_mode.toUpperCase()}</small></div>
      </div>
      <div className="profile-columns">
        <section className="panel"><div className="panel-title"><span>PROFILE ANALYSIS</span><span className="panel-mark">AI</span></div>
          {[['Profession', person.profile?.profession ? [person.profile.profession] : []], ['Education', person.profile?.education ? [person.profile.education] : []], ['Interests', person.profile?.interests], ['Hobbies', person.profile?.hobbies], ['Lifestyle', person.profile?.lifestyle], ['Conversation topics', person.profile?.conversation_topics], ['Preferences', person.profile?.preferences]].map(([label, values]) => <div className="signal-row" key={label as string}>
            <b>{label}</b><div className="signal-list">{((values as string[]) || []).length ? (values as string[]).map(value => <span key={value}>{value}</span>) : <span className="muted">No supported detail</span>}</div>
          </div>)}
          <p className="grounding-note">Only supported, non-sensitive public-profile details are summarized. Missing details remain unknown.</p>
        </section>
        <section className="panel agent-panel"><div className="panel-title"><span>SIMULATED PERSON AGENT</span><span className="agent-pill"><i /> AI SIMULATION</span></div>
          <div className="agent-portrait"><PersonAvatar person={person} /><div><strong>Profile-based AI simulation</strong><small>NOT THE REAL PERSON</small></div></div>
          <p>This AI agent is generated from public profile information for an AI compatibility simulation. It does not speak for this person, and does not imply participation or endorsement.</p>
          <div className="agent-fact"><span>KNOWN SIGNALS</span><b>{person.profile?.interests?.length || 0} interests · {person.profile?.hobbies?.length || 0} hobbies</b></div>
        </section>
      </div>
      <div className="section-heading match-heading"><div><div className="eyebrow">SIMULATED EXCHANGES</div><h2>Compatibility rankings</h2></div></div>
      <p className="grounding-note">Rankings describe only generated AI conversations; they are not claims about actual preferences or compatibility.</p>
      {matches.length ? <div className="match-list">{matches.slice(0, 5).map((match, index) => <article className="match-row" key={match.person.id}>
        <span className="match-rank">0{index + 1}</span><PersonAvatar person={match.person} />
        <div className="match-name"><b>{match.person.name}</b><small>{match.person.profession}</small></div>
        <div className="match-reason">{match.reason}</div><div className="match-score">{Math.round(match.score)}<small>%</small></div>
        <Link className="button button-outline small-button" href={`/date/${match.date_id}`}>View simulation ↗</Link>
      </article>)}</div> : <p className="muted">No simulated exchanges have been ranked yet.</p>}
    </>}
  </section></Shell>;
}
