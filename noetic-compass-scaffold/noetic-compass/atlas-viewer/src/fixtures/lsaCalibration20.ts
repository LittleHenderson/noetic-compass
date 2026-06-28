export type LsaAxis = '40e' | 'f28';

export interface LsaCalibrationItem {
  id: string;
  axis: LsaAxis;
  text: string;
}

export interface LsaDefinition {
  label: string;
  definition: string;
}

export interface LsaCalibrationData {
  schema: string;
  status: string;
  generatedFrom: string;
  items: LsaCalibrationItem[];
  definitions: Record<LsaAxis, LsaDefinition[]>;
}

export const lsaCalibration20: LsaCalibrationData = {
  schema: 'cas_harness_lsa_calibration_pwa_data.v0_1',
  status: 'calibration_only_not_claim_bearing',
  generatedFrom:
    'docs/working/lsa_artifacts_20260530/lsa_arm_a_20_item_redaction_sheet_private_draft_v0_1.csv',
  items: [
    {
      id: 'LSA-A-CAL20-001',
      axis: '40e',
      text:
        'A is the selected aspect of prior visit notes where the case shows an influence that leaves the person unsettled, afraid, and less able to grow; B is the selected aspect where the same notes point to an unseen background charge or purpose-pattern around the event. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-002',
      axis: '40e',
      text:
        'A is the process signal in the packing ticket where the issue is the invisible tone or purpose-pattern around the item; B is the process signal where the issue is a protected inner need for care, growth, and sheltering support. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-003',
      axis: '40e',
      text:
        'A is the process signal in the care decision where the thinking is steady, clear, and constructive; B is the process signal where the thinking is tangled, doubtful, internally conflicted, and leaning toward a harmful conclusion. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-004',
      axis: '40e',
      text:
        'A is the role where the response stays open, imaginative, and receptive to possibilities; B is the role where the response narrows into strict logic, critique, and conscious rule-checking. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-005',
      axis: '40e',
      text:
        'A is the aspect where the case requires grasping a difficult issue and weighing its importance; B is the aspect where the response stays shallow, misses the complexity, and treats the matter as small. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-006',
      axis: '40e',
      text:
        'A is the selected aspect of access history where the response is clear, steady, and benevolent; B is the selected aspect where the response carries warmth, ease, affection, and a pleasant felt bond. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-007',
      axis: '40e',
      text:
        'A is what the auditor notices when the case is shaped by open imagination and receptive possibility; B is what the auditor notices when the case is shaped by care, sympathy, acceptance, and tender receptivity. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-008',
      axis: '40e',
      text:
        'A is the selected aspect of the pipe records where the person is swept along by feeling and cannot hold it steady; B is the selected aspect where the issue is low grade, low placement, or weak material standing. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-009',
      axis: '40e',
      text:
        'A is care, sympathy, acceptance, and tender receptivity; B is the concrete receiving place or facilitator that accepts what is given and helps it develop. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-010',
      axis: '40e',
      text:
        'A is the selected aspect of prior visit notes where the issue is elevated position, strong build quality, or high standing; B is the selected aspect where the issue is hidden inner meaning and moral insight. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-011',
      axis: 'f28',
      text:
        "A is the hands-on moment where a person's pull toward ultimate belonging has to be handled in the actual disclosure plan; B is the hands-on moment where a search for trustworthy insight from access history has to be handled. Focus: A.",
    },
    {
      id: 'LSA-A-CAL20-012',
      axis: 'f28',
      text:
        'A is the felt signal that makes a person\'s longing for ultimate belonging matter inside the switching plan; B is the felt signal that makes a search for trustworthy insight from load records matter. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-013',
      axis: 'f28',
      text:
        'A is the dispatcher holding a reverent concern for whether stable load transfer can stay alive and well; B is the dispatcher making a line-by-line reasoning check of whether that same living capacity remains healthy and active. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-014',
      axis: 'f28',
      text:
        "A is the technician's concrete bodily action around whether the clear quality reading can stay alive and well; B is the technician's concrete bodily action around keeping the care bond with the utility lab joined. Focus: A.",
    },
    {
      id: 'LSA-A-CAL20-015',
      axis: 'f28',
      text:
        'A is the highest-orientation view of whether the urgent treatment path preserves living capacity and wholeness; B is the thought-model check of whether that same living capacity remains healthy and active. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-016',
      axis: 'f28',
      text:
        'A is the explicit reasoning pass that tests whether the bond of care between technician and utility lab keeps the case joined; B is the explicit reasoning pass that tests whether one party can shape the maintenance visit and guide what happens next. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-017',
      axis: 'f28',
      text:
        'A is the highest-orientation view around the push to shape the delivery task and guide what happens next; B is the careful thought path asking whether that same push to shape the delivery task still follows. Focus: B.',
    },
    {
      id: 'LSA-A-CAL20-018',
      axis: 'f28',
      text:
        'A is the highest-level orientation that keeps the need for usable supplies, storage, cleaning, and records visible across the process; B is the highest-level orientation that keeps the urge to continue the compliance step visible. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-019',
      axis: 'f28',
      text:
        'A is the felt signal that makes claims, receipts, approvals, and payouts matter as usable resources that sustain the work; B is the felt signal that makes the urge to carry the review workflow forward matter. Focus: A.',
    },
    {
      id: 'LSA-A-CAL20-020',
      axis: 'f28',
      text:
        "A is the officer's charged reaction around the resources needed for request, consent, data, and deletion work; B is the officer's charged reaction around the urge to carry the privacy action forward into continuation. Focus: B.",
    },
  ],
  definitions: {
    '40e': [
      {
        label: 'A1',
        definition:
          "Spiritual Mind: ultimate source-awareness, unseen purpose, and the soul's contact with what guides all causes.",
      },
      {
        label: 'A2',
        definition:
          'Spiritual Positive: truth or virtue that settles the soul and moves it toward its highest aim.',
      },
      {
        label: 'A3',
        definition:
          'Spiritual Negative: vice, fear, or harmful influence that troubles the soul and slows its growth.',
      },
      {
        label: 'A4',
        definition:
          'Spiritual Vibration: subtle aetheric energy, aura, and purpose-frequency behind a thing.',
      },
      {
        label: 'A5',
        definition:
          'Spiritual Female: receptive spiritual womb for needed growth, nurture, and protection.',
      },
      {
        label: 'A6',
        definition:
          'Spiritual Male: austere practice, discipline, and trial that transmit force for spiritual growth.',
      },
      {
        label: 'A7',
        definition:
          'Spiritual Rhythm: rise and fall of the life journey, destiny pattern, or sacred timing.',
      },
      {
        label: 'A8',
        definition:
          'Spiritual Above/Cause: hidden inner meaning, initiation, deeper reality, and high moral insight.',
      },
      {
        label: 'A9',
        definition:
          'Spiritual Below/Effect: visible shell, public sign, shallow grasp, or empty appearance.',
      },
      {
        label: 'A10',
        definition:
          'Spiritual Idea: unseen spiritual matter such as true self, soul-state, or record of a thing.',
      },
      {
        label: 'B1',
        definition:
          'Mental Mind: ego, memory, past experience, and analysis that reaches conclusions.',
      },
      {
        label: 'B2',
        definition:
          'Mental Positive: clarity, sanity, optimism, benevolence, and enlightened thought.',
      },
      {
        label: 'B3',
        definition:
          'Mental Negative: confusion, indecision, dissonance, pessimism, or malicious thought.',
      },
      {
        label: 'B4',
        definition:
          'Mental Vibration: brainwave-like resonance and the unique psychic signature of a thought.',
      },
      {
        label: 'B5',
        definition:
          'Mental Female: imaginative openness, creative receptivity, and subconscious generation.',
      },
      {
        label: 'B6',
        definition:
          'Mental Male: logic, criticism, rigidity, deliberate rule-use, and conscious analysis.',
      },
      {
        label: 'B7',
        definition:
          'Mental Rhythm: recurring thought pattern, ego-state transition, or frequency of a thought.',
      },
      {
        label: 'B8',
        definition:
          'Mental Above/Cause: complex comprehension, high contemplation, and brilliant intelligence.',
      },
      {
        label: 'B9',
        definition:
          'Mental Below/Effect: limited comprehension, menial concern, or simplistic pondering.',
      },
      {
        label: 'B10',
        definition: 'Mental Idea: thought-content existing as an inner mental object.',
      },
      {
        label: 'C1',
        definition: 'Emotional Mind: awareness of feelings and decisions sorted by feeling.',
      },
      {
        label: 'C2',
        definition: 'Emotional Positive: joy, calm, love, fellowship, and pleasurable feeling.',
      },
      {
        label: 'C3',
        definition:
          'Emotional Negative: sadness, anger, resentment, contempt, loneliness, hate, or mixed pain.',
      },
      {
        label: 'C4',
        definition:
          'Emotional Vibration: felt ambiance, mood-energy, and the aura of a person, place, or event.',
      },
      {
        label: 'C5',
        definition:
          'Emotional Female: compassion, sympathy, acceptance, sensuality, and receptive feeling.',
      },
      {
        label: 'C6',
        definition: 'Emotional Male: aggression, pride, dominance, and forceful feeling.',
      },
      {
        label: 'C7',
        definition:
          'Emotional Rhythm: mood swing, feeling-sequence, or emotional roller-coaster pattern.',
      },
      {
        label: 'C8',
        definition:
          'Emotional Above/Cause: healed resolve and control over lower feelings after deep insight.',
      },
      {
        label: 'C9',
        definition: 'Emotional Below/Effect: being overwhelmed and driven by feeling.',
      },
      {
        label: 'C10',
        definition: 'Emotional Idea: lingering felt sheath or ambiance of an idea.',
      },
      {
        label: 'D1',
        definition:
          'Physical Mind: brain, body, cellular hardware, or machine substrate hosting awareness.',
      },
      {
        label: 'D2',
        definition:
          'Physical Positive: well-fit parts that complement each other and function according to design.',
      },
      {
        label: 'D3',
        definition:
          'Physical Negative: misplaced parts, disorder, disease, dysfunction, or broken symmetry.',
      },
      {
        label: 'D4',
        definition:
          'Physical Vibration: light, sound, radiation, heat, electromagnetism, or particle oscillation.',
      },
      {
        label: 'D5',
        definition:
          'Physical Female: receiver, womb, receptacle, or facilitator that accepts and nurtures a seed.',
      },
      {
        label: 'D6',
        definition:
          'Physical Male: transmitter, appendage, seed-deliverer, or outward-projecting part.',
      },
      {
        label: 'D7',
        definition:
          'Physical Rhythm: music, motion, exercise, dance, sex, routine, or timed physical sequence.',
      },
      {
        label: 'D8',
        definition:
          'Physical Above/Cause: height, high grade, good material integrity, or high social position.',
      },
      {
        label: 'D9',
        definition:
          'Physical Below/Effect: low placement, weak material integrity, low grade, or low social position.',
      },
      {
        label: 'D10',
        definition:
          'Physical Idea: dead matter or a thing existing entirely as a material object.',
      },
    ],
    f28: [
      {
        label: 'F1T',
        definition:
          'F1 in T: spiritual longing for union with the highest source and ultimate belonging.',
      },
      {
        label: 'F1A',
        definition: 'F1 in A: mental model or reasoning about that longing and belonging.',
      },
      {
        label: 'F1f',
        definition:
          'F1 in f: felt longing, ache, awe, or emotional pull toward ultimate belonging.',
      },
      {
        label: 'F1E',
        definition:
          'F1 in E: bodily practice, place, or material action expressing that longing.',
      },
      {
        label: 'F2T',
        definition: 'F2 in T: higher insight or sacred knowledge about what should be trusted.',
      },
      {
        label: 'F2A',
        definition: 'F2 in A: reasoning, analysis, or thought-model for finding truth.',
      },
      {
        label: 'F2f',
        definition: 'F2 in f: intuitive feeling, gut knowing, or emotional discernment.',
      },
      {
        label: 'F2E',
        definition:
          'F2 in E: embodied skill, direct experience, or physical evidence as knowing.',
      },
      {
        label: 'F3T',
        definition: 'F3 in T: soul-level vitality, life force, purification, or higher health.',
      },
      {
        label: 'F3A',
        definition:
          'F3 in A: reasoning about resilience, function, health, or active capacity.',
      },
      {
        label: 'F3f',
        definition:
          'F3 in f: felt vitality, burnout, stress, enthusiasm, or emotional aliveness.',
      },
      {
        label: 'F3E',
        definition:
          'F3 in E: bodily health, material functioning, survival, or physical capacity.',
      },
      {
        label: 'F4T',
        definition:
          'F4 in T: spiritual connection, soul-bond, lineage, or transcendent love.',
      },
      {
        label: 'F4A',
        definition:
          'F4 in A: mental compatibility, shared understanding, or collaborative thought.',
      },
      {
        label: 'F4f',
        definition:
          'F4 in f: affection, empathy, closeness, trust, and emotional bonding.',
      },
      {
        label: 'F4E',
        definition:
          'F4 in E: proximity, touch, shared space, or physical expressions of connection.',
      },
      {
        label: 'F5T',
        definition:
          'F5 in T: sacred authority, will, spiritual influence, or higher command.',
      },
      {
        label: 'F5A',
        definition:
          'F5 in A: strategy, decision structure, influence, control, and planning.',
      },
      {
        label: 'F5f',
        definition:
          'F5 in f: confidence, pride, emotional influence, manipulation, or self-mastery.',
      },
      {
        label: 'F5E',
        definition:
          'F5 in E: physical power, territory, tools, weapons, or material control.',
      },
      {
        label: 'F6T',
        definition:
          'F6 in T: spiritual sustenance, sacred object, talisman, or subtle-resource hunger.',
      },
      {
        label: 'F6A',
        definition:
          'F6 in A: mental resource, doctrine, intellectual property, or food for thought.',
      },
      {
        label: 'F6f',
        definition:
          'F6 in f: emotional attachment to possessions, comfort, aesthetic surroundings.',
      },
      {
        label: 'F6E',
        definition:
          'F6 in E: physical food, goods, possessions, money, shelter, or material supply.',
      },
      {
        label: 'F7T',
        definition:
          'F7 in T: sacred sexuality, divine union, spiritual reproduction, or rebirth.',
      },
      {
        label: 'F7A',
        definition:
          'F7 in A: spreading ideas, intellectual reproduction, debate, or mental replication.',
      },
      {
        label: 'F7f',
        definition:
          'F7 in f: desire, passion, romantic bonding, or emotional replication.',
      },
      {
        label: 'F7E',
        definition:
          'F7 in E: bodily sexuality, reproduction, fertility, continuation, or procreation.',
      },
    ],
  },
};

export const LSA_STORAGE_KEY = 'cas-harness.lsa-calibration.v0_1';
