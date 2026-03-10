import { API_BASE } from '../api.js';

export default class Progress {
    async getHtml() {
        return `
      <div class="page-header">
        <h1 class="page-title">Generating Video...</h1>
        <p class="page-subtitle" id="status-text">Starting pipeline</p>
      </div>

      <div class="card slide-up">
        <div class="progress-container">
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" id="progress-fill" style="width: 0%"></div>
          </div>
          
          <div class="progress-stages">
            <div class="progress-stage active" id="stage-script">
              <span class="progress-stage-icon">📝</span>
              Script
            </div>
            <div class="progress-stage" id="stage-assets">
              <span class="progress-stage-icon">🖼️</span>
              Assets
            </div>
            <div class="progress-stage" id="stage-audio">
              <span class="progress-stage-icon">🎧</span>
              Audio
            </div>
            <div class="progress-stage" id="stage-render">
              <span class="progress-stage-icon">🎬</span>
              Render
            </div>
            <div class="progress-stage" id="stage-upload">
              <span class="progress-stage-icon">🚀</span>
              Done
            </div>
          </div>
        </div>
        
        <div id="log-container" style="margin-top: 32px; background: #000; padding: 16px; border-radius: var(--radius-md); font-family: monospace; font-size: 12px; color: var(--text-muted); height: 150px; overflow-y: auto;">
          > Pipeline initialized...
        </div>
      </div>
    `;
    }

    async init() {
        const params = new URLSearchParams(window.location.hash.split('?')[1]);
        const jobId = params.get('job');

        if (!jobId) {
            window.router.navigate('/dashboard');
            return;
        }

        this.fill = document.getElementById('progress-fill');
        this.statusText = document.getElementById('status-text');
        this.logContainer = document.getElementById('log-container');
        this.stages = {
            script: document.getElementById('stage-script'),
            assets: document.getElementById('stage-assets'),
            audio: document.getElementById('stage-audio'),
            render: document.getElementById('stage-render'),
            upload: document.getElementById('stage-upload'),
        };

        this.connectSSE(jobId);
    }

    connectSSE(jobId) {
        this.eventSource = new EventSource(`${API_BASE}/events/${jobId}`);

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.updateProgress(data);

                if (data.stage === 'complete' || data.stage === 'failed') {
                    this.eventSource.close();
                    if (data.stage === 'complete') {
                        setTimeout(() => {
                            window.router.navigate(`/preview/?job=${jobId}`);
                        }, 1500);
                    } else {
                        this.statusText.innerText = "Pipeline Failed";
                        this.statusText.style.color = "var(--error)";
                    }
                }
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        };

        this.eventSource.onerror = () => {
            this.log('> Connection lost. Reconnecting...');
        };
    }

    updateProgress(data) {
        // data.pct is 0-1
        const percent = Math.round(data.pct * 100);
        this.fill.style.width = `${percent}%`;
        this.statusText.innerText = data.message || `Generating (${percent}%)`;
        this.log(`> [${data.stage}] ${data.message || ''}`);

        // Update stage pills
        if (data.stage.includes('script')) this.setStage('script');
        else if (data.stage.includes('image')) this.setStage('assets');
        else if (data.stage.includes('tts') || data.stage.includes('audio')) this.setStage('audio');
        else if (data.stage.includes('video') || data.stage.includes('caption')) this.setStage('render');
        else if (data.stage.includes('complete')) {
            this.setStage('upload');
            Object.values(this.stages).forEach(el => {
                el.classList.remove('active');
                el.classList.add('done');
            });
        }
    }

    setStage(activeKey) {
        Object.entries(this.stages).forEach(([key, el]) => {
            if (key === activeKey) {
                el.classList.add('active');
                el.classList.remove('done');
            } else if (this.isBefore(key, activeKey)) {
                el.classList.remove('active');
                el.classList.add('done');
            } else {
                el.classList.remove('active', 'done');
            }
        });
    }

    isBefore(key, activeKey) {
        const order = ['script', 'assets', 'audio', 'render', 'upload'];
        return order.indexOf(key) < order.indexOf(activeKey);
    }

    log(msg) {
        const line = document.createElement('div');
        line.innerText = msg;
        this.logContainer.appendChild(line);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    unmount() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}
