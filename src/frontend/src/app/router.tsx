import { createBrowserRouter } from 'react-router-dom';
import { RootLayout } from './RootLayout';
import { NotFoundPage } from '../pages/NotFoundPage';
import { TaskSelectionPage } from '../pages/TaskSelection/TaskSelectionPage';
import { TaskWorkspaceRoute } from '../pages/TaskWorkspace/TaskWorkspacePage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <TaskSelectionPage /> },
      { path: 'tasks/:slug', element: <TaskWorkspaceRoute /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
