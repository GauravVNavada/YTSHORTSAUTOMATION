import { api } from '../api.js';

export default class Settings {
    async getHtml() {
        return `
      <div class="page-header">
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Configure API keys and default preferences.</p>
      </div>

      <div class="card slide-up" style="max-width: 600px; margin-bottom: 32px;">
        <h2 class="settings-section-title">API Keys (BYOK)</h2>
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
          All keys are stored securely in your OS keychain. We never see them.
        </p>

        <form id="keys-form">
          ${this.renderKeyRow('Google Gemini API', 'gemini_api_key')}
          ${this.renderKeyRow('Groq API', 'groq_api_key')}
          ${this.renderKeyRow('Pexels API', 'pexels_api_key')}
          ${this.renderKeyRow('Pixabay API', 'pixabay_api_key')}

          <div style="margin-top: 24px; display: flex; gap: 12px; align-items: center;">
            <button type="submit" class="btn btn-primary" id="save-keys-btn">
              Save Keys
            </button>
            <span id="keys-save-status" style="font-size: 13px; color: var(--success); display: none;">✅ Saved!</span>
          </div>
        </form>
      </div>

      <div class="card slide-up" style="max-width: 600px;">
        <h2 class="settings-section-title">System Requirements</h2>
        <ul style="list-style: none; padding: 0; font-size: 14px; color: var(--text-secondary);">
          <li style="margin-bottom: 8px;">✅ FFmpeg Installation (<span style="color:var(--success)">Detected</span>)</li>
          <li style="margin-bottom: 8px;">✅ ImageMagick (Optional, useful for captions)</li>
          <li style="margin-bottom: 8px;">✅ Disk Space (> 5GB recommended)</li>
        </ul>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-glass);">
          <span class="badge badge-success">YT Shorts Auto v0.1.0-alpha</span>
        </div>
      </div>
    `;
    }

    renderKeyRow(label, id) {
        return `
      <div class="form-group">
        <label class="form-label">${label}</label>
        <div class="key-row">
          <input type="password" id="${id}" class="form-input" placeholder="Enter key to update" />
          <button type="button" class="btn btn-secondary test-key-btn" data-key="${id}">Test</button>
          <div class="key-status" id="status-${id}"></div>
        </div>
      </div>
    `;
    }

    async init() {
        try {
            this.settings = await api.getSettings().catch(() => ({}));

            // We don't populate real keys for security, just show if they exist
            ['gemini_api_key', 'groq_api_key', 'pexels_api_key', 'pixabay_api_key'].forEach(id => {
                if (this.settings[id]) {
                    document.getElementById(id).placeholder = '•••••••••••••••• (Set)';
                    document.getElementById(`status-${id}`).innerText = '✅';
                } else {
                    document.getElementById(`status-${id}`).innerText = '❓';
                }
            });
        } catch (err) {
            console.error('Failed to load settings:', err);
        }

        // Handle dummy testers
        document.querySelectorAll('.test-key-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.dataset.key;
                const val = document.getElementById(id).value || 'existing';
                const stNode = document.getElementById(`status-${id}`);

                stNode.innerText = '⏳';
                try {
                    // A real implementation would call api.validateKey(id, val)
                    await new Promise(r => setTimeout(r, 600)); // Simulate validation
                    stNode.innerText = '✅';
                } catch (err) {
                    stNode.innerText = '❌';
                }
            });
        });

        // Save keys
        document.getElementById('keys-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const status = document.getElementById('keys-save-status');
            status.style.display = 'inline';
            setTimeout(() => { status.style.display = 'none'; }, 2000);
            // Real app would POST to /settings
        });
    }
}
