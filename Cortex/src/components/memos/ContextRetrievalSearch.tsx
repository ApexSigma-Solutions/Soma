import { useState } from 'react';
import { memosApi } from '@/lib/api/client';
import { useToastStore } from '@/lib/store/useToastStore';
import type { ContextRetrievalResult } from '@/lib/api/types/memos';
import { Search, Database, Loader2 } from 'lucide-react';

interface ContextRetrievalSearchProps {
  agentId?: string;
}

export function ContextRetrievalSearch({ agentId = 'default' }: ContextRetrievalSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ContextRetrievalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const { addToast } = useToastStore();

  const handleSearch = async () => {
    if (!query.trim()) {
      addToast('Please enter a search query', 'error');
      return;
    }

    setLoading(true);
    try {
      const response = await memosApi.retrieveContext({
        query,
        agent_id: agentId,
        limit: 10,
      });
      setResults(response);
      addToast(`Found ${response.results_count} results`, 'success');
    } catch (error) {
      addToast('Context retrieval failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Database className="h-5 w-5 text-primary" />
        Context Retrieval
      </h3>

      <div className="space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across working and long-term memory..."
            className="flex-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Retrieve
          </button>
        </div>

        {results && (
          <div className="space-y-4">
            {/* Working Memory */}
            {Object.keys(results.working_memory).length > 0 && (
              <div className="p-4 bg-blue-50 dark:bg-blue-950/30 rounded-md border border-blue-200 dark:border-blue-800">
                <h4 className="font-semibold text-sm mb-2 text-blue-700 dark:text-blue-300">
                  Working Memory
                </h4>
                <div className="space-y-1">
                  {Object.entries(results.working_memory).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">{key}:</span>
                      <span className="font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Long-term Memory Results */}
            {results.long_term_memory.length > 0 && (
              <div>
                <h4 className="font-semibold text-sm mb-2">
                  Long-term Memory ({results.results_count} results)
                </h4>
                <div className="space-y-2">
                  {results.long_term_memory.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 bg-background rounded-md border border-border"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium px-2 py-0.5 bg-muted rounded">
                            {item.source}
                          </span>
                          <code className="text-xs">{item.id}</code>
                        </div>
                        <span className="text-xs text-primary font-medium">
                          {(item.relevance * 100).toFixed(0)}% match
                        </span>
                      </div>
                      <p className="text-sm text-foreground">{item.content}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sources */}
            <div className="flex flex-wrap gap-2">
              <span className="text-sm text-muted-foreground">Sources:</span>
              {results.sources.map((source) => (
                <span
                  key={source}
                  className="text-xs px-2 py-1 bg-muted rounded-full"
                >
                  {source}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
