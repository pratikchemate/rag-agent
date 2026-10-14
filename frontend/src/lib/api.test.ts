import { describe, it, expect } from 'vitest';
import { ApiError } from './api';

describe('ApiError and Client Configuration', () => {
  it('instantiates ApiError with appropriate status and error code', () => {
    const error = new ApiError(
      'Daily LLM budget exhausted',
      429,
      'llm_daily_budget_exhausted',
      '2026-10-15T00:00:00Z',
      { limit: 40 }
    );

    expect(error.name).toBe('ApiError');
    expect(error.status).toBe(429);
    expect(error.code).toBe('llm_daily_budget_exhausted');
    expect(error.resetAt).toBe('2026-10-15T00:00:00Z');
    expect(error.extra).toEqual({ limit: 40 });
    expect(error.message).toBe('Daily LLM budget exhausted');
  });

  it('defaults error code to "error" if unspecified', () => {
    const error = new ApiError('General network failure', 500);
    expect(error.code).toBe('error');
    expect(error.status).toBe(500);
    expect(error.resetAt).toBeUndefined();
  });
});
