import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { memosApi, MirmirResponse } from '@/lib/api/client';
import { Loader2, ShieldCheck, AlertTriangle } from 'lucide-react';
import { Badge } from "@/components/ui/badge";

export function MimirQueryPanel() {
  const [query, setQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<MirmirResponse['result'] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    setIsSubmitting(true);
    setResult(null);
    setError(null);

    try {
      const response = await memosApi.consultMirmir(query);
      if (response.status === 'success') {
          setResult(response.result);
      } else {
          setError('Failed to consult Mirmir.');
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
                        <span className="font-semibold text-sm">Verdict:</span>
                        {result.approved ? (
                            <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600">APPROVED</Badge>
                        ) : (
                            <Badge variant="destructive">REJECTED</Badge>
                        )}
                    </div>
                    
                    <div className="space-y-1">
                         <div className="text-xs font-medium text-muted-foreground">Risk Score:</div>
                         <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                             <div 
                                className={`h-full ${result.risk_score > 0.5 ? 'bg-destructive' : 'bg-emerald-500'}`} 
                                style={{ width: `${result.risk_score * 100}%` }}
                             />
                         </div>
                         <div className="text-xs text-right text-muted-foreground">{(result.risk_score * 100).toFixed(0)}%</div>
                    </div>

                    <div className="text-sm">
                        <span className="font-semibold">Reasoning: </span>
                        {result.reasoning}
                    </div>

                    {result.citations.length > 0 && (
                        <div className="space-y-2">
                            <span className="text-xs font-semibold uppercase text-muted-foreground">Citations</span>
                            {result.citations.map((c, i) => (
                                <div key={i} className="text-xs p-2 bg-muted rounded border flex gap-2 items-start">
                                    <AlertTriangle className={`h-3 w-3 mt-0.5 ${c.severity === 'CRITICAL' ? 'text-destructive' : 'text-yellow-500'}`} />
                                    <div>
                                        <div className="font-mono font-bold text-[10px]">{c.rule_id}</div>
                                        <div>{c.content}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        )}
      </CardContent>
    </Card>
  );
}
