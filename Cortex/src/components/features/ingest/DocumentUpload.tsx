import React, { useState, useRef } from 'react';
import { Upload, File, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ingestApi } from '@/lib/api/client';
import { toast } from '@/lib/store/useToastStore';

interface DocumentUploadProps {
  onSuccess?: (id: string) => void;
}

export function DocumentUpload({ onSuccess }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);
    setStatus('idle');
    setMessage(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setStatus('idle');
    setMessage(null);

    try {
      const res = await ingestApi.ingestFile(file);
      setStatus('success');
      setMessage(`Successfully ingested ${file.name}`);
      toast.success('Document processed successfully');
      setFile(null);
      const ref = res.ref ?? res.id;
      if (onSuccess && ref) onSuccess(ref);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.message || 'Failed to upload document');
      toast.error('Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-6 min-h-[400px] flex flex-col">
      <div 
        className={`relative group border-2 border-dashed rounded-xl p-12 transition-all duration-300 flex-1 flex flex-col items-center justify-center text-center
          ${file 
            ? 'border-teal-500/40 bg-teal-500/5' 
            : 'border-white/10 hover:border-teal-500/30 hover:bg-white/[0.02]'
          }
        `}
      >
        {/* Fix for bottom border overlapping - ensure padding and box-sizing are correct */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
          title=""
        />

        <div className={`p-5 rounded-2xl mb-4 transition-all duration-500 ${file ? 'bg-teal-500/20 text-teal-400 scale-110' : 'bg-white/5 text-white/40 group-hover:text-teal-400 group-hover:bg-teal-500/10'}`}>
          {file ? <File className="h-10 w-10" /> : <Upload className="h-10 w-10" />}
        </div>

        {file ? (
          <div className="z-20 relative">
            <h3 className="text-lg font-bold text-foreground mb-1">{file.name}</h3>
            <p className="text-xs text-muted-foreground uppercase tracking-widest font-mono">
              {(file.size / 1024 / 1024).toFixed(2)} MB • READY FOR RAID
            </p>
            <button 
              onClick={(e) => { e.stopPropagation(); clearFile(); }}
              className="mt-4 p-2 rounded-full bg-white/5 hover:bg-red-500/20 text-white/40 hover:text-red-400 transition-all"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            <h3 className="text-lg font-bold text-foreground mb-1">Upload Documents</h3>
            <p className="text-sm text-muted-foreground max-w-[240px]">
              Deploy PDF, Markdown, or raw code files into the Knowledge Graph
            </p>
            <div className="mt-6 px-4 py-2 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 text-[10px] font-mono uppercase tracking-[0.2em]">
              Select File to Begin
            </div>
          </>
        )}
      </div>

      <Button
        onClick={handleUpload}
        disabled={loading || !file}
        className="w-full h-12 text-sm font-black uppercase tracking-[0.2em] italic border-t border-white/10"
      >
        {loading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          'Initiate Ingestion'
        )}
      </Button>

      {status !== 'idle' && (
        <div className={`p-4 rounded-xl border animate-in fade-in slide-in-from-top-2 duration-300 flex items-center gap-3 text-sm font-mono
          ${status === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
            : 'bg-red-500/10 border-red-500/30 text-red-400'
          }
        `}>
          {status === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          <span className="truncate">{message}</span>
        </div>
      )}
    </div>
  );
}
