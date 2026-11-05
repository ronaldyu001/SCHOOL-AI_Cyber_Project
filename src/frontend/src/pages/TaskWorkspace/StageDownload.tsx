/**
 * Export control for one completed pipeline stage.
 *
 * Every stage serialises to a ZIP of `manifest.json` plus its own data, so the
 * only thing that varies between steps is what lands inside. `prepared` is the
 * one stage holding all three partitions at once, so it is the only one that
 * takes a `partition`; the rest reject it.
 */
import { useState } from 'react';
import {
  datasetDownloadUrl,
  type DownloadPartition,
  type DownloadStage,
  type TaskSlug,
} from '../../api/datasets';
import { PARTITIONS } from '../../api/types';
import { DownloadLink } from '../../components/ui';
import { useBusy } from './action-scope';

interface StageDownloadProps {
  slug: TaskSlug;
  datasetId: string;
  stage: DownloadStage;
  /** Required for every stage but `loaded` and `cleaned`, which reject it. */
  resultId?: string;
  label: string;
  /** What the archive carries beyond `manifest.json`. */
  contents: string;
  /** Offers a partition choice. Only `prepared` supports one. */
  byPartition?: boolean;
}

export function StageDownload({
  slug,
  datasetId,
  stage,
  resultId,
  label,
  contents,
  byPartition = false,
}: StageDownloadProps) {
  const busy = useBusy();
  const [partition, setPartition] = useState<DownloadPartition>('all');
  const href = datasetDownloadUrl(
    slug,
    datasetId,
    stage,
    resultId,
    byPartition ? partition : undefined,
  );

  return (
    <div className="work__export">
      <div className="work__export-row">
        {byPartition ? (
          <label className="field work__export-field">
            <span className="field__label">Partition</span>
            <select
              className="field__input"
              value={partition}
              onChange={(event) => setPartition(event.target.value as DownloadPartition)}
            >
              <option value="all">All three</option>
              {PARTITIONS.map((item) => (
                <option key={item} value={item}>
                  {item.charAt(0).toUpperCase() + item.slice(1)}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <DownloadLink disabled={busy} href={href}>
          {label}
        </DownloadLink>
      </div>
      <p className="work__hint">{contents}</p>
    </div>
  );
}
