import { describe, expect, it, beforeEach } from 'vitest';
import {
  clearFaqReturnPoint,
  findFaqTopic,
  matchFaqTopic,
  popFaqScrollRestore,
  queueFaqScrollRestore,
  readFaqReturnPoint,
  writeFaqReturnPoint,
} from './contextualFaq';

describe('contextualFaq', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('maps product routes to the most relevant FAQ topic', () => {
    expect(matchFaqTopic('/assessment').id).toBe('evaluation-trace');
    expect(matchFaqTopic('/details/abc123').id).toBe('evaluation-trace');
    expect(matchFaqTopic('/idea-atlas').id).toBe('evidence-packet-flight-recorder');
    expect(matchFaqTopic('/compiler').id).toBe('notation-composer');
    expect(matchFaqTopic('/forecast').id).toBe('inversion');
  });

  it('finds deep-link topics by stable FAQ id', () => {
    expect(findFaqTopic('evidence-packet-flight-recorder')?.label).toBe('Evidence Packet');
    expect(findFaqTopic('not-a-real-topic')).toBeUndefined();
  });

  it('round-trips the FAQ return point', () => {
    writeFaqReturnPoint({
      path: '/assessment?mode=audit#verdict',
      scrollTop: 348,
      topicId: 'evaluation-trace',
      topicLabel: 'Evaluation Trace',
    });

    expect(readFaqReturnPoint()).toEqual({
      path: '/assessment?mode=audit#verdict',
      scrollTop: 348,
      topicId: 'evaluation-trace',
      topicLabel: 'Evaluation Trace',
    });

    clearFaqReturnPoint();
    expect(readFaqReturnPoint()).toBeNull();
  });

  it('pops scroll restoration exactly once', () => {
    queueFaqScrollRestore(512);

    expect(popFaqScrollRestore()).toBe(512);
    expect(popFaqScrollRestore()).toBeNull();
  });
});
