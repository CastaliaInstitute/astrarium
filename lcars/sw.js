const SHELL = ['./','./index.html','./manifest.webmanifest','./icon.svg','./terrain-projector.html','./terrain-projector.js','./vendor/three.module.js','./vendor/three.core.js','./stars.json','./named-stars.json','./black-holes.json','./quasars.dat','./exoplanets.json','./sounds/click.wav','./sounds/select.wav','./sounds/confirm.wav','./sounds/error.wav'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open('atlas-shell-v70').then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== 'atlas-shell-v70').map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
