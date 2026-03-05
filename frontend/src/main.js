import { Router } from './router.js';
import { api } from './api.js';

// Page Views
import Dashboard from './pages/dashboard.js';
import Generate from './pages/generate.js';
import Progress from './pages/progress.js';
import Preview from './pages/preview.js';
import Settings from './pages/settings.js';

// Define routes
const routes = [
  { path: '/', view: Dashboard },
  { path: '/generate', view: Generate },
  { path: '/progress', view: Progress },
  { path: '/preview', view: Preview },
  { path: '/settings', view: Settings }
];

// Start App
document.addEventListener('DOMContentLoaded', () => {
  // Make api global for easy debugging
  window.api = api;

  const router = new Router(routes);
  router.handleRoute();
});
