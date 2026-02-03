import { useEffect, useState } from 'react';
import { useAlertStore, type SystemAlert } from '@/lib/store/useAlertStore';
import { Bell, X, AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';

export function AlertNotificationSystem() {
  const { alerts, dismissAlert, clearAllAlerts } = useAlertStore();
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const unread = alerts.filter((a) => !a.dismissed).length;
    setUnreadCount(unread);
  }, [alerts]);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-500" />;
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      default:
        return <Info className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/30';
      case 'warning':
        return 'bg-yellow-500/10 border-yellow-500/30';
      case 'info':
        return 'bg-blue-500/10 border-blue-500/30';
      case 'success':
        return 'bg-green-500/10 border-green-500/30';
      default:
        return 'bg-muted border-border';
    }
  };

  const activeAlerts = alerts.filter((a) => !a.dismissed);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 hover:bg-muted rounded-md transition-colors"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full mt-2 w-96 bg-card border border-border rounded-lg shadow-lg z-50 max-h-96 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="font-semibold flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Notifications
              </h3>
              <div className="flex items-center gap-2">
                {activeAlerts.length > 0 && (
                  <button
                    onClick={clearAllAlerts}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    Clear all
                  </button>
                )}
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 hover:bg-muted rounded"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="overflow-y-auto max-h-80">
              {activeAlerts.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
                  <p>No active alerts</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {activeAlerts.map((alert) => (
                    <AlertItem
                      key={alert.id}
                      alert={alert}
                      onDismiss={dismissAlert}
                      getSeverityIcon={getSeverityIcon}
                      getSeverityColor={getSeverityColor}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface AlertItemProps {
  alert: SystemAlert;
  onDismiss: (id: string) => void;
  getSeverityIcon: (severity: string) => React.ReactNode;
  getSeverityColor: (severity: string) => string;
}

function AlertItem({ alert, onDismiss, getSeverityIcon, getSeverityColor }: AlertItemProps) {
  return (
    <div className={`p-4 ${getSeverityColor(alert.severity)}`}>
      <div className="flex items-start gap-3">
        {getSeverityIcon(alert.severity)}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4 className="font-semibold text-sm truncate">{alert.title}</h4>
            <button
              onClick={() => onDismiss(alert.id)}
              className="p-1 hover:bg-muted rounded flex-shrink-0"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          <p className="text-sm text-foreground/80 mb-1">{alert.message}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {alert.service && (
              <span className="px-2 py-0.5 bg-muted rounded capitalize">
                {alert.service}
              </span>
            )}
            <span>{new Date(alert.createdAt).toLocaleTimeString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
