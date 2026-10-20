(() => {
  'use strict';
  const measurementId = 'G-HHKGJ1KXP9';
  const choiceKey = 'steel-city-analytics-consent-v1';
  const excludeKey = 'steel-city-analytics-excluded';
  const production = ['steelcityhockey.app', 'www.steelcityhockey.app'].includes(location.hostname);
  const read = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const save = (key, value) => { try { localStorage.setItem(key, value); return true; } catch { return false; } };
  let excluded = read(excludeKey) === 'true';
  let consent = read(choiceKey);
  let googleStarted = false;
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('consent', 'default', {
    analytics_storage: 'denied', ad_storage: 'denied',
    ad_user_data: 'denied', ad_personalization: 'denied'
  });

  function startGoogle() {
    if (!production || excluded || consent !== 'granted' || googleStarted) return;
    googleStarted = true;
    window['ga-disable-' + measurementId] = false;
    gtag('consent', 'update', { analytics_storage: 'granted' });
    gtag('js', new Date());
    gtag('config', measurementId, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      page_location: location.origin + location.pathname,
      page_title: document.title
    });
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
    document.head.append(script);
  }

  function clearGoogleCookies() {
    const domains = ['', location.hostname, '.steelcityhockey.app'];
    document.cookie.split(';').forEach(cookie => {
      const name = cookie.trim().split('=')[0];
      if (name === '_ga' || name.startsWith('_ga_') || name === '_gid') {
        domains.forEach(domain => {
          document.cookie = name + '=; Max-Age=0; Path=/; SameSite=Lax' + (domain ? '; Domain=' + domain : '');
        });
      }
    });
  }

  if (production && !excluded) {
    const script = document.createElement('script');
    script.type = 'module';
    script.src = 'https://static.cloudflareinsights.com/beacon.min.js';
    script.setAttribute('data-cf-beacon', '{"token":"991a1493b6e14c31b10dce6502bef0be"}');
    document.head.append(script);
  }

  const dialog = document.createElement('dialog');
  dialog.id = 'analytics-dialog';
  dialog.setAttribute('aria-labelledby', 'analytics-title');
  dialog.innerHTML = `
    <h2 id="analytics-title">Privacy & analytics</h2>
    <p>Allow Google Analytics cookies to help us estimate how many different visitors use the match centre and whether they return?</p>
    <p>The app works either way. Google Analytics loads only if you allow it. Advertising features are off. Cloudflare also counts visits without cookies unless you exclude this browser.</p>
    <p class="analytics-status" aria-live="polite"></p>
    <div class="analytics-actions"><button type="button" id="analytics-allow">Allow analytics</button><button type="button" id="analytics-reject">No thanks</button></div>
    <details><summary>About the counts and your own visits</summary>
      <p>Google receives page visits and browser/device information, using cookies to recognise returning browsers. Its user count is an estimate: another browser or device can count separately. Blocked cookies, rejected consent and offline use may leave visits uncounted.</p>
      <p><a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer">Google privacy policy</a> · <a href="https://www.cloudflare.com/web-analytics/" target="_blank" rel="noreferrer">Cloudflare Web Analytics</a></p>
      <p>Site owner or tester? Exclude this browser from both counters for future visits. Repeat on your other browsers and devices. Clearing browser storage resets your choice.</p>
      <button type="button" id="analytics-exclude"></button>
    </details>
    <button type="button" id="analytics-close">Close</button>`;
  document.body.append(dialog);
  const status = dialog.querySelector('.analytics-status');
  const exclusionButton = dialog.querySelector('#analytics-exclude');
  function updateStatus() {
    status.textContent = excluded ? 'This browser is excluded from both analytics counters.' :
      consent === 'granted' ? 'Google Analytics: allowed on this browser.' :
      consent === 'denied' ? 'Google Analytics: not allowed on this browser.' : 'Google Analytics: waiting for your choice.';
    exclusionButton.textContent = excluded ? 'Include this browser again' : 'Exclude this browser from analytics';
  }
  dialog.querySelector('#analytics-allow').addEventListener('click', () => {
    consent = 'granted';
    save(choiceKey, consent);
    startGoogle();
    updateStatus();
    dialog.close();
  });
  dialog.querySelector('#analytics-reject').addEventListener('click', () => {
    consent = 'denied';
    save(choiceKey, consent);
    window['ga-disable-' + measurementId] = true;
    gtag('consent', 'update', { analytics_storage: 'denied' });
    clearGoogleCookies();
    dialog.close();
    if (googleStarted) location.reload();
  });
  exclusionButton.addEventListener('click', () => {
    const next = !excluded;
    if (!save(excludeKey, String(next))) {
      status.textContent = 'Your browser could not save this choice. Enable site storage and try again.';
      return;
    }
    excluded = next;
    window['ga-disable-' + measurementId] = excluded;
    if (excluded) clearGoogleCookies();
    location.reload();
  });
  dialog.querySelector('#analytics-close').addEventListener('click', () => dialog.close());
  const settingsButton = document.createElement('button');
  settingsButton.type = 'button';
  settingsButton.className = 'analytics-settings';
  settingsButton.textContent = 'Privacy & analytics';
  settingsButton.setAttribute('aria-haspopup', 'dialog');
  settingsButton.addEventListener('click', () => { updateStatus(); dialog.showModal(); });
  (document.querySelector('.footer') || document.body).append(settingsButton);
  updateStatus();
  startGoogle();
  if (!excluded && !consent) dialog.showModal();
})();
