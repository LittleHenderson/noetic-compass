import { useMutation } from '@tanstack/react-query';
import { postWrap } from '../api/endpoints';
import { useHistoryStore } from '../stores/historyStore';
import type { WrapRequest } from '../api/types';

export function useWrap() {
  const addRecord = useHistoryStore((s) => s.add);

  return useMutation({
    mutationFn: (req: WrapRequest) => postWrap(req),
    onSuccess(data, variables) {
      addRecord(variables.text, data);
    },
  });
}
