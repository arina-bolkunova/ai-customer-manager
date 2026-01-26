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
