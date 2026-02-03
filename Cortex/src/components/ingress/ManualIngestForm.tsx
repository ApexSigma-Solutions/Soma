import { useState } from 'react';
import { ingressApi } from '@/lib/api/ingressApi';
import { useToastStore } from '@/lib/store/useToastStore';
import { Send, Loader2 } from 'lucide-react';

export function ManualIngestForm() {
  const [source, setSource] = useState('manual');
  const [eventType, setEventType] = useState('user_action');
  const [payload, setPayload] = useState('{}');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { addToast } = useToastStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Validate JSON payload
      const parsedPayload = JSON.parse(payload);
      
      const response = await ingressApi.manualIngest({
        source,
        event_type: eventType,
        payload: parsedPayload,
      });

      addToast(`Signal captured successfully! Ref: ${response.ref}`, 'success');
      
      // Reset form
      setPayload('{}');
    } catch (error) {
      if (error instanceof SyntaxError) {
        addToast('Invalid JSON payload format', 'error');
      } else {
        addToast(`Ingest failed: ${error}`, 'error');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFormatJson = () => {
    try {
      const parsed = JSON.parse(payload);
      setPayload(JSON.stringify(parsed, null, 2));
    } catch (error) {
      addToast('Invalid JSON - cannot format', 'error');
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Send className="h-5 w-5 text-primary" />
        Manual Signal Ingestion
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Source
            </label>
            <input
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="e.g., manual, test, webhook"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Event Type
            </label>
            <input
              type="text"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="e.g., user_action, system_event"
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium text-foreground">
              Payload (JSON)
            </label>
            <button
              type="button"
              onClick={handleFormatJson}
              className="text-xs text-primary hover:text-primary/80 transition-colors"
            >
              Format JSON
            </button>
          </div>
          <textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            className="w-full h-40 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-mono text-sm"
            placeholder='{"key": "value"}'
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Sending...
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Capture Signal
            </>
          )}
        </button>
      </form>
    </div>
  );
}
