import { memo } from 'react';

import Banner from '../common/Banner';
import Button from '../common/Button';

import type { ToolName } from '../../pages/tools/types';

export type RagRemediationBannerProps = {
  onInvoke: (groupTitle: string, tool: ToolName) => void;
};

export default memo(function RagRemediationBanner({ onInvoke }: RagRemediationBannerProps) {
  return (
    <Banner type='warning'>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <div>
          Vector/Hybrid search unavailable. Ingest files and generate missing embeddings to enable
          RAG features.
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            variant='secondary'
            onClick={() => onInvoke('RAG operations', 'rag_ingest_files')}
          >
            Ingest files…
          </Button>
          <Button
            variant='secondary'
            onClick={() => onInvoke('RAG operations', 'rag_generate_missing_embeddings')}
          >
            Generate embeddings
          </Button>
        </div>
      </div>
    </Banner>
  );
});
