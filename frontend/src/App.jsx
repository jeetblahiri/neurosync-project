import React, { useState, useEffect, useMemo } from 'react';
import { 
  Brain, 
  Radio, 
  Cpu, 
  Activity, 
  Zap, 
  Globe, 
  FileText, 
  Terminal, 
  Share2, 
  ExternalLink,
  RefreshCw,
  Search,
  Layers,
  Sparkles,
  AlertCircle
} from 'lucide-react';

// --- CONFIGURATION ---
// In production, this would be your deployed backend URL (e.g., https://neurosync-api.onrender.com)
const BACKEND_URL = "http://127.0.0.1:8000";

// --- COMPONENTS ---

const Card = ({ item }) => {
  return (
    <div className="group relative bg-slate-900/50 backdrop-blur-md border border-slate-700/50 rounded-xl p-5 hover:border-cyan-500/50 hover:bg-slate-800/60 transition-all duration-300">
      <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <ExternalLink className="w-4 h-4 text-cyan-400" />
      </div>
      
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-xs font-bold px-2 py-1 rounded-full uppercase tracking-wider ${
          item.type === 'news' 
            ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' 
            : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
        }`}>
          {item.type === 'news' ? 'Intel' : 'Research'}
        </span>
        <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
          <Activity className="w-3 h-3" /> {item.date}
        </span>
        {item.author && (
          <span className="text-xs text-slate-500 truncate max-w-[150px]">
            {item.author !== "Unknown" ? `By ${item.author}` : "Multiple Authors"}
          </span>
        )}
      </div>

      <h3 className="text-lg font-semibold text-slate-100 leading-snug mb-2 group-hover:text-cyan-400 transition-colors">
        <a href={item.url} target="_blank" rel="noopener noreferrer" className="focus:outline-none">
          {item.title}
        </a>
      </h3>

      <p className="text-sm text-slate-400 leading-relaxed mb-4 line-clamp-3">
        {item.summary}
      </p>

      <div className="flex items-center justify-between mt-auto pt-3 border-t border-slate-700/30">
        <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">
          Source: {item.source}
        </span>
        <div className="flex gap-3">
          <button className="text-slate-500 hover:text-cyan-400 transition-colors" title="Save to Library">
             <Layers className="w-4 h-4" />
          </button>
          <button className="text-slate-500 hover:text-cyan-400 transition-colors" title="Share Network">
             <Share2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

const SynthesisPanel = ({ synthesis, loading, error }) => {
  return (
    <div className="mb-8 relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800 border border-slate-700 shadow-2xl">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 via-purple-500 to-cyan-500 animate-pulse"></div>
      
      <div className="p-6 md:p-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-500/10 rounded-lg animate-pulse">
            <Sparkles className="w-5 h-5 text-cyan-400" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-widest uppercase">
            Neural Convergence <span className="text-cyan-400">Protocol</span>
          </h2>
        </div>
        
        <div className="bg-black/30 rounded-xl p-6 border border-white/5 backdrop-blur-sm min-h-[100px] flex items-center">
          {loading ? (
            <div className="flex items-center gap-3 text-cyan-400 font-mono text-sm w-full">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span className="animate-pulse">Establishing uplink to Cortex Backend... extracting data...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-3 text-red-400 font-mono text-sm">
              <AlertCircle className="w-5 h-5" />
              <span>Connection Failed: Ensure Backend (main.py) is running on port 8000.</span>
            </div>
          ) : (
            <p className="text-slate-300 leading-relaxed font-light text-lg">
              {synthesis}
            </p>
          )}
        </div>
        
        <div className="mt-4 flex gap-4 text-xs font-mono text-slate-500">
           <span className="flex items-center gap-1"><Cpu className="w-3 h-3"/> BACKEND: {error ? 'OFFLINE' : 'CONNECTED'}</span>
           <span className="flex items-center gap-1"><Radio className="w-3 h-3"/> SOURCE: HYBRID_WEB</span>
           <span className="flex items-center gap-1"><Zap className="w-3 h-3"/> AI: ENABLED</span>
        </div>
      </div>
    </div>
  );
};

const Header = ({ onRefresh }) => (
  <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800 mb-8">
    <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Neuro<span className="text-cyan-400">Sync</span></h1>
          <p className="text-[10px] text-slate-400 font-mono uppercase tracking-widest hidden sm:block">Daily Intelligence Briefing</p>
        </div>
      </div>

      <nav className="flex items-center gap-4">
        <button 
          onClick={onRefresh}
          className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-all"
          title="Refresh Feed"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
        <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
        </div>
      </nav>
    </div>
  </header>
);

const FilterBar = ({ activeFilter, setFilter }) => {
  const filters = [
    { id: 'all', label: 'Global Feed', icon: Globe },
    { id: 'paper', label: 'Research Papers', icon: FileText },
    { id: 'news', label: 'Industry Intel', icon: Terminal },
  ];

  return (
    <div className="flex gap-2 mb-6 overflow-x-auto pb-2 scrollbar-hide">
      {filters.map(f => {
        const Icon = f.icon;
        const isActive = activeFilter === f.id;
        return (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              isActive 
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-[0_0_15px_-5px_rgba(6,182,212,0.5)]' 
                : 'bg-slate-800/50 text-slate-400 border border-slate-700 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <Icon className="w-4 h-4" />
            {f.label}
          </button>
        );
      })}
    </div>
  );
};

export default function App() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState('all');
  const [synthesis, setSynthesis] = useState('');

  const fetchArticles = async () => {
    setLoading(true);
    setError(false);
    try {
      // Fetch from our Python Backend
      const response = await fetch(`${BACKEND_URL}/feed`);
      
      if (!response.ok) {
        throw new Error("Backend connection failed");
      }

      const data = await response.json();
      
      setArticles(data.articles || []);
      setSynthesis(data.synthesis || "No synthesis data available.");
      
    } catch (error) {
      console.error("Failed to fetch stream:", error);
      setError(true);
      setArticles([]); 
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArticles();
  }, []);

  const filteredArticles = useMemo(() => {
    if (filter === 'all') return articles;
    return articles.filter(item => item.type === filter);
  }, [articles, filter]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30">
      <Header onRefresh={fetchArticles} />
      
      <main className="max-w-7xl mx-auto px-4 pb-20">
        <SynthesisPanel synthesis={synthesis} loading={loading} error={error} />
        
        <FilterBar activeFilter={filter} setFilter={setFilter} />

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-64 bg-slate-900/50 rounded-xl border border-slate-800"></div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredArticles.length > 0 ? (
                filteredArticles.map(article => (
                <Card key={article.id} item={article} />
                ))
            ) : (
                !loading && !error && (
                    <div className="col-span-full text-center text-slate-500 py-20">
                        No neural signals detected.
                    </div>
                )
            )}
          </div>
        )}
      </main>
      
      {/* Decorative background elements */}
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden -z-10">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-cyan-900/20 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-purple-900/20 rounded-full blur-[120px]"></div>
      </div>
    </div>
  );
}