import { useMutation } from '@tanstack/react-query';
import { postBatch } from '../api/endpoints';
import type { BatchRequest } from '../api/types';

export function useBatch() {
  return useMutation({
    mutationFn: (req: BatchRequest) => postBatch(req),
  });
}
