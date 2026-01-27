import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { captureApi } from '@/lib/api/client';
import { Loader2, Send } from 'lucide-react';

export function ManualCaptureForm() {
  const [url, setUrl] = useState('');
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content) return;

    setIsSubmitting(true);
    setResult(null);

    try {
      await captureApi.manualCapture({
        url: url || 'manual-entry',
        platform: 'manual',
        content: content,
        messages: [
          {
            role: 'user',
            content: content
          }
        ]
      });
      setResult({ success: true, message: 'Capture queued successfully' });
      setContent('');
      setUrl('');
    } catch (error) {
        let msg = 'Capture failed';
        if (error instanceof Error) msg = error.message;
      setResult({ success: false, message: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Manual Capture</CardTitle>
        <CardDescription>Manually inject content into the ingestion pipeline.</CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Source URL (Optional)</label>
            <Input 
              placeholder="https://example.com" 
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Content / Message</label>
            <textarea
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Enter text content here..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
            />
          </div>
          {result && (
            <div className={`p-3 rounded text-sm ${result.success ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}`}>
              {result.message}
            </div>
          )}
        </CardContent>
        <CardFooter>
          <Button type="submit" disabled={isSubmitting || !content} className="w-full">
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Capturing...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Capture Content
              </>
            )}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
