import { useEffect, useState } from 'react';
import { omegaKgApi } from '@/lib/api/client';
import type { KnowledgeCommit } from '@/lib/api/types/omegakg';
import { GitCommit, CheckCircle, Clock, XCircle } from 'lucide-react';

export function KnowledgeCommitTracker() {
  const [commits, setCommits] = useState<KnowledgeCommit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCommits = async () => {
      try {
        const data = await omegaKgApi.getKnowledgeCommits();
        setCommits(data);
      } catch (error) {
        console.error('Failed to fetch commits:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCommits();
    const interval = setInterval(fetchCommits, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'validated':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'rejected':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'validated':
        return 'bg-green-500/20 text-green-500';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-500';
      case 'rejected':
        return 'bg-red-500/20 text-red-500';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  if (loading) {
    return <div className="animate-pulse bg-card border border-border rounded-lg p-6 h-48" />;
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <GitCommit className="h-5 w-5 text-primary" />
        Knowledge Commits
      </h3>

      <div className="space-y-3">
        {commits.map((commit) => (
          <div
            key={commit.id}
            className="p-4 bg-background rounded-md border border-border"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                {getStatusIcon(commit.status)}
                <code className="text-sm font-mono">{commit.id}</code>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(commit.status)}`}>
                {commit.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Facts:</span>{' '}
                <span className="font-medium">{commit.facts_count}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Created:</span>{' '}
                <span>{new Date(commit.created_at).toLocaleString()}</span>
              </div>
              {commit.validated_at && (
                <div>
                  <span className="text-muted-foreground">Validated:</span>{' '}
                  <span>{new Date(commit.validated_at).toLocaleString()}</span>
                </div>
              )}
              {commit.validator && (
                <div>
                  <span className="text-muted-foreground">Validator:</span>{' '}
                  <span className="font-medium">{commit.validator}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
