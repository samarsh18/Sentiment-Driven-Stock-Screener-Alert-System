/**
 * frontend/src/api/types.ts
 * Exact TypeScript interfaces matching the FastAPI backend schemas.
 */

export type Action = 'BUY' | 'SELL' | 'HOLD' | 'RISK_ALERT' | 'OPPORTUNITY' | 'WATCH' | 'INFORMATIONAL';
export type SeverityLabel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type SentimentType = 'positive' | 'negative' | 'neutral';
export type EvidenceStrength = 'INSUFFICIENT' | 'WEAK' | 'MODERATE' | 'STRONG';

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
}

export interface ErrorResponse {
  detail: string;
  code?: string;
}

export interface UserResponse {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface UserPreferencesResponse {
  user_id: number;
  is_active: boolean;
  email: string;
}

export interface UserPreferencesUpdate {
  is_active?: boolean;
}

export interface WatchlistItemCreate {
  symbol: string;
  company_name: string;
}

export interface WatchlistItemResponse {
  id: number;
  user_id: number;
  symbol: string;
  company_name: string;
  created_at: string;
}

export interface WatchlistResponse {
  items: WatchlistItemResponse[];
  total: number;
}

export interface NewsRecordResponse {
  id: number;
  news_id: string;
  symbol: string;
  company_name: string;
  title: string;
  content: string;
  source: string;
  url: string;
  published_at: string;
  created_at: string;
}

export interface NewsListResponse {
  items: NewsRecordResponse[];
  pagination: PaginationMeta;
}

export interface AlertResponse {
  id: number;
  alert_id: string;
  user_id: number | null;
  symbol: string;
  action: Action;
  severity: number;
  severity_label: SeverityLabel;
  message: string;
  should_alert: boolean;
  created_at: string;
}

export interface AlertListResponse {
  items: AlertResponse[];
  pagination: PaginationMeta;
}

export interface PriceBarResponse {
  symbol: string;
  exchange: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PricesListResponse {
  symbol: string;
  exchange: string;
  items: PriceBarResponse[];
  total: number;
}

export interface StockMetadataInput {
  symbol: string;
  company_name: string;
  aliases?: string[];
  exchange?: string;
  sector?: string;
  industry?: string;
  market_cap_bucket?: string;
}

export interface NewsItemInput {
  news_id: string;
  symbol: string;
  company_name: string;
  title: string;
  content: string;
  source: string;
  url: string;
  published_at: string;
}

export interface PipelineAnalyzeRequest {
  news_item: NewsItemInput;
  stock_metadata: StockMetadataInput;
  ai_sentiment?: SentimentType;
  ai_sentiment_score?: number;
  ai_event_type?: string;
  ai_impact?: string;
  ai_severity?: SeverityLabel;
  gemini_confidence?: number;
  persist_alert?: boolean;
  user_id?: number;
}

export interface PipelineAnalyzeResponse {
  news_id: string;
  symbol: string;
  relevant: boolean;
  relevance_score: number;
  event_type: string;
  sentiment: SentimentType;
  sentiment_score: number;
  impact: string;
  severity_label: SeverityLabel;
  confidence: number;
  evidence_strength: EvidenceStrength;
  action: Action;
  should_alert: boolean;
  reason: string;
  alert_id?: string | null;
}
