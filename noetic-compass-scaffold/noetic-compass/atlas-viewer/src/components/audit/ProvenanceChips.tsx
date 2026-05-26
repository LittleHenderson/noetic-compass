import type { CSSProperties } from 'react';
import {
  ACCENT_AMBER,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
} from '../../lib/designTokens';
import type {
  AuditStatus,
  ProvenanceChip as AuditProvenanceChip,
  ProvenanceChipId,
} from '../../lib/casHarnessAudit';
import { AuditPopover } from './AuditPopover';

export type ProvenanceProofKey =
  | 'model'
  | 'cas'
  | 'causal'
  | 'control'
  | 'output'
  | 'packet';

export type LegacyProvenanceChipState = 'verified' | 'pending' | 'missing' | 'failed';

export interface LegacyProvenanceChip {
  key: ProvenanceProofKey;
  state?: LegacyProvenanceChipState;
  detail?: string;
}

export interface ProvenanceChipsProps {
  chips?: AuditProvenanceChip[];
  proofs?: LegacyProvenanceChip[];
  className?: string;
}

const chipOrder: ProvenanceChipId[] = [
  'model_proof',
  'cas_readout',
  'causal_proof',
  'control_proof',
  'output_proof',
  'packet_proof',
];

const proofLabels: Record<ProvenanceChipId, string> = {
  model_proof: 'Model proof',
  cas_readout: 'CAS readout',
  causal_proof: 'Causal proof',
  control_proof: 'Control proof',
  output_proof: 'Output proof',
  packet_proof: 'Packet proof',
};

const stateLabels: Record<AuditStatus | 'pending', string> = {
  verified: 'Verified',
  present: 'Present',
  pending: 'Pending',
  missing: 'Missing',
  failed: 'Failed',
  unavailable: 'Unavailable',
};

const stateTone: Record<
  AuditStatus | 'pending',
  { color: string; border: string; fill: string }
> = {
  verified: {
    color: '#ccfbf1',
    border: 'rgba(45, 212, 191, 0.42)',
    fill: 'rgba(45, 212, 191, 0.11)',
  },
  present: {
    color: '#dbeafe',
    border: 'rgba(59, 130, 246, 0.36)',
    fill: 'rgba(59, 130, 246, 0.10)',
  },
  pending: {
    color: '#e2e8f0',
    border: 'rgba(148, 163, 184, 0.22)',
    fill: 'rgba(255, 255, 255, 0.04)',
  },
  missing: {
    color: '#fef3c7',
    border: 'rgba(251, 191, 36, 0.38)',
    fill: 'rgba(251, 191, 36, 0.10)',
  },
  failed: {
    color: '#ffe4e6',
    border: 'rgba(251, 113, 133, 0.40)',
    fill: 'rgba(251, 113, 133, 0.10)',
  },
  unavailable: {
    color: '#cbd5e1',
    border: 'rgba(148, 163, 184, 0.24)',
    fill: 'rgba(148, 163, 184, 0.06)',
  },
};

const legacyKeyMap: Record<ProvenanceProofKey, ProvenanceChipId> = {
  model: 'model_proof',
  cas: 'cas_readout',
  causal: 'causal_proof',
  control: 'control_proof',
  output: 'output_proof',
  packet: 'packet_proof',
};

const listStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  margin: 0,
  padding: 0,
  listStyle: 'none',
  fontFamily: FONT_FAMILY,
};

const chipStyle = (state: AuditStatus | 'pending'): CSSProperties => {
  const tone = stateTone[state];
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    minHeight: 32,
    padding: '6px 10px',
    borderRadius: 6,
    border: `1px solid ${tone.border}`,
    background: tone.fill,
    color: tone.color,
    fontSize: 12,
    fontWeight: 700,
    whiteSpace: 'nowrap',
  };
};

const dotStyle = (state: AuditStatus | 'pending'): CSSProperties => ({
  width: 7,
  height: 7,
  borderRadius: '50%',
  background:
    state === 'verified'
      ? ACCENT_TEAL
      : state === 'present'
        ? '#60a5fa'
        : state === 'missing'
          ? ACCENT_AMBER
          : state === 'failed'
            ? '#fb7185'
            : COLORS.textMuted,
});

const detailStyle: CSSProperties = {
  color: COLORS.textSecondary,
  fontWeight: 600,
};

interface NormalizedChip {
  id: ProvenanceChipId;
  name: string;
  status: AuditStatus | 'pending';
  detail?: string;
}

function normalizeChips(
  chips: AuditProvenanceChip[] | undefined,
  proofs: LegacyProvenanceChip[] | undefined,
): Map<ProvenanceChipId, NormalizedChip> {
  const byId = new Map<ProvenanceChipId, NormalizedChip>();

  chips?.forEach((chip) => {
    byId.set(chip.id, {
      id: chip.id,
      name: chip.name,
      status: chip.status,
      detail: chip.detail,
    });
  });

  proofs?.forEach((proof) => {
    const id = legacyKeyMap[proof.key];
    byId.set(id, {
      id,
      name: proofLabels[id],
      status: proof.state ?? 'pending',
      detail: proof.detail,
    });
  });

  return byId;
}

export function ProvenanceChips({
  chips,
  proofs,
  className,
}: ProvenanceChipsProps): JSX.Element {
  const byId = normalizeChips(chips, proofs);

  return (
    <ul
      aria-label="Audit provenance"
      className={className}
      role="list"
      style={listStyle}
    >
      {chipOrder.map((id) => {
        const chip = byId.get(id);
        const state = chip?.status ?? 'pending';
        return (
          <li key={id} style={chipStyle(state)}>
            <AuditPopover
              briefing={chip?.detail ?? 'This proof chip has not attached evidence yet.'}
              placement="top"
            >
              <span aria-hidden="true" style={dotStyle(state)} />
              <span>{chip?.name ?? proofLabels[id]}</span>
              <span style={detailStyle}>{stateLabels[state]}</span>
            </AuditPopover>
          </li>
        );
      })}
    </ul>
  );
}

export default ProvenanceChips;
