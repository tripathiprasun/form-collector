(function () {
  var form = document.getElementById("response-form");
  if (!form) return;
  var button = form.querySelector("button[type=submit]");

  form.addEventListener("submit", function () {
    if (button) {
      button.disabled = true;
      button.textContent = "Sending...";
    }
  });

  // Re-enable if the person comes back with the browser's Back button.
  window.addEventListener("pageshow", function () {
    if (button) {
      button.disabled = false;
      button.textContent = "Submit";
    }
  });
})();
