export interface FaqTopic {
  id: string;
  label: string;
  summary: string;
  routePrefixes: string[];
}

export interface FaqReturnPoint {
  path: string;
  scrollTop: number;
  topicId: string;
  topicLabel: string;
}

export const FAQ_RETURN_KEY = 'casFaqReturnPoint';
export const FAQ_RESTORE_SCROLL_KEY = 'casFaqRestoreScrollTop';

export const FAQ_TOPICS: FaqTopic[] = [
  {
    id: 'what-is-noetic-compass',
    label: 'Noetic Compass',
    summary:
      'Noetic Compass scores AI responses through CAS so users can see structure, risk, and evidence instead of relying on a raw chat answer.',
    routePrefixes: ['/tutorial', '/visualization'],
  },
  {
    id: 'scenario-browser',
    label: 'Scenarios',
    summary:
      'Scenarios are pre-built prompts used to stress-test whether a model resists cognitive manipulation and produces resilient answers.',
    routePrefixes: ['/scenarios', '/ai-challenges'],
  },
  {
    id: 'evaluation-trace',
    label: 'Evaluation Trace',
    summary:
      'The trace shows how a score was produced step by step, so a user can inspect the path from input to verdict.',
    routePrefixes: ['/assessment', '/details', '/validate', '/validation', '/history'],
  },
  {
    id: 'evidence-packet-flight-recorder',
    label: 'Evidence Packet',
    summary:
      'The Evidence Packet is the flight-recorder record for a CAS Harness run: model, prompt, verifier decision, proof chips, hashes, and caveats.',
    routePrefixes: ['/idea-atlas', '/reproducibility'],
  },
  {
    id: 'notation-composer',
    label: 'CAS notation',
    summary:
      'CAS notation lets users state exactly which operators, domains, drives, or pathways should be tested instead of burying intent in prose.',
    routePrefixes: ['/compiler'],
  },
  {
    id: 'inversion',
    label: 'Inversion risk',
    summary:
      'An inversion is a structured drift where the model moves away from the intended operator, drive, pathway, or constraint.',
    routePrefixes: ['/forecast'],
  },
  {
    id: 'providers',
    label: 'Model connection',
    summary:
      'Provider settings connect model APIs to the CAS scoring pipeline while keeping the audit path separate from raw model output.',
    routePrefixes: ['/config', '/cohort'],
  },
  {
    id: 'how-score-calculated',
    label: 'CAS scoring',
    summary:
      'CAS scores combine operator, domain, drive, pathway, inversion, and social-engineering checks into a single readable assessment.',
    routePrefixes: ['/how-it-works'],
  },
];

export const DEFAULT_FAQ_TOPIC = FAQ_TOPICS[0];

export function findFaqTopic(id: string | null | undefined): FaqTopic | undefined {
  if (!id) return undefined;
  return FAQ_TOPICS.find((topic) => topic.id === id);
}

export function matchFaqTopic(pathname: string): FaqTopic {
  const cleanPath = pathname === '/' ? '/scenarios' : pathname;
  return (
    FAQ_TOPICS.find((topic) =>
      topic.routePrefixes.some((prefix) => cleanPath === prefix || cleanPath.startsWith(`${prefix}/`)),
    ) ?? DEFAULT_FAQ_TOPIC
  );
}

export function readFaqReturnPoint(): FaqReturnPoint | null {
  try {
    const raw = window.sessionStorage.getItem(FAQ_RETURN_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<FaqReturnPoint>;
    if (!parsed.path || typeof parsed.scrollTop !== 'number' || !parsed.topicId || !parsed.topicLabel) {
      return null;
    }
    return {
      path: parsed.path,
      scrollTop: parsed.scrollTop,
      topicId: parsed.topicId,
      topicLabel: parsed.topicLabel,
    };
  } catch {
    return null;
  }
}

export function writeFaqReturnPoint(point: FaqReturnPoint): void {
  try {
    window.sessionStorage.setItem(FAQ_RETURN_KEY, JSON.stringify(point));
  } catch {
    // Session storage can be unavailable in private modes; navigation still works.
  }
}

export function clearFaqReturnPoint(): void {
  try {
    window.sessionStorage.removeItem(FAQ_RETURN_KEY);
  } catch {
    // No-op.
  }
}

export function queueFaqScrollRestore(scrollTop: number): void {
  try {
    window.sessionStorage.setItem(FAQ_RESTORE_SCROLL_KEY, String(scrollTop));
  } catch {
    // No-op.
  }
}

export function popFaqScrollRestore(): number | null {
  try {
    const raw = window.sessionStorage.getItem(FAQ_RESTORE_SCROLL_KEY);
    if (!raw) return null;
    window.sessionStorage.removeItem(FAQ_RESTORE_SCROLL_KEY);
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
