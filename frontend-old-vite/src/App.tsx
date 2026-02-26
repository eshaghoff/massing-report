import { useState } from 'react';
import SearchBar from './components/SearchBar';
import MassingViewer from './components/MassingViewer';
import ZoningPanel from './components/ZoningPanel';
import ScenarioPanel from './components/ScenarioPanel';
import { lookupAddress } from './services/api';
import type { CalculationResult } from './types';
import './App.css';

function App() {
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState(0);
  const [activeTab, setActiveTab] = useState<'zoning' | 'scenarios'>('zoning');

  const handleSearch = async (address: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setActiveScenario(0);

    try {
      const data = await lookupAddress(address);
      setResult(data);
      if (data.scenarios.length > 0) {
        setActiveTab('scenarios');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to analyze address';
      if (typeof err === 'object' && err !== null && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || msg);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <h1 className="title">NYC Zoning Feasibility Engine</h1>
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>
      </header>

      {/* Error */}
      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)} className="error-dismiss">x</button>
        </div>
      )}

      {/* Main content */}
      {!result && !loading && (
        <div className="landing">
          <div className="landing-content">
            <h2>Analyze NYC Development Potential</h2>
            <p>
              Enter any NYC address to automatically pull zoning data, calculate buildable
              floor area, and generate 3D massing diagrams for all feasible building configurations.
            </p>
            <div className="features">
              <Feature
                title="Zoning Analysis"
                desc="FAR, height limits, setbacks, yards, parking requirements"
              />
              <Feature
                title="Building Scenarios"
                desc="Max residential, commercial, mixed-use, community facility options"
              />
              <Feature
                title="3D Massing"
                desc="Interactive 3D diagrams showing buildable envelope and floor plates"
              />
              <Feature
                title="Unit Mix"
                desc="Dwelling unit counts, sizes, and configurations per scenario"
              />
            </div>
            <p className="disclaimer">
              This tool is for preliminary feasibility analysis only.
              It does not replace review by a licensed architect or zoning attorney.
            </p>
          </div>
        </div>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner" />
          <p>Analyzing zoning data...</p>
        </div>
      )}

      {result && (
        <div className="main-layout">
          {/* Left sidebar */}
          <div className="sidebar">
            <div className="sidebar-tabs">
              <button
                className={`sidebar-tab ${activeTab === 'zoning' ? 'active' : ''}`}
                onClick={() => setActiveTab('zoning')}
              >
                Zoning
              </button>
              <button
                className={`sidebar-tab ${activeTab === 'scenarios' ? 'active' : ''}`}
                onClick={() => setActiveTab('scenarios')}
              >
                Scenarios ({result.scenarios.length})
              </button>
            </div>
            <div className="sidebar-content">
              {activeTab === 'zoning' ? (
                <ZoningPanel lot={result.lot_profile} envelope={result.zoning_envelope} />
              ) : (
                <ScenarioPanel
                  scenarios={result.scenarios}
                  activeScenario={activeScenario}
                  onSelectScenario={setActiveScenario}
                />
              )}
            </div>
          </div>

          {/* 3D Viewer */}
          <div className="viewer">
            <MassingViewer
              scenarios={result.scenarios}
              activeScenario={activeScenario}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function Feature({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="feature-card">
      <h3>{title}</h3>
      <p>{desc}</p>
    </div>
  );
}

export default App;
