import { useState, useEffect } from 'react';
import { DialSlider } from './DialSlider';
import { validateDials } from '../../lib/validation';
import { INVOLUTION_PAIRS } from '../../lib/constants';

const DEFAULT_DIALS = [6, 6, 6, 6, 6, 6, 6, 6, 6, 6];

export function DialPanel({
  initialValues,
  onSave,
  saving,
}: {
  initialValues?: number[];
  onSave: (values: number[]) => void;
  saving: boolean;
}) {
  const [values, setValues] = useState<number[]>(initialValues ?? DEFAULT_DIALS);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    if (initialValues) setValues(initialValues);
  }, [initialValues]);

  useEffect(() => {
    setErrors(validateDials(values));
  }, [values]);

  function handleChange(index: number, value: number) {
    setValues((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  function handleReset() {
    setValues([...DEFAULT_DIALS]);
  }

  const isValid = errors.length === 0;

  const selfDualIndices = [0, 1, 4, 7];
  const pairIndices = INVOLUTION_PAIRS;

  return (
    <div className="space-y-6">
      <div>
        <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Self-Dual Operators</h4>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {selfDualIndices.map((i) => (
            <DialSlider key={i} index={i} value={values[i]} onChange={handleChange} />
          ))}
        </div>
      </div>

      <div>
        <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Involution Pairs</h4>
        <div className="space-y-4">
          {pairIndices.map(([a, b]) => {
            const divergence = Math.abs(values[a] - values[b]);
            const isWarning = divergence >= 3;
            return (
              <div key={`${a}-${b}`} className={`rounded-lg border p-4 ${isWarning ? 'border-amber-500/30 bg-amber-500/5' : 'border-white/[0.06] bg-white/[0.02]'}`}>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <DialSlider index={a} value={values[a]} onChange={handleChange} />
                  <DialSlider index={b} value={values[b]} onChange={handleChange} />
                </div>
                <div className={`mt-2 text-[10px] text-center font-medium ${isWarning ? 'text-amber-400' : 'text-slate-600'}`}>
                  Divergence: {divergence} / 4 max
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {errors.length > 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
          {errors.map((e, i) => <div key={i}>{e}</div>)}
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={() => onSave(values)}
          disabled={!isValid || saving}
          className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-5 py-3 sm:py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity min-h-[44px]"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
        <button
          onClick={handleReset}
          className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-3 sm:py-2 text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors min-h-[44px]"
        >
          Reset to Default
        </button>
      </div>
    </div>
  );
}
