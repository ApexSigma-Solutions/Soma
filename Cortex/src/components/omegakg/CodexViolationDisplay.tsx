import { useEffect, useState } from 'react';
import { omegaKgApi } from '@/lib/api/client';
import type { CodexViolation } from '@/lib/api/types/omegakg';
import { AlertTriangle, AlertCircle, Info, XCircle, CheckCircle } from 'lucide-react';

export function CodexViolationDisplay() {
  const [violations, setViolations] = useState<CodexViolation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchViolations = async () => {
      try {
        const data = await omegaKgApi.getCodexViolations();
        setViolations(data);
      } catch (error) {
        console.error('Failed to fetch violations:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchViolations();
    const interval = setInterval(fetchViolations, 60000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-400" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-500" />;
      default:
        return <Info className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return 'border-red-500 bg-red-500/10';
      case 'error':
        return 'border-red-400 bg-red-400/10';
      case 'warning':
        return 'border-yellow-500 bg-yellow-500/10';
      case 'info':
        return 'border-blue-500 bg-blue-500/10';
      default:
        return 'border-border bg-background';
    }
  };

  if (loading) {
    return <div className="animate-pulse bg-card border border-border rounded-lg p-6 h-48" />;
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-primary" />
        Codex Violations
      </h3>

      {violations.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
          <p>No violations detected</p>
        </div>
      ) : (
        <div className="space-y-3">
          {violations.map((violation) => (
            <div
              key={violation.id}
              className={`p-4 rounded-md border ${getSeverityColor(violation.severity)}`}
            >
              <div className="flex items-start gap-3">
                {getSeverityIcon(violation.severity)}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold capitalize">{violation.severity}</span>
                    <code className="text-xs bg-muted px-2 py-0.5 rounded">{violation.rule}</code>
                  </div>
                  <p className="text-sm text-foreground">{violation.message}</p>
                  {violation.context && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Context: {violation.context}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground mt-2">
                    Detected: {new Date(violation.detected_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
