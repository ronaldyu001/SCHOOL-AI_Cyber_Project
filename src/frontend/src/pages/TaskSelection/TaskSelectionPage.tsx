/** Landing page: pick the cybersecurity task to work on. */
import { Link } from 'react-router-dom';
import { TASKS } from '../../tasks/catalog';
import { Badge } from '../../components/ui';
import './TaskSelectionPage.css';

export function TaskSelectionPage() {
  return (
    <section>
      <header className="select__header">
        <h1>Select a task</h1>
        <p className="select__lede">
          Each task loads its bundled dataset through the backend dataset API, then walks the clean,
          split, prepare and preprocess steps.
        </p>
      </header>

      <ul className="select__list">
        {TASKS.map((task) => {
          const meta = (
            <div className="select__meta">
              <span className="select__labels">
                {task.labels[0]} vs {task.labels[1]}
              </span>
              <span className="select__file mono">{task.datasetFile}</span>
            </div>
          );

          if (!task.available) {
            return (
              <li className="select__item select__item--off" key={task.slug} aria-disabled="true">
                <div className="select__text">
                  <h2 className="select__name">
                    {task.name} <Badge tone="neutral">Planned</Badge>
                  </h2>
                  <p className="select__summary">{task.summary}</p>
                  <p className="select__note">{task.unavailableNote}</p>
                </div>
                {meta}
              </li>
            );
          }

          return (
            <li className="select__item" key={task.slug}>
              <Link className="select__link" to={`/tasks/${task.slug}`}>
                <div className="select__text">
                  <h2 className="select__name">
                    {task.name} <Badge tone="ok">Available</Badge>
                  </h2>
                  <p className="select__summary">{task.summary}</p>
                </div>
                {meta}
                <span className="select__arrow" aria-hidden="true">
                  →
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
