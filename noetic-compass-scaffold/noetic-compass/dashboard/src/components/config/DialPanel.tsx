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

  // Group: self-dual operators, then involution pairs
  const selfDualIndices = [0, 1, 4, 7];
  const pairIndices = INVOLUTION_PAIRS;

  return (
    <div className="space-y-6">
      {/* Self-dual operators */}
      <div>
        <h4 className="mb-2 text-xs font-semibold text-gray-400 uppercase">Self-Dual Operators</h4>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {selfDualIndices.map((i) => (
            <DialSlider key={i} index={i} value={values[i]} onChange={handleChange} />
          ))}
        </div>
      </div>

      {/* Involution pairs */}
      <div>
        <h4 className="mb-2 text-xs font-semibold text-gray-400 uppercase">Involution Pairs</h4>
        <div className="space-y-4">
          {pairIndices.map(([a, b]) => (
            <div key={`${a}-${b}`} className="rounded-md border border-gray-100 bg-gray-50 p-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <DialSlider index={a} value={values[a]} onChange={handleChange} />
                <DialSlider index={b} value={values[b]} onChange={handleChange} />
              </div>
              <div className="mt-1 text-[10px] text-gray-400 text-center">
                Divergence: {Math.abs(values[a] - values[b])} / 4 max
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-600">
          {errors.map((e, i) => <div key={i}>{e}</div>)}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => onSave(values)}
          disabled={!isValid || saving}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
        <button
          onClick={handleReset}
          className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200"
        >
          Reset to Default
        </button>
      </div>
    </div>
  );
}
