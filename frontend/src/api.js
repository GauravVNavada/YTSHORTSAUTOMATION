/**
 * API Client for FastAPI Backend
 * Base URL is /api (proxied in dev, relative in prod)
 */

export const api = {
    async get(endpoint) {
        const res = await fetch(`/api${endpoint}`);
        if (!res.ok) {
            const error = await res.json().catch(() => ({}));
            throw new Error(error.detail || `API Error: ${res.status}`);
        }
        return res.json();
    },

    async post(endpoint, data = {}) {
        const res = await fetch(`/api${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) {
            const error = await res.json().catch(() => ({}));
            throw new Error(error.detail || `API Error: ${res.status}`);
        }
        return res.json();
    },

    // ─── Endpoints ──────────────────────────────────────────

    getSettings: () => api.get('/settings'),
    getGenres: () => api.get('/genres'),
    getHistory: () => api.get('/history'),
    getQuota: () => api.get('/quota'),
    getAnalytics: () => api.get('/analytics'),
    getPreview: (jobId) => api.get(`/preview/${jobId}`),

    validateKey: (service, key) => api.post('/validate-key', { service, key }),
    generateVideo: (data) => api.post('/generate', data),
    updatePreview: (jobId, data) => api.post(`/preview/${jobId}`, data),
    uploadVideo: (jobId, schedule) => api.post('/upload', { job_id: jobId, schedule }),
    regenerateVideo: (jobId, data) => api.post('/regenerate', { job_id: jobId, ...data }),
};
