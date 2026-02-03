import { useEffect, useState } from 'react';
import { omegaKgApi } from '@/lib/api/client';
import type { AtomicFact } from '@/lib/api/types/omegakg';
import { Database, ChevronLeft, ChevronRight } from 'lucide-react';

const PAGE_SIZE = 10;

export function AtomicFactBrowser() {
  const [facts, setFacts] = useState<AtomicFact[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const fetchFacts = async () => {
    setLoading(true);
    try {
      const response = await omegaKgApi.getAtomicFacts(page, PAGE_SIZE);
      setFacts(response.facts);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to fetch atomic facts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFacts();
  }, [page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Database className="h-5 w-5 text-primary" />
        Atomic Fact Browser
      </h3>

      {loading ? (
        <div className="animate-pulse space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-muted rounded-md" />
          ))}
        </div>
      ) : (
        <>
          <div className="space-y-3 mb-4">
            {facts.map((fact) => (
              <div
                key={fact.id}
                className="p-4 bg-background rounded-md border border-border"
              >
                <div className="flex justify-between items-start mb-2">
                  <code className="text-xs bg-muted px-2 py-1 rounded">{fact.id}</code>
                  {fact.confidence && (
                    <span className="text-xs text-primary font-medium">
                      {(fact.confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
                <p className="text-sm text-foreground">{fact.content}</p>
                <div className="mt-2 text-xs text-muted-foreground">
                  {fact.source} • {new Date(fact.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-border">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center gap-1 px-3 py-1.5 bg-muted rounded-md hover:bg-muted/80 disabled:opacity-50 text-sm"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>

            <span className="text-sm text-muted-foreground">
              Page {page} of {totalPages} ({total} total)
            </span>

            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="flex items-center gap-1 px-3 py-1.5 bg-muted rounded-md hover:bg-muted/80 disabled:opacity-50 text-sm"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
