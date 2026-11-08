/**
 * The two chart shapes the analysis payload needs, drawn as inline SVG.
 *
 * Both axes of a ROC or PR curve are rates, so the domain is fixed to 0–1 and
 * nothing has to be scaled. Colours come from the theme tokens, so the charts
 * follow light and dark like the rest of the console.
 */

const WIDTH = 320;
const HEIGHT = 220;
const MARGIN = { top: 10, right: 12, bottom: 30, left: 38 };
const PLOT_WIDTH = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_HEIGHT = HEIGHT - MARGIN.top - MARGIN.bottom;

const atX = (value: number) => MARGIN.left + value * PLOT_WIDTH;
const atY = (value: number) => MARGIN.top + (1 - value) * PLOT_HEIGHT;

/**
 * A curve over a large partition carries a point per distinct threshold, far
 * more than the plot can show. Striding keeps the shape and both endpoints.
 */
function thin(xs: number[], ys: number[], limit = 400) {
  if (xs.length <= limit) return xs.map((x, index) => [x, ys[index]] as const);
  const step = Math.ceil(xs.length / limit);
  const points = xs.filter((_, index) => index % step === 0).map((x, index) => [x, ys[index * step]] as const);
  const last = xs.length - 1;
  if (points[points.length - 1][0] !== xs[last]) points.push([xs[last], ys[last]]);
  return points;
}

interface CurveProps {
  title: string;
  x: number[];
  y: number[];
  xLabel: string;
  yLabel: string;
  /** The no-skill reference: a diagonal for ROC, a horizontal rate for PR. */
  reference?: 'diagonal' | number;
  summary?: string;
}

export function Curve({ title, x, y, xLabel, yLabel, reference, summary }: CurveProps) {
  const points = thin(x, y)
    .map(([px, py]) => `${atX(px).toFixed(1)},${atY(py).toFixed(1)}`)
    .join(' ');

  return (
    <figure className="chart">
      <figcaption className="chart__title">
        {title}
        {summary === undefined ? null : <span className="chart__summary">{summary}</span>}
      </figcaption>
      <svg className="chart__svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img"
        aria-label={`${title}: ${yLabel} against ${xLabel}`}>
        {[0, 0.5, 1].map((tick) => (
          <g key={tick}>
            <line className="chart__grid" x1={atX(0)} x2={atX(1)} y1={atY(tick)} y2={atY(tick)} />
            <text className="chart__tick" x={MARGIN.left - 6} y={atY(tick) + 3} textAnchor="end">
              {tick}
            </text>
            <text className="chart__tick" x={atX(tick)} y={HEIGHT - 12} textAnchor="middle">
              {tick}
            </text>
          </g>
        ))}
        {reference === undefined ? null : reference === 'diagonal' ? (
          <line className="chart__reference" x1={atX(0)} y1={atY(0)} x2={atX(1)} y2={atY(1)} />
        ) : (
          <line className="chart__reference" x1={atX(0)} y1={atY(reference)} x2={atX(1)} y2={atY(reference)} />
        )}
        <polyline className="chart__line" points={points} />
        <text className="chart__axis" x={atX(0.5)} y={HEIGHT - 1} textAnchor="middle">{xLabel}</text>
        <text className="chart__axis" transform={`rotate(-90 10 ${atY(0.5)})`} x={10} y={atY(0.5)} textAnchor="middle">
          {yLabel}
        </text>
      </svg>
    </figure>
  );
}

export interface BarItem {
  label: string;
  value: number;
  /** Drawn as a whisker, for a permutation importance's spread. */
  error?: number;
}

/**
 * Horizontal bars that keep their sign: an attribution pushing toward the
 * negative class is as meaningful as one pushing toward the positive class, so
 * the axis sits in the middle whenever any value is negative.
 */
export function Bars({ title, items, note }: { title: string; items: BarItem[]; note?: string }) {
  const extent = Math.max(...items.map((item) => Math.abs(item.value) + (item.error ?? 0)), Number.EPSILON);
  const signed = items.some((item) => item.value < 0);

  return (
    <figure className="chart chart--bars">
      <figcaption className="chart__title">
        {title}
        {note === undefined ? null : <span className="chart__summary">{note}</span>}
      </figcaption>
      <ul className="bars">
        {items.map((item) => {
          const share = (Math.abs(item.value) / extent) * (signed ? 50 : 100);
          const whisker = item.error === undefined ? 0 : (item.error / extent) * (signed ? 50 : 100);
          return (
            <li className="bars__row" key={item.label}>
              <span className="bars__label" title={item.label}>{item.label}</span>
              <span className={`bars__track${signed ? ' bars__track--signed' : ''}`}>
                <span
                  className={`bars__fill${item.value < 0 ? ' bars__fill--negative' : ''}`}
                  style={{
                    width: `${share}%`,
                    left: signed ? (item.value < 0 ? `${50 - share}%` : '50%') : '0',
                  }}
                />
                {whisker === 0 ? null : (
                  <span
                    className="bars__error"
                    style={{
                      width: `${whisker}%`,
                      left: signed
                        ? `${50 + (item.value >= 0 ? share : -share)}%`
                        : `${share}%`,
                    }}
                  />
                )}
              </span>
              <span className="bars__value mono">{Number(item.value.toPrecision(3))}</span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}
