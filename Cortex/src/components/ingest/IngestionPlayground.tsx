import { useState } from 'react';
import { ingestApi } from '@/lib/api/client';
import { useToastStore } from '@/lib/store/useToastStore';
import { FileText, Upload, Loader2 } from 'lucide-react';

type TabType = 'text' | 'file';

export function IngestionPlayground() {
  const [activeTab, setActiveTab] = useState<TabType>('text');
  const [textInput, setTextInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{ref: string; status: string} | null>(null);
  const { addToast } = useToastStore();

  const handleTextSubmit = async () => {
    if (!textInput.trim()) {
      addToast('Please enter some text', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await ingestApi.processText(textInput);
      setResult(response);
      addToast(`Text processed successfully! Ref: ${response.ref}`, 'success');
      setTextInput('');
    } catch (error) {
      addToast(`Failed to process text: ${error}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileSubmit = async () => {
    if (!selectedFile) {
      addToast('Please select a file', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await ingestApi.processFile(selectedFile);
      setResult(response);
      addToast(`File processed successfully! Ref: ${response.ref}`, 'success');
      setSelectedFile(null);
    } catch (error) {
      addToast(`Failed to process file: ${error}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Upload className="h-5 w-5 text-primary" />
        Ingestion Playground
      </h3>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-border">
        <button
          onClick={() => setActiveTab('text')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'text'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileText className="inline h-4 w-4 mr-2" />
          Text Input
        </button>
        <button
          onClick={() => setActiveTab('file')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'file'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Upload className="inline h-4 w-4 mr-2" />
          File Upload
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-4">
        {activeTab === 'text' && (
          <div>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Enter text to process..."
              className="w-full h-40 px-3 py-2 bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-mono text-sm"
            />
            <button
              onClick={handleTextSubmit}
              disabled={isSubmitting || !textInput.trim()}
              className="mt-2 w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Process Text
                </>
              )}
            </button>
          </div>
        )}

        {activeTab === 'file' && (
          <div>
            <input
              type="file"
              accept=".txt,.md,.json"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
            />
            {selectedFile && (
              <p className="mt-2 text-sm text-muted-foreground">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
              </p>
            )}
            <button
              onClick={handleFileSubmit}
              disabled={isSubmitting || !selectedFile}
              className="mt-2 w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Process File
                </>
              )}
            </button>
          </div>
        )}

        {/* Result Display */}
        {result && (
          <div className="mt-4 p-4 bg-green-500/10 border border-green-500/30 rounded-md">
            <p className="text-sm font-semibold text-green-500 mb-1">✓ Ingestion Complete</p>
            <p className="text-sm text-foreground">
              Reference ID: <code className="font-mono text-xs bg-muted px-2 py-1 rounded">{result.ref}</code>
            </p>
            <p className="text-sm text-foreground mt-1">
              Status: <span className="font-medium">{result.status}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
