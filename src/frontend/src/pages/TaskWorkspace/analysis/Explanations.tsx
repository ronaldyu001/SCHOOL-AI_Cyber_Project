/**
 * Attributions, rendered per task because each one explains something
 * different: standardized features for network, byte regions for malware, and
 * email tokens for phishing. Units are not comparable across tasks, so each
 * section states its own target.
 */
import type { Explainability, ExplanationSample } from '../../../api/types';
import { Bars, type BarItem } from './Charts';

const round = (value: number | undefined, digits = 4) =>
  value === undefined || !Number.isFinite(value) ? '—' : value.toFixed(digits);

/** Keeps a bar chart readable when the payload names far more than fits. */
const strongest = (items: BarItem[], limit: number) =>
  [...items].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, limit);

function SampleFacts({ facts }: { facts: [string, string][] }) {
  return (
    <dl className="facts">
      {facts.map(([label, value]) => (
        <div className="facts__row" key={label}>
          <dt>{label}</dt>
          <dd className="mono">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function NetworkSample({ sample, features }: { sample: ExplanationSample; features: string[] }) {
  const items = (sample.attributions ?? []).map((value, index) => ({
    label: features[index] ?? `feature[${index}]`,
    value,
  }));
  return (
    <>
      <SampleFacts
        facts={[
          ['Attack probability', round(sample.prediction_value)],
          ['Baseline probability', round(sample.baseline_value)],
          ['Convergence delta', round(sample.convergence_delta)],
        ]}
      />
      <Bars title="Signed attribution" items={strongest(items, 16)} note="toward attack when positive" />
    </>
  );
}

function MalwareSample({ sample }: { sample: ExplanationSample }) {
  const regions = (sample.regions ?? []).map((region) => ({ label: region.name, value: region.attribution }));
  const windows = (sample.windows ?? []).map((window) => ({
    label: `${window.start}–${window.end}`,
    value: window.attribution,
  }));
  return (
    <>
      <SampleFacts
        facts={[
          ['Malware probability', round(sample.malware_probability)],
          ['Logit', round(sample.logit)],
          ['Baseline logit', round(sample.baseline_logit)],
          ['Bytes kept', (sample.retained_byte_length ?? 0).toLocaleString()],
          ['Input length', (sample.input_length ?? 0).toLocaleString()],
          ['Convergence delta', round(sample.convergence_delta)],
        ]}
      />
      {regions.length === 0 ? null : (
        <Bars title="PE region totals" items={regions} note="toward malware when positive" />
      )}
      {windows.length === 0 ? null : (
        <Bars
          title="Strongest byte windows"
          items={strongest(windows, 12)}
          note={`${windows.length.toLocaleString()} windows in all, by byte offset`}
        />
      )}
      {sample.top_bytes === undefined || sample.top_bytes.length === 0 ? null : (
        <details className="analysis__raw">
          <summary>Top individual bytes</summary>
          <p className="analysis__note">
            {sample.top_bytes
              .slice(0, 24)
              .map((entry) => `${entry.offset}: ${entry.attribution.toFixed(4)}`)
              .join('  ·  ')}
          </p>
        </details>
      )}
    </>
  );
}

function PhishingSample({ sample }: { sample: ExplanationSample }) {
  const tokens = sample.tokens ?? [];
  const attributions = sample.attributions ?? [];
  const extent = Math.max(...attributions.map(Math.abs), Number.EPSILON);

  return (
    <>
      <SampleFacts
        facts={[
          ['Phishing probability', round(sample.phishing_probability)],
          ['Margin', round(sample.margin)],
          ['Baseline margin', round(sample.baseline_margin)],
          ['Premise tokens', (sample.retained_premise_tokens ?? tokens.length).toLocaleString()],
          ['Convergence delta', round(sample.convergence_delta)],
        ]}
      />
      <p className="analysis__note">
        Shaded toward phishing when positive and toward legitimate when negative; hover a token for
        its attribution.
      </p>
      <p className="tokens">
        {tokens.map((token, index) => {
          const value = attributions[index] ?? 0;
          const weight = Math.round((Math.abs(value) / extent) * 100);
          return (
            <span
              className="tokens__token"
              key={`${token}:${index}`}
              title={`${token}: ${value.toFixed(5)}`}
              style={{
                background: `color-mix(in srgb, var(${value >= 0 ? '--danger' : '--ok'}) ${weight * 0.45}%, transparent)`,
              }}
            >
              {token.replace(/^[Ġ▁]/, ' ').trim() === '' ? token : token.replace(/^[Ġ▁]/, '')}
            </span>
          );
        })}
      </p>
    </>
  );
}

export function Explanations({ task, explainability }: { task: string; explainability: Explainability }) {
  const features = explainability.feature_names ?? [];
  const permutation = explainability.feature_permutation;

  return (
    <section className="analysis__explanations">
      <h3 className="analysis__heading">Explanations</h3>
      <p className="analysis__note">
        {`${explainability.method.replace(/_/g, ' ')} on ${explainability.target.replace(/_/g, ' ')}. Baseline: ${explainability.baseline}.`}
      </p>

      {explainability.global_importance === undefined ? null : (
        <Bars
          title="Mean absolute attribution"
          items={explainability.global_importance.features.map((label, index) => ({
            label,
            value: explainability.global_importance?.mean_absolute_attribution[index] ?? 0,
          }))}
          note="across the explained rows"
        />
      )}

      {permutation == null || permutation.available !== true || permutation.features === undefined ? (
        permutation?.reason === undefined ? null : (
          <p className="analysis__note">Feature permutation unavailable: {permutation.reason}</p>
        )
      ) : (
        <Bars
          title="Feature permutation importance"
          items={permutation.features.map((label, index) => ({
            label: `${label}${permutation.feature_types?.[index] === 'categorical' ? ' (cat)' : ''}`,
            value: permutation.importance?.[index] ?? 0,
            error: permutation.std?.[index],
          }))}
          note={`drop in true-class probability over ${permutation.repeats ?? 0} repeats`}
        />
      )}

      {explainability.global_token_importance === undefined ? null : (
        <Bars
          title="Most influential tokens"
          items={explainability.global_token_importance.slice(0, 16).map((entry) => ({
            label: `${entry.token} ×${entry.count}`,
            value: entry.mean_attribution,
          }))}
          note="mean signed attribution, ordered by magnitude"
        />
      )}

      {explainability.samples.map((sample) => (
        <details className="analysis__sample" key={sample.row_id}>
          <summary>
            Row <span className="mono">{sample.row_id}</span>
          </summary>
          <div className="analysis__sample-body">
            {task === 'network_intrusion' ? (
              <NetworkSample sample={sample} features={features} />
            ) : task === 'malware_detection' ? (
              <MalwareSample sample={sample} />
            ) : (
              <PhishingSample sample={sample} />
            )}
          </div>
        </details>
      ))}
    </section>
  );
}
