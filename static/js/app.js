// AI Customer Manager - Interactive Features
document.addEventListener('DOMContentLoaded', function() {
  // Auto-focus input
  const promptInput = document.getElementById('prompt');
  if (promptInput) {
    promptInput.focus();
  }

  // Form submission feedback
  const form = document.querySelector('form');
  if (form) {
    form.addEventListener('submit', function() {
      const submitBtn = this.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Processing...';
      submitBtn.disabled = true;

      // Re-enable after 3 seconds (form will reload anyway)
      setTimeout(() => {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
      }, 3000);
    });
  }
});

// Dark mode toggle
document.addEventListener('DOMContentLoaded', function() {
  const themeToggle = document.getElementById('themeToggle');
  const body = document.body;

  // Check for saved theme
  if (localStorage.getItem('darkMode') === 'enabled') {
    body.classList.add('dark-mode');
    themeToggle.textContent = '☀️';
  }

  themeToggle.addEventListener('click', function() {
    body.classList.toggle('dark-mode');

    if (body.classList.contains('dark-mode')) {
      localStorage.setItem('darkMode', 'enabled');
      themeToggle.textContent = '☀️';
    } else {
      localStorage.removeItem('darkMode');
      themeToggle.textContent = '🌙';
    }
  });
});
