import { useState } from 'react';
import { memosApi } from '@/lib/api/client';
import { useToastStore } from '@/lib/store/useToastStore';
import { ArrowUp, Star, Archive } from 'lucide-react';

interface MemoryPromotionInterfaceProps {
  sessionId?: string;
}

export function MemoryPromotionInterface({ sessionId = 'default' }: MemoryPromotionInterfaceProps) {
  const [key, setKey] = useState('');
  const [significance, setSignificance] = useState<'low' | 'medium' | 'high'>('medium');
  const [loading, setLoading] = useState(false);
  const { addToast } = useToastStore();

  const handleMarkSignificant = async () => {
    if (!key.trim()) {
      addToast('Please enter a memory key', 'error');
      return;
    }

    setLoading(true);
    try {
      const result = await memosApi.markSignificant(sessionId, key, significance);
      if (result.status === 'promoted') {
        addToast(`Memory marked as ${significance} significance`, 'success');
        setKey('');
      } else {
        addToast(result.message, 'error');
      }
    } catch (error) {
      addToast('Failed to mark memory', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handlePromote = async () => {
    if (!key.trim()) {
      addToast('Please enter a memory key', 'error');
      return;
    }

    setLoading(true);
    try {
      const result = await memosApi.promoteMemory({
        session_id: sessionId,
        key,
        significance,
      });
      if (result.status === 'promoted') {
        addToast('Memory promoted to long-term storage', 'success');
        setKey('');
      } else {
        addToast(result.message, 'error');
      }
    } catch (error) {
      addToast('Failed to promote memory', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <ArrowUp className="h-5 w-5 text-primary" />
        Memory Promotion
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Memory Key
          </label>
          <input
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="e.g., last_query, context_depth"
            className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Significance Level
          </label>
          <div className="flex gap-2">
            {(['low', 'medium', 'high'] as const).map((level) => (
              <button
                key={level}
                onClick={() => setSignificance(level)}
                className={`flex-1 px-4 py-2 rounded-md border transition-colors capitalize ${
                  significance === level
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-border hover:bg-muted'
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            onClick={handleMarkSignificant}
            disabled={loading || !key.trim()}
            className="flex-1 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Star className="h-4 w-4" />
            Mark Significant
          </button>
          <button
            onClick={handlePromote}
            disabled={loading || !key.trim()}
            className="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-md transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Archive className="h-4 w-4" />
            Promote to LTM
          </button>
        </div>
      </div>
    </div>
  );
}
