import { useState, useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import { PositionTable } from './components/PositionTable';
import { AddPositionForm } from './components/AddPositionForm';
import { AllocationChart } from './components/AllocationChart';
import { PerformanceChart } from './components/PerformanceChart';
import { IBKRConnect } from './components/IBKRConnect';
import { StockAnalysis } from './components/StockAnalysis';
import { AgentDashboard } from './components/AgentDashboard';
import { MLPredictor } from './components/MLPredictor';
import { ChatInterface } from './components/ChatInterface';
import { api } from './services/api';

type TabType = 'portfolio' | 'analysis' | 'ml' | 'chat' | 'agents';

const tabs: { id: TabType; label: string; icon: string; badge?: string }[] = [
  { id: 'portfolio', label: 'Portfolio', icon: '📊' },
  { id: 'chat', label: 'Lili Claude', icon: '💬', badge: 'NEW' },
  { id: 'analysis', label: 'Analysis', icon: '📈' },
  { id: 'ml', label: 'ML Predictor', icon: '🤖' },
  { id: 'agents', label: 'Automation', icon: '⚡' },
];

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [portfolioSymbols, setPortfolioSymbols] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('portfolio');

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
    setLastUpdate(new Date());
  };

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

  useEffect(() => {
    const interval = setInterval(() => {
      handleRefresh();
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#0a0e27' }}>
      {/* Header */}
      <header className="border-b border-slate-700/50 sticky top-0 z-50" style={{ backgroundColor: '#0d1230' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            {/* Logo */}
            <div>
              <h1 className="text-xl font-bold" style={{ color: '#f59e0b' }}>
                Wealth Buddy
              </h1>
              <p className="text-xs text-slate-400">Your Investment Companion</p>
            </div>

            {/* Status */}
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-sm text-slate-400">
                <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: '#22c55e' }}></div>
                <span>Live</span>
                <span className="text-slate-600">•</span>
                <span>{lastUpdate.toLocaleTimeString()}</span>
              </div>
              <button
                onClick={handleRefresh}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all hover:scale-105"
                style={{ backgroundColor: '#1a1f4e', color: '#f59e0b' }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'text-white shadow-lg'
                    : 'text-slate-400 hover:text-white'
                }`}
                style={{
                  backgroundColor: activeTab === tab.id ? '#1a1f4e' : 'transparent',
                  borderLeft: activeTab === tab.id ? '3px solid #f59e0b' : '3px solid transparent'
                }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className="text-xs px-1.5 py-0.5 rounded-full"
                    style={{
                      backgroundColor: activeTab === tab.id ? '#f59e0b' : '#1a1f4e',
                      color: activeTab === tab.id ? '#0a0e27' : '#f59e0b'
                    }}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'portfolio' && (
          <div className="space-y-6">
            <IBKRConnect onSync={handleRefresh} />
            <Dashboard refreshTrigger={refreshTrigger} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-xl p-6 border border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
                <AllocationChart refreshTrigger={refreshTrigger} />
              </div>
              <div className="rounded-xl p-6 border border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
                <PerformanceChart refreshTrigger={refreshTrigger} />
              </div>
            </div>

            <div className="rounded-xl p-6 border border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-white">Your Holdings</h2>
                <AddPositionForm onSuccess={handleRefresh} />
              </div>
              <PositionTable refreshTrigger={refreshTrigger} onRefresh={handleRefresh} />
            </div>
          </div>
        )}

        {activeTab === 'chat' && (
          <div className="rounded-xl border border-slate-700/50 overflow-hidden" style={{ backgroundColor: '#0d1230' }}>
            <ChatInterface />
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="rounded-xl p-6 border border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
            <StockAnalysis portfolioSymbols={portfolioSymbols} />
          </div>
        )}

        {activeTab === 'ml' && (
          <div className="rounded-xl p-6 border border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
            <MLPredictor />
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="rounded-xl p-6 border border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
            <AgentDashboard />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-700/50 mt-auto" style={{ backgroundColor: '#0d1230' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-xs text-slate-500 text-center">
            For educational purposes only. Not financial advice.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
