document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');

  const preview = document.getElementById('preview');
  const videoPlayer = document.getElementById('videoPlayer');
  const fileInfo = document.getElementById('fileInfo');

  const actions = document.getElementById('actions');
  const processBtn = document.getElementById('processBtn');
  const removeBtn = document.getElementById('removeBtn');

  const status = document.getElementById('status');

  const downloadSection = document.getElementById('downloadSection');
  const downloadLink = document.getElementById('downloadLink');

  const headerCta = document.querySelector('.btn-header-cta');

  let currentFile = null;
  let originalVideoURL = null;
  let processedVideoURL = null;
  let isProcessing = false;

  function showToast(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    }
  }

  function setHeaderCtaVisible(visible) {
    if (headerCta) {
      headerCta.style.display = visible ? '' : 'none';
    }
  }

  if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => {
      if (!isProcessing) {
        fileInput.click();
      }
    });

    dropZone.addEventListener('keydown', (event) => {
      if (isProcessing) return;

      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        fileInput.click();
      }
    });

    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];

      if (file) {
        loadFile(file);
      }
    });

    ['dragenter', 'dragover'].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        if (isProcessing) return;

        event.preventDefault();
        event.stopPropagation();
        dropZone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        event.stopPropagation();
        dropZone.classList.remove('dragover');
      });
    });

    dropZone.addEventListener('drop', (event) => {
      if (isProcessing) return;

      const file = event.dataTransfer.files[0];

      if (file) {
        loadFile(file);
      }
    });
  }

  function loadFile(file) {
    if (!file.type.startsWith('video/')) {
      showToast('Please select a valid video file.', 'error');
      fileInput.value = '';
      return;
    }

    const maxSize = 100 * 1024 * 1024;

    if (file.size > maxSize) {
      showToast('Video size must be less than 100MB.', 'warning');
      fileInput.value = '';
      return;
    }

    currentFile = file;

    if (originalVideoURL) {
      URL.revokeObjectURL(originalVideoURL);
      originalVideoURL = null;
    }

    if (processedVideoURL) {
      processedVideoURL = null;
    }

    originalVideoURL = URL.createObjectURL(file);

    if (videoPlayer) {
      videoPlayer.src = originalVideoURL;
      videoPlayer.load();
    }

    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);

    if (fileInfo) {
      fileInfo.textContent = `${file.name} : ${sizeMB} MB`;
    }

    if (preview) {
      preview.style.display = 'block';
    }

    if (actions) {
      actions.style.display = 'flex';
    }

    if (processBtn) {
      processBtn.style.display = '';
      processBtn.disabled = false;
    }

    if (removeBtn) {
      removeBtn.disabled = false;
    }

    if (dropZone) {
      dropZone.style.display = 'none';
    }

    if (status) {
      status.classList.remove('show');
    }

    if (downloadSection) {
      downloadSection.classList.remove('show');
    }

    setHeaderCtaVisible(true);

    showToast('Video selected and ready to process.', 'success');
  }

  if (removeBtn) {
    removeBtn.addEventListener('click', () => {
      if (isProcessing) return;

      resetVideo();
    });
  }

  async function processVideo() {
    if (!currentFile || isProcessing) {
      return;
    }

    isProcessing = true;

    if (processBtn) {
      processBtn.disabled = true;
      processBtn.style.display = 'none';
    }

    if (removeBtn) {
      removeBtn.disabled = true;
    }

    if (dropZone) {
      dropZone.style.pointerEvents = 'none';
    }

    setHeaderCtaVisible(false);

    if (status) {
      status.innerHTML = `
        <span class="spinner"></span>
        Processing your video. This may take a few minutes…
      `;

      status.classList.add('show');
    }

    if (downloadSection) {
      downloadSection.classList.remove('show');
    }

    showToast('Video processing started.', 'info');

    const formData = new FormData();
    formData.append('video', currentFile);

    try {
      const response = await fetch('/video/upload', {
        method: 'POST',
        body: formData
      });

      let result;

      try {
        result = await response.json();
      } catch {
        throw new Error('The server returned an invalid response.');
      }

      if (!response.ok || !result.success) {
        throw new Error(
          result.error || 'Video processing failed.'
        );
      }

      const processedUrl = result.video?.url;

      if (!processedUrl) {
        throw new Error(
          'The processed video URL was not returned by the server.'
        );
      }

      processedVideoURL = processedUrl;

      if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.src = processedUrl;
        videoPlayer.load();
      }

      if (fileInfo) {
        fileInfo.textContent = `${currentFile.name} : Redacted video`;
      }

      if (downloadLink) {
        downloadLink.href = processedUrl;

        const originalName = currentFile.name;
        const extensionIndex = originalName.lastIndexOf('.');

        const baseName = extensionIndex > 0
          ? originalName.substring(0, extensionIndex)
          : originalName;

        downloadLink.download = `redacted_${baseName}.mp4`;
      }

      if (status) {
        status.innerHTML = `
          <i class="bi bi-check-circle-fill"></i>
          Video processing completed successfully.
        `;
      }

      if (downloadSection) {
        downloadSection.classList.add('show');
      }

      // Keep Process Video button hidden and header CTA hidden after success
      if (processBtn) {
        processBtn.style.display = 'none';
      }
      setHeaderCtaVisible(false);

      showToast(
        'Video processed successfully. Your redacted video is ready.',
        'success'
      );

    } catch (error) {
      console.error('Video processing error:', error);

      if (status) {
        status.classList.remove('show');
      }

      // On failure, allow user to retry processing the currently selected video
      if (processBtn) {
        processBtn.style.display = '';
        processBtn.disabled = false;
      }

      setHeaderCtaVisible(true);

      showToast(
        error.message || 'Unable to process the video.',
        'error'
      );

    } finally {
      isProcessing = false;

      if (removeBtn) {
        removeBtn.disabled = false;
      }

      if (dropZone) {
        dropZone.style.pointerEvents = '';
      }
    }
  }

  if (processBtn) {
    processBtn.addEventListener('click', processVideo);
  }

  function resetVideo() {
    if (isProcessing) {
      return;
    }

    currentFile = null;

    if (originalVideoURL) {
      URL.revokeObjectURL(originalVideoURL);
      originalVideoURL = null;
    }

    if (processedVideoURL) {
      processedVideoURL = null;
    }

    if (videoPlayer) {
      videoPlayer.pause();
      videoPlayer.removeAttribute('src');
      videoPlayer.load();
    }

    if (fileInfo) {
      fileInfo.textContent = '';
    }

    if (preview) {
      preview.style.display = 'none';
    }

    if (actions) {
      actions.style.display = 'none';
    }

    if (dropZone) {
      dropZone.style.display = '';
      dropZone.classList.remove('dragover');
      dropZone.style.pointerEvents = '';
    }

    if (status) {
      status.classList.remove('show');
      status.innerHTML = `
        <span class="spinner"></span>
        Processing your video…
      `;
    }

    if (downloadSection) {
      downloadSection.classList.remove('show');
    }

    if (downloadLink) {
      downloadLink.removeAttribute('href');
    }

    if (processBtn) {
      processBtn.style.display = '';
      processBtn.disabled = false;
    }

    if (removeBtn) {
      removeBtn.disabled = false;
    }

    if (fileInput) {
      fileInput.value = '';
    }

    setHeaderCtaVisible(true);
  }

  window.addEventListener('beforeunload', () => {
    if (originalVideoURL) {
      URL.revokeObjectURL(originalVideoURL);
    }
  });

  const sections = document.querySelectorAll('main[id], section[id]');
  const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');

  function updateActiveNav(id) {
    navLinks.forEach((link) => {
      if (link.getAttribute('href') === `#${id}`) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }

  if ('IntersectionObserver' in window && sections.length > 0) {
    const observerOptions = {
      root: null,
      rootMargin: '-20% 0px -65% 0px',
      threshold: 0
    };

    const sectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('id');

            if (id) {
              updateActiveNav(id);
            }
          }
        });
      },
      observerOptions
    );

    sections.forEach((section) => {
      sectionObserver.observe(section);
    });
  }

  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (event) {
      const targetId = this.getAttribute('href').substring(1);
      const targetElement = document.getElementById(targetId);

      if (targetElement) {
        event.preventDefault();

        targetElement.scrollIntoView({
          behavior: 'smooth'
        });

        updateActiveNav(targetId);
      }
    });
  });
});