import { useConfigQuery, useConfigMutation } from '../hooks/useConfig';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { DialPanel } from '../components/config/DialPanel';

export function ConfigPage() {
  const config = useConfigQuery();
  const mutation = useConfigMutation();

  function handleSave(values: number[]) {
    mutation.mutate({ values });
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Dial Configuration</h2>

      {config.isLoading && <LoadingSpinner />}
      <ErrorBanner error={(config.error ?? mutation.error) as Error | null} />

      {mutation.isSuccess && (
        <div className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          Configuration saved successfully.
        </div>
      )}

      {config.data && (
        <Card>
          <DialPanel
            initialValues={config.data.values}
            onSave={handleSave}
            saving={mutation.isPending}
          />
        </Card>
      )}
    </div>
  );
}
