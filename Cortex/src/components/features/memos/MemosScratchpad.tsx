import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { memosApi } from '@/lib/api/client';
import { ClipboardList, RefreshCw } from 'lucide-react';

export function MemosScratchpad() {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const fetchScratchpad = async () => {
    setLoading(true);
    try {
      const data = await memosApi.getScratchpad();
      setContent(data.content || 'Scratchpad is empty.');
    } catch (error) {
      console.error('Failed to fetch scratchpad', error);
      setContent('Error loading scratchpad.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScratchpad();
  }, []);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="space-y-1">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
                <ClipboardList className="h-4 w-4" /> 
                Working Memory
            </CardTitle>
            <CardDescription>Current scratchpad context.</CardDescription>
        </div>
        <Button variant="ghost" size="icon" onClick={fetchScratchpad} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        <div className="h-full w-full rounded-md border bg-muted/50 p-4 font-mono text-sm overflow-auto whitespace-pre-wrap text-muted-foreground">
            {content}
        </div>
      </CardContent>
    </Card>
  );
}
