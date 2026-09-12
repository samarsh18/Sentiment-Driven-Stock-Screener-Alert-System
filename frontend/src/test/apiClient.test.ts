import { describe, it, expect } from 'vitest';
import { API_BASE_URL } from '../api/client';
import { MOCK_ALERTS, MOCK_NEWS, MOCK_PIPELINE_RESULT, MOCK_WATCHLIST } from '../api/mockData';

describe('Frontend API Client & Mock Data Structures', () => {
  it('API_BASE_URL has no trailing slash', () => {
    expect(API_BASE_URL).not.toMatch(/\/$/);
    expect(API_BASE_URL).toContain('/api');
  });

  it('MOCK_WATCHLIST matches API schema', () => {
    expect(MOCK_WATCHLIST.total).toBeGreaterThan(0);
    expect(MOCK_WATCHLIST.items[0]).toHaveProperty('symbol');
    expect(MOCK_WATCHLIST.items[0]).toHaveProperty('company_name');
  });

  it('MOCK_ALERTS exposes severity_label', () => {
    expect(MOCK_ALERTS.items.length).toBeGreaterThan(0);
    const first = MOCK_ALERTS.items[0];
    expect(first).toHaveProperty('severity_label');
    expect(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']).toContain(first.severity_label);
  });

  it('MOCK_PIPELINE_RESULT exposes reasoning and confidence', () => {
    expect(MOCK_PIPELINE_RESULT.confidence).toBeGreaterThan(0);
    expect(MOCK_PIPELINE_RESULT.reason).toContain('Historical matches');
    expect(MOCK_PIPELINE_RESULT.evidence_strength).toBe('STRONG');
  });
});
