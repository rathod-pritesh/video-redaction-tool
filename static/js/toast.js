(function() {
  const TOAST_ICONS = {
    success: 'bi-check-circle-fill',
    error: 'bi-exclamation-circle-fill',
    danger: 'bi-exclamation-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info: 'bi-info-circle-fill'
  };

  const TOAST_TITLES = {
    success: 'Success',
    error: 'Error',
    danger: 'Error',
    warning: 'Warning',
    info: 'Notice'
  };

  window.showToast = function(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const normType = (type || 'info').toLowerCase();
    const variant = TOAST_ICONS[normType] ? normType : 'info';
    const iconClass = TOAST_ICONS[variant] || 'bi-info-circle-fill';
    const defaultTitle = TOAST_TITLES[variant] || 'Notice';

    const toast = document.createElement('div');
    toast.className = `custom-toast toast-${variant}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');

    toast.innerHTML = `
      <div class="custom-toast-icon">
        <i class="bi ${iconClass}"></i>
      </div>
      <div class="custom-toast-content">
        <div class="custom-toast-title">${defaultTitle}</div>
        <div class="custom-toast-body">${message}</div>
      </div>
      <button type="button" class="custom-toast-close" aria-label="Close notification">
        <i class="bi bi-x-lg" style="font-size: 0.75rem;"></i>
      </button>
    `;

    container.appendChild(toast);

    // Force layout reflow before adding .show for animation
    void toast.offsetHeight;
    toast.classList.add('show');

    let timer = null;
    let remaining = duration;
    let startTime = Date.now();

    function startTimer() {
      if (duration <= 0) return;
      timer = setTimeout(() => {
        dismissToast(toast);
      }, remaining);
    }

    function pauseTimer() {
      if (timer) {
        clearTimeout(timer);
        timer = null;
        remaining -= Date.now() - startTime;
      }
    }

    function resumeTimer() {
      if (duration > 0 && remaining > 0) {
        startTime = Date.now();
        startTimer();
      }
    }

    startTimer();

    toast.addEventListener('mouseenter', pauseTimer);
    toast.addEventListener('mouseleave', resumeTimer);

    const closeBtn = toast.querySelector('.custom-toast-close');
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      pauseTimer();
      dismissToast(toast);
    });

    return toast;
  };

  function dismissToast(toast) {
    if (!toast || toast.classList.contains('hide')) return;
    toast.classList.remove('show');
    toast.classList.add('hide');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 320);
  }

  // Auto-display server-side flash messages on page load
  document.addEventListener('DOMContentLoaded', () => {
    const flashElements = document.querySelectorAll('.server-flash-msg');
    flashElements.forEach((el, index) => {
      const cat = el.getAttribute('data-category') || 'info';
      const msg = el.getAttribute('data-message') || '';
      if (msg) {
        setTimeout(() => {
          window.showToast(msg, cat);
        }, index * 200 + 100);
      }
    });
  });
})();
