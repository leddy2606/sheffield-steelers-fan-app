const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
for (const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
  if (match[1].trim()) new Function(match[1]);
}
const helperLines = html
  .split(/\r?\n/)
  .filter(line => /^    const safe(?:Url|EmbedUrl)?=/.test(line))
  .map(line => line.trim())
  .join('\n');

assert.equal(helperLines.split(/\r?\n/).length, 3, 'Expected all three rendering helpers');

const context = { URL, location: { origin: 'https://steelcityhockey.app' } };
vm.runInNewContext(`${helperLines}\nthis.results = {
  html: safe('<img src=x onerror=alert(1)>'),
  scriptUrl: safeUrl('javascript:alert(1)'),
  dataUrl: safeUrl('data:text/html,<script>alert(1)</script>'),
  plainHttp: safeUrl('http://example.com/'),
  https: safeUrl('https://www.eliteleague.co.uk/fixtures?a=1&b=2'),
  hostileEmbed: safeEmbedUrl('https://attacker.example/embed/1'),
  youtubeEmbed: safeEmbedUrl('https://www.youtube.com/embed/abc123')
};`, context);

assert.equal(context.results.html, '&lt;img src=x onerror=alert(1)&gt;');
assert.equal(context.results.scriptUrl, '#');
assert.equal(context.results.dataUrl, '#');
assert.equal(context.results.plainHttp, '#');
assert.equal(context.results.https, 'https://www.eliteleague.co.uk/fixtures?a=1&amp;b=2');
assert.equal(context.results.hostileEmbed, '');
assert.equal(context.results.youtubeEmbed, 'https://www.youtube.com/embed/abc123');

for (const pattern of [
  '${r.team}',
  '${p.name}</span>',
  'href="${safe(item.url)}"',
  'href="${g.details_url}"',
  'href="${safe(g.ticket_url)}"'
]) {
  assert.equal(html.includes(pattern), false, `Unsafe rendering pattern remains: ${pattern}`);
}

console.log('External data rendering security checks passed.');
