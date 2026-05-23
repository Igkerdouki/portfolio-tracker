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
  { id: 'chat', label: 'AI Advisor', icon: '🧠', badge: 'NEW' },
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-xl border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-xl flex items-center justify-center text-xl shadow-lg shadow-purple-500/30">
                🏛️
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">
                  Yiayia's Alpha
                </h1>
                <p className="text-xs text-gray-400">Investment Intelligence</p>
              </div>
            </div>

            {/* Status */}
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-400">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span>Live</span>
                <span className="text-gray-600">•</span>
                <span>{lastUpdate.toLocaleTimeString()}</span>
              </div>
              <button
                onClick={handleRefresh}
                className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all hover:scale-105"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="mt-4 flex gap-1 overflow-x-auto pb-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg shadow-purple-500/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/10'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.badge && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                    activeTab === tab.id
                      ? 'bg-white/20 text-white'
                      : 'bg-purple-500/20 text-purple-300'
                  }`}>
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
        {/* Portfolio Tab */}
        {activeTab === 'portfolio' && (
          <div className="space-y-6">
            <IBKRConnect onSync={handleRefresh} />
            <Dashboard refreshTrigger={refreshTrigger} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
                <AllocationChart refreshTrigger={refreshTrigger} />
              </div>
              <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
                <PerformanceChart refreshTrigger={refreshTrigger} />
              </div>
            </div>

            <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-white">Your Holdings</h2>
                <AddPositionForm onSuccess={handleRefresh} />
              </div>
              <PositionTable refreshTrigger={refreshTrigger} onRefresh={handleRefresh} />
            </div>
          </div>
        )}

        {/* AI Chat Tab */}
        {activeTab === 'chat' && (
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 overflow-hidden">
            <ChatInterface />
          </div>
        )}

        {/* Analysis Tab */}
        {activeTab === 'analysis' && (
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
            <StockAnalysis portfolioSymbols={portfolioSymbols} />
          </div>
        )}

        {/* ML Predictor Tab */}
        {activeTab === 'ml' && (
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
            <MLPredictor />
          </div>
        )}

        {/* Agents Tab */}
        {activeTab === 'agents' && (
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
            <AgentDashboard />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-black/30 border-t border-white/10 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🏛️</span>
              <div>
                <p className="text-sm font-medium bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                  Yiayia's Alpha
                </p>
                <p className="text-xs text-gray-500">Built with Areti (Excellence)</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 text-center">
              For educational purposes only. Not financial advice. Always do your own research.
            </p>
            <div className="flex items-center gap-4 text-gray-500 text-sm">
              <span>🇬🇷</span>
              <span>Made with wisdom</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
