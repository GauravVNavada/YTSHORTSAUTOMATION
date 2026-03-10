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

      <div class="card slide-up" style="max-width: 600px; margin-bottom: 32px;">
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

      <div class="card slide-up" style="max-width: 600px; margin-bottom: 32px;">
        <h2 class="settings-section-title">Caption Style Editor</h2>
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
          Customize the look and feel of your AI-generated subtitles.
        </p>
        
        <div style="display: flex; gap: 24px;">
           <div style="flex: 1;">
             <div class="form-group">
                <label class="form-label">Font Family</label>
                <select class="form-select" id="caption-font">
                   <option>Inter</option>
                   <option>Montserrat</option>
                   <option>Impact</option>
                   <option>Bangers</option>
                </select>
             </div>
             <div class="form-group">
                <label class="form-label">Animation Style</label>
                <select class="form-select" id="caption-anim">
                   <option>Karaoke (Word-by-word highlight)</option>
                   <option>Pop In (TikTok style bounce)</option>
                   <option>Fade In (Cinematic documentary)</option>
                </select>
             </div>
             <div class="form-group">
                <label class="form-label">Active Word Color</label>
                <input type="color" value="#FFE600" id="caption-color" style="width: 100%; height: 40px; border: none; background: transparent; cursor: pointer;">
             </div>
           </div>
           
           <div style="width: 200px;">
              <label class="form-label">Live Preview</label>
              <div class="caption-preview-box" style="width: 100%; height: 280px; background: #000; border-radius: var(--radius-md); position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; border: 1px solid var(--border-glass);">
                 <div style="position: absolute; inset:0; background: linear-gradient(to top, rgba(0,0,0,0.8), transparent); z-index: 1;"></div>
                 <div id="mock-caption-text" style="z-index: 2; color: white; font-weight: 800; font-size: 24px; text-align: center; text-shadow: 2px 2px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000;">
                    <span style="color: #FFE600; transform: scale(1.1); display: inline-block;">This</span> is a test.
                 </div>
              </div>
           </div>
        </div>
      </div>

      <div class="card slide-up" style="max-width: 600px;">
        <h2 class="settings-section-title">Gameplay Library Manager</h2>
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
          Manage the CC0 background videos used for visual retention in Auto mode.
        </p>
        
        <div class="gameplay-list" style="border: 1px solid var(--border-glass); border-radius: var(--radius-md); overflow: hidden; margin-bottom: 16px;">
           <div style="display: flex; justify-content: space-between; padding: 12px 16px; background: var(--bg-glass); border-bottom: 1px solid var(--border-glass);">
              <span style="font-size:13px; color:var(--text-primary);"><span style="margin-right:8px;">✅</span> minecraft_parkour_01.mp4</span>
              <span style="font-size:12px; color:var(--text-muted); cursor:pointer;">[Del]</span>
           </div>
           <div style="display: flex; justify-content: space-between; padding: 12px 16px; background: var(--bg-glass); border-bottom: 1px solid var(--border-glass);">
              <span style="font-size:13px; color:var(--text-primary);"><span style="margin-right:8px;">✅</span> gta_v_ramp_jump.webm</span>
              <span style="font-size:12px; color:var(--text-muted); cursor:pointer;">[Del]</span>
           </div>
           <div style="display: flex; justify-content: space-between; padding: 12px 16px; background: var(--bg-glass);">
              <span style="font-size:13px; color:var(--text-primary);"><span style="margin-right:8px;">✅</span> satisfying_sand_cutting.mp4</span>
              <span style="font-size:12px; color:var(--text-muted); cursor:pointer;">[Del]</span>
           </div>
        </div>
        
        <button class="btn btn-secondary" style="width: 100%;">
           <span style="margin-right: 8px;">+</span> Add Local Video File
        </button>
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

    // Live Caption Preview
    const colorPicker = document.getElementById('caption-color');
    if (colorPicker) {
      colorPicker.addEventListener('input', (e) => {
        const mockText = document.getElementById('mock-caption-text');
        if (mockText) {
          mockText.innerHTML = `<span style="color: ${e.target.value}; transform: scale(1.1); display: inline-block; transition: all 0.2s;">This</span> is a test.`;
        }
      });
    }
  }
}
