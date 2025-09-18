import ToolGroupCard from './ToolGroupCard';

import type { ToolGroup, ToolName } from '../../pages/tools/types';

export type ToolGridProps = {
  groups: ToolGroup[];
  wiredReadOnlyTools: Set<ToolName>;
  loadingTool: ToolName | null;
  onInvoke: (groupTitle: string, tool: ToolName) => void;
};

export default function ToolGrid({
  groups,
  wiredReadOnlyTools,
  loadingTool,
  onInvoke,
}: ToolGridProps) {
  return (
    <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      {groups.map(group => (
        <ToolGroupCard
          key={group.title}
          group={group}
          wiredReadOnlyTools={wiredReadOnlyTools}
          loadingTool={loadingTool}
          onInvoke={onInvoke}
        />
      ))}
    </section>
  );
}
