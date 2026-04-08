import { useMutation } from '@tanstack/react-query';
import { postBenchmark } from '../api/endpoints';
import type { BenchmarkRequest } from '../api/types';

export function useBenchmark() {
  return useMutation({
    mutationFn: (req: BenchmarkRequest) => postBenchmark(req),
  });
}
