import { ManualIngestForm } from '@/components/ingress/ManualIngestForm';
import { SystemVitalsWidget } from '@/components/ingress/SystemVitalsWidget';
import { TelemetryStreamViewer } from '@/components/ingress/TelemetryStreamViewer';
import { RawLakeStatusWidget } from '@/components/ingress/RawLakeStatusWidget';
import { WebhookActivityLog } from '@/components/ingress/WebhookActivityLog';

export function InGressPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">InGress - Senses</h1>
        <p className="text-muted-foreground">
          System monitoring, manual ingestion, and webhook activity
        </p>
      </div>

      {/* Top Row - System Vitals and Raw Lake */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SystemVitalsWidget />
        <RawLakeStatusWidget />
      </div>

      {/* Manual Ingest Form */}
      <ManualIngestForm />

      {/* Bottom Row - Telemetry and Webhooks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TelemetryStreamViewer />
        <WebhookActivityLog />
      </div>
    </div>
  );
}
