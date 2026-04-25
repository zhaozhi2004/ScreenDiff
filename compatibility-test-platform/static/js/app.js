/* ── Toast 通知 ── */
function showToast(msg, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}

/* ── 关闭弹窗 ── */
function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

/* ── 点击遮罩关闭 ── */
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.add('hidden');
  }
});

/* ── 键盘 ESC 关闭 ── */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay:not(.hidden)').forEach(m => m.classList.add('hidden'));
  }
});

/* ── 图片弹窗（base64 / URL） ── */
function viewImage(src, title = '图片') {
  const modal = document.getElementById('imgModal') || createImgModal();
  document.getElementById('imgModalTitle').textContent = title;
  document.getElementById('imgModalContent').src = src;
  modal.classList.remove('hidden');
}

function createImgModal() {
  const div = document.createElement('div');
  div.id = 'imgModal';
  div.className = 'modal-overlay hidden';
  div.innerHTML = `
    <div class="modal modal-img">
      <div class="modal-header">
        <div class="modal-title" id="imgModalTitle">图片</div>
        <button class="modal-close" onclick="document.getElementById('imgModal').classList.add('hidden')">✕</button>
      </div>
      <div class="modal-body" style="display:flex; justify-content:center; background:#111;">
        <img id="imgModalContent" src="" style="max-width:100%; max-height:70vh; border-radius:4px;">
      </div>
    </div>`;
  document.body.appendChild(div);
  return div;
}
