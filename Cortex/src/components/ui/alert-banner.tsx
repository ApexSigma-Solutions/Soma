import { useAlertStore, AlertSeverity } from '@/lib/store/useAlertStore';
import { X, AlertTriangle, AlertCircle, Info, Server } from 'lucide-react';
import { cn } from '@/lib/utils';

const severityStyles: Record<AlertSeverity, string> = {
  info: 'bg-blue-500/10 border-blue-500/50 text-blue-400',
  warning: 'bg-amber-500/10 border-amber-500/50 text-amber-400',
  critical: 'bg-red-500/10 border-red-500/50 text-red-400',
};

const severityIcons: Record<AlertSeverity, typeof AlertTriangle> = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertCircle,
};

export function AlertBanner() {
  const { alerts, dismissAlert } = useAlertStore();
  const visibleAlerts = alerts.filter((a) => !a.dismissed);

  if (visibleAlerts.length === 0) return null;

  return (
    <div className="space-y-2 mb-4">
      {visibleAlerts.map((alert) => {
        const Icon = severityIcons[alert.severity];
        return (
          <div
            key={alert.id}
            role="alert"
            className={cn(
              "flex items-start gap-3 p-3 rounded-lg border",
              severityStyles[alert.severity]
            )}
          >
            <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-sm">{alert.title}</h4>
                {alert.service && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-white/10 flex items-center gap-1">
                    <Server className="h-3 w-3" />
                    {alert.service}
                  </span>
                )}
              </div>
              <p className="text-xs opacity-80 mt-0.5">{alert.message}</p>
            </div>
            <button
              onClick={() => dismissAlert(alert.id)}
              className="p-1 rounded hover:bg-white/10 transition-colors"
              aria-label="Dismiss alert"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
