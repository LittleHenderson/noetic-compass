import { INVOLUTION_PAIRS } from './constants';

export function validateDials(values: number[]): string[] {
  const errors: string[] = [];

  if (values.length !== 10) {
    errors.push(`Expected 10 dial values, got ${values.length}`);
    return errors;
  }

  for (let i = 0; i < 10; i++) {
    if (values[i] < 3 || values[i] > 9) {
      errors.push(`CO-${i} value ${values[i]} is out of range [3, 9]`);
    }
  }

  for (const [a, b] of INVOLUTION_PAIRS) {
    const divergence = Math.abs(values[a] - values[b]);
    if (divergence > 4) {
      errors.push(
        `CO-${a}/CO-${b} divergence ${divergence} exceeds max of 4`
      );
    }
  }

  return errors;
}
