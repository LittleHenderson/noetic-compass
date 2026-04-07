import { Link } from 'react-router-dom';
import { useHistoryStore } from '../stores/historyStore';
import { CertBadge } from '../components/shared/CertBadge';
import { Card } from '../components/shared/Card';

export function HistoryPage() {
  const records = useHistoryStore((s) => s.records);
  const clearHistory = useHistoryStore((s) => s.clear);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100">History</h2>
        {records.length > 0 && (
          <button
            onClick={() => {
              if (confirm('Clear all history?')) clearHistory();
            }}
            className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors"
          >
            Clear All
          </button>
        )}
      </div>

      {records.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500 text-center py-8">No assessments yet.</p>
        </Card>
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-[11px] text-slate-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Text</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Level</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-500">
                      {new Date(r.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate">
                      <Link to={`/details/${r.id}`} className="text-accent-teal hover:text-accent-cyan transition-colors">
                        {r.text.slice(0, 80)}{r.text.length > 80 ? '...' : ''}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">{r.result.nccs.composite.toFixed(1)}</td>
                    <td className="px-4 py-3">
                      <CertBadge certification={r.result.nccs.certification} composite={r.result.nccs.composite} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
