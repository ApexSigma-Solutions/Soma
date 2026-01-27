import { useToastStore } from '@/lib/store/useToastStore';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

const iconMap = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const styleMap = {
  success: 'bg-green-500/90 border-green-400',
  error: 'bg-red-500/90 border-red-400',
  warning: 'bg-amber-500/90 border-amber-400',
  info: 'bg-blue-500/90 border-blue-400',
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div 
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm" 
      role="region" 
      aria-label="Notifications"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        const Icon = iconMap[toast.type];
        return (
          <div
            key={toast.id}
            role="alert"
            className={cn(
              "flex items-center gap-3 p-4 rounded-lg shadow-lg border text-white animate-in slide-in-from-right-5 fade-in duration-300",
              styleMap[toast.type]
            )}
          >
            <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
            <p className="text-sm font-medium flex-1">{toast.message}</p>
            <button
              onClick={() => removeToast(toast.id)}
              className="p-1 rounded-full hover:bg-white/20 transition-colors"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
