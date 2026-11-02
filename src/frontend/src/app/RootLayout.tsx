/** Root navigator: persistent header and the routed outlet. */
import { NavLink, Outlet } from 'react-router-dom';
import { ThemeToggle } from '../components/ThemeToggle';
import { TASKS } from '../tasks/catalog';
import { useTheme } from './use-theme';
import './RootLayout.css';

export function RootLayout() {
  const { theme, toggle } = useTheme();

  return (
    <div className="shell">
      <a className="shell__skip" href="#main">
        Skip to content
      </a>

      <header className="shell__header">
        <div className="shell__bar">
          <NavLink className="shell__brand" to="/">
            <span className="shell__brand-mark" aria-hidden="true" />
            AI Cyber Console
          </NavLink>

          <nav aria-label="Primary">
            <ul className="shell__nav">
              <li>
                <NavLink className="shell__link" to="/" end>
                  Tasks
                </NavLink>
              </li>
              {TASKS.filter((task) => task.available).map((task) => (
                <li key={task.slug}>
                  <NavLink className="shell__link" to={`/tasks/${task.slug}`}>
                    {task.name}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <ThemeToggle theme={theme} onToggle={toggle} />
        </div>
      </header>

      <main className="shell__main" id="main">
        <Outlet />
      </main>
    </div>
  );
}
