import * as THREE from './vendor/three.module.js';

const observationHost = ['localhost', '127.0.0.1'].includes(location.hostname)
  ? `${location.origin}/`
  : 'https://astrarium.castalia.institute/lcars/';
const HST_IR_PROJECTION_URL = new URL('observations/m16-hst/hubble-wfc3ir-volume.bin.gz?v=3', observationHost).href;
const SKY_CATALOG_URL = new URL('stars.json', observationHost).href;
const M16_GAIA_URL = new URL('observations/m16-jwst/gaia-dr3-wide-stars.json', observationHost).href;
const EARTH_MAP_URL = new URL('observations/earth-blue-marble.webp', observationHost).href;
// World coordinates in this view are light-years from Earth's position. NASA
// gives the Pillars a nominal Earth distance of 6,500 ly. The image field is
// placed at that distance as an observation plane; its depth is not measured.
const M16_DISTANCE_LY = 6500;
const M16_FIELD_WIDTH_ARCSEC = 260;
const M16_FIELD_HEIGHT_ARCSEC = 243.0415;
const M16_POSITION_ANGLE_DEG = 35.1;
const KILOMETERS_PER_LIGHT_YEAR = 9.460730472e12;
const EARTH_RADIUS_LY = 6371 / KILOMETERS_PER_LIGHT_YEAR;
const EARTH_ORBIT_START_Y_LY = (6371 + 250) / KILOMETERS_PER_LIGHT_YEAR;

async function loadHubbleIRProjection() {
  const response = await fetch(HST_IR_PROJECTION_URL);
  if (!response.ok) throw new Error(`Hubble WFC3/IR projection unavailable (${response.status})`);
  if (!('DecompressionStream' in window)) throw new Error('This browser cannot decompress Hubble infrared points');
  const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
  const bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  if (new TextDecoder().decode(bytes.subarray(0, 8)) !== 'ASTIR1\0\0') throw new Error('Hubble infrared projection has an unknown format');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const count = view.getUint32(8, true), stride = 10;
  if (bytes.byteLength < 12 + count * stride) throw new Error('Hubble infrared projection is truncated');
  const decodedPositions = new Float32Array(count * 3), decodedColors = new Float32Array(count * 3), indexes = [];
  const fieldWidthLy = 2 * M16_DISTANCE_LY * Math.tan(THREE.MathUtils.degToRad(M16_FIELD_WIDTH_ARCSEC / 7200));
  const fieldHeightLy = 2 * M16_DISTANCE_LY * Math.tan(THREE.MathUtils.degToRad(M16_FIELD_HEIGHT_ARCSEC / 7200));
  const color = new THREE.Color();
  for (let i = 0, offset = 12; i < count; i++, offset += stride) {
    const x = view.getUint16(offset, true) / 65535;
    const y = view.getUint16(offset + 2, true) / 65535;
    const code = bytes[offset + 9];
    if (code & 0x80) continue; // These detected sources have no measured Gaia distance here.
    // Diffuse Hubble signal is projected onto the observed field at M16's
    // nominal distance. No source data supplies its line-of-sight gas depth.
    decodedPositions[i * 3] = (x - 0.5) * fieldWidthLy;
    decodedPositions[i * 3 + 1] = (0.5 - y) * fieldHeightLy;
    decodedPositions[i * 3 + 2] = M16_DISTANCE_LY;
    color.setRGB(bytes[offset + 6] / 255, bytes[offset + 7] / 255, bytes[offset + 8] / 255, THREE.SRGBColorSpace);
    decodedColors[i * 3] = color.r; decodedColors[i * 3 + 1] = color.g; decodedColors[i * 3 + 2] = color.b;
    indexes.push(i);
  }
  const makeLayer = entries => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(entries.length * 3), colors = new Float32Array(entries.length * 3);
    for (let j = 0; j < entries.length; j++) {
      const i = entries[j];
      positions.set(decodedPositions.subarray(i * 3, i * 3 + 3), j * 3);
      colors.set(decodedColors.subarray(i * 3, i * 3 + 3), j * 3);
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    // Each sample spans two source pixels. PointsMaterial's perspective size
    // attenuation preserves that transverse physical pixel scale throughout
    // the camera route, while Three.js supplies its supported depth shader.
    const material = new THREE.PointsMaterial({
      color: 0xffffff, size: fieldWidthLy * 2 / 1800, sizeAttenuation: true,
      transparent: true, opacity: 0.96, depthWrite: true, vertexColors: true, toneMapped: false
    });
    const points = new THREE.Points(geometry, material);
    points.frustumCulled = false; points.renderOrder = 1;
    return { points, geometry, material, count: entries.length };
  };
  return makeLayer(indexes);
}

async function loadParallaxStars() {
  const [catalogResponse, gaiaResponse] = await Promise.all([fetch(SKY_CATALOG_URL), fetch(M16_GAIA_URL)]);
  if (!catalogResponse.ok) throw new Error(`Astrarium star catalog unavailable (${catalogResponse.status})`);
  if (!gaiaResponse.ok) throw new Error(`M16 Gaia DR3 sources unavailable (${gaiaResponse.status})`);
  const [{ stars = [] }, gaia = {}] = await Promise.all([catalogResponse.json(), gaiaResponse.json()]);
  const centerRa = THREE.MathUtils.degToRad(274.7170416667);
  const centerDec = THREE.MathUtils.degToRad(-13.8347916667);
  const imageHalfWidthDeg = M16_FIELD_WIDTH_ARCSEC / 7200, imageHalfHeightDeg = M16_FIELD_HEIGHT_ARCSEC / 7200;
  const imagePositionAngle = THREE.MathUtils.degToRad(M16_POSITION_ANGLE_DEG);
  const catalogStars = stars.filter(star => star.length > 6 && Number.isFinite(Number(star[6])) && Number(star[6]) > 0)
    .map(star => ({ ra: Number(star[0]), dec: Number(star[1]), magnitude: Number(star[2]), colorIndex: Number(star[3]), distancePc: Number(star[6]) }));
  const centerDecDegrees = -13.8347916667;
  const gaiaStars = (gaia.stars || []).filter(star => {
    if (!(Number(star.parallax_mas) > 0)) return false;
    const ra = THREE.MathUtils.degToRad(Number(star.ra_deg));
    const dec = THREE.MathUtils.degToRad(Number(star.dec_deg));
    const dra = THREE.MathUtils.euclideanModulo(ra - centerRa + Math.PI, Math.PI * 2) - Math.PI;
    const cosc = Math.sin(centerDec) * Math.sin(dec) + Math.cos(centerDec) * Math.cos(dec) * Math.cos(dra);
    if (cosc <= 0) return false;
    const eastDeg = Math.cos(dec) * Math.sin(dra) / cosc * 180 / Math.PI;
    const northDeg = (Math.cos(centerDec) * Math.sin(dec) - Math.sin(centerDec) * Math.cos(dec) * Math.cos(dra)) / cosc * 180 / Math.PI;
    const imageX = eastDeg * Math.cos(imagePositionAngle) + northDeg * Math.sin(imagePositionAngle);
    const imageY = -eastDeg * Math.sin(imagePositionAngle) + northDeg * Math.cos(imagePositionAngle);
    return Math.abs(imageX) <= imageHalfWidthDeg && Math.abs(imageY) <= imageHalfHeightDeg;
  })
    .map(star => ({
      ra: Number(star.ra_deg) / 15, dec: Number(star.dec_deg), magnitude: Number(star.g_mag),
      colorIndex: Number.isFinite(Number(star.bp_rp)) ? Number(star.bp_rp) - 0.2 : 0.7,
      distancePc: 1000 / Number(star.parallax_mas), localGaia: true
    }));
  // Keep catalog stars across the full field. Gaia entries replace only an
  // effectively coincident HYG entry, so the local catalog does not create holes.
  const visible = catalogStars.filter(star => !gaiaStars.some(gaiaStar => {
    const dra = (star.ra - gaiaStar.ra) * 15 * Math.cos(centerDec) * 3600;
    const ddec = (star.dec - gaiaStar.dec) * 3600;
    return Math.hypot(dra, ddec) < 0.5;
  })).concat(gaiaStars);
  const positions = new Float32Array(visible.length * 3);
  const colors = new Float32Array(visible.length * 3);
  const absoluteMagnitudes = new Float32Array(visible.length);
  const centerSin = Math.sin(centerDec), centerCos = Math.cos(centerDec);
  const blueStar = new THREE.Color(0x9cbcff), warmStar = new THREE.Color(0xff9c57), starColor = new THREE.Color();
  let maxDistanceLy = 0;

  for (let i = 0; i < visible.length; i++) {
    const star = visible[i];
    const ra = THREE.MathUtils.degToRad(star.ra * 15);
    const dec = THREE.MathUtils.degToRad(star.dec);
    const distanceLy = star.distancePc * 3.26156;
    maxDistanceLy = Math.max(maxDistanceLy, distanceLy);
    const dra = THREE.MathUtils.euclideanModulo(ra - centerRa + Math.PI, Math.PI * 2) - Math.PI;
    const sinDec = Math.sin(dec), cosDec = Math.cos(dec), cosDra = Math.cos(dra);
    const along = centerSin * sinDec + centerCos * cosDec * cosDra;
    const east = cosDec * Math.sin(dra);
    const north = centerCos * sinDec - centerSin * cosDec * cosDra;
    // Positions use the catalog parallax distance (or the source catalog's
    // distance) and the measured ICRS direction, rotated to the image PA.
    const imageEast = east * Math.cos(imagePositionAngle) + north * Math.sin(imagePositionAngle);
    const imageNorth = -east * Math.sin(imagePositionAngle) + north * Math.cos(imagePositionAngle);
    positions[i * 3] = distanceLy * imageEast;
    positions[i * 3 + 1] = distanceLy * imageNorth;
    positions[i * 3 + 2] = distanceLy * along;

    const bv = star.colorIndex;
    const t = THREE.MathUtils.clamp((bv + 0.4) / 2.4, 0, 1);
    starColor.copy(blueStar).lerp(warmStar, t);
    if (star.localGaia) starColor.lerp(new THREE.Color(0xf4f1e8), 0.58);
    const magnitude = star.magnitude;
    absoluteMagnitudes[i] = magnitude - 5 * Math.log10(star.distancePc / 10);
    colors[i * 3] = starColor.r;
    colors[i * 3 + 1] = starColor.g;
    colors[i * 3 + 2] = starColor.b;
  }

  const layerGeometry = new THREE.BufferGeometry();
  layerGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  layerGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  layerGeometry.setAttribute('absoluteMagnitude', new THREE.BufferAttribute(absoluteMagnitudes, 1));
    const layerMaterial = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, vertexColors: true, toneMapped: false,
      vertexShader: '#include <common>\n#include <logdepthbuf_pars_vertex>\nattribute float absoluteMagnitude; varying vec3 vColor; varying float vFlux; void main(){vColor=color;vec4 mv=modelViewMatrix*vec4(position,1.0);float distancePc=max(length(mv.xyz)/3.26156,0.000001);float apparentMagnitude=absoluteMagnitude+5.0*log(distancePc/10.0)/log(10.0);vFlux=pow(10.0,-0.4*(apparentMagnitude-8.0));gl_Position=projectionMatrix*mv;gl_PointSize=2.8;\n#include <logdepthbuf_vertex>\n}',
      fragmentShader: '#include <common>\n#include <logdepthbuf_pars_fragment>\nvarying vec3 vColor; varying float vFlux; void main(){float r=length(gl_PointCoord-vec2(0.5));if(r>0.5)discard;\n#include <logdepthbuf_fragment>\nfloat psf=1.0-smoothstep(0.15,0.5,r);gl_FragColor=vec4(vColor,psf*clamp(vFlux,0.0,1.0));\n#include <colorspace_fragment>}'
    });
    const layerPoints = new THREE.Points(layerGeometry, layerMaterial);
  layerPoints.frustumCulled = false; layerPoints.renderOrder = 2;
  return {
    points: layerPoints, geometry: layerGeometry, material: layerMaterial, count: visible.length, maxDistanceLy
  };
}

/** Render catalog stars at catalog distances and Hubble diffuse IR data at its measured angular scale. */
export function createNebulaVolume({ canvas, modelStatus }) {
  const params = new URLSearchParams(location.search);
  const vectorParam = (name, fallback) => {
    const values = (params.get(name) || '').split(',').map(Number);
    return values.length === 3 && values.every(Number.isFinite) ? values : fallback;
  };
  const imageWidthLy = 2 * M16_DISTANCE_LY * Math.tan(THREE.MathUtils.degToRad(M16_FIELD_WIDTH_ARCSEC / 7200));
  const imageHeightLy = 2 * M16_DISTANCE_LY * Math.tan(THREE.MathUtils.degToRad(M16_FIELD_HEIGHT_ARCSEC / 7200));
  const viewFov = THREE.MathUtils.clamp(Number(params.get('viewFov')) || 42, 4, 100);
  const defaultEndDistance = aspect => Math.max(
    imageHeightLy / (2 * Math.tan(THREE.MathUtils.degToRad(viewFov / 2))),
    imageWidthLy / (2 * Math.tan(THREE.MathUtils.degToRad(viewFov / 2)) * Math.max(aspect, 0.1))
  );
  const initialAspect = canvas.clientWidth > 0 && canvas.clientHeight > 0 ? canvas.clientWidth / canvas.clientHeight : 1;
  const startPosition = vectorParam('start', [0, EARTH_ORBIT_START_Y_LY, 0]);
  const startLookAt = vectorParam('startLookAt', [0, EARTH_ORBIT_START_Y_LY, M16_DISTANCE_LY]);
  const endPosition = vectorParam('end', [0, 0, M16_DISTANCE_LY - defaultEndDistance(initialAspect)]);
  const endLookAt = vectorParam('endLookAt', [0, 0, M16_DISTANCE_LY]);
  const duration = THREE.MathUtils.clamp(Number(params.get('duration')) || 22, 1, 600);
  const waypointText = params.get('waypoints');
  const waypoints = waypointText ? waypointText.split(';').map(value => {
    const point = value.split(',').map(Number);
    return point.length === 3 && point.every(Number.isFinite) ? point : null;
  }).filter(Boolean) : [[0, 0, M16_DISTANCE_LY * 0.15], [0, 0, M16_DISTANCE_LY * 0.72]];
  const routePositions = [startPosition, ...waypoints, endPosition];
  const autoPlay = params.get('autoplay') !== '0';
  const startZoom = THREE.MathUtils.clamp(Number(params.get('startZoom')) || 1, 0.25, 4);
  const endZoom = THREE.MathUtils.clamp(Number(params.get('endZoom')) || 1, 0.25, 4);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power', logarithmicDepthBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x02040a);
  const camera = new THREE.PerspectiveCamera(viewFov, 1, 0.0000000000001, 100000);
  camera.position.fromArray(autoPlay ? startPosition : endPosition);
  camera.zoom = autoPlay ? startZoom : endZoom;
  const orbitTarget = new THREE.Vector3(...(autoPlay ? startLookAt : endLookAt));
  camera.lookAt(orbitTarget);
  const group = new THREE.Group();
  scene.add(group);

  let earthMapState = 'loading', resolveEarthMap;
  const earthMapReady = new Promise(resolve => { resolveEarthMap = resolve; });
  const earthMap = new THREE.TextureLoader().load(EARTH_MAP_URL,
    () => { earthMapState = 'ready'; updateModelStatus(); resolveEarthMap(true); },
    undefined,
    () => { earthMapState = 'failed'; updateModelStatus(); resolveEarthMap(false); }
  );
  earthMap.colorSpace = THREE.SRGBColorSpace;
  const earth = new THREE.Mesh(
    new THREE.SphereGeometry(EARTH_RADIUS_LY, 96, 64),
    new THREE.MeshBasicMaterial({ map: earthMap, toneMapped: false })
  );
  scene.add(earth);

  let starsState = 'loading', projectionState = 'loading', starsCount = 0, projectionCount = 0;
  const updateModelStatus = () => {
    if (!modelStatus) return;
    const states = [
      starsState === 'ready' ? `${starsCount.toLocaleString()} catalog stars` : `stars ${starsState}`,
      projectionState === 'ready' ? `${projectionCount.toLocaleString()} Hubble IR samples · ${M16_DISTANCE_LY.toLocaleString()} ly · depth unknown` : `IR data ${projectionState}`,
      `Earth texture ${earthMapState}`
    ];
    modelStatus.textContent = states.join(' · ');
  };
  updateModelStatus();
  let parallaxStars = null;
  const starsPromise = loadParallaxStars().then(layer => {
    parallaxStars = layer;
    scene.add(layer.points);
    const routeExtent = Math.max(...routePositions.map(position => Math.hypot(...position)));
    camera.far = Math.max(camera.far, layer.maxDistanceLy + routeExtent + 100);
    camera.updateProjectionMatrix();
    starsState = 'ready'; starsCount = layer.count; updateModelStatus();
    return layer;
  }).catch(error => {
    starsState = `failed (${error.message || error})`; updateModelStatus();
    console.warn('Could not load Gaia/HYG star field:', error);
    return null;
  });
  let hubbleProjection = null;
  const projectionPromise = loadHubbleIRProjection().then(layer => {
    hubbleProjection = layer;
    group.add(layer.points);
    projectionState = 'ready'; projectionCount = layer.count; updateModelStatus();
    return layer;
  }).catch(error => {
    projectionState = `failed (${error.message || error})`; updateModelStatus();
    console.warn('Could not load calibrated Hubble infrared samples:', error);
    return null;
  });
  let disposed = false, tourStartedAt = 0, tourRunning = false, endpointView = !autoPlay;

  let dragging = false, previousX = 0, previousY = 0;
  canvas.style.cursor = 'grab';
  canvas.addEventListener('pointerdown', event => {
    tourRunning = false;
    endpointView = false;
    dragging = true; previousX = event.clientX; previousY = event.clientY;
    canvas.setPointerCapture(event.pointerId); canvas.style.cursor = 'grabbing';
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging) return;
    const aim = orbitTarget.clone().sub(camera.position);
    const radius = Math.max(aim.length(), 0.0001);
    const theta = Math.atan2(aim.x, aim.z) - (event.clientX - previousX) * 0.006;
    const phi = THREE.MathUtils.clamp(Math.acos(THREE.MathUtils.clamp(aim.y / radius, -1, 1)) + (event.clientY - previousY) * 0.006, 0.025, Math.PI - 0.025);
    aim.set(Math.sin(phi) * Math.sin(theta), Math.cos(phi), Math.sin(phi) * Math.cos(theta));
    orbitTarget.copy(camera.position).addScaledVector(aim, radius);
    camera.lookAt(orbitTarget);
    previousX = event.clientX; previousY = event.clientY;
  });
  const stopDrag = () => { dragging = false; canvas.style.cursor = 'grab'; };
  canvas.addEventListener('pointerup', stopDrag);
  canvas.addEventListener('pointercancel', stopDrag);
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    tourRunning = false;
    endpointView = false;
    const offset = camera.position.clone().sub(orbitTarget);
    offset.setLength(THREE.MathUtils.clamp(offset.length() * Math.exp(event.deltaY * 0.001), 0.0001, 50000));
    camera.position.copy(orbitTarget).add(offset);
  }, { passive: false });
  function resetView() {
    tourRunning = false;
    endpointView = true;
    group.rotation.set(0, 0, 0); camera.position.fromArray(endPosition); orbitTarget.fromArray(endLookAt); camera.lookAt(orbitTarget);
    camera.zoom = endZoom; camera.updateProjectionMatrix();
  }

  function travelFromEarth() {
    endpointView = false;
    group.rotation.set(0, 0, 0);
    camera.position.fromArray(startPosition); orbitTarget.fromArray(startLookAt); camera.lookAt(orbitTarget);
    camera.zoom = startZoom; camera.updateProjectionMatrix();
    tourStartedAt = performance.now(); tourRunning = true;
  }
  function smooth(t) { const x = THREE.MathUtils.clamp(t, 0, 1); return x * x * (3 - 2 * x); }
  function updateTour(now) {
    if (!tourRunning) return;
    const elapsed = (now - tourStartedAt) / 1000;
    if (elapsed >= duration) {
      tourRunning = false;
      endpointView = true;
      group.rotation.set(0, 0, 0); camera.position.fromArray(endPosition); orbitTarget.fromArray(endLookAt); camera.lookAt(orbitTarget);
      camera.zoom = endZoom; camera.updateProjectionMatrix();
      return;
    }
    const progress = smooth(elapsed / duration) * (routePositions.length - 1);
    const index = Math.min(routePositions.length - 2, Math.floor(progress));
    const u = progress - index;
    const mix = (a, b, t) => a.map((value, i) => value + (b[i] - value) * t);
    camera.position.fromArray(mix(routePositions[index], routePositions[index + 1], u));
    orbitTarget.fromArray(mix(startLookAt, endLookAt, smooth(elapsed / duration)));
    camera.lookAt(orbitTarget);
    const zoomProgress = smooth((elapsed / duration - 0.62) / 0.38);
    camera.zoom = startZoom + (endZoom - startZoom) * zoomProgress;
    camera.updateProjectionMatrix();
  }

  function resize() {
    const width = Math.max(1, canvas.clientWidth), height = Math.max(1, canvas.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    if (!params.has('end')) {
      endPosition[2] = M16_DISTANCE_LY - defaultEndDistance(camera.aspect);
      if (endpointView) { camera.position.fromArray(endPosition); camera.lookAt(orbitTarget); }
    }
    camera.updateProjectionMatrix();
  }
  const observer = new ResizeObserver(resize); observer.observe(canvas); resize();
  const update = () => {};
  let active = true;
  const frame = now => { if (!disposed) { updateTour(now); if (active) renderer.render(scene, camera); requestAnimationFrame(frame); } };
  frame();
  return {
    update,
    ready: Promise.all([starsPromise, projectionPromise, earthMapReady]).then(([starLayer, projectionLayer, earthLoaded]) => {
      if (!starLayer) throw new Error('Catalog star field did not load');
      if (!projectionLayer) throw new Error('Calibrated Hubble WFC3/IR projection did not load');
      if (!earthLoaded || earthMapState !== 'ready') throw new Error('Earth texture did not load');
      return { stars: starLayer.count, diffuseSamples: projectionLayer.count, distanceLy: M16_DISTANCE_LY, fieldWidthLy: imageWidthLy, fieldHeightLy: imageHeightLy, infraredFilter: 'HST WFC3/IR F110W + F160W' };
    }),
    travelFromEarth,
    resetView,
    stopTour() { tourRunning = false; },
    setActive(value) { active = Boolean(value); },
    dispose() {
      disposed = true; observer.disconnect(); renderer.dispose();
      earth.geometry.dispose(); earth.material.dispose(); earthMap.dispose();
      if (parallaxStars) {
        scene.remove(parallaxStars.points);
        parallaxStars.geometry.dispose(); parallaxStars.material.dispose();
      }
      if (hubbleProjection) {
        group.remove(hubbleProjection.points);
        hubbleProjection.geometry.dispose(); hubbleProjection.material.dispose();
      }
    }
  };
}
