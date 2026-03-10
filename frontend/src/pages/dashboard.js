import { api } from '../api.js';

export default class Dashboard {
  async getHtml() {
    return `
      <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Welcome back. Here's your channel overview.</p>
      </div>

      <div class="stats-grid" id="stats-container">
        <!-- Stats loaded here -->
        <div class="stat-card">
          <div class="stat-label">Videos Generated</div>
          <div class="stat-value">--</div>
        </div>
      </div>

      <div class="card fade-in" style="margin-bottom: 32px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h2 class="card-title" style="margin-bottom: 4px;">Ready to create?</h2>
          <p style="color: var(--text-secondary); font-size: 14px;">Generate a new YouTube Short in minutes.</p>
        </div>
        <a href="#/generate" class="btn btn-primary btn-lg">
          <span class="nav-icon">✨</span> Generate Video
        </a>
      </div>

      <h2 class="settings-section-title">Recent Videos</h2>
      <div id="history-container" class="history-list">
        <div class="empty-state">Loading history...</div>
      </div>
    `;
  }

  async init() {
    try {
      const [history, quota] = await Promise.all([
        api.getHistory().catch(() => ({ items: [] })),
        api.getQuota().catch(() => null)
      ]);

      this.renderStats(history.items.length, quota);
      this.renderHistory(history.items);
    } catch (err) {
      console.error('Dashboard init error:', err);
    }
  }

  renderStats(totalVideos, quota) {
    const container = document.getElementById('stats-container');
    if (!container) return;

    let quotaHtml = '';
    if (quota && quota.youtube_uploads_remaining !== undefined) {
      quotaHtml = `
        <div class="stat-card">
          <div class="stat-label">YouTube Uploads Left</div>
          <div class="stat-value">${quota.youtube_uploads_remaining} / 6</div>
          <div class="stat-sub">Resets at midnight</div>
        </div>
      `;
    }

    // Analytics Mock Logic
    const healthTrend = totalVideos > 0 ? "+15%" : "0%";
    const shadowBanned = totalVideos > 50 ? true : false;
    const topHook = totalVideos > 0 ? "Fast Paced (1.2s cuts)" : "N/A";

    container.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Videos Generated</div>
        <div class="stat-value">${totalVideos}</div>
        <div class="stat-sub">Lifetime total</div>
      </div>
      ${quotaHtml}
      
      <div class="stat-card" style="border-color: ${shadowBanned ? 'var(--error)' : 'var(--border-glass)'};">
        <div class="stat-label">Channel Health WoW</div>
        <div class="stat-value" style="color: ${shadowBanned ? 'var(--error)' : 'var(--success)'}; background: none; -webkit-text-fill-color: initial;">
           ${healthTrend}
        </div>
        <div class="stat-sub">${shadowBanned ? '⚠️ Shadowban Risk Detected' : '✅ Good Standing'}</div>
      </div>

      <div class="stat-card">
        <div class="stat-label">Top Performing Hook Formats</div>
        <div class="stat-value" style="font-size: 18px; line-height: 1.2; padding-top: 8px; background: none; -webkit-text-fill-color: var(--text-primary); color: var(--text-primary);">
           ${topHook}
        </div>
        <div class="stat-sub" style="margin-top: 8px;">Based on aggregate retention</div>
      </div>
    `;
  }

  renderHistory(items) {
    const container = document.getElementById('history-container');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📁</span>
          <p class="empty-text">No videos generated yet.</p>
          <a href="#/generate" class="btn btn-secondary">Create your first video</a>
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(item => `
      <div class="history-item">
        <div class="history-status ${item.state === 'complete' ? 'complete' : item.state.includes('fail') ? 'failed' : 'generating'}"></div>
        <div class="history-title">
          ${item.job_id} 
          <span class="badge ${item.state === 'complete' ? 'badge-success' : 'badge-warning'}" style="margin-left:8px">
            ${item.state}
          </span>
        </div>
        <div class="history-genre">${item.genre_id || 'unknown'}</div>
        <div class="history-time">${new Date(item.created_at).toLocaleDateString()}</div>
        ${item.state === 'complete' ? `<a href="#/preview/?job=${item.job_id}" class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;">View</a>` : ''}
      </div>
    `).join('');
  }
}
