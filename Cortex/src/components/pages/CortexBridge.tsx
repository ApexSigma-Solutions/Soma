import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Brain, Zap, Activity, Send, Loader2, AlertCircle } from 'lucide-react';
import { useSystemTelemetry } from '@/hooks/useSystemTelemetry';
import { PeristalticFlow } from '@/components/visualization/PeristalticFlow';
import { ingressApi } from '@/lib/api/client';

export function CortexBridge() {
  const { telemetry, connected, error: pulseError } = useSystemTelemetry();
  const [sensationText, setSensationText] = useState('');
  const [isInitiating, setIsInitiating] = useState(false);

  const handleInitiateSensation = async () => {
    if (!sensationText.trim()) return;
    
    setIsInitiating(true);
    try {
      const response = await ingressApi.manualIngest({
        source: 'cortex_bridge',
        event_type: 'manual_sensation',
        payload: {
          content: sensationText,
          timestamp: new Date().toISOString(),
          metadata: { user: 'SigmaDev11' }
        }
      });
      
      console.log('Sensation captured:', response.ref);
      setSensationText('');
    } catch (error) {
      console.error('Failed to initiate sensation:', error);
    } finally {
      setIsInitiating(false);
    }
  };

  const allConnected = connected;
  const events = telemetry.senses.eventBuffer;
  const highEntropyCount = events.filter(e => e.metadata.entropy > 0.35).length;
  const reductionRate = events.length > 0 
    ? Math.round((highEntropyCount / events.length) * 100)
    : 0;

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-black text-foreground tracking-tighter uppercase italic">
            Cortex <span className="text-teal-500">Bridge</span>
          </h2>
          <p className="text-teal-500 font-mono text-[10px] uppercase tracking-[0.3em] font-bold mt-1">
            Biomorphic Neural Telemetry Stream
          </p>
        </div>
        <div className="flex items-center gap-2 bg-teal-500/10 border border-teal-500/20 rounded-lg px-4 py-2 glass-panel">
          <div className={`w-2 h-2 rounded-full ${allConnected ? 'bg-teal-500 animate-pulse shadow-[0_0_8px_rgba(0,191,166,0.8)]' : 'bg-red-500'}`}></div>
          <span className="text-[10px] text-foreground font-mono uppercase tracking-widest font-bold">
            {allConnected ? 'Neural Link Active' : 'Neural Link Offline'}
          </span>
        </div>
      </div>

      {/* Connection Error Banner */}
      {pulseError && (
        <Card className="border-red-500/30 bg-red-500/5">
          <CardContent className="py-4 flex items-center gap-2 text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm font-mono">{pulseError}</span>
          </CardContent>
        </Card>
      )}

      {/* Peristaltic Flow Visualization */}
      <PeristalticFlow telemetry={telemetry} />

      {/* Main Content Tabs */}
      <Tabs defaultValue="senses" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 bg-card/50 border border-teal-500/10 p-1">
          <TabsTrigger value="flow" className="data-[state=active]:bg-teal-500/20 data-[state=active]:text-teal-400">
            <Activity className="w-4 h-4 mr-2" />
            Flow
          </TabsTrigger>
          <TabsTrigger value="senses" className="data-[state=active]:bg-teal-500/20 data-[state=active]:text-teal-400">
            <Zap className="w-4 h-4 mr-2" />
            Senses
          </TabsTrigger>
          <TabsTrigger value="stomach" className="data-[state=active]:bg-teal-500/20 data-[state=active]:text-teal-400">
            <Activity className="w-4 h-4 mr-2" />
            Stomach
          </TabsTrigger>
          <TabsTrigger value="brain" className="data-[state=active]:bg-teal-500/20 data-[state=active]:text-teal-400">
            <Brain className="w-4 h-4 mr-2" />
            Brain
          </TabsTrigger>
        </TabsList>

        {/* Flow Tab - Peristaltic Flow already shown above, but providing details here */}
        <TabsContent value="flow" className="space-y-6">
          <Card className="glass-panel border-teal-500/10">
            <CardHeader>
              <CardTitle className="text-lg font-black tracking-tighter uppercase italic">Peristaltic Flow Details</CardTitle>
              <CardDescription className="font-mono text-[10px] tracking-wider">
                Real-time pipeline visualization showing data movement through biological systems
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-teal-500/10 rounded-lg">
                  <p className="text-sm font-bold text-teal-400">Senses Queue</p>
                  <p className="text-2xl font-mono">{telemetry.senses.eventBuffer.length}</p>
                </div>
                <div className="text-center p-4 bg-blue-500/10 rounded-lg">
                  <p className="text-sm font-bold text-blue-400">Stomach Queue</p>
                  <p className="text-2xl font-mono">{telemetry.stomach.queueDepth}</p>
                </div>
                <div className="text-center p-4 bg-purple-500/10 rounded-lg">
                  <p className="text-sm font-bold text-purple-400">Brain Nodes</p>
                  <p className="text-2xl font-mono">{telemetry.brain.nodeCount}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Senses Tab */}
        <TabsContent value="senses" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Manual Sensation Input */}
            <Card className="glass-panel border-teal-500/10">
              <CardHeader>
                <CardTitle className="text-lg font-black tracking-tighter uppercase italic">Manual Sensation</CardTitle>
                <CardDescription className="font-mono text-[10px] tracking-wider">
                  Inject raw signals into InGress (Senses Layer)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <textarea
                  className="flex min-h-[120px] w-full rounded-md border border-input bg-background/50 px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
                  placeholder="Enter sensation content here..."
                  value={sensationText}
                  onChange={(e) => setSensationText(e.target.value)}
                />
                <Button 
                  onClick={handleInitiateSensation} 
                  disabled={isInitiating || !sensationText.trim()}
                  className="w-full bg-teal-500/20 border border-teal-500/30 hover:bg-teal-500/30 text-teal-400"
                >
                  {isInitiating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Initiating...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Initiate Sensation
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Sensation Buffer */}
            <Card className="glass-panel border-teal-500/10">
              <CardHeader>
                <CardTitle className="text-lg font-black tracking-tighter uppercase italic">
                  Sensation Buffer
                  <Badge variant="outline" className="ml-2 border-teal-500/30 text-teal-400">
                    {events.length} events
                  </Badge>
                </CardTitle>
                <CardDescription className="font-mono text-[10px] tracking-wider">
                  Real-time stream from raw_lake → working_memory
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {events.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Activity className="w-12 h-12 mx-auto mb-3 opacity-30" />
                      <p className="text-sm font-mono">Waiting for neural pulses...</p>
                    </div>
                  ) : (
                    events.slice(0, 10).map((event) => (
                      <div
                        key={event.source_id}
                        className="p-3 rounded border border-teal-500/10 bg-card/50 text-xs font-mono space-y-1 hover:border-teal-500/30 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-teal-400 font-bold">{event.metadata.source}</span>
                          <Badge variant="outline" className="text-[10px]">
                            H: {event.metadata.entropy.toFixed(2)}
                          </Badge>
                        </div>
                        <div className="text-muted-foreground truncate">
                          {event.fact_units[0]?.text || 'Processing...'}
                        </div>
                        <div className="text-[10px] text-muted-foreground/50">
                          {new Date(event.metadata.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Stomach Tab */}
        <TabsContent value="stomach" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Entropy Gate Stats */}
            <Card className="glass-panel border-teal-500/10">
              <CardHeader>
                <CardTitle className="text-lg font-black tracking-tighter uppercase italic">Entropy Gate</CardTitle>
                <CardDescription className="font-mono text-[10px] tracking-wider">
                  SimpleMem Stage 1 Filtering (H &gt; 0.35)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-baseline justify-between mb-1">
                      <span className="text-sm text-muted-foreground font-mono">Reduction Rate</span>
                      <span className="text-2xl font-black text-teal-400">{reductionRate}%</span>
                    </div>
                    <div className="h-2 bg-card rounded-full overflow-hidden border border-teal-500/20">
                      <div 
                        className="h-full bg-gradient-to-r from-teal-500 to-emerald-500 transition-all duration-500"
                        style={{ width: `${reductionRate}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground font-mono space-y-1">
                    <div className="flex justify-between">
                      <span>High Entropy (passed):</span>
                      <span className="text-teal-400 font-bold">{highEntropyCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Low Entropy (filtered):</span>
                      <span className="text-muted-foreground">{events.length - highEntropyCount}</span>
                    </div>
                    <div className="flex justify-between border-t border-teal-500/10 pt-1 mt-1">
                      <span>Total Processed:</span>
                      <span className="font-bold">{events.length}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Latest Digestion Event */}
            <Card className="lg:col-span-2 glass-panel border-teal-500/10">
              <CardHeader>
                <CardTitle className="text-lg font-black tracking-tighter uppercase italic">Latest Digestion Event</CardTitle>
                <CardDescription className="font-mono text-[10px] tracking-wider">
                  Most recent pulse from InGest metabolism
                </CardDescription>
              </CardHeader>
              <CardContent>
                {latestEvent ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="border-teal-500/30 text-teal-400">
                        {latestEvent.metadata.event_type}
                      </Badge>
                      <span className="text-xs text-muted-foreground font-mono">
                        {new Date(latestEvent.metadata.timestamp).toLocaleString()}
                      </span>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="text-sm font-semibold text-foreground">Fact Units ({latestEvent.fact_units.length})</div>
                      {latestEvent.fact_units.map((fact, idx) => (
                        <div key={idx} className="p-3 rounded border border-teal-500/10 bg-card/30 text-sm">
                          <div className="text-foreground mb-2">{fact.text}</div>
                          {fact.entity_mentions.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {fact.entity_mentions.map((entity, i) => (
                                <Badge key={i} variant="secondary" className="text-[10px]">
                                  {entity}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center justify-between p-3 rounded border border-teal-500/10 bg-teal-500/5">
                      <span className="text-xs text-muted-foreground font-mono">Entropy Score</span>
                      <span className="text-lg font-black text-teal-400">{latestEvent.metadata.entropy.toFixed(3)}</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <Activity className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p className="text-sm font-mono">No digestion events yet</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Brain Tab */}
        <TabsContent value="brain" className="space-y-6">
          <Card className="glass-panel border-teal-500/10">
            <CardHeader>
              <CardTitle className="text-lg font-black tracking-tighter uppercase italic">OmegaKG Knowledge Graph</CardTitle>
              <CardDescription className="font-mono text-[10px] tracking-wider">
                Real-time Neo4j metrics from the Brain layer
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Total Nodes */}
                <div className="text-center p-6 bg-purple-500/10 rounded-lg border border-purple-500/20">
                  <Brain className="w-12 h-12 mx-auto mb-3 text-purple-500" />
                  <p className="text-4xl font-black text-purple-400 font-mono">
                    {telemetry.brain.nodeCount.toLocaleString()}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">Total Atomic Facts</p>
                </div>

                {/* Average Connectivity */}
                <div className="text-center p-6 bg-purple-500/10 rounded-lg border border-purple-500/20">
                  <Activity className="w-12 h-12 mx-auto mb-3 text-purple-500" />
                  <p className="text-4xl font-black text-purple-400 font-mono">
                    {telemetry.brain.avgConnectivity.toFixed(2)}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">Avg Connectivity</p>
                </div>

                {/* Embedding Dimension */}
                <div className="text-center p-6 bg-purple-500/10 rounded-lg border border-purple-500/20">
                  <Zap className="w-12 h-12 mx-auto mb-3 text-purple-500" />
                  <p className="text-4xl font-black text-purple-400 font-mono">
                    {telemetry.brain.embeddingDimension}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">Embedding Dimension</p>
                </div>
              </div>

              {/* Connection Status */}
              <div className="mt-6 flex items-center justify-center gap-4">
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
                  telemetry.brain.connected 
                    ? 'bg-green-500/10 text-green-400' 
                    : 'bg-red-500/10 text-red-400'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${
                    telemetry.brain.connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                  }`} />
                  <span className="text-sm font-mono">
                    {telemetry.brain.connected ? 'Connected to Neo4j' : 'Neo4j Disconnected'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
