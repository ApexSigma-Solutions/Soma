import { useState, useEffect } from 'react';
import { memosApi } from '@/lib/api/client';
import { useToastStore } from '@/lib/store/useToastStore';
import type { ScratchpadEntry } from '@/lib/api/types/memos';
import { StickyNote, Plus, Trash2, RefreshCw } from 'lucide-react';

interface ScratchpadInterfaceProps {
  sessionId?: string;
}

export function ScratchpadInterface({ sessionId = 'default' }: ScratchpadInterfaceProps) {
  const [entries, setEntries] = useState<ScratchpadEntry[]>([]);
  const [newEntry, setNewEntry] = useState('');
  const [loading, setLoading] = useState(false);
  const { addToast } = useToastStore();

  const fetchEntries = async () => {
    try {
      const data = await memosApi.readScratchpad(sessionId);
      setEntries(data);
    } catch (error) {
      console.error('Failed to fetch scratchpad:', error);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, [sessionId]);

  const handleAddEntry = async () => {
    if (!newEntry.trim()) return;

    setLoading(true);
    try {
      const entry = await memosApi.writeScratchpad(sessionId, newEntry);
      setEntries([entry, ...entries]);
      setNewEntry('');
      addToast('Entry added to scratchpad', 'success');
    } catch (error) {
      addToast('Failed to add entry', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    if (!confirm('Clear all scratchpad entries?')) return;

    try {
      await memosApi.clearScratchpad(sessionId);
      setEntries([]);
      addToast('Scratchpad cleared', 'success');
    } catch (error) {
      addToast('Failed to clear scratchpad', 'error');
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          <StickyNote className="h-5 w-5 text-primary" />
          Scratchpad
        </h3>
        <div className="flex gap-2">
          <button
            onClick={fetchEntries}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={handleClear}
            className="p-2 hover:bg-muted rounded-md transition-colors text-destructive"
            title="Clear all"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex gap-2">
          <textarea
            value={newEntry}
            onChange={(e) => setNewEntry(e.target.value)}
            placeholder="Add a quick note..."
            className="flex-1 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary text-sm"
            rows={2}
          />
          <button
            onClick={handleAddEntry}
            disabled={loading || !newEntry.trim()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Plus className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-2 max-h-64 overflow-y-auto">
          {entries.length === 0 ? (
            <p className="text-muted-foreground text-center py-8 text-sm">
              No entries yet. Add your first note above.
            </p>
          ) : (
            entries.map((entry) => (
              <div
                key={entry.id}
                className="p-3 bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-800 rounded-md"
              >
                <p className="text-sm text-foreground">{entry.content}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {new Date(entry.timestamp).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
