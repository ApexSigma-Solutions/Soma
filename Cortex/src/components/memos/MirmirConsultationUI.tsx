import { useState } from 'react';
import { memosApi } from '@/lib/api/client';
import { useToastStore } from '@/lib/store/useToastStore';
import type { MirmirConsultationResult } from '@/lib/api/types/memos';
import { Sparkles, Loader2, Lightbulb, CheckCircle } from 'lucide-react';

export function MirmirConsultationUI() {
  const [plan, setPlan] = useState('');
  const [context, setContext] = useState('');
  const [result, setResult] = useState<MirmirConsultationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const { addToast } = useToastStore();

  const handleConsult = async () => {
    if (!plan.trim()) {
      addToast('Please enter a plan to evaluate', 'error');
      return;
    }

    setLoading(true);
    try {
      const response = await memosApi.consultMirmir({
        plan,
        context: context || undefined,
      });
      setResult(response);
      addToast('Mirmir consultation complete', 'success');
    } catch (error) {
      addToast('Consultation failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-primary" />
        Mirmir Consultation
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Plan to Evaluate
          </label>
          <textarea
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
            placeholder="Describe your implementation plan..."
            className="w-full h-32 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Additional Context (optional)
          </label>
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Any relevant context for Mirmir..."
            className="w-full h-20 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary text-sm"
          />
        </div>

        <button
          onClick={handleConsult}
          disabled={loading || !plan.trim()}
          className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Consulting Mirmir...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Consult Mirmir
            </>
          )}
        </button>

        {result && (
          <div className="mt-4 p-4 bg-background rounded-md border border-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span className="font-semibold">Recommendation</span>
              </div>
              <span className="text-sm text-muted-foreground">
                Confidence: {(result.confidence * 100).toFixed(0)}%
              </span>
            </div>

            <p className="text-sm text-foreground">{result.recommendation}</p>

            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Reasoning:</p>
              <p className="text-sm text-foreground">{result.reasoning}</p>
            </div>

            {result.suggested_actions && result.suggested_actions.length > 0 && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" />
                  Suggested Actions:
                </p>
                <ul className="space-y-1">
                  {result.suggested_actions.map((action, index) => (
                    <li key={index} className="text-sm text-foreground flex items-start gap-2">
                      <span className="text-primary">•</span>
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
