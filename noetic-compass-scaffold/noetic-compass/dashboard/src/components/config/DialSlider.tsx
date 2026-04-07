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
    <div className="flex flex-col gap-1.5">
      <label className="text-[11px] font-medium text-slate-400">
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
          className="flex-1"
        />
        <span className="w-7 text-center text-sm font-mono font-bold text-accent-teal">
          {value}
        </span>
      </div>
    </div>
  );
}
