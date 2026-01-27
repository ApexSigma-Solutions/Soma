import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { memosApi, MemosStats } from '@/lib/api/client';
import { Brain, Database, FileText, Layers } from 'lucide-react';



export function MemosStatus() {
  const [stats, setStats] = useState<MemosStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const data = await memosApi.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch memos stats', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Memory Status</CardTitle>
        </CardHeader>
        <CardContent>Loading memory metrics...</CardContent>
      </Card>
    );
  }

  // Calculate totals from tiers if needed, or use reported total
  const semanticCount = stats?.by_tier?.['semantic'] || 0;
  const proceduralCount = stats?.by_tier?.['procedural'] || 0;
  
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Total Memories */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Memories</CardTitle>
          <Database className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.total_memories || 0}</div>
          <p className="text-xs text-muted-foreground">
            Stored in PGVector
          </p>
        </CardContent>
      </Card>

      {/* Semantic Memory */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Semantic</CardTitle>
          <Brain className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{semanticCount}</div>
          <p className="text-xs text-muted-foreground">
            Knowledge & Concepts
          </p>
        </CardContent>
      </Card>

      {/* Procedural Memory */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Procedural</CardTitle>
          <Layers className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{proceduralCount}</div>
          <p className="text-xs text-muted-foreground">
            Code & Workflows
          </p>
        </CardContent>
      </Card>

      {/* Agents Active */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
          <FileText className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.by_agent ? Object.keys(stats.by_agent).length : 0}</div>
          <p className="text-xs text-muted-foreground">
            Contributing to memory
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
