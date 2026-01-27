import { useEffect, useState } from 'react';
import { IngestStatus } from './IngestStatus';
import IngestPlayground from './IngestPlayground';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ingestApi, ServiceConfig } from '@/lib/api/client';
import { Loader2 } from 'lucide-react';

export function IngestControl() {
  const [config, setConfig] = useState<ServiceConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const data = await ingestApi.getConfig();
        setConfig(data);
      } catch (error) {
        console.error("Failed to fetch ingest config:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Section: Queue Metrics */}
      <section>
        <IngestStatus />
      </section>

      {/* Main Content Grid */}
      <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Left Column: Playground */}
        <div className="lg:col-span-2 h-[500px]">
            <IngestPlayground />
        </div>
        
        {/* Right Column: Info/Config */}
        <div className="h-full">
            <Card className="h-full">
                <CardHeader>
                    <CardTitle>Configuration</CardTitle>
                </CardHeader>
                <CardContent className="text-muted-foreground text-sm space-y-2">
                    {loading ? (
                        <div className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span>Loading config...</span>
                        </div>
                    ) : config ? (
                        <>
                            <p><strong className="text-foreground">Async Processing:</strong> {config.async_processing ? 'Enabled' : 'Disabled'}</p>
                            <p><strong className="text-foreground">Chunk Size:</strong> {config.chunk_size} chars</p>
                            <p><strong className="text-foreground">Embedding Model:</strong> {config.embedding_model}</p>
                            <p><strong className="text-foreground">Summarizer:</strong> {config.summarizer_model} <span className="text-xs opacity-70">({config.llm_provider})</span></p>
                        </>
                    ) : (
                        <p className="text-destructive">Failed to load configuration.</p>
                    )}
                    
                    <div className="pt-4 border-t border-border mt-4">
                        <p className="text-xs text-muted-foreground/70">
                            Configure these settings in environment variables or the Settings view.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
      </section>
    </div>
  );
}
