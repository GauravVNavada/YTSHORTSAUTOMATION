import { api } from '../api.js';

export default class Preview {
    async getHtml() {
        return `
      <div class="page-header">
        <a href="#/dashboard" style="color: var(--text-muted); text-decoration: none; font-size: 14px; margin-bottom: 8px; display: inline-block;">← Back to Dashboard</a>
        <h1 class="page-title">Video Preview</h1>
      </div>

      <div class="preview-layout" id="preview-container" style="display: none;">
        <!-- Left: Video Player -->
        <div class="video-wrapper">
          <video id="video-player" controls preload="metadata">
            Your browser does not support the video tag.
          </video>
        </div>

        <!-- Right: Details & Actions -->
        <div>
          <div class="card" style="margin-bottom: 24px;">
            <form id="metadata-form">
              <div class="form-group">
                <label class="form-label">Title</label>
                <input type="text" id="meta-title" class="form-input" required />
              </div>
              <div class="form-group">
                <label class="form-label">Description (AI Disclosure added automatically)</label>
                <textarea id="meta-desc" class="form-textarea"></textarea>
              </div>
              <div class="form-group">
                <label class="form-label">Hashtags</label>
                <input type="text" id="meta-tags" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label">Update Schedule</label>
                <select id="meta-schedule" class="form-select">
                  <option value="now">Upload Now (Unlisted)</option>
                  <option value="next_best">Smart Schedule (Next Best Time)</option>
                </select>
              </div>
            </form>
          </div>

          <div style="display: flex; gap: 16px;">
            <button id="btn-upload" class="btn btn-primary" style="flex: 2;">
              <span class="nav-icon">🚀</span> Upload to YouTube
            </button>
            <button id="btn-regen" class="btn btn-secondary" style="flex: 1;">
              <span class="nav-icon">🔄</span> Regenerate
            </button>
          </div>
          
          <div id="upload-status" style="margin-top: 16px; font-size: 14px; color: var(--success); display: none;">
            ✅ Uploading to YouTube...
          </div>
        </div>
      </div>
      
      <div id="loading-state" class="empty-state">
        <div class="empty-text">Loading preview...</div>
      </div>
    `;
    }

    async init() {
        const params = new URLSearchParams(window.location.hash.split('?')[1]);
        this.jobId = params.get('job');

        if (!this.jobId) {
            window.router.navigate('/dashboard');
            return;
        }

        try {
            this.data = await api.getPreview(this.jobId);
            this.render();
        } catch (err) {
            document.getElementById('loading-state').innerHTML = `
        <div class="empty-icon">❌</div>
        <div class="empty-text">Failed to load preview: ${err.message}</div>
      `;
        }
    }

    render() {
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('preview-container').style.display = 'grid';

        // Player
        const player = document.getElementById('video-player');
        // For local dev, we assume the backend serves the video via a static mount or endpoint
        // We'll just construct a generic URL that FastAPI can serve
        player.src = `/api/media/${this.jobId}/final.mp4`;

        // Metadata
        const state = this.data.state;
        if (state && state.script_output) {
            document.getElementById('meta-title').value = state.script_output.title || '';
            document.getElementById('meta-desc').value = state.script_output.description || '';
            document.getElementById('meta-tags').value = (state.script_output.hashtags || []).join(' ');
        }

        // Handlers
        document.getElementById('btn-upload').addEventListener('click', () => this.upload());
        document.getElementById('btn-regen').addEventListener('click', () => alert('Regeneration UI coming soon (Phase 3)'));
    }

    async upload() {
        const btn = document.getElementById('btn-upload');
        const status = document.getElementById('upload-status');

        btn.disabled = true;
        status.style.display = 'block';

        try {
            // Save metadata first
            await api.updatePreview(this.jobId, {
                title: document.getElementById('meta-title').value,
                description: document.getElementById('meta-desc').value,
                hashtags: document.getElementById('meta-tags').value.split(' ').filter(Boolean)
            });

            // Then upload
            const schedule = document.getElementById('meta-schedule').value;
            const res = await api.uploadVideo(this.jobId, schedule);

            status.innerText = `✅ Uploaded successfully! Video ID: ${res.video_id || 'unknown'}`;
        } catch (err) {
            status.style.color = 'var(--error)';
            status.innerText = `❌ Upload failed: ${err.message}`;
            btn.disabled = false;
        }
    }
}
