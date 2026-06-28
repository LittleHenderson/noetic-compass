import {
  isLiveRunnableMethod,
  type TestingMethod,
} from './testingMethods';

export type LiveKnobValue = string | number | boolean | string[];

export interface LiveMethodConfigPayload {
  enabled: boolean;
  knobs: Record<string, LiveKnobValue>;
}

export interface LiveSessionRequestPayload {
  prompt: string;
  model_id?: string;
  max_new_tokens?: number;
  temperature?: number;
  seed?: number | null;
  method_configs: Record<string, LiveMethodConfigPayload>;
}

export interface BuildLiveSessionRequestInput {
  prompt: string;
  modelId?: string;
  maxNewTokens?: number;
  temperature?: number;
  seed?: number | null;
  methods: readonly TestingMethod[];
  enabledMethodIds: Set<string>;
  knobValues: Record<string, Record<string, LiveKnobValue>>;
}

export function buildLiveSessionRequest(
  input: BuildLiveSessionRequestInput,
): LiveSessionRequestPayload {
  const method_configs: Record<string, LiveMethodConfigPayload> = {};

  for (const method of input.methods) {
    const enabled = input.enabledMethodIds.has(method.id);
    if (!isLiveRunnableMethod(method)) {
      method_configs[method.id] = {
        enabled: false,
        knobs: input.knobValues[method.id] ?? {},
      };
      continue;
    }
    method_configs[method.id] = {
      enabled,
      knobs: input.knobValues[method.id] ?? {},
    };
  }

  return {
    prompt: input.prompt,
    model_id: input.modelId,
    max_new_tokens: input.maxNewTokens,
    temperature: input.temperature,
    seed: input.seed,
    method_configs,
  };
}
