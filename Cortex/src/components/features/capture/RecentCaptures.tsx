import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { captureApi, CaptureResponse } from '@/lib/api/client';

export function RecentCaptures() {
  const [captures, setCaptures] = useState<CaptureResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchCaptures = async () => {
      try {
        const data = await captureApi.getRecent();
        setCaptures(data);
      } catch (error) {
        console.error('Failed to fetch recently captured items', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCaptures();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchCaptures, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Recent Captures</CardTitle>
        <CardDescription>Latest content ingested into the system.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
            <div className="flex justify-center items-center h-40">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        ) : (
            <div className="space-y-4">
            {captures.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                    No recent captures found.
                </div>
            ) : (
                captures.map((capture, index) => {
                    // Extract data from message for display using a simple split for now
                    // Message format: "Captured via {platform} at {timestamp}"
                    const parts = capture.message.split(' via ');
                    const platform = parts.length > 1 ? parts[1].split(' at ')[0] : 'Unknown';
                    const isProcessed = capture.success; // Simplified status logic

                    return (
                        <div key={index} className="flex items-center justify-between p-3 border border-border rounded-lg bg-card/50 hover:bg-card transition-colors">
                        <div className="flex items-start gap-3">
                            <div className={`mt-1 p-1 rounded-full ${
                            isProcessed ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
                            }`}>
                            {isProcessed ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                            </div>
                            <div>
                            <p className="text-sm font-medium text-primary line-clamp-1">{capture.file_path}</p>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-muted-foreground capitalize">{platform}</span>
                            </div>
                            </div>
                        </div>
                        <Badge variant={isProcessed ? 'success' : 'error'}>
                            {isProcessed ? 'Queued' : 'Failed'}
                        </Badge>
                        </div>
                    );
                })
            )}
            </div>
        )}
      </CardContent>
    </Card>
  );
}
