import { ScratchpadInterface } from '@/components/memos/ScratchpadInterface';
import { WorkingMemoryViewer } from '@/components/memos/WorkingMemoryViewer';
import { MemoryPromotionInterface } from '@/components/memos/MemoryPromotionInterface';
import { MirmirConsultationUI } from '@/components/memos/MirmirConsultationUI';
import { ContextRetrievalSearch } from '@/components/memos/ContextRetrievalSearch';

export function MemosPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">memOS - Hands</h1>
        <p className="text-muted-foreground">
          Working memory, scratchpad, and context retrieval
        </p>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ScratchpadInterface />
        <WorkingMemoryViewer />
      </div>

      {/* Memory Promotion */}
      <MemoryPromotionInterface />

      {/* Mirmir Consultation */}
      <MirmirConsultationUI />

      {/* Context Retrieval */}
      <ContextRetrievalSearch />
    </div>
  );
}
