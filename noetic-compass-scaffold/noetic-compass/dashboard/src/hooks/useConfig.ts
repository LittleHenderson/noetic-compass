import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getConfig, putConfig } from '../api/endpoints';
import type { DialConfig } from '../api/types';

export function useConfigQuery() {
  return useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
  });
}

export function useConfigMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: DialConfig) => putConfig(config),
    onSuccess(data) {
      qc.setQueryData(['config'], data);
    },
  });
}
