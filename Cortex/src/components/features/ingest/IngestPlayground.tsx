import { useState, useRef } from 'react';
import { Upload, FileText, Activity, Server, AlertCircle, Play, Loader2, Timer } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ParseResponse } from '@/lib/api/client';
import { useToastStore } from '@/lib/store/useToastStore';
import { IngestStatus } from './IngestStatus';

const InGestPlayground = () => {
  const { addToast } = useToastStore();
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [model, setModel] = useState<string>('en_core_web_trf');
  const [extractionMode, setExtractionMode] = useState<string>('llm_inference');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingTime, setLoadingTime] = useState(0);
  const [result, setResult] = useState<ParseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Timer ref to manage the loading counter
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // File Handler
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setFileName(selectedFile.name);
    setError(null);
    setResult(null);
  };

  // API Integration (Connecting to TNP-PAR-500 Backend)
  const handleParse = async () => {
    if (!file) {
      setError("Please upload a file first.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setLoadingTime(0);

    // Start a visual timer
    timerRef.current = setInterval(() => {
      setLoadingTime(prev => prev + 1);
    }, 1000);

    // Timeout Configuration (60s for xlarge_docs per KG)
    const TIMEOUT_MS = 60000; 
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      // Construct FormData for file upload
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model_name', model);
      formData.append('extraction_mode', extractionMode);

      // Direct fetch to /graph/parse/file endpoint
      const response = await fetch('http://localhost:8766/graph/parse/file', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Engine Error: ${response.statusText} (${response.status})`);
      }

      const data = await response.json();
      const graphData = data.data || data; 
      setResult(graphData);
      addToast('Knowledge Digest Received', 'success');
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          setError(`Request timed out after ${TIMEOUT_MS / 1000}s. The document might be too large.`);
        } else {
          setError(err.message);
        }
      } else {
        setError("An unknown error occurred");
      }
    } finally {
      setIsLoading(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Real-time Stats Integration */}
      <IngestStatus />

      {/* Header Area */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold text-primary tracking-tight flex items-center gap-2">
            <Activity className="w-6 h-6" />
            InGest-LLM.as Playground
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Knowledge Graph Extraction Engine (v4.0.2 Integration)
          </p>
        </div>
        <Badge variant="success" className="flex items-center gap-2">
          <Server className="w-4 h-4" />
          <span>ONLINE</span>
        </Badge>
      </div>

      <div className="grid gap-6 md:grid-cols-2 h-[500px]">
        
        {/* LEFT PANEL: Input & Controls */}
        <div className="h-full flex flex-col gap-4">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Document Upload</CardTitle>
              <CardDescription>Upload files for knowledge graph extraction</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              
              {/* File Upload Zone */}
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-border rounded-lg cursor-pointer bg-card/50 hover:bg-card transition-all">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <Upload className="w-8 h-8 mb-2 text-muted-foreground hover:text-primary" />
                  <p className="mb-2 text-sm text-muted-foreground">
                    <span className="font-semibold">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-muted-foreground/80">TXT, MD, PDF, DOCX files (MAX 5MB)</p>
                </div>
                <input 
                  type="file" 
                  className="hidden" 
                  accept=".txt,.md,.pdf,.docx"
                  onChange={handleFileUpload} 
                />
              </label>
              
          {fileName && (
                <div className="flex items-center gap-2 text-primary text-sm bg-primary/10 p-2 rounded border border-border">
                  <FileText className="w-4 h-4" />
                  <span className="truncate">{fileName}</span>
                </div>
              )}

              {/* Model Selection */}
              <div className="space-y-2 pt-2 border-t border-border/50">
                  <label className="text-xs font-mono font-bold uppercase text-muted-foreground tracking-wider">Extraction Model</label>
                  <select 
                    value={model} 
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-card/50 border border-input rounded-md py-2 px-3 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                        <option value="en_core_web_trf">Best Accuracy (Transformer)</option>
                        <option value="en_core_web_md">Balanced (Vectors)</option>
                        <option value="en_core_web_sm">Fastest (Lightweight)</option>
                  </select>
                  <p className="text-[10px] text-muted-foreground italic">
                      {model === 'en_core_web_trf' && "High memory usage. Best for complex entities."}
                      {model === 'en_core_web_md' && "Good balance of speed and accuracy."}
                      {model === 'en_core_web_sm' && "Instant results, basic extraction."}
                  </p>
              </div>
              
              {/* Extraction Mode selection */}
              <div className="space-y-2 pt-2 border-t border-border/50">
                  <label className="text-xs font-mono font-bold uppercase text-muted-foreground tracking-wider">Extraction Strategy</label>
                  <select 
                    value={extractionMode} 
                    onChange={(e) => setExtractionMode(e.target.value)}
                    className="w-full bg-card/50 border border-input rounded-md py-2 px-3 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                        <option value="llm_inference">LLM Inference (Deep Analysis)</option>
                        <option value="hybrid">Hybrid (NER + SVO)</option>
                        <option value="ner_only">Named Entities (Fast)</option>
                        <option value="svo">Subject-Verb-Object (Legacy)</option>
                  </select>
                  <p className="text-[10px] text-muted-foreground italic">
                      {extractionMode === 'llm_inference' && "Uses GPT-4o-mini logic for high-quality relationship mapping."}
                      {extractionMode === 'hybrid' && "Combines recognized entities with implied relationships."}
                      {extractionMode === 'ner_only' && "Focuses on Person, Organization, Location, and Work entities."}
                      {extractionMode === 'svo' && "Extracts all noun-verb triples. High recall, lower precision."}
                  </p>
              </div>

              {/* Action Button */}
              <button
                onClick={handleParse}
                disabled={!file || isLoading}
                className={`
                  w-full py-3 px-4 rounded-lg font-bold flex items-center justify-center gap-2 transition-all
                  {!file || isLoading 
                    ? 'bg-muted text-muted-foreground cursor-not-allowed' 
                    : 'bg-primary hover:bg-primary/90 text-primary-foreground'}
                `}
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing... ({loadingTime}s)</span>
                  </div>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    Initialize Extraction
                  </>
                )}
              </button>

              {/* Timeout Warning / Hint */}
              {isLoading && loadingTime > 5 && (
                <div className="text-xs text-yellow-500/80 flex items-center gap-1 bg-yellow-950/20 p-2 rounded">
                  <Timer className="w-3 h-3" />
                  <span>Large documents may take up to 60s...</span>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="bg-destructive/10 border border-destructive/50 text-destructive p-3 rounded text-sm flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* RIGHT PANEL: Results Visualization */}
        <div className="h-full">
          <Card className="h-full">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Extraction Results</CardTitle>
                {result && (
                  <Badge variant="outline">
                    {result.nodes.length} Nodes | {result.edges.length} Relations
                  </Badge>
                )}
              </div>
              <CardDescription>Extracted entities and relationships from document</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {!result ? (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
                  <Activity className="w-16 h-16 mb-4" />
                  <p>Waiting for input stream...</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Nodes List */}
                  <div className="space-y-2">
                    <h3 className="text-xs text-muted-foreground mb-2 font-bold uppercase tracking-wider">DETECTED ENTITIES</h3>
                    {result.nodes.map((node, i) => (
                      <div key={i} className="flex flex-col p-3 border border-border rounded-lg bg-card/50 hover:bg-card transition-colors group/node">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-primary font-bold tracking-tight">{node.id}</span>
                          <Badge variant="secondary" className="text-[10px] uppercase font-mono px-1.5 py-0 h-4">
                            {node.label || node.type}
                          </Badge>
                        </div>
                        {node.description && (
                          <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-2 mt-1 italic border-l-2 border-primary/20 pl-2 group-hover/node:border-primary/50 transition-colors">
                            "{node.description}"
                          </p>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Edges List */}
                  <div className="space-y-2">
                    <h3 className="text-xs text-secondary mb-2 font-bold uppercase tracking-wider">RELATIONSHIPS</h3>
                    {result.edges.map((edge, i) => (
                      <div key={i} className="flex flex-col p-3 border border-border rounded-lg bg-card/50 hover:bg-card transition-colors">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-muted-foreground text-sm">{edge.source}</span>
                          <span className="text-primary">→</span>
                          <span className="text-muted-foreground text-sm">{edge.target}</span>
                        </div>
                        <Badge variant="outline" className="text-xs self-start">
                          {edge.relationship || edge.type}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
};

export default InGestPlayground;
