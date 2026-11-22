(function () {
  'use strict';

  function labelQuantityButtons() {
    document.querySelectorAll('.bootstrap-touchspin-up').forEach(function (button) {
      button.setAttribute('aria-label', 'Zwiększ ilość');
    });
    document.querySelectorAll('.bootstrap-touchspin-down').forEach(function (button) {
      button.setAttribute('aria-label', 'Zmniejsz ilość');
    });
  }

  function scheduleLabels() {
    // Classic najpierw odtwarza przyciski TouchSpin po aktualizacji AJAX.
    window.requestAnimationFrame(labelQuantityButtons);
  }

  // Callback uruchamia się po callbackach Classic tworzących przyciski ilości.
  window.jQuery(function () {
    labelQuantityButtons();
    window.prestashop.on('updatedProduct', scheduleLabels);
    window.prestashop.on('updatedCart', scheduleLabels);
  });
})();
