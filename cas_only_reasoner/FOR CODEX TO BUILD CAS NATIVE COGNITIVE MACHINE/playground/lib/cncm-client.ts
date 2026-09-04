export interface MemorySummary {
  episode_count: number;
  episode_ids: string[];
}

export interface RuntimeReady {
  type: 'ready';
  runtimeVersion: string;
  bridgeVersion: string;
  runtimeSha256: string;
  packageTreeSha256: string;
  sourceSpecSha256: string;
  pyodideVersion: string;
  conversationProtocolVersion: string;
  capabilities: string[];
  memory: MemorySummary;
}

export interface ConversationState {
  schema_version: string;
  turn_index: number;
  entities: Array<{ entity_id: string; label: string }>;
  facts: Array<Record<string, unknown>>;
  rules: Array<Record<string, unknown>>;
  recent_entities: string[];
  pending_reference: Record<string, unknown> | null;
}

export interface ExecutionParity {
  performed?: boolean;
  matches?: boolean;
  [key: string]: unknown;
}

export interface ConversationTrace {
  schema_version: string;
  turn_index: number;
  input: string;
  parse_candidates: Array<Record<string, unknown>>;
  selected_meaning: Record<string, unknown> | null;
  references: Array<Record<string, unknown>>;
  problem_packet: Record<string, unknown> | null;
  reasoning_bundle: Record<string, unknown> | null;
  verification: Record<string, unknown> | null;
  execution_parity?: ExecutionParity | null;
  response_plan: Record<string, unknown>;
}

export interface ConversationTurn {
  schema_version: string;
  status: 'ACKNOWLEDGED' | 'ANSWERED' | 'CLARIFICATION_REQUIRED' | 'NO_COMMITMENT' | 'REJECTED';
  response: string;
  state: ConversationState;
  trace: ConversationTrace;
}

export interface RuntimeFatal {
  type: 'fatal';
  error: string;
}

export interface BridgeError {
  kind: string;
  type: string;
  message: string;
}

export interface BridgeReply {
  bridge_version: string;
  ok: boolean;
  operation: string;
  runtime_version?: string;
  error?: BridgeError;
  memory?: MemorySummary;
  report?: Record<string, unknown>;
  validation?: Record<string, unknown>;
  verification?: Record<string, unknown>;
  result?: Record<string, unknown>;
  conversation?: ConversationTurn;
  conversation_state?: ConversationState;
  math_result?: Record<string, unknown>;
  math_counterexample?: Record<string, unknown>;
  math_verification?: Record<string, unknown>;
  language_demo_cases?: string[];
  language_qualification?: Record<string, unknown>;
  cognitive_apprenticeship_demo_cases?: string[];
  cognitive_apprenticeship?: Record<string, unknown>;
}

type LifecycleMessage = RuntimeReady | RuntimeFatal;

interface PendingRequest {
  resolve: (reply: BridgeReply) => void;
  reject: (error: Error) => void;
}

export class CncmClient {
  private readonly worker: Worker;
  private readonly pending = new Map<number, PendingRequest>();
  private bridgeVersion: string | null = null;
  private nextId = 1;

  constructor(onLifecycle: (message: LifecycleMessage) => void) {
    this.worker = new Worker('/runtime/cncm-worker.mjs', { type: 'module' });

    this.worker.addEventListener('message', ({ data }: MessageEvent) => {
      if (data?.type === 'ready' || data?.type === 'fatal') {
        if (data.type === 'ready') this.bridgeVersion = data.bridgeVersion;
        onLifecycle(data as LifecycleMessage);
        return;
      }

      const request = this.pending.get(data?.id);
      if (!request) return;
      this.pending.delete(data.id);
      const reply = data.reply as BridgeReply;
      if (this.bridgeVersion && reply.bridge_version !== this.bridgeVersion) {
        request.reject(
          new Error(
            `CNCM bridge reply mismatch: expected ${this.bridgeVersion}, found ${String(reply.bridge_version)}`,
          ),
        );
        return;
      }
      request.resolve(reply);
    });

    this.worker.addEventListener('error', (event) => {
      const error = new Error(event.message || 'CNCM worker failed');
      for (const request of this.pending.values()) request.reject(error);
      this.pending.clear();
      onLifecycle({ type: 'fatal', error: error.message });
    });
  }

  request(operation: string, json?: string): Promise<BridgeReply> {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, operation, json });
    });
  }

  run(problemJson: string) {
    return this.request('run', problemJson);
  }

  validate(problemJson: string) {
    return this.request('validate', problemJson);
  }

  verify(bundleJson: string) {
    return this.request('verify', bundleJson);
  }

  replay() {
    return this.request('replay');
  }

  mathValidate(notation: string, variables: string[]) {
    return this.request('math_validate', JSON.stringify({ notation, variables }));
  }

  mathSolve(notation: string, variable: string) {
    return this.request('math_solve', JSON.stringify({ notation, variable }));
  }

  mathCounterexample(
    notation: string,
    bounds: Array<{ variable: string; lower: number; upper: number }>,
    guards: string[] = [],
    maxAssignments = 4096,
  ) {
    return this.request(
      'math_counterexample',
      JSON.stringify({ notation, bounds, guards, max_assignments: maxAssignments }),
    );
  }

  mathVerify(bundle: Record<string, unknown>) {
    return this.request('math_verify', JSON.stringify(bundle));
  }

  mathVerifyCounterexample(bundle: Record<string, unknown>) {
    return this.request('math_verify_counterexample', JSON.stringify(bundle));
  }

  conversationTurn(text: string) {
    return this.request('conversation_turn', JSON.stringify({ text }));
  }

  conversationStatus() {
    return this.request('conversation_status');
  }

  status() {
    return this.request('status');
  }

  conversationReset() {
    return this.request('conversation_reset');
  }

  languageDemoCases() {
    return this.request('language_demo_cases');
  }

  languageQualify(caseId: string) {
    return this.request('language_qualify', JSON.stringify({ case_id: caseId }));
  }

  cognitiveApprenticeshipDemoCases() {
    return this.request('cognitive_apprenticeship_demo_cases');
  }

  cognitiveApprenticeshipQualify(caseId: string) {
    return this.request('cognitive_apprenticeship_qualify', JSON.stringify({ case_id: caseId }));
  }

  reset() {
    return this.request('reset');
  }

  dispose() {
    this.worker.terminate();
    const error = new Error('CNCM worker disposed');
    for (const request of this.pending.values()) request.reject(error);
    this.pending.clear();
  }
}
