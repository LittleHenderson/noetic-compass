import { OPERATOR_LABELS } from '../../lib/constants';

export function DialSlider({
  index,
  value,
  onChange,
}: {
  index: number;
  value: number;
  onChange: (index: number, value: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-600">
        {OPERATOR_LABELS[index]}
      </label>
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={3}
          max={9}
          step={1}
          value={value}
          onChange={(e) => onChange(index, Number(e.target.value))}
          className="flex-1 accent-indigo-600"
        />
        <span className="w-6 text-center text-sm font-mono font-bold text-gray-700">
          {value}
        </span>
      </div>
    </div>
  );
}
