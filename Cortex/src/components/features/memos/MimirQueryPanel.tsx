import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { memosApi } from '@/lib/api/client';
import type { MirmirConsultationResult } from '@/lib/api/types/memos';
import { Loader2, ShieldCheck } from 'lucide-react';
import { Badge } from "@/components/ui/badge";

export function MimirQueryPanel() {
  const [query, setQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<MirmirConsultationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    setIsSubmitting(true);
    setResult(null);
    setError(null);

    try {
      const response = await memosApi.consultMirmir({ plan: query });
      if (response.status && response.status !== 'success') {
          setError(response.result ?? 'Failed to consult Mirmir.');
      } else {
          setResult(response);
      }
    } catch (err) {
        let msg = 'Consultation failed';
        if (err instanceof Error) msg = err.message;
        setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-500" />
            Mimir Query
        </CardTitle>
        <CardDescription>Consult the Codex for architectural constraints.</CardDescription>
      </CardHeader>
      
      <CardContent className="flex-1 overflow-hidden flex flex-col gap-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
            <Input 
              placeholder="Describe your plan (e.g., 'Delete legacy user table')" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={isSubmitting || !query} size="sm">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Consult'}
            </Button>
        </form>

        {error && (
            <div className="p-3 rounded text-sm bg-destructive/10 text-destructive">
                {error}
            </div>
        )}

        {result && (
             <div className="flex-1 rounded-md border p-4 overflow-auto">
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm">Recommendation</span>
                        {result.status && (
                            <Badge
                                variant={result.status === 'success' ? 'default' : 'destructive'}
                                className={result.status === 'success' ? 'bg-emerald-500 hover:bg-emerald-600' : undefined}
                            >
                                {result.status.toUpperCase()}
                            </Badge>
                        )}
                    </div>

                    <div className="text-sm">
                        {result.recommendation}
                    </div>

                    <div className="text-xs text-muted-foreground">
                        Confidence: {Number.isFinite(result.confidence) ? `${Math.round(result.confidence * 100)}%` : '--'}
                    </div>

                    <div className="text-sm">
                        <span className="font-semibold">Reasoning: </span>
                        {result.reasoning}
                    </div>

                    {result.suggested_actions && result.suggested_actions.length > 0 && (
                        <div className="space-y-2">
                            <span className="text-xs font-semibold uppercase text-muted-foreground">Suggested Actions</span>
                            <ul className="space-y-1">
                                {result.suggested_actions.map((action, i) => (
                                    <li key={i} className="text-xs text-muted-foreground">• {action}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
        )}
      </CardContent>
    </Card>
  );
}
