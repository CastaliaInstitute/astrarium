import * as THREE from './vendor/three.module.js';

const observationHost = ['localhost', '127.0.0.1'].includes(location.hostname)
  ? `${location.origin}/`
  : 'https://astrarium.castalia.institute/lcars/';
const MODEL_URL = new URL('observations/m16-jwst/pillars-stsci-mesh.bin.gz?v=207', observationHost).href;
const MODEL_COLOR_URL = new URL('observations/m16-hst/hubble-wfc3ir-mesh-colors.bin.gz?v=1', observationHost).href;
const HST_IR_VOLUME_URL = new URL('observations/m16-hst/hubble-wfc3ir-volume.bin.gz?v=1', observationHost).href;
const SKY_CATALOG_URL = new URL('stars.json', observationHost).href;
const M16_GAIA_URL = new URL('observations/m16-jwst/gaia-dr3-wide-stars.json', observationHost).href;
const EARTH_MAP_URL = new URL('observations/earth-blue-marble.webp', observationHost).href;

async function loadPillarsGeometry() {
  const response = await fetch(MODEL_URL);
  if (!response.ok) throw new Error(`NASA/STScI Pillars mesh unavailable (${response.status})`);
  if (!('DecompressionStream' in window)) throw new Error('This browser cannot decompress the mesh asset');
  const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
  const bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const magic = new TextDecoder().decode(bytes.subarray(0, 8));
  if (magic !== 'ASTL3D1\0') throw new Error('Pillars mesh has an unknown format');
  const vertexCount = view.getUint32(8, true), indexCount = view.getUint32(12, true);
  const min = [0, 0, 0], max = [0, 0, 0];
  for (let i = 0; i < 3; i++) min[i] = view.getFloat32(16 + i * 4, true);
  for (let i = 0; i < 3; i++) max[i] = view.getFloat32(28 + i * 4, true);
  const positions = new Float32Array(bytes.buffer, bytes.byteOffset + 40, vertexCount * 3);
  const indices = new Uint32Array(bytes.buffer, bytes.byteOffset + 40 + vertexCount * 12, indexCount);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.userData.sourceBounds = { min, max };
  return geometry;
}

async function loadPillarsVertexColors() {
  const response = await fetch(MODEL_COLOR_URL);
  if (!response.ok) throw new Error(`JWST mesh colors unavailable (${response.status})`);
  if (!('DecompressionStream' in window)) throw new Error('This browser cannot decompress JWST mesh colors');
  const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
  const bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  if (new TextDecoder().decode(bytes.subarray(0, 8)) !== 'ASTVC1\0\0') throw new Error('JWST mesh colors have an unknown format');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const count = view.getUint32(8, true);
  const encoded = new Uint8Array(bytes.buffer, bytes.byteOffset + 12, count * 3);
  const colors = new Float32Array(count * 3);
  const color = new THREE.Color();
  for (let i = 0; i < encoded.length; i += 3) {
    color.setRGB(encoded[i] / 255, encoded[i + 1] / 255, encoded[i + 2] / 255, THREE.SRGBColorSpace);
    colors[i] = color.r; colors[i + 1] = color.g; colors[i + 2] = color.b;
  }
  return { colors, count };
}

async function loadHubbleIRVolume() {
  const response = await fetch(HST_IR_VOLUME_URL);
  if (!response.ok) throw new Error(`Hubble WFC3/IR volume unavailable (${response.status})`);
  if (!('DecompressionStream' in window)) throw new Error('This browser cannot decompress Hubble infrared points');
  const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
  const bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  if (new TextDecoder().decode(bytes.subarray(0, 8)) !== 'ASTIR1\0\0') throw new Error('Hubble infrared volume has an unknown format');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const count = view.getUint32(8, true), stride = 10;
  if (bytes.byteLength < 12 + count * stride) throw new Error('Hubble infrared volume is truncated');
  const decodedPositions = new Float32Array(count * 3), decodedColors = new Float32Array(count * 3), decodedSizes = new Float32Array(count);
  const starFlags = new Uint8Array(count), indexes = { gas: [], stars: [] };
  const fieldHeight = 2.1 * 243.0415 / 260.0;
  const color = new THREE.Color();
  for (let i = 0, offset = 12; i < count; i++, offset += stride) {
    const x = view.getUint16(offset, true) / 65535;
    const y = view.getUint16(offset + 2, true) / 65535;
    const z = view.getUint16(offset + 4, true) / 65535;
    decodedPositions[i * 3] = (x - 0.5) * 2.1;
    decodedPositions[i * 3 + 1] = (0.5 - y) * fieldHeight;
    decodedPositions[i * 3 + 2] = z * 3 - 1.5;
    color.setRGB(bytes[offset + 6] / 255, bytes[offset + 7] / 255, bytes[offset + 8] / 255, THREE.SRGBColorSpace);
    decodedColors[i * 3] = color.r; decodedColors[i * 3 + 1] = color.g; decodedColors[i * 3 + 2] = color.b;
    const code = bytes[offset + 9];
    starFlags[i] = code & 0x80 ? 1 : 0;
    decodedSizes[i] = code & 0x7f;
    indexes[starFlags[i] ? 'stars' : 'gas'].push(i);
  }
  const makeLayer = (entries, stars) => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(entries.length * 3), colors = new Float32Array(entries.length * 3), sizes = new Float32Array(entries.length);
    for (let j = 0; j < entries.length; j++) {
      const i = entries[j];
      positions.set(decodedPositions.subarray(i * 3, i * 3 + 3), j * 3);
      colors.set(decodedColors.subarray(i * 3, i * 3 + 3), j * 3);
      sizes[j] = stars ? THREE.MathUtils.clamp(2.0 + decodedSizes[i] * 0.72, 3.2, 9.2) : THREE.MathUtils.clamp(0.55 + decodedSizes[i] * 0.72, 1.2, 4.8);
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    const material = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, vertexColors: true, toneMapped: false,
      vertexShader: 'attribute float size; varying vec3 vColor; void main(){vColor=color;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=size;}',
      fragmentShader: stars
        ? 'varying vec3 vColor; void main(){vec2 p=abs(gl_PointCoord-vec2(0.5))*2.0;float r=length(p);if(r>1.0)discard;float core=exp(-r*10.0);float halo=exp(-r*3.2)*0.38;float spikes=(exp(-p.x*42.0)*exp(-p.y*4.0)+exp(-p.y*42.0)*exp(-p.x*4.0))*0.22;float a=clamp(core+halo+spikes,0.0,1.0);gl_FragColor=vec4(mix(vColor,vec3(1.0),0.16),a);\n#include <colorspace_fragment>}'
        : 'varying vec3 vColor; void main(){float r=length(gl_PointCoord-vec2(0.5));if(r>0.5)discard;float a=(1.0-smoothstep(0.22,0.5,r))*0.96;gl_FragColor=vec4(vColor,a);\n#include <colorspace_fragment>}'
    });
    const points = new THREE.Points(geometry, material);
    points.frustumCulled = false; points.renderOrder = stars ? 4 : 1;
    return { points, geometry, material, count: entries.length };
  };
  const gas = makeLayer(indexes.gas, false), stars = makeLayer(indexes.stars, true);
  return {
    ...gas,
    stars: stars.points, starsGeometry: stars.geometry, starsMaterial: stars.material, starCount: stars.count
  };
}

async function loadParallaxStars() {
  const [catalogResponse, gaiaResponse] = await Promise.all([fetch(SKY_CATALOG_URL), fetch(M16_GAIA_URL)]);
  if (!catalogResponse.ok) throw new Error(`Astrarium star catalog unavailable (${catalogResponse.status})`);
  if (!gaiaResponse.ok) throw new Error(`M16 Gaia DR3 sources unavailable (${gaiaResponse.status})`);
  const [{ stars = [] }, gaia = {}] = await Promise.all([catalogResponse.json(), gaiaResponse.json()]);
  const centerRa = THREE.MathUtils.degToRad(274.7170416667);
  const centerDec = THREE.MathUtils.degToRad(-13.8347916667);
  const earthDistance = 6500; // light-years, used to orient the view toward M16
  const viewDistance = 26; // scene units from Earth to M16; the gas model is deliberately enlarged
  const compressionScale = 0.1; // light-years; strong log compression keeps catalog stars visible at the target while retaining distance order
  const denominator = Math.log1p(earthDistance / compressionScale);
  const imageHalfWidthDeg = 130 / 3600, imageHalfHeightDeg = 121.52075 / 3600;
  const imagePositionAngle = THREE.MathUtils.degToRad(35.1);
  const imageFieldScaleX = 1.05 / Math.tan(THREE.MathUtils.degToRad(imageHalfWidthDeg));
  const imageFieldScaleY = (2.1 * 243.0415 / 260.0 / 2) / Math.tan(THREE.MathUtils.degToRad(imageHalfHeightDeg));
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
  const isInM16GaiaField = star => {
    const ra = THREE.MathUtils.degToRad(star.ra * 15), dec = THREE.MathUtils.degToRad(star.dec);
    const dra = THREE.MathUtils.euclideanModulo(ra - centerRa + Math.PI, Math.PI * 2) - Math.PI;
    const dec0 = THREE.MathUtils.degToRad(centerDecDegrees), dec1 = dec;
    const cosAngle = Math.sin(dec0) * Math.sin(dec1) + Math.cos(dec0) * Math.cos(dec1) * Math.cos(dra);
    return cosAngle >= Math.cos(THREE.MathUtils.degToRad(0.0556));
  };
  const visible = catalogStars.filter(star => !isInM16GaiaField(star)).concat(gaiaStars);
  const positions = new Float32Array(visible.length * 3);
  const colors = new Float32Array(visible.length * 3);
  const sizes = new Float32Array(visible.length);
  const centerSin = Math.sin(centerDec), centerCos = Math.cos(centerDec);
  const blueStar = new THREE.Color(0x9cbcff), warmStar = new THREE.Color(0xff9c57), starColor = new THREE.Color();

  for (let i = 0; i < visible.length; i++) {
    const star = visible[i];
    const ra = THREE.MathUtils.degToRad(star.ra * 15);
    const dec = THREE.MathUtils.degToRad(star.dec);
    const distanceLy = star.distancePc * 3.26156;
    const dra = THREE.MathUtils.euclideanModulo(ra - centerRa + Math.PI, Math.PI * 2) - Math.PI;
    const sinDec = Math.sin(dec), cosDec = Math.cos(dec), cosDra = Math.cos(dra);
    const along = centerSin * sinDec + centerCos * cosDec * cosDra;
    const east = cosDec * Math.sin(dra);
    const north = centerCos * sinDec - centerSin * cosDec * cosDra;
    const compressedDistance = viewDistance * Math.log1p(distanceLy / compressionScale) / denominator;

    // Gaia/HYG distance and sky direction place each catalog star in 3D.
    // Log depth compression is visual navigation only; it preserves foreground/background order.
    if (star.localGaia) {
      // The gas mesh is enlarged to the image field, so register Gaia's sky
      // positions to that same 200 arcsec footprint while preserving parallax depth.
      const eastDeg = east / along * 180 / Math.PI, northDeg = north / along * 180 / Math.PI;
      const imageX = eastDeg * Math.cos(imagePositionAngle) + northDeg * Math.sin(imagePositionAngle);
      const imageY = -eastDeg * Math.sin(imagePositionAngle) + northDeg * Math.cos(imagePositionAngle);
      positions[i * 3] = THREE.MathUtils.degToRad(imageX) * imageFieldScaleX;
      positions[i * 3 + 1] = THREE.MathUtils.degToRad(imageY) * imageFieldScaleY;
      positions[i * 3 + 2] = viewDistance - compressedDistance * along;
    } else {
      positions[i * 3] = compressedDistance * east;
      positions[i * 3 + 1] = compressedDistance * north;
      positions[i * 3 + 2] = viewDistance - compressedDistance * along;
    }

    const bv = star.colorIndex;
    const t = THREE.MathUtils.clamp((bv + 0.4) / 2.4, 0, 1);
    starColor.copy(blueStar).lerp(warmStar, t);
    if (star.localGaia) starColor.lerp(new THREE.Color(0xf4f1e8), 0.58);
    const magnitude = star.magnitude;
    const brightness = star.localGaia
      ? THREE.MathUtils.clamp(2.25 - Math.max(0, magnitude - 12) * 0.075, 1.05, 2.25)
      : THREE.MathUtils.clamp(1.25 - Math.max(0, magnitude) * 0.085, 0.34, 1.25);
    colors[i * 3] = starColor.r * brightness;
    colors[i * 3 + 1] = starColor.g * brightness;
    colors[i * 3 + 2] = starColor.b * brightness;
    sizes[i] = star.localGaia
      ? THREE.MathUtils.clamp(10.5 - Math.max(0, magnitude - 12) * 0.35, 4.5, 10.5)
      : THREE.MathUtils.clamp(3.9 - magnitude * 0.32, 1.1, 4.2);
  }

  const localIndexes = [], wideIndexes = [];
  for (let i = 0; i < visible.length; i++) (visible[i].localGaia ? localIndexes : wideIndexes).push(i);
  const makeLayer = (indexes, local) => {
    const layerGeometry = new THREE.BufferGeometry();
    const layerPositions = new Float32Array(indexes.length * 3);
    const layerColors = new Float32Array(indexes.length * 3);
    const layerSizes = new Float32Array(indexes.length);
    const layerLocal = new Float32Array(indexes.length);
    for (let j = 0; j < indexes.length; j++) {
      const i = indexes[j];
      layerPositions.set(positions.subarray(i * 3, i * 3 + 3), j * 3);
      layerColors.set(colors.subarray(i * 3, i * 3 + 3), j * 3);
      layerSizes[j] = sizes[i]; layerLocal[j] = local ? 1 : 0;
    }
    layerGeometry.setAttribute('position', new THREE.BufferAttribute(layerPositions, 3));
    layerGeometry.setAttribute('color', new THREE.BufferAttribute(layerColors, 3));
    layerGeometry.setAttribute('size', new THREE.BufferAttribute(layerSizes, 1));
    layerGeometry.setAttribute('localGaia', new THREE.BufferAttribute(layerLocal, 1));
    const layerMaterial = new THREE.ShaderMaterial({
      uniforms: { showWideSky: { value: 1 } },
      transparent: true, depthWrite: false, vertexColors: true, toneMapped: false,
      vertexShader: 'attribute float size; attribute float localGaia; varying vec3 vColor; varying float vLocal; void main(){vColor=color;vLocal=localGaia;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=size;}',
      fragmentShader: 'uniform float showWideSky; varying vec3 vColor; varying float vLocal; void main(){vec2 p=abs(gl_PointCoord-vec2(0.5))*2.0;float r=length(p);if(r>1.0)discard;float roundStar=1.0-smoothstep(0.25,1.0,r);float core=exp(-r*11.0);float halo=exp(-r*3.6)*0.3;float spikes=(exp(-p.x*42.0)*exp(-p.y*4.0)+exp(-p.y*42.0)*exp(-p.x*4.0))*0.2;float star=clamp(core+halo+spikes,0.0,1.0);float a=mix(roundStar,star,vLocal)*max(showWideSky,vLocal);gl_FragColor=vec4(mix(vColor,vec3(1.0),vLocal*0.22),a);\n#include <colorspace_fragment>}'
    });
    const layerPoints = new THREE.Points(layerGeometry, layerMaterial);
    layerPoints.frustumCulled = false; layerPoints.renderOrder = local ? 3 : 2;
    return { points: layerPoints, geometry: layerGeometry, material: layerMaterial, count: indexes.length };
  };
  const wideLayer = makeLayer(wideIndexes, false), localLayer = makeLayer(localIndexes, true);
  return {
    ...wideLayer,
    localPoints: localLayer.points, localGeometry: localLayer.geometry, localMaterial: localLayer.material,
    count: wideLayer.count + localLayer.count
  };
}

/** Render catalog stars in depth and the STScI gas mesh with calibrated JWST vertex colors.
 * Stellar depth comes from parallax; the gas depth is authored visualization geometry.
 */
export function createNebulaVolume({ canvas, modelStatus }) {
  const params = new URLSearchParams(location.search);
  const vectorParam = (name, fallback) => {
    const values = (params.get(name) || '').split(',').map(Number);
    return values.length === 3 && values.every(Number.isFinite) ? values : fallback;
  };
  const startPosition = vectorParam('start', [0, 0, 26]);
  const startLookAt = vectorParam('startLookAt', [1.8, 0.25, 20.5]);
  const endPosition = vectorParam('end', [0, 0, 3.4]);
  const endLookAt = vectorParam('endLookAt', [0, 0, 0]);
  const duration = THREE.MathUtils.clamp(Number(params.get('duration')) || 22, 1, 600);
  const waypointText = params.get('waypoints');
  const waypoints = waypointText ? waypointText.split(';').map(value => {
    const point = value.split(',').map(Number);
    return point.length === 3 && point.every(Number.isFinite) ? point : null;
  }).filter(Boolean) : [[0, 0, 19], [0, 0, 11]];
  const routePositions = [startPosition, ...waypoints, endPosition];
  const autoPlay = params.get('autoplay') !== '0';
  const viewFov = THREE.MathUtils.clamp(Number(params.get('viewFov')) || 42, 4, 100);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x02040a);
  const camera = new THREE.PerspectiveCamera(viewFov, 1, 0.01, 1000);
  camera.position.fromArray(autoPlay ? startPosition : endPosition);
  camera.lookAt(...(autoPlay ? startLookAt : endLookAt));
  scene.add(new THREE.AmbientLight(0xb9c9d8, 1.8));
  const keyLight = new THREE.DirectionalLight(0xffd9ae, 2.5);
  keyLight.position.set(4, 7, 8);
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0x377eb4, 1.6);
  rimLight.position.set(-5, -2, -4);
  scene.add(rimLight);
  const group = new THREE.Group();
  scene.add(group);

  let earthMapState = 'loading', resolveEarthMap;
  const earthMapReady = new Promise(resolve => { resolveEarthMap = resolve; });
  const earthMap = new THREE.TextureLoader().load(EARTH_MAP_URL, () => { earthMapState = 'ready'; updateModelStatus(); resolveEarthMap(true); }, undefined, () => { earthMapState = 'failed'; updateModelStatus(); resolveEarthMap(false); });
  earthMap.colorSpace = THREE.SRGBColorSpace;
  const earth = new THREE.Mesh(new THREE.SphereGeometry(1.25, 96, 64), new THREE.MeshStandardMaterial({ map: earthMap, roughness: 1, metalness: 0 }));
  earth.position.set(1.8, 0.25, 20.5);
  scene.add(earth);
  let starsState = 'loading', modelState = 'loading', dustState = 'loading', starsCount = 0, dustCount = 0, triangleCount = 0;
  const updateModelStatus = () => {
    if (!modelStatus) return;
    const states = [
      starsState === 'ready' ? `${starsCount.toLocaleString()} catalog stars` : `stars ${starsState}`,
      dustState === 'ready' ? `${dustCount.toLocaleString()} Hubble IR gas samples and stars` : `IR volume ${dustState}`,
      modelState === 'ready' ? `Pillars · ${triangleCount.toLocaleString()} triangles` : `gas ${modelState}`,
      `Earth texture ${earthMapState}`
    ];
    modelStatus.textContent = states.join(' · ');
  };
  earthMapState = earthMap.image?.complete && earthMap.image?.naturalWidth ? 'ready' : 'loading';
  updateModelStatus();
  let parallaxStars = null;
  const starsPromise = loadParallaxStars().then(layer => {
    parallaxStars = layer;
    scene.add(layer.points);
    group.add(layer.localPoints);
    starsState = 'ready'; starsCount = layer.count; updateModelStatus();
    return layer;
  }).catch(error => {
    starsState = `failed (${error.message || error})`; updateModelStatus();
    console.warn('Could not load Gaia/HYG star field:', error);
    return null;
  });
  let hubbleVolume = null;
  const dustPromise = loadHubbleIRVolume().then(layer => {
    hubbleVolume = layer;
    group.add(layer.points); group.add(layer.stars);
    dustState = 'ready'; dustCount = layer.count + layer.starCount; updateModelStatus();
    return layer;
  }).catch(error => {
    dustState = `failed (${error.message || error})`; updateModelStatus();
    console.warn('Could not load calibrated Hubble infrared volume:', error);
    return null;
  });
  let model = null, modelMaterial = null, disposed = false, tourStartedAt = 0, tourRunning = false;
  const modelPromise = loadPillarsGeometry();
  const modelColorsPromise = loadPillarsVertexColors();
  Promise.all([modelPromise, modelColorsPromise]).then(([geometry, colorData]) => {
    if (disposed) { geometry.dispose(); return; }
    const geometryVertexCount = geometry.getAttribute('position').count;
    if (geometryVertexCount !== colorData.count) throw new Error(`JWST mesh color count mismatch (${colorData.count} colors for ${geometryVertexCount} vertices)`);
    geometry.setAttribute('color', new THREE.BufferAttribute(colorData.colors, 3));
    modelMaterial = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, toneMapped: false, transparent: true, opacity: 0.22, depthWrite: false });
    model = new THREE.Mesh(geometry, modelMaterial);
    const box = geometry.boundingBox;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const imagePlaneScaleX = 2.1 / Math.max(size.x, size.z) * 1.4;
    const imagePlaneScaleY = (2.1 * 243.0415 / 260.0) / Math.max(size.x, size.z);
    const depthScale = 2.1 / Math.max(size.x, size.y, size.z);
    geometry.translate(-center.x, -center.y, -center.z);
    model.scale.set(imagePlaneScaleX, depthScale, imagePlaneScaleY);
    model.position.set(0, 0, 0);
    model.rotation.x = -Math.PI / 2; // Rotate NASA's Z-up mesh into Three.js Y-up; source parts keep their shared placement.
    model.renderOrder = 0;
    group.add(model);
    modelState = 'ready'; triangleCount = Math.round(geometry.index.count / 3); updateModelStatus();
  }).catch(error => {
    modelState = `failed (${error.message || error})`; updateModelStatus();
    console.warn('Could not load Pillars of Creation 3D model:', error);
  });

  let dragging = false, previousX = 0, previousY = 0;
  canvas.style.cursor = 'grab';
  canvas.addEventListener('pointerdown', event => {
    tourRunning = false;
    dragging = true; previousX = event.clientX; previousY = event.clientY;
    canvas.setPointerCapture(event.pointerId); canvas.style.cursor = 'grabbing';
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging) return;
    group.rotation.y += (event.clientX - previousX) * 0.006;
    group.rotation.x += (event.clientY - previousY) * 0.006;
    previousX = event.clientX; previousY = event.clientY;
  });
  const stopDrag = () => { dragging = false; canvas.style.cursor = 'grab'; };
  canvas.addEventListener('pointerup', stopDrag);
  canvas.addEventListener('pointercancel', stopDrag);
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    tourRunning = false;
    camera.position.z = THREE.MathUtils.clamp(camera.position.z + event.deltaY * 0.035, 2.5, 30);
  }, { passive: false });
  function resetView() {
    tourRunning = false;
    group.rotation.set(0, 0, 0); camera.position.fromArray(endPosition); camera.lookAt(...endLookAt);
  }

  function travelFromEarth() {
    group.rotation.set(0, 0, 0);
    camera.position.fromArray(startPosition); camera.lookAt(...startLookAt);
    tourStartedAt = performance.now(); tourRunning = true;
  }
  function smooth(t) { const x = THREE.MathUtils.clamp(t, 0, 1); return x * x * (3 - 2 * x); }
  function updateTour(now) {
    if (parallaxStars) parallaxStars.points.visible = camera.position.length() > 25;
    if (!tourRunning) return;
    const elapsed = (now - tourStartedAt) / 1000;
    earth.rotation.y += 0.0008;
    if (elapsed >= duration) {
      tourRunning = false;
      group.rotation.set(0, 0, 0); camera.position.fromArray(endPosition); camera.lookAt(...endLookAt);
      return;
    }
    const progress = smooth(elapsed / duration) * (routePositions.length - 1);
    const index = Math.min(routePositions.length - 2, Math.floor(progress));
    const u = progress - index;
    const mix = (a, b, t) => a.map((value, i) => value + (b[i] - value) * t);
    camera.position.fromArray(mix(routePositions[index], routePositions[index + 1], u));
    camera.lookAt(...mix(startLookAt, endLookAt, smooth(elapsed / duration)));
  }

  function resize() {
    const width = Math.max(1, canvas.clientWidth), height = Math.max(1, canvas.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  const observer = new ResizeObserver(resize); observer.observe(canvas); resize();
  const update = () => {};
  let active = true;
  const frame = now => { if (!disposed) { updateTour(now); if (active) renderer.render(scene, camera); requestAnimationFrame(frame); } };
  frame();
  return {
    update,
    ready: Promise.all([starsPromise, dustPromise, modelPromise, modelColorsPromise, earthMapReady]).then(([starLayer, dustLayer, geometry, colors, earthLoaded]) => {
      if (!starLayer) throw new Error('Catalog star field did not load');
      if (!dustLayer) throw new Error('Calibrated Hubble WFC3/IR gas and star data did not load');
      if (!geometry || !colors || !model) throw new Error('Pillars gas geometry or infrared vertex colors did not load');
      if (!earthLoaded || earthMapState !== 'ready') throw new Error('Earth texture did not load');
      return { stars: starLayer.count + dustLayer.starCount, dustPoints: dustLayer.count, triangles: triangleCount, earthTexture: true, infraredFilter: 'HST WFC3/IR F110W + F160W' };
    }),
    travelFromEarth,
    resetView,
    stopTour() { tourRunning = false; },
    setActive(value) { active = Boolean(value); },
    dispose() {
      disposed = true; observer.disconnect(); renderer.dispose();
      if (model) { model.geometry.dispose(); modelMaterial.dispose(); }
      earth.geometry.dispose(); earth.material.dispose();
      earthMap.dispose();
      if (parallaxStars) {
        scene.remove(parallaxStars.points); group.remove(parallaxStars.localPoints);
        parallaxStars.geometry.dispose(); parallaxStars.material.dispose();
        parallaxStars.localGeometry.dispose(); parallaxStars.localMaterial.dispose();
      }
      if (hubbleVolume) {
        group.remove(hubbleVolume.points); group.remove(hubbleVolume.stars);
        hubbleVolume.geometry.dispose(); hubbleVolume.material.dispose();
        hubbleVolume.starsGeometry.dispose(); hubbleVolume.starsMaterial.dispose();
      }
    }
  };
}
