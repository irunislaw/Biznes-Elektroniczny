(function () {
  'use strict';

  var COOKIE_NAME = 'be_cookie_consent';
  var MAX_AGE = 31536000; // 1 rok w sekundach

  function hasConsent() {
    return document.cookie.split('; ').indexOf(COOKIE_NAME + '=1') !== -1;
  }

  function init() {
    var banner = document.getElementById('be-cookie-banner');
    var button = banner ? banner.querySelector('.be-cookie-banner__button') : null;
    var observer = null;

    if (!banner || !button) {
      return;
    }

    // Odstęp na dole, żeby pasek nie zasłaniał przycisków.
    function reserveSpace() {
      document.body.style.paddingBottom = banner.offsetHeight + 'px';
    }

    function hide() {
      if (observer) {
        observer.disconnect();
      } else {
        window.removeEventListener('resize', reserveSpace);
      }
      document.body.style.paddingBottom = '';
      if (banner.parentNode) {
        banner.parentNode.removeChild(banner);
      }
    }

    if (hasConsent()) {
      hide();
      return;
    }

    if ('ResizeObserver' in window) {
      observer = new ResizeObserver(reserveSpace);
      observer.observe(banner);
    } else {
      window.addEventListener('resize', reserveSpace);
    }
    reserveSpace();

    button.addEventListener('click', function () {
      var cookie = COOKIE_NAME + '=1; max-age=' + MAX_AGE + '; path=/; SameSite=Lax';
      if (window.location.protocol === 'https:') {
        cookie += '; Secure';
      }
      document.cookie = cookie;
      hide();
    });

    // Po „Wstecz” przeglądarka może pokazać starą stronę z paskiem.
    window.addEventListener('pageshow', function () {
      if (hasConsent()) {
        hide();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
