
  (function(){
    // check query string for show_login=1
    const params = new URLSearchParams(window.location.search);
    if (params.get('show_login') === '1') {
      // use Bootstrap 5 modal API to show modal programmatically
      try {
        const modalEl = document.getElementById('loginModal');
        if (modalEl) {
          const bsModal = new bootstrap.Modal(modalEl);
          bsModal.show();
          // remove show_login from URL so refresh won't reopen it
          params.delete('show_login');
          const clean = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
          window.history.replaceState({}, '', clean);
        }
      } catch (err) {
        /* if bootstrap not available or JS error, degrade silently */
        console.warn('Could not auto-open login modal:', err);
      }
    }
  })();

