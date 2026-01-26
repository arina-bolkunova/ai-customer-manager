document.addEventListener('DOMContentLoaded', function() {
  // Dark mode toggle
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', function() {
      document.body.classList.toggle('dark-mode');
      themeToggle.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    });
  }

  // Bulk email functionality
  const selectAll = document.getElementById('selectAll');
  const checkboxes = document.querySelectorAll('.lead-checkbox');
  const emailGoldPlatinum = document.getElementById('emailGoldPlatinum');
  const emailSelected = document.getElementById('emailSelected');

  // Select all checkbox
  if (selectAll) {
    selectAll.addEventListener('change', function() {
      checkboxes.forEach(cb => cb.checked = this.checked);
    });
  }

  // Email Gold/Platinum only
  if (emailGoldPlatinum) {
    emailGoldPlatinum.addEventListener('click', function() {
      const goldPlatinum = Array.from(checkboxes).filter(cb =>
        cb.dataset.category === 'Gold' || cb.dataset.category === 'Platinum'
      );
      sendBulkEmail(goldPlatinum, 'Gold/Platinum');
    });
  }

  // Email selected leads
  if (emailSelected) {
    emailSelected.addEventListener('click', function() {
      const selected = Array.from(checkboxes).filter(cb => cb.checked);
      if (selected.length === 0) {
        alert('Please select leads first!');
        return;
      }
      sendBulkEmail(selected, 'selected');
    });
  }

  function sendBulkEmail(leads, type) {
    if (leads.length === 0) {
      alert('No ' + type + ' leads found!');
      return;
    }

    leads.forEach((lead, index) => {
      const name = lead.dataset.name;
      const email = lead.dataset.email;
      const category = lead.dataset.category;
      const keyInfo = lead.dataset.keyinfo || '';

      const subject = `Quick chat about your ${category.toLowerCase()} opportunity?`;
      const body = `Hi ${name},

Saw you're a ${category} lead${keyInfo ? ' with ' + keyInfo.toLowerCase() : ''}.

Would love to discuss:
• Your timeline & budget needs
• CRM evaluation
• Next steps

Best regards,
Your Name

---
Lead added via AI Customer Manager`;

      // Gmail compose URL
      const gmailUrl = `https://mail.google.com/mail/?view=cm&to=${encodeURIComponent(email)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

      // Staggered opening (prevents browser blocking)
      setTimeout(() => {
        window.open(gmailUrl, '_blank', 'noopener,noreferrer');
      }, index * 600); // 0.6s delay between tabs
    });

    // Confirmation after all tabs opened
    setTimeout(() => {
      alert(`✅ Opened ${leads.length} Gmail compose tabs for ${type.toLowerCase()} leads!\n\nEach tab is pre-filled and ready to send.`);
    }, leads.length * 600 + 200);
  }
});
