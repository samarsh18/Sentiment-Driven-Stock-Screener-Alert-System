/**
 * frontend/src/hooks/usePipeline.ts
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { analyzeNewsPipeline } from '../api/pipeline';
import { PipelineAnalyzeRequest } from '../api/types';

export function usePipelineAnalyze() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PipelineAnalyzeRequest) => analyzeNewsPipeline(payload),
    onSuccess: (data, variables) => {
      if (variables.user_id) {
        queryClient.invalidateQueries({ queryKey: ['userAlerts', variables.user_id] });
      }
      queryClient.invalidateQueries({ queryKey: ['stockNews', data.symbol] });
    },
  });
}
