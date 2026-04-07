import { Link } from 'react-router-dom';
import { useHistoryStore } from '../stores/historyStore';
import { CertBadge } from '../components/shared/CertBadge';
import { Card } from '../components/shared/Card';

export function HistoryPage() {
  const records = useHistoryStore((s) => s.records);
  const clearHistory = useHistoryStore((s) => s.clear);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">History</h2>
        {records.length > 0 && (
          <button
            onClick={() => {
              if (confirm('Clear all history?')) clearHistory();
            }}
            className="rounded-md bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100"
          >
            Clear All
          </button>
        )}
      </div>

      {records.length === 0 ? (
        <Card>
          <p className="text-sm text-gray-500 text-center py-8">No assessments yet.</p>
        </Card>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Text</th>
                <th className="px-3 py-2">Score</th>
                <th className="px-3 py-2">Level</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-500">
                    {new Date(r.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 max-w-xs truncate">
                    <Link to={`/details/${r.id}`} className="text-indigo-600 hover:underline">
                      {r.text.slice(0, 80)}{r.text.length > 80 ? '...' : ''}
                    </Link>
                  </td>
                  <td className="px-3 py-2 font-mono">{r.result.nccs.composite.toFixed(1)}</td>
                  <td className="px-3 py-2">
                    <CertBadge certification={r.result.nccs.certification} composite={r.result.nccs.composite} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
