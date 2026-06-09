import { useState, type CSSProperties } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AuditPopover } from '../components/audit/AuditPopover';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import {
  ACCENT_TEAL,
  COLORS,
  FONT_MONO,
  THEME,
  TONE_TINT,
} from '../lib/designTokens';

type LegalSectionId = 'legal' | 'privacy' | 'terms';

interface LegalSection {
  id: LegalSectionId;
  title: string;
  eyebrow: string;
  body: string[];
}

interface ClaimStatusDefinition {
  status: 'ACCEPT' | 'FLAG_FOR_HUMAN_REVIEW' | 'LICENSED' | 'NOT LICENSED' | 'OPEN' | 'present' | 'unavailable';
  summary: string;
}

const SECTIONS: LegalSection[] = [
  {
    id: 'legal',
    eyebrow: 'Public beta legal notice',
    title: 'Legal',
    body: [
      'CAS Harness is offered as a scoped public beta for model-audit evaluation. Results are evidence-backed product outputs, not legal advice, safety certification, or regulatory approval.',
      'Launch claim statuses must remain exact: ACCEPT, FLAG_FOR_HUMAN_REVIEW, LICENSED, NOT LICENSED, OPEN, present, and unavailable. A research result, archived packet, or retained anchor does not upgrade a customer-production claim by itself.',
      'Compliance program items including consent ledger, data-subject requests, residency controls, crypto-shred erasure, and SOC 2 evidence remain OPEN until production evidence is attached.',
    ],
  },
  {
    id: 'privacy',
    eyebrow: 'Public beta privacy notice',
    title: 'Privacy',
    body: [
      'Beta audit runs may send submitted prompts, target metadata, model connection details, run events, and Evidence Packet fields to the CAS Harness backend so the audit can be executed and verified.',
      'Do not submit regulated personal data, confidential customer data, or production secrets unless a separate written agreement says that workflow is approved. Data-rights operations and residency enforcement are OPEN.',
      'If a service, proof chip, receipt, or worker is unavailable, the UI should say unavailable rather than imply collection, retention, deletion, or verification that did not happen.',
    ],
  },
  {
    id: 'terms',
    eyebrow: 'Public beta terms',
    title: 'Terms',
    body: [
      'Beta access is provided for evaluation and feedback. CAS Harness may change, limit, suspend, or remove beta features while account-mode auth, quotas, billing, support, and hosted smoke coverage remain OPEN.',
      'Evidence Packet retention means the backend returned active Object Lock retention for that packet. If the returned mode is GOVERNANCE, copy must say GOVERNANCE. Do not call it COMPLIANCE unless the receipt says COMPLIANCE.',
      'License display is literal: LICENSED only when an entitlement signal is positive, NOT LICENSED only when it is explicitly negative, and OPEN when unresolved.',
    ],
  },
];

const sectionById = new Map(SECTIONS.map((section) => [section.id, section]));

const CLAIM_STATUS_DEFINITIONS: ClaimStatusDefinition[] = [
  {
    status: 'ACCEPT',
    summary:
      'A verifier-backed product decision that the evidence supports the claim. Do not use this for research-only or unresolved customer-production claims.',
  },
  {
    status: 'FLAG_FOR_HUMAN_REVIEW',
    summary:
      'The system found enough signal to preserve and escalate, but a human reviewer must decide before it becomes ACCEPT.',
  },
  {
    status: 'LICENSED',
    summary:
      'A positive entitlement signal is present for the account, model, or run.',
  },
  {
    status: 'NOT LICENSED',
    summary:
      'The entitlement check explicitly failed or returned a negative license signal.',
  },
  {
    status: 'OPEN',
    summary:
      'Unresolved launch work or an unfinished claim boundary. The product must not present it as complete until production evidence closes it.',
  },
  {
    status: 'present',
    summary:
      'The proof artifact or service signal was observed in this packet or run.',
  },
  {
    status: 'unavailable',
    summary:
      'The proof artifact or service signal was not returned or could not be checked; the UI must not imply it exists.',
  },
];

function sectionFromPath(pathname: string): LegalSection {
  const cleaned = pathname.replace(/^\/+/, '').split('/')[0] as LegalSectionId;
  return sectionById.get(cleaned) ?? sectionById.get('legal')!;
}

const headingStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 26,
  fontWeight: 850,
  letterSpacing: 0,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontFamily: FONT_MONO,
  fontSize: 11,
  fontWeight: 850,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const introStyle: CSSProperties = {
  margin: '8px 0 0',
  color: COLORS.textSecondary,
  fontSize: 13.5,
  lineHeight: 1.55,
};

const navStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  marginTop: 18,
};

const linkStyle = (active: boolean): CSSProperties => {
  const tone = active ? TONE_TINT.teal : TONE_TINT.muted;
  return {
    minHeight: 32,
    padding: '7px 10px',
    borderRadius: 6,
    border: `1px solid ${active ? tone.border : COLORS.borderSubtle}`,
    background: active ? tone.fillSoft : 'rgba(148, 163, 184, 0.06)',
    color: active ? tone.text : COLORS.textSecondary,
    fontFamily: THEME.fontFamily,
    fontSize: 12,
    fontWeight: 800,
    textDecoration: 'none',
  };
};

const blockStyle: CSSProperties = {
  display: 'grid',
  gap: 12,
  paddingTop: 18,
  borderTop: `1px solid ${COLORS.borderSubtle}`,
};

const bodyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13.5,
  lineHeight: 1.6,
};

const statusGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 8,
  marginTop: 18,
};

const statusButtonStyle = (active: boolean): CSSProperties => ({
  width: '100%',
  minHeight: 42,
  padding: '9px 10px',
  borderRadius: 6,
  border: `1px solid ${active ? TONE_TINT.teal.border : COLORS.borderSubtle}`,
  background: active ? TONE_TINT.teal.fillSoft : 'rgba(15, 23, 42, 0.44)',
  color: active ? TONE_TINT.teal.text : COLORS.textSecondary,
  cursor: 'help',
  fontFamily: FONT_MONO,
  fontSize: 11,
  fontWeight: 850,
  letterSpacing: 0,
  textAlign: 'left',
});

const legendHelpStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textMuted,
  fontSize: 12.5,
  lineHeight: 1.5,
};

const definitionPanelStyle: CSSProperties = {
  display: 'grid',
  gap: 6,
  minHeight: 92,
  marginTop: 12,
  padding: '13px 14px',
  borderRadius: 6,
  border: `1px solid ${TONE_TINT.teal.border}`,
  background: 'rgba(13, 148, 136, 0.10)',
};

const definitionStatusStyle: CSSProperties = {
  margin: 0,
  color: TONE_TINT.teal.text,
  fontFamily: FONT_MONO,
  fontSize: 11,
  fontWeight: 900,
  letterSpacing: 0,
};

const definitionTextStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.55,
};

const contactBlockStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
  padding: '12px 14px',
  borderRadius: 6,
  border: `1px solid ${TONE_TINT.teal.border}`,
  background: TONE_TINT.teal.fillSoft,
};

const contactLinkStyle: CSSProperties = {
  color: TONE_TINT.teal.text,
  fontWeight: 850,
  textDecoration: 'none',
};

export default function LegalPage(): JSX.Element {
  const location = useLocation();
  const active = sectionFromPath(location.pathname);
  const [selectedStatus, setSelectedStatus] = useState<ClaimStatusDefinition>(
    CLAIM_STATUS_DEFINITIONS.find((definition) => definition.status === 'OPEN')!,
  );

  return (
    <PageShell cardMaxWidth={820}>
      <GlassPanel intensity="regular" padding={26} ariaLabel="CAS Harness legal notices">
        <div style={{ display: 'grid', gap: 18 }}>
          <header>
            <p style={eyebrowStyle}>{active.eyebrow}</p>
            <h1 style={headingStyle}>{active.title}</h1>
            <p style={introStyle}>
              Public beta language for CAS Harness. These notices keep product
              claims tied to live evidence and leave unresolved launch work as OPEN.
            </p>
            <nav style={navStyle} aria-label="Legal notice sections">
              {SECTIONS.map((section) => (
                <Link
                  key={section.id}
                  to={`/${section.id}`}
                  style={linkStyle(section.id === active.id)}
                  aria-current={section.id === active.id ? 'page' : undefined}
                >
                  {section.title}
                </Link>
              ))}
            </nav>
          </header>

          <section style={blockStyle} aria-label={`${active.title} notice`}>
            {active.body.map((paragraph) => (
              <p key={paragraph} style={bodyStyle}>
                {paragraph}
              </p>
            ))}
          </section>

          <section style={contactBlockStyle} aria-label="CAS Compass contact">
            <p style={eyebrowStyle}>CAS Compass contact</p>
            <p style={bodyStyle}>
              CAS Compass is the public early-access surface for CAS Harness
              beta requests and contact routing. For beta access, support,
              privacy, terms, or security-routing questions, use{' '}
              <a href="mailto:hello@cascompass.ai" style={contactLinkStyle}>
                hello@cascompass.ai
              </a>
              {' '}or visit{' '}
              <a
                href="https://cascompass.ai/"
                style={contactLinkStyle}
                rel="noreferrer"
                target="_blank"
              >
                cascompass.ai
              </a>
              .
            </p>
          </section>

          <section style={blockStyle} aria-label="Claim status legend">
            <p style={eyebrowStyle}>Claim status legend</p>
            <p style={legendHelpStyle}>
              Hover, focus, or tap a status to see the exact product boundary it
              represents.
            </p>
            <div style={statusGridStyle}>
              {CLAIM_STATUS_DEFINITIONS.map((definition) => {
                const activeStatus = selectedStatus.status === definition.status;
                return (
                  <AuditPopover
                    key={definition.status}
                    block
                    briefing={definition.summary}
                    focusable={false}
                    placement="bottom"
                    width={360}
                  >
                    <button
                      type="button"
                      aria-describedby="claim-status-definition"
                      aria-pressed={activeStatus}
                      onClick={() => setSelectedStatus(definition)}
                      style={statusButtonStyle(activeStatus)}
                      title={definition.summary}
                    >
                      {definition.status}
                    </button>
                  </AuditPopover>
                );
              })}
            </div>
            <div id="claim-status-definition" role="note" style={definitionPanelStyle}>
              <p style={definitionStatusStyle}>{selectedStatus.status}</p>
              <p style={definitionTextStyle}>{selectedStatus.summary}</p>
            </div>
          </section>
        </div>
      </GlassPanel>
    </PageShell>
  );
}
