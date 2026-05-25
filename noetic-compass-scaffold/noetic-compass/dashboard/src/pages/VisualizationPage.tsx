import { useState } from 'react';
import {
  MOCK_PROFILE_A,
  MOCK_PROFILE_LACUNARIC,
  RadialArchitectureDisplay,
} from '../components/RadialArchitectureDisplay';
import { TemporalCognitiveScore } from '../components/TemporalCognitiveScore';
import { Card } from '../components/shared/Card';
import type { CognitiveStateData, Domain } from '../lib/mandala_types';
import { DOMAIN_NAMES } from '../lib/mandala_types';

const PROFILES: readonly {
  id: string;
  label: string;
  description: string;
  data: CognitiveStateData;
}[] = [
  {
    id: 'balanced',
    label: 'Balanced reference',
    description: 'A readable profile with activity across the main CAS axes.',
    data: MOCK_PROFILE_A,
  },
  {
    id: 'lacunarity',
    label: 'Visible gaps',
    description: 'A profile where structural absence becomes both visible and audible.',
    data: MOCK_PROFILE_LACUNARIC,
  },
];

export function VisualizationPage() {
  const [profileId, setProfileId] = useState(PROFILES[0].id);
  const [activeDomain, setActiveDomain] = useState<Domain | null>(null);
  const activeProfile = PROFILES.find((profile) => profile.id === profileId) ?? PROFILES[0];

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="relative overflow-hidden rounded-2xl border border-accent-teal/20 bg-gradient-to-br from-dark-800 via-dark-900 to-dark-900 p-6 shadow-[0_0_50px_rgba(45,212,191,0.06)]">
        <div className="absolute -right-20 -top-28 h-72 w-72 rounded-full bg-accent-cyan/10 blur-3xl" />
        <div className="absolute -bottom-28 left-1/3 h-64 w-64 rounded-full bg-accent-teal/10 blur-3xl" />
        <div className="relative">
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="rounded-full border border-accent-teal/25 bg-accent-teal/[0.08] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-teal">
              Multi-Modal Cognitive Signature
            </span>
            <span className="rounded-full border border-accent-gold/25 bg-accent-gold/[0.08] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-gold">
              Audio requires Play
            </span>
          </div>
          <h1 className="max-w-3xl text-3xl font-black tracking-tight text-slate-100 sm:text-4xl">
            See and hear the same CAS structure.
          </h1>
          <p className="mt-3 max-w-3xl text-sm text-slate-400">
            Pick a profile. Inspect the state. Press play.
          </p>
        </div>
      </div>

      <Card title="Choose a profile">
        <div className="grid gap-3 md:grid-cols-2">
          {PROFILES.map((profile) => (
            <button
              key={profile.id}
              type="button"
              onClick={() => {
                setProfileId(profile.id);
                setActiveDomain(null);
              }}
              className={`rounded-xl border p-4 text-left transition-colors ${
                profile.id === profileId
                  ? 'border-accent-teal/45 bg-accent-teal/[0.08] text-slate-100'
                  : 'border-white/[0.08] bg-white/[0.03] text-slate-300 hover:border-accent-teal/25'
              }`}
            >
              <p className="text-sm font-semibold">{profile.label}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{profile.description}</p>
            </button>
          ))}
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <Card
          title="Radial Architecture Display"
          action={
            <span className="rounded-full border border-white/[0.08] px-3 py-1 text-xs text-slate-400">
              {activeDomain ? `Sounding ${activeDomain} ${DOMAIN_NAMES[activeDomain]}` : 'Idle'}
            </span>
          }
        >
          <RadialArchitectureDisplay
            data={activeProfile.data}
            title="Radial Architecture Display"
            highlightDomain={activeDomain}
          />
        </Card>

        <Card title="Temporal Cognitive Score">
          <TemporalCognitiveScore
            cognitiveState={activeProfile.data}
            onCurrentDomainChange={setActiveDomain}
          />
        </Card>
      </div>

      <Card title="Quick key">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
            <p className="text-sm font-semibold text-slate-100">Pitch means Noetic</p>
            <p className="mt-1 text-xs text-slate-500">Different primitive.</p>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
            <p className="text-sm font-semibold text-slate-100">Expression means Register</p>
            <p className="mt-1 text-xs text-slate-500">Different processing mode.</p>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
            <p className="text-sm font-semibold text-slate-100">Silence means lacunarity</p>
            <p className="mt-1 text-xs text-slate-500">Detected structural gap.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default VisualizationPage;
