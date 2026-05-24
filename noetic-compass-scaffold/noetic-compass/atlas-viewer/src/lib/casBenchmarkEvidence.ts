export interface CasBenchmarkEvidence {
  id: string;
  headline: string;
  plainClaim: string;
  casResult: string;
  baselineResult: string;
  whyItMatters: string;
  scope: string;
}

export const CAS_BENCHMARK_HEADLINE =
  'CAS beats the baseline on the validated jobs below.';

export const CAS_BENCHMARK_SUBHEAD =
  'This is the direct product claim: CAS is not just naming states. In the validated tests, CAS labels predict internal labels, causal removals, output shifts, and accept/suppress decisions better than the control methods listed here.';

export const CAS_BENCHMARK_EVIDENCE: readonly CasBenchmarkEvidence[] = [
  {
    id: 'internal-readout',
    headline: 'Internal state readout',
    plainClaim:
      'CAS reads model-internal structure better than guessing from surface text.',
    casResult:
      'Pythia-160M Foundation probe 78.6%; Pythia-160M 40-element probe 89.8%; OLMo-1B 90.6%; Qwen2.5-1.5B 82.0%.',
    baselineResult:
      'Text baseline was lower by +28.9 percentage points on Foundation and +39.7 points on the 40-element readout.',
    whyItMatters:
      'If the signal only lived in wording, the hidden-state probe would not beat text by that much.',
    scope: 'Validated on Pythia, OLMo, and Qwen families.',
  },
  {
    id: 'causal-removal',
    headline: 'Causal removal',
    plainClaim:
      'When the CAS-related internal direction is removed, the readout collapses to chance.',
    casResult:
      'Foundation readout dropped from 78.6% to 3.57% after CAS subspace ablation.',
    baselineResult:
      '3.57% is exact 1-in-28 chance. Random same-rank ablations had mean disruption 0.000 and max 0.000.',
    whyItMatters:
      'That is the key causal test: remove the CAS direction and the signal dies; remove random directions and it does not.',
    scope: 'Pythia-160M Foundation subspace validation.',
  },
  {
    id: 'output-effect',
    headline: 'Output effect prediction',
    plainClaim:
      'CAS-conditioned choices move model likelihood in the predicted direction.',
    casResult:
      'Likelihood shifts: Pythia-160M +0.283, Pythia-1B +0.554, OLMo-1B +0.604, Qwen2.5-1.5B +0.796.',
    baselineResult:
      'Raw-CAS-symbol control on Qwen was near null at -0.0002.',
    whyItMatters:
      'This connects CAS labels to output behavior instead of only to pretty visual labels.',
    scope: 'Eta-to-epsilon likelihood bridge across Pythia, OLMo, and Qwen.',
  },
  {
    id: 'verification-stack',
    headline: 'Accept/suppress verification',
    plainClaim:
      'When the verifier accepts a row, it is highly accurate, with coverage reported separately.',
    casResult:
      'OLMo accepted accuracy 98.16% at 71.73% coverage; Qwen accepted accuracy 99.49% at 74.57% coverage.',
    baselineResult:
      'Accepting everything would hide the risk. CAS separates high-confidence accepted rows from rows that need suppress/triage.',
    whyItMatters:
      'This is the product behavior users care about: which outputs should be trusted, blocked, or reviewed.',
    scope: 'Stage 22.4 OLMo/Qwen diagnostic rows.',
  },
  {
    id: 'inversion-coverage',
    headline: 'Inversion coverage',
    plainClaim:
      'The scanner now produces numeric inversion proxy attribution for every OLMo/Qwen diagnostic row.',
    casResult:
      'Stage 22.6/22.7 measured 4,704 of 4,704 rows: numeric proxy rate 1.000.',
    baselineResult:
      'Stage 22.5 had 0 numeric inversion rows; inversion fields were reserved but not measured.',
    whyItMatters:
      'Coverage matters because a risk scanner that leaves the field blank cannot support an audit trail.',
    scope: 'Proxy-level inversion attribution, not a full semantic inversion theorem.',
  },
];

export const CAS_BENCHMARK_BOUNDARY =
  'Boundary: these are validated benchmark claims, not a claim that CAS controls every model, every token, or every semantic failure mode.';
