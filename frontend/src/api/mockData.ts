/**
 * frontend/src/api/mockData.ts
 * Deterministic mock data matching exact API response interfaces.
 */

import {
  AlertListResponse,
  NewsListResponse,
  PipelineAnalyzeResponse,
  PricesListResponse,
  UserPreferencesResponse,
  UserResponse,
  WatchlistResponse,
} from './types';

export const MOCK_USER: UserResponse = {
  id: 1,
  email: 'demo@screener.local',
  is_active: true,
  created_at: new Date().toISOString(),
};

export const MOCK_PREFERENCES: UserPreferencesResponse = {
  user_id: 1,
  is_active: true,
  email: 'demo@screener.local',
};

export const MOCK_WATCHLIST: WatchlistResponse = {
  total: 4,
  items: [
    { id: 101, user_id: 1, symbol: 'TCS', company_name: 'Tata Consultancy Services', created_at: '2024-05-01T10:00:00Z' },
    { id: 102, user_id: 1, symbol: 'RELIANCE', company_name: 'Reliance Industries Ltd', created_at: '2024-05-02T11:00:00Z' },
    { id: 103, user_id: 1, symbol: 'INFY', company_name: 'Infosys Limited', created_at: '2024-05-03T12:00:00Z' },
    { id: 104, user_id: 1, symbol: 'HDFCBANK', company_name: 'HDFC Bank Ltd', created_at: '2024-05-04T13:00:00Z' },
  ],
};

export const MOCK_ALERTS: AlertListResponse = {
  pagination: { total: 4, limit: 20, offset: 0 },
  items: [
    {
      id: 501,
      alert_id: 'ALERT-TCS-001',
      user_id: 1,
      symbol: 'TCS',
      action: 'BUY',
      severity: 8,
      severity_label: 'HIGH',
      message: 'Strong Q4 earnings beat (+14% YoY). Historical event study shows 82% positive excess returns across 45 similar past earnings beats.',
      should_alert: true,
      created_at: '2024-05-10T14:30:00Z',
    },
    {
      id: 502,
      alert_id: 'ALERT-RELIANCE-002',
      user_id: 1,
      symbol: 'RELIANCE',
      action: 'BUY',
      severity: 9,
      severity_label: 'HIGH',
      message: 'Major $10B Green Energy expansion announced. Historical matching indicates strong positive drift over 5D horizon (Wilson CI: 0.64–0.88).',
      should_alert: true,
      created_at: '2024-05-09T09:15:00Z',
    },
    {
      id: 503,
      alert_id: 'ALERT-INFY-003',
      user_id: 1,
      symbol: 'INFY',
      action: 'SELL',
      severity: 7,
      severity_label: 'HIGH',
      message: 'Guidance downgrade by major brokerages following margin compression. Negative excess return of -3.4% projected based on 32 historical matches.',
      should_alert: true,
      created_at: '2024-05-08T16:45:00Z',
    },
    {
      id: 504,
      alert_id: 'ALERT-HDFCBANK-004',
      user_id: 1,
      symbol: 'HDFCBANK',
      action: 'HOLD',
      severity: 3,
      severity_label: 'LOW',
      message: 'Routine executive transition announced. Historical statistical reaction indicates negligible benchmark excess return.',
      should_alert: false,
      created_at: '2024-05-07T11:20:00Z',
    },
  ],
};

export const MOCK_NEWS: NewsListResponse = {
  pagination: { total: 4, limit: 20, offset: 0 },
  items: [
    {
      id: 301,
      news_id: 'NEWS-TCS-001',
      symbol: 'TCS',
      company_name: 'Tata Consultancy Services',
      title: 'TCS reports stellar Q4 results, beats consensus on margins',
      content: 'Tata Consultancy Services reported revenue growth of 14% year-on-year, outperforming street estimates across all key verticals.',
      source: 'Financial Express',
      url: 'https://example.com/tcs-q4-results',
      published_at: '2024-05-10T14:00:00Z',
      created_at: '2024-05-10T14:05:00Z',
    },
    {
      id: 302,
      news_id: 'NEWS-RELIANCE-002',
      symbol: 'RELIANCE',
      company_name: 'Reliance Industries Ltd',
      title: 'Reliance unveils $10 Billion clean energy roadmap',
      content: 'Reliance Industries has committed $10 Billion towards solar module manufacturing and green hydrogen production facilities.',
      source: 'Reuters',
      url: 'https://example.com/reliance-clean-energy',
      published_at: '2024-05-09T08:45:00Z',
      created_at: '2024-05-09T08:50:00Z',
    },
    {
      id: 303,
      news_id: 'NEWS-INFY-003',
      symbol: 'INFY',
      company_name: 'Infosys Limited',
      title: 'Morgan Stanley cuts Infosys target price on discretionary spend slowdown',
      content: 'Analysts trimmed price targets citing ongoing softness in European banking IT budgets and delayed project starts.',
      source: 'Bloomberg',
      url: 'https://example.com/infosys-downgrade',
      published_at: '2024-05-08T16:00:00Z',
      created_at: '2024-05-08T16:05:00Z',
    },
    {
      id: 304,
      news_id: 'NEWS-HDFCBANK-004',
      symbol: 'HDFCBANK',
      company_name: 'HDFC Bank Ltd',
      title: 'HDFC Bank board approves dividend of Rs 19.50 per share',
      content: 'The board of directors approved the dividend payout following annual general meeting approval.',
      source: 'Economic Times',
      url: 'https://example.com/hdfc-dividend',
      published_at: '2024-05-07T10:30:00Z',
      created_at: '2024-05-07T10:35:00Z',
    },
  ],
};

export const MOCK_PRICES: Record<string, PricesListResponse> = {
  TCS: {
    symbol: 'TCS',
    exchange: 'NSE',
    total: 10,
    items: [
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-01', open: 3800, high: 3850, low: 3790, close: 3840, volume: 1200000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-02', open: 3840, high: 3875, low: 3830, close: 3865, volume: 1100000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-03', open: 3865, high: 3890, low: 3850, close: 3880, volume: 1400000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-06', open: 3880, high: 3910, low: 3870, close: 3905, volume: 1600000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-07', open: 3905, high: 3925, low: 3895, close: 3915, volume: 1300000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-08', open: 3915, high: 3950, low: 3910, close: 3940, volume: 1800000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-09', open: 3940, high: 3980, low: 3935, close: 3970, volume: 2100000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-10', open: 3970, high: 4050, low: 3960, close: 4030, volume: 3500000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-13', open: 4030, high: 4080, low: 4020, close: 4065, volume: 2800000 },
      { symbol: 'TCS', exchange: 'NSE', timestamp: '2024-05-14', open: 4065, high: 4110, low: 4055, close: 4095, volume: 2400000 },
    ],
  },
};

export const MOCK_PIPELINE_RESULT: PipelineAnalyzeResponse = {
  news_id: 'NEWS-TCS-001',
  symbol: 'TCS',
  relevant: true,
  relevance_score: 95,
  event_type: 'EARNINGS_BEAT',
  sentiment: 'positive',
  sentiment_score: 0.92,
  impact: 'HIGH',
  severity_label: 'HIGH',
  confidence: 0.88,
  evidence_strength: 'STRONG',
  action: 'BUY',
  should_alert: true,
  reason: 'Historical matches indicate that positive earnings beats in IT Services lead to benchmark excess returns in 82% of 45 similar past events over 5D horizon (Wilson 95% CI: 0.69–0.90).',
  alert_id: 'ALERT-TCS-001',
};
