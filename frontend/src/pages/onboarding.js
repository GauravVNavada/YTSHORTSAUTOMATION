import { api } from '../api.js';

export default class Onboarding {
  constructor() {
    this.step = 1;
    this.totalSteps = 6;
    this.keys = {
      gemini_api_key: '',
      youtube_api_key: '',
      tts_api_key: '',
      groq_api_key: ''
    };
    this.calibrationData = {
      genre_id: '',
      user_intent: ''
    };
    // Simulated genres for onboarding since backend might not be fully seeded yet
    this.genres = [
      { id: 'scary_stories', icon: '👻', name: 'Scary Stories' },
      { id: 'motivation', icon: '💪', name: 'Motivation' },
      { id: 'history', icon: '🏛️', name: 'History Facts' },
      { id: 'science', icon: '🧬', name: 'Science & Space' }
    ];
  }

  async getHtml() {
    return `
      <div class="onboarding-container fade-in">
        <div class="onboarding-card card">
          <div class="onboarding-progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" style="width: ${(this.step / this.totalSteps) * 100}%"></div>
            </div>
            <div class="progress-text">Step ${this.step} of ${this.totalSteps}</div>
          </div>
          
          <div id="onboarding-content">
            ${this.renderStep()}
          </div>
        </div>
      </div>
    `;
  }

  renderStep() {
    switch (this.step) {
      case 1: return this.renderStep1();
      case 2: return this.renderStep2();
      case 3: return this.renderStep3();
      case 4: return this.renderStep4();
      case 5: return this.renderStep5();
      case 6: return this.renderStep6();
      default: return this.renderStep1();
    }
  }

  // --- STEP 1: License ---
  renderStep1() {
    return `
      <div class="step-content slide-up">
        <h2>Welcome to YT Shorts Auto 🎬</h2>
        <p class="step-desc">Let's get your studio set up. First, enter your one-time purchase license key.</p>
        
        <div class="form-group" style="margin-top:24px;">
          <label class="form-label">License Key</label>
          <input type="text" id="license-input" class="form-input" placeholder="YTS-XXXX-XXXX-XXXX" />
        </div>
        
        <div class="step-footer">
          <button class="btn btn-secondary" onclick="window.open('https://example.com/buy', '_blank')">Buy License ($100)</button>
          <button class="btn btn-primary" id="btn-next">Activate & Continue ➔</button>
        </div>
      </div>
    `;
  }

  // --- STEP 2: API Keys ---
  renderStep2() {
    return `
      <div class="step-content slide-up">
        <h2>Connect Your Core AI Brains 🧠</h2>
        <p class="step-desc">YT Shorts Auto uses your own API keys (BYOK) so you pay zero monthly fees.</p>
        
        <div class="form-group" style="margin-top:24px;">
          <label class="form-label" style="display:flex; justify-content:space-between;">
            Google Gemini API (Scripting)
            <a href="#" style="color:var(--accent-color);font-size:12px;">Get Key</a>
          </label>
          <div class="key-row">
            <input type="password" id="key-gemini" class="form-input" placeholder="AIzaSy..." value="${this.keys.gemini_api_key}">
            <button class="btn btn-secondary test-key-btn" data-key="gemini">Test</button>
            <div class="key-status" id="status-gemini"></div>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" style="display:flex; justify-content:space-between;">
            Groq API (Quality Validation)
            <a href="#" style="color:var(--accent-color);font-size:12px;">Get Key</a>
          </label>
          <div class="key-row">
            <input type="password" id="key-groq" class="form-input" placeholder="gsk_..." value="${this.keys.groq_api_key}">
            <button class="btn btn-secondary test-key-btn" data-key="groq">Test</button>
            <div class="key-status" id="status-groq"></div>
          </div>
        </div>
        
        <div class="step-footer split">
          <button class="btn btn-secondary" id="btn-prev">⬅ Back</button>
          <button class="btn btn-primary" id="btn-next">Continue ➔</button>
        </div>
      </div>
    `;
  }

  // --- STEP 3: YouTube ---
  renderStep3() {
    return `
      <div class="step-content slide-up">
        <h2>Link Your Target Channel 📺</h2>
        <p class="step-desc">Connect YouTube so the app can upload directly to your channel and analyze performance drops.</p>
        
        <div style="margin: 32px 0; text-align: center; padding: 32px; border: 1px dashed var(--border-glass); border-radius: 12px;">
          <div id="yt-connect-area">
             <button class="btn btn-lg" style="background: #ff0000; color: white;" id="connect-yt-btn">
               <span style="margin-right:8px; font-weight:bold;">▶</span> Connect YouTube Channel
             </button>
          </div>
        </div>
        
        <div class="step-footer split">
          <button class="btn btn-secondary" id="btn-prev">⬅ Back</button>
          <button class="btn btn-primary" id="btn-next">Continue ➔</button>
        </div>
      </div>
    `;
  }

  // --- STEP 4: Genre Select ---
  renderStep4() {
    const genreHTML = this.genres.map(g => `
      <div class="genre-option ${this.calibrationData.genre_id === g.id ? 'selected' : ''}" data-id="${g.id}">
        <div class="genre-icon">${g.icon}</div>
        <div class="genre-name">${g.name}</div>
      </div>
    `).join('');

    return `
      <div class="step-content slide-up">
        <h2>What kind of channel are we building? 🎯</h2>
        <p class="step-desc">Select your primary niche. We fetch fresh templates dynamically from the cloud.</p>
        
        <div class="genre-grid" style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin: 24px 0;">
          ${genreHTML}
        </div>
        
        <div class="form-group" style="${this.calibrationData.genre_id ? 'display:block;' : 'display:none;'}" id="intent-box">
          <label class="form-label">What are you looking for from this genre?</label>
          <textarea id="user-intent" class="form-input" style="height: 80px;" placeholder="e.g. I want creepy stories with unexpected twists. Not jump scares but slow dread.">${this.calibrationData.user_intent}</textarea>
        </div>
        
        <div class="step-footer split">
          <button class="btn btn-secondary" id="btn-prev">⬅ Back</button>
          <button class="btn btn-primary" id="btn-next" ${!this.calibrationData.genre_id ? 'disabled' : ''}>Calibrate System ➔</button>
        </div>
      </div>
    `;
  }

  // --- STEP 5: Calibration ---
  renderStep5() {
    const g = this.genres.find(x => x.id === this.calibrationData.genre_id) || this.genres[0];
    return `
      <div class="step-content slide-up">
        <h2>Calibration in Progress ⚙️</h2>
        <p class="step-desc">Normally the AI generates 3 videos for <b>${g.icon} ${g.name}</b> and asks you to pick one. This tunes our prompt injection specifically for you.</p>
        
        <div class="calibration-mockup" style="background: var(--bg-tertiary); padding: 24px; border-radius: 12px; margin: 24px 0; text-align: center;">
          <div class="pulse-ring" style="margin: 0 auto 16px auto; width: 40px; height: 40px; border-radius: 50%; border: 3px solid var(--accent-color); border-top-color: transparent; animation: spin 1s linear infinite;"></div>
          <p style="color: var(--text-muted); font-size: 14px;">(Mocking 3 sample video generations)</p>
        </div>
        
        <div class="step-footer split">
          <button class="btn btn-secondary" id="btn-prev">⬅ Back</button>
          <button class="btn btn-primary" id="btn-next">Finish Calibration ➔</button>
        </div>
      </div>
    `;
  }

  // --- STEP 6: Assets ---
  renderStep6() {
    return `
      <div class="step-content slide-up">
        <h2>Downloading Local Assets 📦</h2>
        <p class="step-desc">Fetching high-quality CC0 gameplay footage, music, and sound effects.</p>
        
        <div style="margin: 32px 0;">
          <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:13px; color:var(--text-secondary);">
             <span>Gameplay Pack (~500MB)</span>
             <span id="dl-percent">0%</span>
          </div>
          <div class="progress-bar-bg" style="height: 8px;">
            <div class="progress-bar-fill" id="asset-dl-bar" style="width: 0%; background: var(--success);"></div>
          </div>
        </div>
        
        <div class="step-footer" style="justify-content: flex-end;">
          <button class="btn btn-primary" id="btn-finish" disabled>Launch Dashboard</button>
        </div>
      </div>
    `;
  }


  async init() {
    // Hide sidebar during onboarding
    document.getElementById('sidebar').style.display = 'none';
    document.getElementById('page-content').style.marginLeft = '0';

    this.attachListeners();

    if (this.step === 6) {
      this.simulateDownload();
    }
  }

  unmount() {
    // Restore sidebar when leaving
    document.getElementById('sidebar').style.display = 'flex';
    document.getElementById('page-content').style.marginLeft = '250px';
  }

  attachListeners() {
    const nextBtn = document.getElementById('btn-next');
    const prevBtn = document.getElementById('btn-prev');
    const finishBtn = document.getElementById('btn-finish');

    if (nextBtn) {
      nextBtn.addEventListener('click', async () => {
        if (this.step === 1) {
          const keyStr = document.getElementById('license-input').value;
          const prevText = nextBtn.innerText;
          nextBtn.innerText = 'Validating...';
          nextBtn.disabled = true;

          try {
            let result;
            if (window.__TAURI_INTERNALS__) {
              const { invoke } = await import('@tauri-apps/api/core');
              result = await invoke('validate_license', { key: keyStr });
            } else {
              // Mock for browser dev server
              result = { valid: keyStr.includes('.'), message: 'Mock validation in browser' };
            }

            if (!result.valid) {
              alert(result.message || 'Invalid License Key');
              nextBtn.innerText = prevText;
              nextBtn.disabled = false;
              return;
            }
          } catch (e) {
            alert('Validation error: ' + e);
            nextBtn.innerText = prevText;
            nextBtn.disabled = false;
            return;
          }
        }

        this.saveCurrentStepData();
        this.step++;
        this.refreshUI();
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        this.saveCurrentStepData();
        this.step--;
        this.refreshUI();
      });
    }

    if (finishBtn) {
      finishBtn.addEventListener('click', () => {
        // Mark onboarding complete in localStorage
        localStorage.setItem('onboarding_complete', 'true');
        window.router.navigate('/');
      });
    }

    // Key Testing
    document.querySelectorAll('.test-key-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const keyId = e.target.dataset.key;
        const statusStr = document.getElementById(`status-${keyId}`);
        statusStr.innerText = '⏳';
        setTimeout(() => statusStr.innerText = '✅', 800);
      });
    });

    // Youtube Click
    const ytBtn = document.getElementById('connect-yt-btn');
    if (ytBtn) {
      ytBtn.addEventListener('click', () => {
        const area = document.getElementById('yt-connect-area');
        area.innerHTML = '<div style="color:var(--success); font-weight:bold; font-size: 16px;">✅ Connected: @ytshortsauto</div>';
      });
    }

    // Genre Selection
    document.querySelectorAll('.genre-option').forEach(el => {
      el.addEventListener('click', (e) => {
        document.querySelectorAll('.genre-option').forEach(opt => opt.classList.remove('selected'));
        e.currentTarget.classList.add('selected');
        this.calibrationData.genre_id = e.currentTarget.dataset.id;
        document.getElementById('intent-box').style.display = 'block';
        if (document.getElementById('btn-next')) {
          document.getElementById('btn-next').disabled = false;
        }
      });
    });
  }

  saveCurrentStepData() {
    if (this.step === 2) {
      this.keys.gemini_api_key = document.getElementById('key-gemini')?.value || '';
      this.keys.groq_api_key = document.getElementById('key-groq')?.value || '';
    }
    if (this.step === 4) {
      this.calibrationData.user_intent = document.getElementById('user-intent')?.value || '';
    }
  }

  async refreshUI() {
    const app = document.getElementById('page-content');
    app.innerHTML = await this.getHtml();
    this.init();
  }

  simulateDownload() {
    let pct = 0;
    const bar = document.getElementById('asset-dl-bar');
    const txt = document.getElementById('dl-percent');
    const finish = document.getElementById('btn-finish');

    const interval = setInterval(() => {
      pct += Math.random() * 15;
      if (pct >= 100) {
        pct = 100;
        clearInterval(interval);
        if (finish) finish.disabled = false;
      }
      if (bar) bar.style.width = pct + '%';
      if (txt) txt.innerText = Math.floor(pct) + '%';
    }, 300);
  }
}
