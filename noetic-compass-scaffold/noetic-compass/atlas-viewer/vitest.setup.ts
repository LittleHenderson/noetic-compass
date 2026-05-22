import '@testing-library/jest-dom/vitest';

// jsdom doesn't ship PointerEvent. framer-motion's whileTap / press-gesture
// path constructs a PointerEvent under the hood (via motion.div interactive
// handlers); without a polyfill, the press handler throws ReferenceError
// during keyboard-press tests on motion components. Provide a minimal
// MouseEvent-derived stand-in that satisfies the type check and carries the
// pointerId framer-motion reads.
if (
  typeof window !== 'undefined' &&
  typeof (globalThis as { PointerEvent?: unknown }).PointerEvent === 'undefined'
) {
  class PointerEventPolyfill extends MouseEvent {
    pointerId: number;
    pointerType: string;
    isPrimary: boolean;
    width: number;
    height: number;
    pressure: number;
    tangentialPressure: number;
    tiltX: number;
    tiltY: number;
    twist: number;

    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init);
      this.pointerId = init.pointerId ?? 0;
      this.pointerType = init.pointerType ?? '';
      this.isPrimary = init.isPrimary ?? false;
      this.width = init.width ?? 1;
      this.height = init.height ?? 1;
      this.pressure = init.pressure ?? 0;
      this.tangentialPressure = init.tangentialPressure ?? 0;
      this.tiltX = init.tiltX ?? 0;
      this.tiltY = init.tiltY ?? 0;
      this.twist = init.twist ?? 0;
    }
  }
  (globalThis as { PointerEvent?: unknown }).PointerEvent = PointerEventPolyfill;
}
