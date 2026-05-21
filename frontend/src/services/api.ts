import type { Position, PositionCreate, PortfolioSummary, PortfolioHistoryItem, PriceData } from '../types';

const API_BASE_URL = 'http://localhost:8000';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  // Positions
  getPositions: () => fetchApi<Position[]>('/positions'),

  getPosition: (id: number) => fetchApi<Position>(`/positions/${id}`),

  createPosition: (position: PositionCreate) =>
    fetchApi<Position>('/positions', {
      method: 'POST',
      body: JSON.stringify(position),
    }),

  updatePosition: (id: number, position: Partial<PositionCreate>) =>
    fetchApi<Position>(`/positions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(position),
    }),

  deletePosition: (id: number) =>
    fetchApi<void>(`/positions/${id}`, { method: 'DELETE' }),

  // Portfolio
  getPortfolioSummary: () => fetchApi<PortfolioSummary>('/portfolio/summary'),

  getPortfolioHistory: (days = 30) =>
    fetchApi<PortfolioHistoryItem[]>(`/portfolio/history?days=${days}`),

  createSnapshot: () => fetchApi<void>('/portfolio/snapshot', { method: 'POST' }),

  // Prices
  getPrice: (symbol: string) => fetchApi<PriceData>(`/prices/${symbol}`),

  // IBKR
  connectIBKR: (port = 7497) =>
    fetchApi<{ status: string }>('/ibkr/connect', {
      method: 'POST',
      body: JSON.stringify({ port }),
    }),

  disconnectIBKR: () =>
    fetchApi<{ status: string }>('/ibkr/disconnect', { method: 'POST' }),

  getIBKRStatus: () => fetchApi<{ connected: boolean }>('/ibkr/status'),

  getIBKRAccount: () => fetchApi<Record<string, unknown>>('/ibkr/account'),

  getIBKRPositions: () => fetchApi<{ positions: unknown[] }>('/ibkr/positions'),

  syncIBKR: () => fetchApi<{ status: string; positions_synced: number }>('/ibkr/sync', { method: 'POST' }),
};
