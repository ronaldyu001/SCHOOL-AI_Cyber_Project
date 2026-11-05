/**
 * Renders one preprocessing artifact's manifest.
 *
 * The split follows how an artifact is actually used. Scalar settings are
 * values you retype in your own training code, so they are shown plainly.
 * Fitted series and maps are data you consume rather than read — they are
 * summarised here and travel in the downloadable bundle, along with any
 * separate member files the task needs.
 *
 * Nothing is keyed off the task: the manifest is grouped by the shape of its
 * values, so a task that adds a setting shows it without changing this file.
 */
import { useState } from 'react';
import type { PreprocessingArtifact } from '../../api/types';
import { Badge, DownloadLink, Summary, type SummaryItem } from '../../components/ui';
import { formatCell } from '../../tasks/records';
import { useBusy } from './action-scope';
import './ArtifactPanel.css';

type Primitive = string | number | boolean | null;

const isPrimitive = (value: unknown): value is Primitive =>
  value === null || ['string', 'number', 'boolean'].includes(typeof value);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

/** `max_length` reads as "Max length"; good enough for every key so far. */
const humanise = (key: string) => {
  const spaced = key.replace(/_/g, ' ');
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
};

interface Grouped {
  /** Primitives, plus short string lists: the values you apply by hand. */
  scalars: [string, Primitive[] | Primitive][];
  /** Numeric series, usually one entry per feature. */
  series: [string, Primitive[]][];
  /** Objects, such as per-column category mappings. */
  maps: [string, Record<string, unknown>][];
  /** Anything of a shape the three buckets above do not cover. Nothing in the
   *  current tasks lands here, but a setting must never become invisible just
   *  because this file did not anticipate it. */
  other: [string, unknown][];
}

function group(settings: Record<string, unknown>): Grouped {
  const scalars: Grouped['scalars'] = [];
  const series: Grouped['series'] = [];
  const maps: Grouped['maps'] = [];
  const other: Grouped['other'] = [];

  for (const [key, value] of Object.entries(settings)) {
    if (isPrimitive(value)) {
      scalars.push([key, value]);
    } else if (Array.isArray(value) && value.every(isPrimitive)) {
      series.push([key, value]);
    } else if (isRecord(value)) {
      maps.push([key, value]);
    } else {
      other.push([key, value]);
    }
  }
  return { scalars, series, maps, other };
}

/**
 * What each bundled file is for, keyed by basename. The folder already names
 * the consumer, so this only has to explain the individual members.
 */
const FILE_PURPOSE: Record<string, string> = {
  'tokenizer.json': 'Vocabulary, merge rules and normalisation in one fast-tokenizer file.',
  'vocab.json': 'Token string to token ID lookup.',
  'merges.txt': 'Byte-pair merge rules, applied before the vocabulary lookup.',
  'tokenizer_config.json': 'Tokenizer class and the defaults it was saved with.',
  'special_tokens_map.json': 'Which tokens act as pad, bos, eos and unk.',
  'config.json': 'Model configuration saved alongside the tokenizer.',
};

/** How a folder of members is meant to be loaded once the ZIP is unpacked. */
const FOLDER_USAGE: Record<string, string> = {
  tokenizer: 'Unzip, then point transformers.AutoTokenizer.from_pretrained() at this folder.',
};

const basename = (path: string) => path.slice(path.lastIndexOf('/') + 1);
const folderOf = (path: string) => (path.includes('/') ? path.slice(0, path.indexOf('/')) : '');

/**
 * Pairs each numeric series with a string series of the same length, so the
 * per-feature statistics line up with the feature they were fitted for rather
 * than appearing as four unlabelled rows of sixteen numbers.
 */
function alignSeries(series: Grouped['series']) {
  const labels = series.filter(([, values]) => values.every((v) => typeof v === 'string'));
  const values = series.filter(([, items]) => items.some((v) => typeof v === 'number'));
  const used = new Set<string>();

  const tables = labels
    .map(([labelKey, names]) => {
      const columns = values.filter(([, items]) => items.length === names.length);
      columns.forEach(([key]) => used.add(key));
      if (columns.length > 0) used.add(labelKey);
      return { labelKey, names: names as string[], columns };
    })
    .filter((table) => table.columns.length > 0);

  // Whatever found no partner: short string lists read well inline, the rest
  // keep their own index-labelled table.
  const loose = series.filter(([key]) => !used.has(key));
  const inline = loose.filter(([, items]) => items.every((v) => typeof v === 'string') && items.length <= 8);
  const orphans = loose.filter(([key]) => !inline.some(([other]) => other === key));

  return { tables, inline, orphans };
}

function SeriesTable({ caption, names, columns }: {
  caption: string;
  names: string[];
  columns: [string, Primitive[]][];
}) {
  return (
    <div className="artifact__table-wrap">
      <table className="artifact__table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col">{caption}</th>
            {columns.map(([key]) => (
              <th scope="col" key={key} className="artifact__numeric">
                {humanise(key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {names.map((name, index) => (
            <tr key={name}>
              <th scope="row" className="mono">{name}</th>
              {columns.map(([key, items]) => (
                <td key={key} className="artifact__numeric mono">{formatCell(items[index])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Category maps run to thousands of entries, so only a sample is rendered. */
const SAMPLE_SIZE = 12;

function MapEntry({ name, value }: { name: string; value: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(value);
  const nested = entries.length > 0 && entries.every(([, item]) => isRecord(item));

  if (nested) {
    return (
      <div className="artifact__map">
        <h5 className="artifact__map-title">{humanise(name)}</h5>
        <table className="artifact__table">
          <thead>
            <tr>
              <th scope="col">Column</th>
              <th scope="col" className="artifact__numeric">Distinct values</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([column, item]) => (
              <tr key={column}>
                <th scope="row" className="mono">{column}</th>
                <td className="artifact__numeric mono">
                  {Object.keys(item as Record<string, unknown>).length.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" className="artifact__toggle" onClick={() => setOpen(!open)}>
          {open ? 'Hide sample mappings' : 'Show sample mappings'}
        </button>
        {!open ? null : (
          <dl className="artifact__sample">
            {entries.map(([column, item]) => {
              const pairs = Object.entries(item as Record<string, unknown>);
              return (
                <div className="artifact__sample-row" key={column}>
                  <dt className="mono">{column}</dt>
                  <dd className="mono">
                    {pairs.length === 0
                      ? '—'
                      : pairs
                          .slice(0, SAMPLE_SIZE)
                          .map(([k, v]) => `${k} → ${formatCell(v)}`)
                          .join(', ')}
                    {pairs.length > SAMPLE_SIZE
                      ? ` … ${(pairs.length - SAMPLE_SIZE).toLocaleString()} more`
                      : ''}
                  </dd>
                </div>
              );
            })}
          </dl>
        )}
      </div>
    );
  }

  return (
    <div className="artifact__map">
      <h5 className="artifact__map-title">{humanise(name)}</h5>
      <Summary
        items={entries.map(([key, item]) => ({
          label: humanise(key),
          value: formatCell(item),
          mono: true,
        }))}
      />
    </div>
  );
}

interface ArtifactPanelProps {
  artifact: PreprocessingArtifact;
  /** Href for the bundle ZIP, which always carries manifest.json. */
  downloadUrl: string;
}

export function ArtifactPanel({ artifact, downloadUrl }: ArtifactPanelProps) {
  const busy = useBusy();
  const { manifest } = artifact;
  const { scalars, series, maps, other } = group(manifest.settings);
  const { tables, inline, orphans } = alignSeries(series);
  const files = Object.entries(manifest.files);
  const folders = [...new Set(files.map(([path]) => folderOf(path)))].filter(
    (folder) => FOLDER_USAGE[folder] !== undefined,
  );

  const applied: SummaryItem[] = [
    ...scalars.map(([key, value]) => ({
      label: humanise(key),
      value: formatCell(value),
      mono: true,
    })),
    ...inline.map(([key, items]) => ({
      label: humanise(key),
      value: (items as string[]).join(', '),
      mono: true,
    })),
  ];

  return (
    <section className="artifact">
      <header className="artifact__head">
        <div className="artifact__identity">
          <span className="artifact__label">Artifact</span>
          <code className="artifact__id" title={artifact.artifact_id}>
            {artifact.artifact_id.slice(0, 24)}…
          </code>
        </div>
        <DownloadLink variant="primary" disabled={busy} href={downloadUrl}>
          Download bundle (.zip)
        </DownloadLink>
      </header>

      <p className="artifact__lede">
        {files.length === 0 ? (
          <>
            The bundle is just <code>manifest.json</code>, holding every value below. Nothing
            here has to be copied by hand — read it from the file instead.
          </>
        ) : (
          <>
            The bundle holds <code>manifest.json</code> plus {files.length} file
            {files.length === 1 ? '' : 's'}. The values below are yours to read or retype; the
            files are what your preprocessing code actually opens.
          </>
        )}
      </p>

      <h4 className="artifact__heading">Provenance</h4>
      <Summary
        items={[
          { label: 'Task', value: manifest.task, mono: true },
          { label: 'Schema version', value: manifest.schema_version },
          {
            label: 'Training samples',
            value: manifest.provenance.training_sample_count.toLocaleString(),
          },
          { label: 'Dataset version', value: manifest.provenance.dataset_version, mono: true },
          {
            label: 'Training fingerprint',
            value: `${manifest.provenance.training_fingerprint.slice(0, 16)}…`,
            mono: true,
          },
        ]}
      />

      {applied.length === 0 ? null : (
        <>
          <h4 className="artifact__heading">Settings to apply in training</h4>
          <p className="artifact__note">
            Informational — nothing to download. Retype these in your own pipeline; they are
            not fitted.
          </p>
          <Summary items={applied} />
        </>
      )}

      {tables.length === 0 && orphans.length === 0 && maps.length === 0 ? null : (
        <>
          <h4 className="artifact__heading">Fitted values</h4>
          <p className="artifact__note">
            Informational, and summarised here because they are long. They were fitted on the
            training partition and ship inside <code>manifest.json</code>, so read them from
            the bundle rather than copying them by hand.
          </p>
          {tables.map((table) => (
            <SeriesTable
              key={table.labelKey}
              caption={humanise(table.labelKey)}
              names={table.names}
              columns={table.columns}
            />
          ))}
          {orphans.map(([key, items]) => (
            <SeriesTable
              key={key}
              caption={humanise(key)}
              names={items.map((_, index) => String(index))}
              columns={[[key, items]]}
            />
          ))}
          {maps.map(([key, value]) => (
            <MapEntry key={key} name={key} value={value} />
          ))}
        </>
      )}

      <h4 className="artifact__heading">Files your preprocessing loads</h4>
      {files.length === 0 ? (
        <p className="artifact__note">
          None — this task fits nothing to a file, so <code>manifest.json</code> is the whole
          bundle and the values above are all you need.
        </p>
      ) : (
        <>
          <p className="artifact__note">
            These are the downloadable part. Take the bundle, unpack it, and load them from
            your training code.
          </p>
          {folders.map((folder) => (
            <p className="artifact__usage" key={folder}>
              <code>{folder}/</code> — {FOLDER_USAGE[folder]}
            </p>
          ))}
          <div className="artifact__table-wrap">
            <table className="artifact__table">
              <caption className="sr-only">Files inside the artifact bundle</caption>
              <thead>
                <tr>
                  <th scope="col">Path</th>
                  <th scope="col">What it is for</th>
                  <th scope="col">SHA-256</th>
                </tr>
              </thead>
              <tbody>
                {files.map(([path, digest]) => (
                  <tr key={path}>
                    <th scope="row" className="mono">{path}</th>
                    <td className="artifact__purpose">
                      {FILE_PURPOSE[basename(path)] ?? 'Loaded as part of this bundle.'}
                    </td>
                    <td className="mono artifact__digest" title={digest}>
                      {digest.slice(0, 16)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {other.length === 0 ? null : (
        <>
          <h4 className="artifact__heading">Other settings</h4>
          <p className="artifact__note">
            Informational. Shown as stored, because their shape has no table form here.
          </p>
          <pre className="artifact__other">{JSON.stringify(Object.fromEntries(other), null, 2)}</pre>
        </>
      )}

      <details className="artifact__raw">
        <summary>Raw manifest</summary>
        <pre>{JSON.stringify(manifest, null, 2)}</pre>
      </details>
    </section>
  );
}

/** Lets callers show the badge without re-deriving the count. */
export function ArtifactFileBadge({ artifact }: { artifact: PreprocessingArtifact }) {
  const count = Object.keys(artifact.manifest.files).length;
  return (
    <Badge tone={count === 0 ? 'neutral' : 'accent'}>
      {count === 0 ? 'manifest only' : `${count} file${count === 1 ? '' : 's'}`}
    </Badge>
  );
}
