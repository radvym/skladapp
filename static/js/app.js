document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const submit = form.querySelector('button[type="submit"]');
      if (submit) {
        submit.disabled = true;
        submit.dataset.originalText = submit.textContent;
        submit.textContent = "Odesilam...";
        window.setTimeout(() => {
          submit.disabled = false;
          submit.textContent = submit.dataset.originalText || submit.textContent;
        }, 2500);
      }
    });
  });
});
