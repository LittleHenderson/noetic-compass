/**
 * Hook for cohort comparison API calls.
 */

import { useMutation } from '@tanstack/react-query';
import { postCohortCompare } from '../api/endpoints';
import type { CohortCompareRequest, CohortCompareResult } from '../api/types';

export function useCohort() {
  return useMutation<CohortCompareResult, Error, CohortCompareRequest>({
    mutationFn: postCohortCompare,
  });
}
