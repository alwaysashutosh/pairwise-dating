'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { analyzeProfile } from '../../lib/api';
import { PageTitle, Shell } from '../components';

export default function AnalyzePage() {
  const router = useRouter();
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [instagramUrl, setInstagramUrl] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusStep, setStatusStep] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!linkedinUrl.trim() && !instagramUrl.trim()) {
      setError('Please provide at least one public profile URL (LinkedIn or Instagram).');
      return;
    }

    setError('');
    setLoading(true);
    setStatusStep('1/4: Ingesting public profiles via Apify adapters...');

    try {
      setTimeout(() => setStatusStep('2/4: Normalizing profile text & running Gemini 2.5 Flash analysis...'), 2000);
      setTimeout(() => setStatusStep('3/4: Generating Person Agent & simulating agent date...'), 5000);

      const result = await analyzeProfile({
        linkedin_url: linkedinUrl.trim() || undefined,
        instagram_url: instagramUrl.trim() || undefined,
        name: name.trim() || undefined,
      });

      setStatusStep('4/4: Complete! Opening profile page...');
      setTimeout(() => {
        router.push(`/people/${result.id}`);
      }, 1000);
    } catch (err: unknown) {
      setLoading(false);
      setStatusStep('');
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Profile analysis failed. Please verify the URLs and try again.');
      }
    }
  };

  return (
    <Shell>
      <section className="content">
        <PageTitle
          eyebrow="PUBLIC PROFILE SIMULATION"
          title="Analyze Profile"
          detail="Paste a public LinkedIn and Instagram URL to ingest, normalize, and analyze with Gemini 2.5 Flash and run agent-to-agent simulations."
        />

        <div className="simulation-notice">
          <b>GEMINI 2.5 FLASH · LIVE AGENT SIMULATION</b>
          <p>
            Public-profile simulations extract supported non-sensitive details. Real people are not represented as participants or endorsers.
          </p>
        </div>

        <div className="hero-band" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: '640px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {error && <div className="notice">{error}</div>}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.05em', color: 'var(--text-muted, #94a3b8)' }}>
                DISPLAY NAME (OPTIONAL)
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Alex Morgan"
                disabled={loading}
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.15)',
                  background: 'rgba(15,23,42,0.6)',
                  color: '#fff',
                  fontSize: '1rem',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.05em', color: 'var(--text-muted, #94a3b8)' }}>
                LINKEDIN URL
              </label>
              <input
                type="url"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                placeholder="https://www.linkedin.com/in/username"
                disabled={loading}
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.15)',
                  background: 'rgba(15,23,42,0.6)',
                  color: '#fff',
                  fontSize: '1rem',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.05em', color: 'var(--text-muted, #94a3b8)' }}>
                INSTAGRAM URL
              </label>
              <input
                type="url"
                value={instagramUrl}
                onChange={(e) => setInstagramUrl(e.target.value)}
                placeholder="https://www.instagram.com/username"
                disabled={loading}
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.15)',
                  background: 'rgba(15,23,42,0.6)',
                  color: '#fff',
                  fontSize: '1rem',
                }}
              />
            </div>

            <button
              type="submit"
              className="button button-primary"
              disabled={loading}
              style={{
                marginTop: '0.5rem',
                padding: '0.85rem 1.5rem',
                fontSize: '1rem',
                fontWeight: 600,
                justifyContent: 'center',
                cursor: loading ? 'wait' : 'pointer',
              }}
            >
              {loading ? 'ANALYZING PROFILE...' : 'ANALYZE PROFILE ↗'}
            </button>

            {loading && statusStep && (
              <div className="notice" style={{ background: 'rgba(59,130,246,0.15)', borderColor: 'rgba(59,130,246,0.4)', color: '#60a5fa' }}>
                <span className="status-dot" style={{ background: '#60a5fa' }} /> {statusStep}
              </div>
            )}
          </form>
        </div>
      </section>
    </Shell>
  );
}
