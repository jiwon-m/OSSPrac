const audio = document.getElementById('bgm');
const btn = document.getElementById('bgmToggle');
const icon = document.getElementById('bgmIcon');

function applyBgmState(on) {
  if (!audio || !btn || !icon) return;

  if (on) {
    audio.muted = false;
    audio.play().catch(() => {}); // 일부 브라우저 자동재생 방지 예외
    btn.setAttribute('aria-pressed', 'true');
    icon.src = '/static/icons/sound_on.png';
  } else {
    audio.pause();
    audio.muted = true;
    btn.setAttribute('aria-pressed', 'false');
    icon.src = '/static/icons/sound_off.png';
  }
  localStorage.setItem('bgm_enabled', on ? '1' : '0');
}

btn?.addEventListener('click', () => {
  const current = localStorage.getItem('bgm_enabled') === '1';
  applyBgmState(!current);
});

document.addEventListener('DOMContentLoaded', () => {
  const state = localStorage.getItem('bgm_enabled') === '1';
  applyBgmState(state);
});

function addPortfolioRow() {
  const box = document.getElementById('portfolioList');
  const row = document.createElement('div');
  row.className = 'portfolio-row';
  row.innerHTML = `
    <div class="field-line">
      <input type="text" name="project_title[]" placeholder="프로젝트명">
    </div>
    <div class="period-line">
      <input type="month" name="start_month[]">
      <span class="dash">–</span>
      <input type="month" name="end_month[]">
    </div>
    <div class="field-line">
      <input type="text" name="proj_role[]" placeholder="역할">
    </div>
    <div class="field-line">
      <input type="text" name="description[]" placeholder="설명">
    </div>
    <input type="hidden" name="period[]" value="">
    <div class="row-actions">
      <button type="button" class="btn-mini danger" onclick="this.closest('.portfolio-row').remove()">삭제</button>
    </div>
  `;
  box.appendChild(row);
}
