import { useState } from 'react';
import { omegaKgApi } from '@/lib/api/client';
import { useToastStore } from '@/lib/store/useToastStore';
import type { SemanticSearchResult } from '@/lib/api/types/omegakg';
import { Search, Loader2, SlidersHorizontal } from 'lucide-react';

export function SemanticSearchInterface() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SemanticSearchResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [useHybrid, setUseHybrid] = useState(true);
  const [threshold, setThreshold] = useState(0.7);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { addToast } = useToastStore();

  const handleSearch = async () => {
    if (!query.trim()) {
      addToast('Please enter a search query', 'error');
      return;
    }

    setIsSearching(true);
    try {
      const response = await omegaKgApi.semanticSearch({
        query,
        hybrid: useHybrid,
        threshold,
        limit: 10,
      });
      setResults(response);
    } catch (error) {
      addToast(`Search failed: ${error}`, 'error');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Search className="h-5 w-5 text-primary" />
        Semantic Search
      </h3>

      <div className="space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search knowledge graph..."
            className="flex-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={isSearching}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isSearching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Search
          </button>
        </div>

        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-2"
        >
          <SlidersHorizontal className="h-4 w-4" />
          {showAdvanced ? 'Hide' : 'Show'} Advanced Options
        </button>

        {showAdvanced && (
          <div className="p-4 bg-background rounded-md border border-border space-y-4">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="hybrid"
                checked={useHybrid}
                onChange={(e) => setUseHybrid(e.target.checked)}
                className="h-4 w-4 rounded border-border"
              />
              <label htmlFor="hybrid" className="text-sm">
                Enable hybrid search (vector + keyword)
              </label>
            </div>

            <div>
              <label className="block text-sm mb-2">
                Similarity Threshold: {threshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0.5"
                max="0.95"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
          </div>
        )}

        {results && (
          <div className="mt-4 space-y-3">
            <div className="flex justify-between items-center text-sm text-muted-foreground">
              <span>{results.total} results</span>
              <span>{results.query_time_ms}ms</span>
            </div>

            {results.facts.map((fact) => (
              <div
                key={fact.id}
                className="p-4 bg-background rounded-md border border-border hover:border-primary/50 transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <code className="text-xs bg-muted px-2 py-1 rounded">{fact.id}</code>
                  <div className="flex gap-2 text-xs">
                    {fact.similarity && (
                      <span className="text-primary font-medium">
                        {(fact.similarity * 100).toFixed(1)}% match
                      </span>
                    )}
                    {fact.confidence && (
                      <span className="text-muted-foreground">
                        {(fact.confidence * 100).toFixed(0)}% conf
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-sm text-foreground">{fact.content}</p>
                <div className="mt-2 text-xs text-muted-foreground">
                  Source: {fact.source} • {new Date(fact.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
