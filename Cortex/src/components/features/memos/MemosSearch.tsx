import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { memosApi } from '@/lib/api/client';
import { Search, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface MemoryResult {
  content: string;
  similarity: number;
  metadata?: Record<string, unknown>;
  created_at?: string;
  id?: number;
}

export function MemosSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<MemoryResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    setIsSearching(true);
    setSearched(true);
    setResults([]);

    try {
      const data = await memosApi.search(query);
      setResults(data.results || []);
    } catch (error) {
      console.error('Search failed', error);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>Memory Search</CardTitle>
        <CardDescription>Query the semantic knowledge graph.</CardDescription>
      </CardHeader>
      <div className="p-6 pt-0 border-b border-border">
        <form onSubmit={handleSearch} className="flex gap-2">
          <Input 
            placeholder="Search for concepts, code, or context..." 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Button type="submit" disabled={isSearching || !query}>
            {isSearching ? <Loader2 className="animate-spin h-4 w-4" /> : <Search className="h-4 w-4" />}
          </Button>
        </form>
      </div>
      <CardContent className="flex-1 overflow-auto p-0">
        {searched && results.length === 0 && !isSearching && (
           <div className="p-8 text-center text-muted-foreground">
             No memories found matching your query.
           </div>
        )}
        
        <div className="divide-y divide-border">
          {results.map((result, idx) => (
            <div key={result.id ?? `result-${idx}`} className="p-4 hover:bg-card/50 transition-colors">
              <div className="flex items-start justify-between mb-2">
                 <Badge variant="outline" className="font-mono text-[10px]">
                    score: {result.similarity?.toFixed(3)}
                 </Badge>
                 <span className="text-xs text-muted-foreground">
                    {result.created_at ? new Date(result.created_at).toLocaleDateString() : 'Unknown Date'}
                 </span>
              </div>
              <p className="text-sm text-foreground whitespace-pre-wrap line-clamp-4">
                {result.content}
              </p>
             {result.metadata && Object.keys(result.metadata).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                    {Object.entries(result.metadata).map(([k, v]) => (
                        <Badge key={`${result.id ?? `result-${idx}`}-${k}`} variant="secondary" className="text-[10px]">
                            {k}: {String(v).slice(0, 20)}
                        </Badge>
                    ))}
                </div>
             )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
