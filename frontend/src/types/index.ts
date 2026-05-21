export type AssetType = 'stock' | 'etf' | 'bond' | 'cash' | 'crypto' | 'other';

export interface Position {
  id: number;
  symbol: string;
  shares: number;
  cost_basis: number;
  purchase_date: string;
  asset_type: AssetType;
  current_price: number | null;
  current_value: number | null;
  gain_loss: number | null;
  gain_loss_percent: number | null;
}

export interface PositionCreate {
  symbol: string;
  shares: number;
  cost_basis: number;
  purchase_date: string;
  asset_type: AssetType;
}

export interface AllocationItem {
  asset_type: string;
  value: number;
  percentage: number;
  symbols: string[];
}

export interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  total_gain_loss: number;
  total_gain_loss_percent: number;
  positions_count: number;
  allocation: AllocationItem[];
}

export interface PortfolioHistoryItem {
  date: string;
  total_value: number;
  total_cost: number;
  daily_return: number;
}

export interface PriceData {
  symbol: string;
  price: number;
  currency: string;
  change: number | null;
  change_percent: number | null;
}
