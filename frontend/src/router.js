/**
 * Simple hash-based SPA Router
 */

export class Router {
    constructor(routes) {
        this.routes = routes;
        this.currentView = null;
        this.root = document.getElementById('page-content');

        // Make router global for easy app access
        window.router = this;

        window.addEventListener('hashchange', () => this.handleRoute());
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-page]')) {
                document.querySelectorAll('[data-page]').forEach(el => el.classList.remove('active'));
                e.target.classList.add('active');
            }
        });
    }

    async handleRoute() {
        let hash = window.location.hash.slice(1) || '/';
        let path = hash.split('?')[0];

        // Find matching route
        let route = this.routes.find(r => r.path === path);

        // Fallback behavior
        if (!route) {
            if (path.startsWith('/progress/')) route = this.routes.find(r => r.path === '/progress');
            else if (path.startsWith('/preview/')) route = this.routes.find(r => r.path === '/preview');
            else route = this.routes[0];
        }

        // Call unmount on current view if it exists
        if (this.currentView && this.currentView.unmount) {
            this.currentView.unmount();
        }

        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(el => {
            el.classList.toggle('active', el.getAttribute('href') === `#${route.path}`);
        });

        // Render new view
        const view = new route.view();
        this.currentView = view;
        this.root.innerHTML = await view.getHtml();

        // Add page transition
        this.root.firstElementChild?.classList.add('fade-in');

        if (view.init) {
            // Small timeout ensures DOM is fully updated before init attaches listeners
            setTimeout(() => view.init(), 0);
        }
    }

    navigate(path) {
        window.location.hash = path;
    }
}
