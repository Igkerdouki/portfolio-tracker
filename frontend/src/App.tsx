import { useState, useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import { PositionTable } from './components/PositionTable';
import { AddPositionForm } from './components/AddPositionForm';
import { AllocationChart } from './components/AllocationChart';
import { PerformanceChart } from './components/PerformanceChart';
import { IBKRConnect } from './components/IBKRConnect';
import { StockAnalysis } from './components/StockAnalysis';
import { AgentDashboard } from './components/AgentDashboard';
import { api } from './services/api';

type TabType = 'portfolio' | 'analysis' | 'agents';

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [portfolioSymbols, setPortfolioSymbols] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('portfolio');

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
    setLastUpdate(new Date());
  };

  // Fetch portfolio symbols for analysis watchlist sync
  useEffect(() => {
    const fetchSymbols = async () => {
      try {
        const positions = await api.getPositions();
        setPortfolioSymbols(positions.map((p) => p.symbol));
      } catch {
        // ignore
      }
    };
    fetchSymbols();
  }, [refreshTrigger]);

  // Auto-refresh prices every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      handleRefresh();
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">Portfolio Tracker</h1>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </span>
              <button
                onClick={handleRefresh}
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="mt-4 flex gap-4 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('portfolio')}
              className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'portfolio'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Portfolio
            </button>
            <button
              onClick={() => setActiveTab('analysis')}
              className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'analysis'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              AI Analysis
            </button>
            <button
              onClick={() => setActiveTab('agents')}
              className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                activeTab === 'agents'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Agents & Webhooks
              <span className="bg-purple-100 text-purple-700 text-xs px-1.5 py-0.5 rounded">
                NEW
              </span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'portfolio' && (
          <>
            <IBKRConnect onSync={handleRefresh} />
            <Dashboard refreshTrigger={refreshTrigger} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <AllocationChart refreshTrigger={refreshTrigger} />
              <PerformanceChart refreshTrigger={refreshTrigger} />
            </div>

            <div className="mb-4 flex justify-end">
              <AddPositionForm onSuccess={handleRefresh} />
            </div>

            <PositionTable refreshTrigger={refreshTrigger} onRefresh={handleRefresh} />
          </>
        )}

        {activeTab === 'analysis' && (
          <StockAnalysis portfolioSymbols={portfolioSymbols} />
        )}

        {activeTab === 'agents' && (
          <AgentDashboard />
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-sm text-gray-500 text-center">
            Portfolio Tracker - Agentic AI Trading System with TradingView Integration
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
