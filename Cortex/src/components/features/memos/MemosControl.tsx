import { MemosStatus } from './MemosStatus';
import { MemosSearch } from './MemosSearch';
import { MemosScratchpad } from './MemosScratchpad';
import { PulseStreamViewer } from './PulseStreamViewer';

export function MemosControl() {
  return (
    <div className="space-y-6 h-[calc(100vh-100px)] flex flex-col">
      {/* Top Section: Metrics */}
      <section className="flex-none">
        <MemosStatus />
      </section>

      {/* Main Content Grid */}
      <section className="grid gap-6 md:grid-cols-3 flex-1 min-h-0">
        {/* Left: Search Interface (2/3) */}
        <div className="md:col-span-2 h-full min-h-[400px] flex flex-col gap-6">
            <div className="flex-1 min-h-0">
                <MemosSearch />
            </div>
             <div className="h-[250px] flex-none">
                <MemosScratchpad />
            </div>
        </div>
        
        {/* Right: Live Pulse Stream (1/3) */}
        <div className="h-full">
            <PulseStreamViewer />
        </div>
      </section>
    </div>
  );
}
