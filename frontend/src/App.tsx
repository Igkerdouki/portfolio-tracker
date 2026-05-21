import { useState, useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import { PositionTable } from './components/PositionTable';
import { AddPositionForm } from './components/AddPositionForm';
import { AllocationChart } from './components/AllocationChart';
import { PerformanceChart } from './components/PerformanceChart';
import { IBKRConnect } from './components/IBKRConnect';

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
    setLastUpdate(new Date());
  };

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
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
      </main>

      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-sm text-gray-500 text-center">
            Portfolio Tracker - Prices refresh every 60 seconds
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
