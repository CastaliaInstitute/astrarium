import * as THREE from '/vendor/three.module.js';

const $ = id => document.getElementById(id);
const world = $('view');
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
world.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x02040a);
const camera = new THREE.PerspectiveCamera(54, innerWidth / innerHeight, 0.02, 1e7);
scene.add(new THREE.HemisphereLight(0x9eb9df, 0x392715, 1.15));
const sun = new THREE.DirectionalLight(0xffdfb1, 2.1);
sun.position.set(-4, 5, 7);
scene.add(sun);

const stars = new THREE.BufferGeometry();
const starPoints = new Float32Array(2100 * 3);
for (let i = 0; i < starPoints.length; i += 3) {
  const radius = 2400 + Math.random() * 5000;
  const a = Math.random() * Math.PI * 2;
  const z = Math.random() * 2 - 1;
  const r = Math.sqrt(1 - z * z);
  starPoints[i] = Math.cos(a) * r * radius;
  starPoints[i + 1] = z * radius;
  starPoints[i + 2] = Math.sin(a) * r * radius;
}
stars.setAttribute('position', new THREE.BufferAttribute(starPoints, 3));
scene.add(new THREE.Points(stars, new THREE.PointsMaterial({ color: 0xc8d7ff, size: 1.5, sizeAttenuation: false })));

const bodies = {
  Mercury: { radiusKm: 2439.7, texture: null, color: 0x9a8a78 },
  Venus: { radiusKm: 6051.8, texture: null, color: 0xc58d50 },
  Earth: { radiusKm: 6371.0, texture: 'earth.png', color: 0x3b77b8 },
  Moon: { radiusKm: 1737.4, texture: 'moon.png', color: 0xaaa9a1 },
  Mars: { radiusKm: 3389.5, texture: 'mars.png', color: 0xc45d37 },
  Jupiter: { radiusKm: 69911, texture: 'jupiter.png', color: 0xc69a69 },
  Io: { radiusKm: 1821.6, texture: null, color: 0xb88856 },
  Saturn: { radiusKm: 58232, texture: 'saturn.png', color: 0xd2b985 },
  Titan: { radiusKm: 2575.0, texture: null, color: 0xc88b53 },
  Uranus: { radiusKm: 25362, texture: null, color: 0x79b9c7 },
  Neptune: { radiusKm: 24622, texture: 'neptune.png', color: 0x416ed5 },
  Ceres: { radiusKm: 470.0, texture: null, color: 0xaaa89f },
  Vesta: { radiusKm: 262.7, texture: null, color: 0xa39c91 },
  Pluto: { radiusKm: 1188.3, texture: null, color: 0x9d8c7d },
  Charon: { radiusKm: 606.0, texture: null, color: 0x8c969b }
};
const TERRAIN_FLYOVER_ALTITUDE_KM = 350;
const textureLoader = new THREE.TextureLoader();
let bodyMesh = null;
let routeLine = null;
let terrainMesh = null;
let probeMarker = null;
let flightPath = null;
let mission = null;
let missionKey = '';
let missionReceivedAt = 0;
let radius = 1;
let scale = 1;
let lowOrbitDistance = 1;
let targetNormal = new THREE.Vector3(0, 0, 1);
let east = new THREE.Vector3(1, 0, 0);
let north = new THREE.Vector3(0, 1, 0);
let surfacePoint = new THREE.Vector3();
let terrainState = 'Terrain model not loaded';
let recordedTrajectory = null;
let terrainRequestKey = '';
let terrainRequestToken = 0;
let lastTerrainRequestAt = 0;
let recordedApproachLine = null;
let solarBodies = [];
const terrainManifestPromises = new Map();
// Constant DE421 principal-axes to mean-Earth transform from NAIF moon_080317.tf.
const moonPaToMe = new THREE.Matrix3().set(
  0.999999873, -0.000329285422, 0.000380869619,
  0.000329286000, 0.999999946, -0.000001454441,
  -0.000380869119, 0.000001579856, 0.999999927
);
let animationFrame = 0;
let flyoverLimit = 0;

function clearBody() {
  for (const object of [bodyMesh, routeLine, recordedApproachLine, terrainMesh, probeMarker, ...solarBodies]) {
    if (object) {
      scene.remove(object);
      object.traverse(child => {
        child.geometry?.dispose();
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        for (const material of materials) { material?.map?.dispose(); material?.dispose(); }
      });
    }
  }
  bodyMesh = routeLine = recordedApproachLine = terrainMesh = probeMarker = null;
  solarBodies = [];
  flightPath = null;
  flyoverLimit = 0;
  terrainRequestKey = '';
  terrainRequestToken++;
}

function setMission(s) {
  const key = s.trajectoryId ? `${s.body}/trajectory/${s.trajectoryId}` : `${s.body}/${s.latitude}/${s.longitude}`;
  if (key === missionKey) { mission = s; missionReceivedAt = performance.now(); return; }
  missionKey = key;
  mission = s;
  missionReceivedAt = performance.now();
  clearBody();
  const data = bodies[s.body] || bodies.Mars;
  radius = 1000;
  scale = radius / data.radiusKm;
  lowOrbitDistance = radius + 100 * scale;
  recordedTrajectory = null;
  const lat = THREE.MathUtils.degToRad(s.latitude || 0);
  const lon = THREE.MathUtils.degToRad(s.longitude || 0);
  targetNormal.set(Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon)).normalize();
  east.set(Math.cos(lon), 0, -Math.sin(lon)).normalize();
  north.crossVectors(targetNormal, east).normalize();
  surfacePoint.copy(targetNormal).multiplyScalar(radius);

  const map = data.texture ? textureLoader.load(`/sky/planets/${data.texture}`, undefined, undefined, () => {
    $('data').textContent = 'Base imagery unavailable; elevation remains source driven.';
  }) : null;
  if (map) map.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshStandardMaterial({ map, color: map ? 0xffffff : data.color, roughness: 1, metalness: 0 });
  bodyMesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 160, 112), material);
  bodyMesh.rotation.y = -Math.PI / 2;
  scene.add(bodyMesh);

  flightPath = new THREE.QuadraticBezierCurve3(
    targetNormal.clone().multiplyScalar(radius * 8),
    targetNormal.clone().multiplyScalar(radius * 4).add(north.clone().multiplyScalar(radius * 1.8)),
    targetNormal.clone().multiplyScalar(lowOrbitDistance)
  );
  const points = flightPath.getPoints(140);
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  routeLine = new THREE.Line(geometry, new THREE.LineDashedMaterial({ color: 0xffb548, dashSize: 18, gapSize: 12, transparent: true, opacity: 0.8 }));
  routeLine.computeLineDistances();
  scene.add(routeLine);
  probeMarker = makeProbeMarker();
  scene.add(probeMarker);
  camera.position.copy(points[0]);
  camera.up.copy(north);
  camera.lookAt(surfacePoint);
  if (s.trajectoryId) {
    loadRecordedTrajectory(s).catch(() => { terrainState = 'Recorded trajectory data unavailable'; });
  } else {
    loadTerrainTile(s).catch(() => { terrainState = 'No installed elevation tiles for this location'; });
  }
}

async function loadRecordedTrajectory(s) {
  terrainState = 'Loading recorded SPICE trajectory…';
  const response = await fetch(`/trajectory-data/${encodeURIComponent(s.trajectoryId)}/trajectory.json`, { cache: 'no-store' });
  if (!response.ok) throw new Error('Trajectory unavailable');
  const data = await response.json();
  if (data.schemaVersion === 2 && data.coordinateFrame === 'J2000_INERTIAL' && data.origin === 'Sun (NAIF 10)' && Array.isArray(data.samples) && data.samples.length > 1) {
    const auScale = 80;
    const points = data.samples.map(sample => ({ et: Number(sample.etSeconds), point: new THREE.Vector3(...sample.positionKm.map(v => v / 149597870.7 * auScale)) }));
    if (points.some(p => !Number.isFinite(p.et) || !p.point.toArray().every(Number.isFinite))) throw new Error('Invalid solar-system trajectory');
    for (let i = 1; i < points.length; i++) if (points[i].et <= points[i - 1].et) throw new Error('Trajectory epochs must increase');
    recordedTrajectory = { data, points, duration: points.at(-1).et - points[0].et, solar: true };
    bodyMesh.visible = false;
    routeLine.visible = false;
    const routePoints = [];
    for (let i = 0; i < points.length; i += 2) routePoints.push(points[i].point);
    if (routePoints.at(-1) !== points.at(-1).point) routePoints.push(points.at(-1).point);
    recordedApproachLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(routePoints), new THREE.LineBasicMaterial({ color: 0xffb548, transparent: true, opacity: 0.72 }));
    scene.add(recordedApproachLine);
    const colors = { Sun: 0xffd37b, Mercury: 0xb7afa4, Venus: 0xdcb779, Earth: 0x4c9cff, Mars: 0xe87955, Jupiter: 0xe6c293 };
    const keys = Object.keys(colors);
    for (const name of keys) {
      let positions = data.samples.map(sample => sample.planetPositionsAu?.[name]).filter(Boolean);
      if (name === 'Sun' && positions.length !== data.samples.length) {
        positions = data.samples.map(() => [0, 0, 0]);
      }
      if (positions.length !== data.samples.length) continue;
      const geo = new THREE.SphereGeometry(name === 'Sun' ? 1.5 : name === 'Jupiter' ? 0.75 : name === 'Earth' ? 0.48 : 0.28, 24, 16);
      const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: colors[name], emissive: name === 'Sun' ? colors[name] : 0x000000, emissiveIntensity: name === 'Sun' ? 0.8 : 0 }));
      mesh.userData.positions = positions.map(p => new THREE.Vector3(p[0] * auScale, p[1] * auScale, p[2] * auScale));
      scene.add(mesh); solarBodies.push(mesh);
    }
    probeMarker.position.copy(points[0].point);
    camera.position.copy(points[0].point).add(new THREE.Vector3(0, 3.5, 7));
    camera.lookAt(points[0].point);
    terrainState = `${data.missionName} · ${data.source.shortName} · ${data.samples.length} inertial SPICE samples`;
    return;
  }
  if (data.schemaVersion === 2 && data.coordinateFrame === 'J2000_INERTIAL' &&
      data.origin === 'Solar System Barycenter (NAIF 0)' && Array.isArray(data.samples) && data.samples.length > 1) {
    const auScale = 80;
    const points = data.samples.map(sample => ({ et: Number(sample.etSeconds), point: new THREE.Vector3(...sample.positionKm.map(v => v / 149597870.7 * auScale)) }));
    if (points.some(p => !Number.isFinite(p.et) || !p.point.toArray().every(Number.isFinite))) throw new Error('Invalid solar-system trajectory');
    for (let i = 1; i < points.length; i++) if (points[i].et <= points[i - 1].et) throw new Error('Trajectory epochs must increase');
    recordedTrajectory = { data, points, duration: points.at(-1).et - points[0].et, solar: true };
    bodyMesh.visible = false;
    routeLine.visible = false;
    const routePoints = [];
    for (let i = 0; i < points.length; i += 2) routePoints.push(points[i].point);
    if (routePoints.at(-1) !== points.at(-1).point) routePoints.push(points.at(-1).point);
    recordedApproachLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(routePoints), new THREE.LineBasicMaterial({ color: 0x7ed8ff, transparent: true, opacity: 0.78 }));
    scene.add(recordedApproachLine);
    const colors = { Sun: 0xffd37b, Mercury: 0xb7afa4, Venus: 0xdcb779, Earth: 0x4c9cff, Mars: 0xe87955, Jupiter: 0xe6c293 };
    for (const [name, color] of Object.entries(colors)) {
      const positions = data.samples.map(sample => sample.planetPositionsAu?.[name]);
      if (positions.some(p => !Array.isArray(p) || p.length !== 3 || !p.every(Number.isFinite))) continue;
      const geo = new THREE.SphereGeometry(name === 'Sun' ? 1.5 : name === 'Jupiter' ? 0.75 : name === 'Earth' ? 0.48 : 0.28, 24, 16);
      const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, emissive: name === 'Sun' ? color : 0x000000, emissiveIntensity: name === 'Sun' ? 0.8 : 0 }));
      mesh.userData.positions = positions.map(p => new THREE.Vector3(p[0] * auScale, p[1] * auScale, p[2] * auScale));
      scene.add(mesh); solarBodies.push(mesh);
    }
    probeMarker.position.copy(points[0].point);
    camera.position.copy(points[0].point).add(new THREE.Vector3(0, 3.5, 7));
    camera.lookAt(points[0].point);
    terrainState = `${data.missionName} · ${data.source.shortName} · ${data.samples.length} barycentric SPICE samples`;
    return;
  }
  if (data.schemaVersion !== 1 || data.body !== s.body || data.coordinateFrame !== 'IAU_BODY_FIXED' ||
      data.coordinateType !== 'PLANETOCENTRIC latitude and east longitude' ||
      !Array.isArray(data.samples) || data.samples.length < 2) throw new Error('Unsupported trajectory schema');
  const points = data.samples.map(sample => {
    const lat = Number(sample.latitudeDeg), lon = Number(sample.longitudeDeg), alt = Number(sample.altitudeKm);
    if (![lat, lon, alt, Number(sample.etSeconds)].every(Number.isFinite) || lat < -90 || lat > 90 || lon < -180 || lon > 180 || radius + alt * scale <= 0) throw new Error('Invalid trajectory sample');
    const phi = THREE.MathUtils.degToRad(lat), lam = THREE.MathUtils.degToRad(lon);
    const normal = new THREE.Vector3(Math.cos(phi) * Math.sin(lam), Math.sin(phi), Math.cos(phi) * Math.cos(lam));
    return { point: normal.clone().multiplyScalar(radius + alt * scale), normal, et: Number(sample.etSeconds), lat, lon, alt };
  });
  for (let i = 1; i < points.length; i++) if (points[i].et <= points[i - 1].et) throw new Error('Trajectory epochs must increase');
  recordedTrajectory = { data, points, duration: points.at(-1).et - points[0].et };
  const routePoints = [];
  for (let i = 0; i < points.length - 1; i++) {
    for (let part = 0; part < 4; part++) routePoints.push(interpolateTrajectoryPoint(points[i], points[i + 1], part / 4));
  }
  routePoints.push(points.at(-1).point);
  routeLine.geometry.dispose();
  routeLine.geometry = new THREE.BufferGeometry().setFromPoints(routePoints);
  routeLine.computeLineDistances();
  mission.latitude = points[0].lat;
  mission.longitude = points[0].lon;
  const firstLat = THREE.MathUtils.degToRad(points[0].lat), firstLon = THREE.MathUtils.degToRad(points[0].lon);
  targetNormal.set(Math.cos(firstLat) * Math.sin(firstLon), Math.sin(firstLat), Math.cos(firstLat) * Math.cos(firstLon)).normalize();
  east.set(Math.cos(firstLon), 0, -Math.sin(firstLon)).normalize();
  north.crossVectors(targetNormal, east).normalize();
  surfacePoint.copy(targetNormal).multiplyScalar(radius);
  // Reuse the same full approach arc, but make its endpoint the first recorded
  // ephemeris point so the camera can begin outside the body and meet the probe.
  const first = points[0];
  const firstNormal = first.point.clone().normalize();
  flightPath = new THREE.QuadraticBezierCurve3(
    firstNormal.clone().multiplyScalar(radius * 8),
    firstNormal.clone().multiplyScalar(radius * 4).add(north.clone().multiplyScalar(radius * 1.8)),
    first.point.clone()
  );
  const approachPoints = flightPath.getPoints(140);
  recordedApproachLine = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(approachPoints),
    new THREE.LineDashedMaterial({ color: 0xffb548, dashSize: 18, gapSize: 12, transparent: true, opacity: 0.8 })
  );
  recordedApproachLine.computeLineDistances();
  scene.add(recordedApproachLine);
  camera.position.copy(approachPoints[0]);
  camera.lookAt(surfacePoint);
  terrainState = `${data.missionName} · ${data.source.shortName} · ${data.samples.length} SPICE samples`;
}

async function updateTrajectoryTerrain(sample) {
  if (!mission || !recordedTrajectory) return;
  if (sample.alt > TERRAIN_FLYOVER_ALTITUDE_KM) return;
  const now = performance.now();
  if (now - lastTerrainRequestAt < 120) return;
  lastTerrainRequestAt = now;
  try {
    const manifest = await getTerrainManifest(mission.body);
    const covering = (manifest.layers || []).filter(layer => {
      const b = layer.coverageLonLat;
      return b && longitudeInBounds(sample.lon, b) && sample.lat >= b[1] && sample.lat <= b[3];
    }).sort((a, b) => b.maxLevel - a.maxLevel);
    const fallbackLevel = mission.body === 'Mars' ? 7 : ['Mercury', 'Ceres', 'Vesta', 'Pluto', 'Charon'].includes(mission.body) ? 6 : mission.body === 'Titan' ? 4 : 9;
    const tileLevel = covering[0]?.maxLevel ?? fallbackLevel;
    const tile = covering[0]?.tileScheme === 'projected-square'
      ? projectedTileFor(sample.lat, sample.lon, tileLevel, covering[0])
      : tileFor(sample.lat, sample.lon, tileLevel);
    const key = `${mission.body}/${tile.x}/${tile.y}/${tileLevel}`;
    if (key === terrainRequestKey) return;
    terrainRequestKey = key;
  } catch {
    terrainState = 'Terrain product catalog unavailable at current trajectory position';
    return;
  }
  const requestToken = ++terrainRequestToken;
  loadTerrainTileAt(sample.lat, sample.lon, mission.body, requestToken).catch(() => {
    if (requestToken === terrainRequestToken) {
      clearTerrainMesh();
      terrainState = 'Terrain data unavailable at current trajectory position';
    }
  });
}

function clearTerrainMesh() {
  if (!terrainMesh) return;
  scene.remove(terrainMesh);
  terrainMesh.geometry.dispose();
  terrainMesh.material.dispose();
  terrainMesh = null;
}

function interpolateTrajectoryPoint(a, b, fraction) {
  const normal = a.normal.clone().lerp(b.normal, fraction).normalize();
  const altitude = a.alt + (b.alt - a.alt) * fraction;
  return normal.multiplyScalar(radius + altitude * scale);
}

function makeProbeMarker() {
  const probe = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, 0.34), new THREE.MeshStandardMaterial({ color: 0xd8d5cc, metalness: 0.55, roughness: 0.4 }));
  probe.add(body);
  const panelMaterial = new THREE.MeshStandardMaterial({ color: 0x3877b5, metalness: 0.25, roughness: 0.6, emissive: 0x10294a });
  for (const side of [-1, 1]) {
    const panel = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.018, 0.2), panelMaterial);
    panel.position.x = side * 0.34;
    probe.add(panel);
  }
  const dish = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.12, 14), new THREE.MeshStandardMaterial({ color: 0xffc86e, metalness: 0.6, roughness: 0.35 }));
  dish.position.z = -0.23;
  dish.rotation.x = Math.PI;
  probe.add(dish);
  return probe;
}

function tileFor(lat, lon, z) {
  const w = 2 ** (z + 1), h = 2 ** z;
  const x = Math.max(0, Math.min(w - 1, Math.floor((lon + 180) / 360 * w)));
  const y = Math.max(0, Math.min(h - 1, Math.floor((90 - lat) / 180 * h)));
  return { x, y, w, h };
}

function longitudeInBounds(longitude, bounds) {
  return bounds[0] <= bounds[2]
    ? longitude >= bounds[0] && longitude <= bounds[2]
    : longitude >= bounds[0] || longitude <= bounds[2];
}

function projectedTileFor(lat, lon, z, layer) {
  const config = layer.projection;
  const radius = Number(config.radiusKm) * 1000;
  const rho = 2 * radius * Math.tan(Math.PI / 4 + THREE.MathUtils.degToRad(lat) / 2);
  const longitude = THREE.MathUtils.degToRad(lon - Number(config.centralMeridianDeg || 0));
  const xMeters = rho * Math.sin(longitude), yMeters = rho * Math.cos(longitude);
  const [left, bottom, right, top] = config.projectedBoundsMeters;
  const n = 2 ** z, span = (right - left) / n;
  const x = Math.max(0, Math.min(n - 1, Math.floor((xMeters - left) / span)));
  const y = Math.max(0, Math.min(n - 1, Math.floor((top - yMeters) / span)));
  return { x, y, w: n, h: n, span, bounds: [left + x * span, top - (y + 1) * span, left + (x + 1) * span, top - y * span] };
}

async function loadTerrainTile(s) {
  terrainRequestKey = '';
  await loadTerrainTileAt(s.latitude, s.longitude, s.body);
}

async function getTerrainManifest(body) {
  const slug = body.toLowerCase().replaceAll(' ', '-');
  if (!terrainManifestPromises.has(slug)) {
    terrainManifestPromises.set(slug, fetch(`/terrain-data/${slug}/manifest.json`, { cache: 'no-store' })
      .then(response => { if (!response.ok) throw new Error('No terrain manifest'); return response.json(); })
      .catch(error => { terrainManifestPromises.delete(slug); throw error; }));
  }
  return terrainManifestPromises.get(slug);
}

async function loadTerrainTileAt(latitude, longitude, body, requestToken = ++terrainRequestToken, maxLevelOverride = null) {
  terrainState = 'Checking installed elevation products…';
  const slug = body.toLowerCase().replaceAll(' ', '-');
  const manifest = await getTerrainManifest(body);
  const layers = (manifest.layers || []).filter(layer => {
    const b = layer.coverageLonLat;
    return b && longitudeInBounds(longitude, b) && latitude >= b[1] && latitude <= b[3];
  }).sort((a, b) => b.maxLevel - a.maxLevel);
  for (const layer of layers) {
    for (let z = Math.min(layer.maxLevel, maxLevelOverride ?? layer.maxLevel); z >= layer.minLevel; z--) {
      const tile = layer.tileScheme === 'projected-square'
        ? projectedTileFor(latitude, longitude, z, layer)
        : tileFor(latitude, longitude, z);
      const url = `/terrain-data/${slug}/${layer.urlTemplate.replace('{z}', z).replace('{x}', tile.x).replace('{y}', tile.y)}`;
      const r = await fetch(url);
      if (!r.ok) continue;
      const buffer = await r.arrayBuffer();
      const sampleBytes = layer.sampleType === 'int16' ? 2 : 4;
      if (buffer.byteLength !== 256 * 256 * sampleBytes) continue;
      let heights;
      if (layer.sampleType === 'int16') {
        const samples = new Int16Array(buffer);
        heights = new Float32Array(samples.length);
        const scale = Number(layer.sampleScale ?? 1), offset = Number(layer.sampleOffset ?? 0);
        for (let i = 0; i < samples.length; i++) heights[i] = samples[i] === layer.sampleNoData ? NaN : samples[i] * scale + offset;
      } else {
        heights = new Float32Array(buffer);
      }
      if (!heights.some(Number.isFinite)) continue;
      if (requestToken !== terrainRequestToken) return;
      const selected = { body, latitude, longitude };
      const nextMesh = layer.tileScheme === 'projected-square'
        ? makeProjectedTerrainPatch(heights, tile, z, selected, layer)
        : makeTerrainPatch(heights, tile, z, selected, layer);
      clearTerrainMesh();
      terrainMesh = nextMesh;
      if (layer.tileScheme === 'projected-square') {
        flyoverLimit = tile.span / 1000 * 0.8 * scale;
        mission.flyoverSign = 1;
      } else {
        const rowPosition = (90 - latitude) / 180 * tile.h - tile.y;
        const northKm = rowPosition * (Math.PI / 180) * (180 / tile.h) * bodyRadiusKm(body);
        const southKm = (1 - rowPosition) * (Math.PI / 180) * (180 / tile.h) * bodyRadiusKm(body);
        flyoverLimit = Math.max(0, Math.max(northKm, southKm) * 0.8 * scale);
        mission.flyoverSign = northKm >= southKm ? 1 : -1;
      }
      scene.add(terrainMesh);
      terrainState = `${layer.name} · ${layer.verticalDatum} · level ${z}`;
      return;
    }
  }
  if (requestToken === terrainRequestToken) {
    clearTerrainMesh();
    terrainState = 'No installed elevation tiles cover this trajectory position';
  }
  throw new Error('No elevation tile covers the selected coordinates');
}

function bodyRadiusKm(body) { return (bodies[body] || bodies.Mars).radiusKm; }

function makeTerrainPatch(heights, tile, z, s, layer) {
  const width = tile.w, height = tile.h;
  const west = -180 + 360 * tile.x / width;
  const eastLon = -180 + 360 * (tile.x + 1) / width;
  const northLat = 90 - 180 * tile.y / height;
  const southLat = 90 - 180 * (tile.y + 1) / height;
  return makeTerrainMesh(heights, s, layer, (px, py) => {
    const lat = THREE.MathUtils.degToRad(northLat + (southLat - northLat) * py / 255);
    const lon = THREE.MathUtils.degToRad(west + (eastLon - west) * px / 255);
    return new THREE.Vector3(Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon));
  });
}

function makeProjectedTerrainPatch(heights, tile, z, s, layer) {
  const [left, bottom, right, top] = tile.bounds;
  const projectionRadius = Number(layer.projection.radiusKm) * 1000;
  return makeTerrainMesh(heights, s, layer, (px, py) => {
    const x = left + (right - left) * px / 255;
    const y = top - (top - bottom) * py / 255;
    const longitude = Math.atan2(x, y);
    const latitude = -Math.PI / 2 + 2 * Math.atan2(Math.hypot(x, y), 2 * projectionRadius);
    return new THREE.Vector3(Math.cos(latitude) * Math.sin(longitude), Math.sin(latitude), Math.cos(latitude) * Math.cos(longitude));
  });
}

function makeTerrainMesh(heights, s, layer, normalAt) {
  const positions = new Float32Array(256 * 256 * 3);
  const colors = new Float32Array(256 * 256 * 3);
  const color = new THREE.Color();
  const terrainTint = ({ Mars: [0.60, 0.48, 0.30], Moon: [0.58, 0.59, 0.62], Mercury: [0.58, 0.55, 0.49], Ceres: [0.50, 0.49, 0.47], Vesta: [0.55, 0.51, 0.46] })[s.body] || [0.64, 0.53, 0.39];
  for (let py = 0; py < 256; py++) for (let px = 0; px < 256; px++) {
    const i = py * 256 + px;
    const h = heights[i];
    const referenceOffsetKm = (Number(layer.referenceRadiusKm) || bodyRadiusKm(s.body)) - bodyRadiusKm(s.body);
    const heightRadius = radius + (referenceOffsetKm + (Number.isFinite(h) ? h / 1000 : 0)) * scale;
    const normal = normalAt(px, py);
    if (s.body === 'Moon' && layer.coordinateFrame === 'MOON_PA_DE421') normal.applyMatrix3(moonPaToMe).normalize();
    positions[i * 3] = normal.x * heightRadius;
    positions[i * 3 + 1] = normal.y * heightRadius;
    positions[i * 3 + 2] = normal.z * heightRadius;
    const shade = Number.isFinite(h) ? THREE.MathUtils.clamp(0.42 + h / 12000, 0.12, 0.95) : 0.03;
    color.setRGB(terrainTint[0] * shade, terrainTint[1] * shade, terrainTint[2] * shade);
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }
  const indices = [];
  for (let y = 0; y < 255; y++) for (let x = 0; x < 255; x++) {
    const a = y * 256 + x, b = a + 1, c = a + 256, d = c + 1;
    if (Number.isFinite(heights[a]) && Number.isFinite(heights[b]) &&
        Number.isFinite(heights[c]) && Number.isFinite(heights[d])) indices.push(a, c, b, b, c, d);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  const material = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, side: THREE.DoubleSide });
  return new THREE.Mesh(geometry, material);
}

function animate() {
  animationFrame = 0;
  if (!mission?.running) {
    renderer.render(scene, camera);
    return;
  }
  const elapsed = mission.elapsedMs + (mission.paused ? 0 : performance.now() - missionReceivedAt);
  const approachSeconds = 32;
  const descentSeconds = 16;
  const t = Math.max(0, elapsed / 1000);
  if (recordedTrajectory) {
    const samples = recordedTrajectory.points;
    if (recordedTrajectory.solar) {
      const replaySeconds = 240;
      const replayT = Math.max(0, t);
      const progress = Math.min(recordedTrajectory.duration, replayT / replaySeconds * recordedTrajectory.duration);
      let index = 0;
      while (index < samples.length - 2 && samples[index + 1].et < samples[0].et + progress) index++;
      const a = samples[index], b = samples[index + 1];
      const fraction = THREE.MathUtils.clamp((samples[0].et + progress - a.et) / (b.et - a.et), 0, 1);
      probeMarker.position.copy(a.point).lerp(b.point, fraction);
      const tangent = b.point.clone().sub(a.point).normalize();
      probeMarker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent);
      for (const mesh of solarBodies) {
        const positions = mesh.userData.positions;
        mesh.position.copy(positions[index]).lerp(positions[index + 1], fraction);
      }
      camera.position.copy(probeMarker.position).addScaledVector(tangent, -5).add(new THREE.Vector3(0, 2.5, 0));
      camera.up.set(0, 1, 0);
      camera.lookAt(probeMarker.position.clone().addScaledVector(tangent, 2));
      $('phase').textContent = replayT >= replaySeconds ? `RECORDED ${recordedTrajectory.data.missionName.toUpperCase()} · END OF TRACK` : `RECORDED ${recordedTrajectory.data.missionName.toUpperCase()} · CRUISE`;
      $('coords').textContent = `${(progress / 86400).toFixed(0)} mission days · heliocentric J2000`;
      $('data').textContent = `${terrainState} · ${recordedTrajectory.data.source.citation}`;
      renderer.render(scene, camera);
      animationFrame = requestAnimationFrame(animate);
      return;
    }
    const approachSeconds = 32;
    const replaySeconds = 240;
    if (t < approachSeconds) {
      const p = t / approachSeconds;
      const smooth = p * p * (3 - 2 * p);
      probeMarker.position.copy(flightPath.getPoint(smooth));
      const tangent = flightPath.getTangent(smooth).normalize();
      probeMarker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent);
      camera.position.copy(probeMarker.position).addScaledVector(tangent, -radius * 0.06);
      camera.up.copy(north);
      camera.lookAt(surfacePoint);
      $('phase').textContent = `RECORDED ${recordedTrajectory.data.missionName.toUpperCase()} · APPROACH`;
      $('coords').textContent = 'Interplanetary approach';
      $('data').textContent = `${terrainState} · ${recordedTrajectory.data.source.citation}`;
      renderer.render(scene, camera);
      animationFrame = requestAnimationFrame(animate);
      return;
    }
    const replayT = Math.max(0, t - approachSeconds);
    const progress = Math.min(recordedTrajectory.duration, replayT / replaySeconds * recordedTrajectory.duration);
    let index = 0;
    while (index < samples.length - 2 && samples[index + 1].et < samples[0].et + progress) index++;
    const a = samples[index], b = samples[index + 1];
    const fraction = THREE.MathUtils.clamp((samples[0].et + progress - a.et) / (b.et - a.et), 0, 1);
    probeMarker.position.copy(interpolateTrajectoryPoint(a, b, fraction));
    const tangent = b.point.clone().sub(a.point).normalize();
    probeMarker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent);
    const radial = probeMarker.position.clone().normalize();
    camera.position.copy(probeMarker.position).addScaledVector(tangent, -Math.max(radius * 0.003, 12));
    camera.up.copy(radial);
    camera.lookAt(probeMarker.position.clone().addScaledVector(tangent, Math.max(radius * 0.01, 30)));
    const normal = probeMarker.position.clone().normalize();
    const sample = { lat: THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(normal.y, -1, 1))),
      lon: THREE.MathUtils.radToDeg(Math.atan2(normal.x, normal.z)),
      alt: a.alt + (b.alt - a.alt) * fraction };
    updateTrajectoryTerrain(sample);
    const surfaceApproach = sample.alt <= TERRAIN_FLYOVER_ALTITUDE_KM && terrainMesh;
    if (surfaceApproach) {
      const terrainPoint = new THREE.Vector3(
        Math.cos(THREE.MathUtils.degToRad(sample.lat)) * Math.sin(THREE.MathUtils.degToRad(sample.lon)),
        Math.sin(THREE.MathUtils.degToRad(sample.lat)),
        Math.cos(THREE.MathUtils.degToRad(sample.lat)) * Math.cos(THREE.MathUtils.degToRad(sample.lon))
      ).multiplyScalar(radius + sample.alt * scale);
      const tangent = b.point.clone().sub(a.point).normalize();
      camera.position.copy(terrainPoint).addScaledVector(tangent, -Math.max(radius * 0.0007, 3));
      camera.up.copy(terrainPoint).normalize();
      camera.lookAt(terrainPoint.clone().addScaledVector(tangent, Math.max(radius * 0.0012, 6)));
    }
    const trajectoryLabel = recordedTrajectory.data.missionName.toUpperCase();
    $('phase').textContent = replayT > replaySeconds
      ? `RECORDED ${trajectoryLabel} · COMPLETE`
      : sample.alt <= 30 && terrainMesh
        ? `RECORDED ${trajectoryLabel} · CLOSE TERRAIN PASS`
        : sample.alt <= TERRAIN_FLYOVER_ALTITUDE_KM && terrainMesh
          ? `RECORDED ${trajectoryLabel} · ORBITAL TERRAIN PASS`
          : `RECORDED ${trajectoryLabel} TRAJECTORY`;
    $('coords').textContent = `${sample.lat.toFixed(3)}° · ${sample.lon.toFixed(3)}° · ${sample.alt.toFixed(1)} km`;
    $('data').textContent = `${terrainState} · ${recordedTrajectory.data.source.citation}`;
    renderer.render(scene, camera);
    animationFrame = requestAnimationFrame(animate);
    return;
  }
  let distance;
  if (t < approachSeconds) {
    const p = t / approachSeconds;
    const progress = p * p * (3 - 2 * p);
    probeMarker.position.copy(flightPath.getPoint(progress));
    const tangent = flightPath.getTangent(progress).normalize();
    probeMarker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent);
    camera.position.copy(probeMarker.position).addScaledVector(tangent, -radius * 0.06).addScaledVector(targetNormal, radius * 0.015);
    camera.up.copy(north);
    camera.lookAt(surfacePoint);
    distance = probeMarker.position.length();
    $('phase').textContent = `INTERPLANETARY APPROACH · ${(distance / radius).toFixed(2)} body radii`;
    $('coords').textContent = `${mission.latitude.toFixed(4)}° · ${mission.longitude.toFixed(4)}°`;
    $('data').textContent = `Planned direct approach · schematic probe marker · ${terrainState}`;
    renderer.render(scene, camera);
    animationFrame = requestAnimationFrame(animate);
    return;
  } else if (t < approachSeconds + descentSeconds && terrainMesh) {
    const p = (t - approachSeconds) / descentSeconds;
    distance = radius + (100 - 8 * p) * scale;
    probeMarker.position.copy(targetNormal).multiplyScalar(distance);
    probeMarker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), targetNormal.clone().negate());
    $('phase').textContent = `ATMOSPHERIC DESCENT · ${(100 - 92 * p).toFixed(1)} km AGL`;
  } else if (terrainMesh) {
    const drift = Math.min(flyoverLimit, (t - approachSeconds - descentSeconds) * 0.35 * scale) * (mission.flyoverSign || 1);
    distance = radius + 8 * scale;
    probeMarker.position.copy(targetNormal).multiplyScalar(distance).add(north.clone().multiplyScalar(drift));
    probeMarker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), north.clone().multiplyScalar(mission.flyoverSign || 1));
    $('phase').textContent = `LOW ALTITUDE TERRAIN PASS · ${(8).toFixed(1)} km AGL`;
    const chaseOffset = radius * 0.0008;
    camera.position.copy(targetNormal).multiplyScalar(distance + chaseOffset)
      .add(north.clone().multiplyScalar(drift - (mission.flyoverSign || 1) * chaseOffset));
    camera.up.copy(north);
    const lookAhead = Math.min(10 * scale, flyoverLimit * 0.5);
    camera.lookAt(surfacePoint.clone().add(north.clone().multiplyScalar(drift + (mission.flyoverSign || 1) * lookAhead)));
    $('data').textContent = terrainState;
    $('coords').textContent = `${mission.latitude.toFixed(4)}° · ${mission.longitude.toFixed(4)}°`;
    renderer.render(scene, camera);
    animationFrame = requestAnimationFrame(animate);
    return;
  } else {
    distance = lowOrbitDistance;
    probeMarker.position.copy(targetNormal).multiplyScalar(distance);
    probeMarker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), targetNormal.clone().negate());
    $('phase').textContent = 'LOW ORBIT · ELEVATION MODEL REQUIRED FOR SURFACE PASS';
  }
  camera.position.copy(targetNormal).multiplyScalar(distance + radius * 0.0008);
  camera.up.copy(north);
  camera.lookAt(surfacePoint);
  $('coords').textContent = `${mission.latitude.toFixed(4)}° · ${mission.longitude.toFixed(4)}°`;
  $('data').textContent = terrainState;
  renderer.render(scene, camera);
  animationFrame = requestAnimationFrame(animate);
}

async function poll() {
  try {
    const r = await fetch('/api/terrain', { cache: 'no-store' });
    if (r.ok) {
      const s = await r.json();
      if (s.running) {
        setMission(s);
        $('title').textContent = `${s.body} · ${s.destination || 'Probe approach'}`;
        if (!animationFrame) animationFrame = requestAnimationFrame(animate);
      } else {
        mission = null;
        missionKey = '';
        if (animationFrame) cancelAnimationFrame(animationFrame);
        animationFrame = 0;
        $('title').textContent = 'Awaiting mission';
        $('phase').textContent = '—';
        $('coords').textContent = '—';
        $('data').textContent = 'Three.js projector renderer ready';
        clearBody();
        camera.position.set(0, 0, 2400);
        camera.lookAt(0, 0, 0);
        renderer.render(scene, camera);
      }
    }
  } catch (_) { $('data').textContent = 'Projector mission link unavailable'; }
  setTimeout(poll, 1000);
}

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
camera.position.set(0, 0, 2400);
camera.lookAt(0, 0, 0);
renderer.render(scene, camera);
poll();
