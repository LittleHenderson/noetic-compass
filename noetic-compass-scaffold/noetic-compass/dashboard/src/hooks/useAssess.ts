import { useMutation } from '@tanstack/react-query';
import { postAssess } from '../api/endpoints';
import type { AssessRequest } from '../api/types';

export function useAssess() {
  return useMutation({
    mutationFn: (req: AssessRequest) => postAssess(req),
  });
}
