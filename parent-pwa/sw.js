const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon.svg", "./terrain-projector.html", "./terrain-projector.js", "./nebula-volume.js", "./vendor/three.module.js", "./vendor/three.core.js", "./stars.json", "./hii-regions-dr3.bin.gz", "./named-stars.json", "./black-holes.json", "./quasars.dat", "./exoplanets.json", "./sounds/click.wav", "./sounds/select.wav", "./sounds/confirm.wav", "./sounds/error.wav"];

self.addEventListener('install', e => {
  e.waitUntil(caches.open('atlas-shell-v187').then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== 'atlas-shell-v187' && k !== 'atlas-observation-v1').map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;
  const isObservationAsset = url.pathname.includes('/observations/');
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (isObservationAsset && response.ok) {
          const copy = response.clone();
          e.waitUntil(caches.open('atlas-observation-v1').then(cache => cache.put(e.request, copy)));
        }
        return response;
      });
    })
  );
});
