/**
 * frontend/src/api/pipeline.ts
 */
import { apiRequest, USE_MOCK } from './client';
import { MOCK_PIPELINE_RESULT } from './mockData';
import { PipelineAnalyzeRequest, PipelineAnalyzeResponse } from './types';

export async function analyzeNewsPipeline(
  payload: PipelineAnalyzeRequest
): Promise<PipelineAnalyzeResponse> {
  if (USE_MOCK) {
    return {
      ...MOCK_PIPELINE_RESULT,
      news_id: payload.news_item.news_id,
      symbol: payload.news_item.symbol,
    };
  }
  return apiRequest<PipelineAnalyzeResponse>('/pipeline/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
