import { api } from '../api.js';

export default class Generate {
  async getHtml() {
    return `
      <div class="page-header">
        <h1 class="page-title">Generate Video</h1>
        <p class="page-subtitle">One click to hook, script, voice, assets, and render.</p>
      </div>

      <div class="card slide-up" style="max-width: 600px;">
        <form id="generate-form">
          <div class="form-group">
            <label class="form-label">Genre</label>
            <select id="genre-select" class="form-select" required>
              <option value="">Loading genres...</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Generation Mode</label>
            <div class="toggle-group" id="mode-toggle">
              <button type="button" class="toggle-option active" data-mode="auto">Auto (System Picks)</button>
              <button type="button" class="toggle-option" data-mode="custom">Custom Topic</button>
            </div>
            <input type="hidden" id="mode-input" value="auto" />
          </div>

          <div class="form-group" id="topic-group" style="display: none;">
            <label class="form-label">Custom Topic</label>
            <input type="text" id="topic-input" class="form-input" placeholder="e.g. A haunted lighthouse in Japan..." />
          </div>

          <div class="form-group">
            <label class="form-label">Upload Schedule</label>
            <select id="schedule-select" class="form-select">
              <option value="now">Upload Now (Unlisted)</option>
              <option value="next_best">Smart Schedule (Next Best Time)</option>
            </select>
          </div>

          <div style="margin-top: 32px;">
            <button type="submit" class="btn btn-primary btn-lg" style="width: 100%" id="submit-btn">
              ✨ Generate Video
            </button>
          </div>
        </form>
      </div>
    `;
  }

  async init() {
    this.form = document.getElementById('generate-form');
    this.genreSelect = document.getElementById('genre-select');
    this.modeInput = document.getElementById('mode-input');
    this.topicGroup = document.getElementById('topic-group');
    this.topicInput = document.getElementById('topic-input');
    this.submitBtn = document.getElementById('submit-btn');

    // Load genres
    try {
      const res = await api.getGenres();
      const genresList = res.genres || [];
      this.genreSelect.innerHTML = genresList.map(g =>
        `<option value="${g.genre_id}">${g.icon || '🎬'} ${g.display_name}</option>`
      ).join('');
    } catch (err) {
      this.genreSelect.innerHTML = '<option value="">Failed to load genres</option>';
    }

    // Toggle mode
    document.getElementById('mode-toggle').addEventListener('click', (e) => {
      if (!e.target.matches('.toggle-option')) return;

      document.querySelectorAll('.toggle-option').forEach(el => el.classList.remove('active'));
      e.target.classList.add('active');

      const mode = e.target.dataset.mode;
      this.modeInput.value = mode;

      if (mode === 'custom') {
        this.topicGroup.style.display = 'block';
        this.topicInput.required = true;
      } else {
        this.topicGroup.style.display = 'none';
        this.topicInput.required = false;
        this.topicInput.value = '';
      }
    });

    // Handle submit
    this.form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const data = {
        genre_id: this.genreSelect.value,
        mode: this.modeInput.value,
        custom_topic: this.topicInput.value,
        schedule: document.getElementById('schedule-select').value
      };

      this.submitBtn.disabled = true;
      this.submitBtn.innerHTML = 'Starting pipeline...';

      try {
        const res = await api.generateVideo(data);
        if (res.job_id) {
          window.router.navigate(`/progress/?job=${res.job_id}`);
        }
      } catch (err) {
        alert(err.message || 'Failed to start generation');
        this.submitBtn.disabled = false;
        this.submitBtn.innerHTML = '✨ Generate Video';
      }
    });
  }
}
