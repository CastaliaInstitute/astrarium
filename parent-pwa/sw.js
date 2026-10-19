const SHELL_CACHE = 'atlas-shell-v223';
const OBSERVATION_CACHE = 'atlas-observation-v1';
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon.svg", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png", "./apple-touch-icon.png", "./favicon-32.png", "./favicon-16.png", "./terrain-projector.html", "./terrain-projector.js", "./nebula-volume.js?v=233", "./observations/m16-hst/hubble-wfc3ir-volume.bin.gz?v=2", "./observations/m16-hst/hubble-wfc3ir-mesh-colors.bin.gz?v=1", "./observations/earth-blue-marble.webp", "./observations/m16-jwst/pillars-stsci-mesh.bin.gz?v=207", "./observations/m16-jwst/gaia-dr3-stars.json", "./observations/m16-jwst/gaia-dr3-wide-stars.json", "./sky/planets/mercury.jpg", "./sky/planets/venus.jpg", "./sky/planets/mars.jpg", "./sky/planets/jupiter.jpg", "./sky/planets/saturn.jpg", "./sky/planets/uranus.jpg", "./sky/planets/neptune.jpg", "./sky/planets/metadata.json", "./vendor/three.module.js", "./vendor/three.core.js", "./stars.json", "./hii-regions-dr3.bin.gz", "./named-stars.json", "./black-holes.json", "./quasars.dat", "./exoplanets.json", "./sounds/click.wav", "./sounds/select.wav", "./sounds/confirm.wav", "./sounds/error.wav"];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL_CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== SHELL_CACHE && k !== OBSERVATION_CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(async () => {
      const cache = await caches.open(SHELL_CACHE);
      return (await cache.match('./index.html')) || cache.match('./');
    }));
    return;
  }
  const isObservationAsset = url.pathname.includes('/observations/');
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (isObservationAsset && response.ok) {
          const copy = response.clone();
          e.waitUntil(caches.open(OBSERVATION_CACHE).then(cache => cache.put(e.request, copy)));
        }
        return response;
      });
    })
  );
});
