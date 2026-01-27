import { CaptureStatus } from './CaptureStatus';
import { MimirQueryPanel } from '../memos/MimirQueryPanel';
import { RecentCaptures } from './RecentCaptures';

export function CaptureControl() {
  return (
    <div className="space-y-6">
      {/* Top Section: Health Metrics */}
      <section>
        <CaptureStatus />
      </section>

      {/* Main Content Grid */}
      <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 h-[500px]">
        {/* Left Column: List (2/3 width on large screens) */}
        <div className="lg:col-span-2 h-full">
            <RecentCaptures />
        </div>
        
        {/* Right Column: Manual Entry (1/3 width) */}
        <div className="h-full">
            <MimirQueryPanel />
        </div>
      </section>
    </div>
  );
}
