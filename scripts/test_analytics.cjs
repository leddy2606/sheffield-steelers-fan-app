const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../assets/analytics.js'), 'utf8');
function browser(initial = {}, hostname = 'steelcityhockey.app') {
  const storage = new Map(Object.entries(initial));
  const nodes = new Map();
  const scripts = [];
  let reloads = 0;
  function element(tag) {
    return { tag, attrs: {}, events: {}, textContent: '',
      setAttribute(k,v) { this.attrs[k] = v; },
      addEventListener(k,v) { this.events[k] = v; },
      querySelector(key) { if (!nodes.has(key)) nodes.set(key, element('button')); return nodes.get(key); },
      append(node) { if (node.tag === 'script') scripts.push(node); },
      showModal() { this.open = true; }, close() { this.open = false; }
    };
  }
  const document = { title: 'Steel City Match Centre', head: element('head'), body: element('body'),
    cookie: '_ga=existing; _ga_HHKGJ1KXP9=existing',
    createElement: element, querySelector: () => null };
  const window = {};
  const context = { window, document,
    location: { hostname, origin: 'https://' + hostname, pathname: '/', reload() { reloads++; } },
    localStorage: { getItem: k => storage.get(k) ?? null, setItem: (k,v) => storage.set(k,v) }
  };
  vm.runInNewContext(source, context);
  return { window, scripts, storage, click: selector => nodes.get(selector).events.click(),
    google: () => scripts.filter(s => s.src.includes('googletagmanager')), reloads: () => reloads };
}
const consent = 'steel-city-analytics-consent-v1';
const exclude = 'steel-city-analytics-excluded';
const fresh = browser();
assert.equal(fresh.google().length, 0, 'Google must not load before consent');
assert.equal(fresh.scripts.length, 1, 'Cookieless Cloudflare remains available');
fresh.click('#analytics-allow');
fresh.click('#analytics-allow');
assert.equal(fresh.google().length, 1, 'Accepting twice must not duplicate the Google tag');
assert.equal(fresh.storage.get(consent), 'granted');
fresh.click('#analytics-reject');
assert.equal(fresh.window['ga-disable-G-HHKGJ1KXP9'], true);
assert.equal(fresh.reloads(), 1, 'Withdrawal must reload to unload the Google script');
const denied = browser({ [consent]: 'denied' });
assert.equal(denied.google().length, 0);
denied.click('#analytics-reject');
denied.click('#analytics-allow');
assert.equal(denied.google().length, 1);
assert.equal(denied.window['ga-disable-G-HHKGJ1KXP9'], false, 'A later acceptance must undo rejection');
const owner = browser({ [consent]: 'granted', [exclude]: 'true' });
assert.equal(owner.scripts.length, 0, 'Owner exclusion must suppress both trackers');
owner.click('#analytics-allow');
assert.equal(owner.scripts.length, 0, 'Consent must not override owner exclusion');
const local = browser({ [consent]: 'granted' }, '127.0.0.1');
assert.equal(local.scripts.length, 0, 'Local testing must not pollute production analytics');
const included = browser({ [consent]: 'granted' });
included.click('#analytics-exclude');
assert.equal(included.storage.get(exclude), 'true');
assert.equal(included.reloads(), 1);
assert.equal(included.window['ga-disable-G-HHKGJ1KXP9'], true);
console.log('Analytics consent, repeat loads, withdrawal, owner exclusion and local-preview checks passed.');
