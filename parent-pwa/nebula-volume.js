import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { DRACOLoader } from './vendor/DRACOLoader.js';
import './vendor/geotiff.js';

const observationHost = ['localhost', '127.0.0.1'].includes(location.hostname)
  ? `${location.origin}/`
  : 'https://astrarium.castalia.institute/lcars/';
const HST_IR_PROJECTION_URL = new URL('observations/m16-hst/hubble-wfc3ir-volume.bin.gz?v=4', observationHost).href;
const SKY_CATALOG_URL = new URL('stars.json', observationHost).href;
const M16_GAIA_URL = new URL('observations/m16-jwst/gaia-dr3-wide-stars.json', observationHost).href;
const EARTH_MAP_URL = new URL('observations/earth-blue-marble.webp', observationHost).href;
const TERRAIN_API_URL = new URL('/api/v1/earth-terrain/', location.origin).href;
const JWST_MODEL_URL = new URL('models/jwst-nasa.glb', observationHost).href;
const HUBBLE_MODEL_URL = new URL('models/hubble-nasa.glb', observationHost).href;
// World coordinates in this view are light-years from Earth's position. NASA
// gives the Pillars a nominal Earth distance of 6,500 ly. The image field is
// placed at that distance as an observation plane; its depth is not measured.
const M16_DISTANCE_LY = 6500;
const M16_FIELD_WIDTH_ARCSEC = 260;
const M16_FIELD_HEIGHT_ARCSEC = 243.0415;
const M16_POSITION_ANGLE_DEG = 35.1;
const KILOMETERS_PER_LIGHT_YEAR = 9.460730472e12;
const EARTH_RADIUS_LY = 6371 / KILOMETERS_PER_LIGHT_YEAR;
const EARTH_RADIUS_KM = 6371;
const WGS84_EQUATORIAL_RADIUS_KM = 6378.137;
const WGS84_POLAR_RADIUS_KM = 6356.7523142;
const WGS84_ECCENTRICITY_SQUARED = 1 - (WGS84_POLAR_RADIUS_KM ** 2 / WGS84_EQUATORIAL_RADIUS_KM ** 2);
const OBSERVATORIES = {
  jwst: {
    name: 'JWST', modelUrl: JWST_MODEL_URL, modelSizeM: 21.197,
    time: '2022-08-19T08:11:48.360Z', timeBasis: 'FITS MJD-AVG',
    positionKm: [704566.3435096678, -1254992.0843262503, -801005.3019814028],
    positionSource: 'M16 NIRCam F444W calibrated Level 3 FITS OBSGEO-X/Y/Z',
    attitude: { raV1: 274.8870583990749, decV1: -13.839823482758614, paV3: 92.34742767851586 }
  },
  hubble: {
    name: 'Hubble', modelUrl: HUBBLE_MODEL_URL, modelSizeM: 13.2,
    time: '2014-09-07T05:42:01.027Z', timeBasis: 'FITS EXPSTART',
    positionKm: [-6614.32351139, -1271.45634271, -1623.01642716],
    positionSource: 'NAIF HST SPK hst.bsp, relative to Earth center in J2000 at FITS EXPSTART',
    attitude: { ra: 274.7172066667, dec: -13.8360555556, paV3: 280.001099 }
  }
};
const M16_RA = THREE.MathUtils.degToRad(274.7170416667);
const M16_DEC = THREE.MathUtils.degToRad(-13.8347916667);
const M16_PA = THREE.MathUtils.degToRad(M16_POSITION_ANGLE_DEG);
const M16_CENTER = new THREE.Vector3(Math.cos(M16_DEC) * Math.cos(M16_RA), Math.cos(M16_DEC) * Math.sin(M16_RA), Math.sin(M16_DEC));
const M16_EAST = new THREE.Vector3(-Math.sin(M16_RA), Math.cos(M16_RA), 0);
const M16_NORTH = new THREE.Vector3(-Math.sin(M16_DEC) * Math.cos(M16_RA), -Math.sin(M16_DEC) * Math.sin(M16_RA), Math.cos(M16_DEC));
const IMAGE_EAST = M16_EAST.clone().multiplyScalar(Math.cos(M16_PA)).addScaledVector(M16_NORTH, Math.sin(M16_PA));
const IMAGE_NORTH = M16_EAST.clone().multiplyScalar(-Math.sin(M16_PA)).addScaledVector(M16_NORTH, Math.cos(M16_PA));
function icrsToScene(x, y, z) {
  return new THREE.Vector3(x, y, z).applyMatrix3(new THREE.Matrix3().set(
    IMAGE_EAST.x, IMAGE_EAST.y, IMAGE_EAST.z,
    IMAGE_NORTH.x, IMAGE_NORTH.y, IMAGE_NORTH.z,
    M16_CENTER.x, M16_CENTER.y, M16_CENTER.z
  ));
}
function wgs84SurfacePosition(latitudeDeg, longitudeDeg, gmst, heightM = 0) {
  const latitude = THREE.MathUtils.degToRad(latitudeDeg);
  const longitudeAngle = gmst + THREE.MathUtils.degToRad(longitudeDeg);
  const sineLatitude = Math.sin(latitude), cosineLatitude = Math.cos(latitude);
  const primeVerticalKm = WGS84_EQUATORIAL_RADIUS_KM / Math.sqrt(1 - WGS84_ECCENTRICITY_SQUARED * sineLatitude ** 2);
  const heightKm = heightM / 1000;
  return icrsToScene(
    (primeVerticalKm + heightKm) * cosineLatitude * Math.cos(longitudeAngle) / KILOMETERS_PER_LIGHT_YEAR,
    (primeVerticalKm + heightKm) * cosineLatitude * Math.sin(longitudeAngle) / KILOMETERS_PER_LIGHT_YEAR,
    (primeVerticalKm * (1 - WGS84_ECCENTRICITY_SQUARED) + heightKm) * sineLatitude / KILOMETERS_PER_LIGHT_YEAR
  );
}
function gmstRadians(date) {
  const jd = date.getTime() / 86400000 + 2440587.5;
  const t = (jd - 2451545.0) / 36525;
  const deg = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t - t * t * t / 38710000;
  return THREE.MathUtils.degToRad(THREE.MathUtils.euclideanModulo(deg, 360));
}
function solarIcrsDirection(date) {
  const jd = date.getTime() / 86400000 + 2440587.5, n = jd - 2451545.0;
  const L = THREE.MathUtils.degToRad(THREE.MathUtils.euclideanModulo(280.460 + 0.9856474 * n, 360));
  const g = THREE.MathUtils.degToRad(THREE.MathUtils.euclideanModulo(357.528 + 0.9856003 * n, 360));
  const lambda = L + THREE.MathUtils.degToRad(1.915) * Math.sin(g) + THREE.MathUtils.degToRad(0.020) * Math.sin(2 * g);
  const epsilon = THREE.MathUtils.degToRad(23.439 - 0.0000004 * n);
  return new THREE.Vector3(Math.cos(lambda), Math.cos(epsilon) * Math.sin(lambda), Math.sin(epsilon) * Math.sin(lambda)).normalize();
}

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
  const decodedPositions = new Float32Array(count * 3), decodedColors = new Float32Array(count * 3), decodedAlphas = new Float32Array(count), indexes = [];
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
    decodedAlphas[i] = code / 127;
    indexes.push(i);
  }
  const makeLayer = entries => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(entries.length * 3), colors = new Float32Array(entries.length * 3), alphas = new Float32Array(entries.length);
    for (let j = 0; j < entries.length; j++) {
      const i = entries[j];
      positions.set(decodedPositions.subarray(i * 3, i * 3 + 3), j * 3);
      colors.set(decodedColors.subarray(i * 3, i * 3 + 3), j * 3);
      alphas[j] = decodedAlphas[i];
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('sampleAlpha', new THREE.BufferAttribute(alphas, 1));
    // The pixel values come from the Hubble display product. Keep their relative
    // brightness and let the unobserved/low-signal field edge dissolve to sky.
    const material = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, vertexColors: true, toneMapped: false,
      fragmentShader: '#include <common>\n#include <logdepthbuf_pars_fragment>\nvarying vec3 vColor; varying float vAlpha; void main(){float r=length(gl_PointCoord-vec2(0.5));if(r>0.5)discard;\n#include <logdepthbuf_fragment>\nfloat psf=1.0-smoothstep(0.12,0.5,r);gl_FragColor=vec4(vColor,psf*vAlpha*0.96);\n#include <colorspace_fragment>}',
      uniforms: { viewportHeight: { value: 1 } },
      vertexShader: '#include <common>\n#include <logdepthbuf_pars_vertex>\nuniform float viewportHeight; attribute float sampleAlpha; varying vec3 vColor; varying float vAlpha; void main(){vColor=color;vAlpha=sampleAlpha;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=max(1.0,' + (fieldWidthLy * 2 / 1800).toPrecision(9) + '*projectionMatrix[1][1]*viewportHeight/max(-mv.z,0.000001));\n#include <logdepthbuf_vertex>\n}'
    });
    const points = new THREE.Points(geometry, material);
    points.frustumCulled = false; points.renderOrder = 1;
    return { points, geometry, material, count: entries.length };
  };
  return makeLayer(indexes);
}

async function loadEarthSurfacePatch(latitude, longitude, gmst) {
  const radiusM = 500, size = 1024, segments = 512;
  const query = new URLSearchParams({ lat: String(latitude), lon: String(longitude), radiusM: String(radiusM), size: String(size) });
  const [demResponse, imageryResponse] = await Promise.all([
    fetch(`${TERRAIN_API_URL}dem?${query}`),
    fetch(`${TERRAIN_API_URL}imagery?${query}`)
  ]);
  if (!demResponse.ok) throw new Error(`3DEP elevation unavailable (${demResponse.status})`);
  if (!imageryResponse.ok) throw new Error(`USGS aerial imagery unavailable (${imageryResponse.status})`);
  const [demBytes, imageryBlob] = await Promise.all([demResponse.arrayBuffer(), imageryResponse.blob()]);
  const bounds = demResponse.headers.get('X-Astrarium-Terrain-Bounds');
  if (!bounds) throw new Error('Terrain tile is missing its geospatial bounds');
  const [west, south, east, north] = bounds.split(',').map(Number);
  if (![west, south, east, north].every(Number.isFinite)) throw new Error('Terrain tile bounds are invalid');
  const geotiff = await globalThis.GeoTIFF.fromArrayBuffer(demBytes);
  const image = await geotiff.getImage();
  const rasterWidth = segments + 1;
  const heights = await image.readRasters({ width: rasterWidth, height: rasterWidth, interleave: true });
  const noDataTag = image.getGDALNoData();
  const noData = noDataTag === null || noDataTag === undefined ? NaN : Number(noDataTag);
  const isValidHeight = height => Number.isFinite(height) && height > -1200 && height < 10000 && (!Number.isFinite(noData) || height !== noData);
  let validSamples = 0;
  for (const height of heights) if (isValidHeight(height)) validSamples++;
  if (validSamples < heights.length * 0.5) throw new Error('No 3DEP elevation coverage at this location');

  const bitmap = await createImageBitmap(imageryBlob);
  const texture = new THREE.Texture(bitmap);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.flipY = false;
  texture.needsUpdate = true;
  const positions = new Float32Array(rasterWidth * rasterWidth * 3);
  const uvs = new Float32Array(rasterWidth * rasterWidth * 2);
  const latitudeAt = row => north - (north - south) * row / segments;
  const longitudeAt = column => west + (east - west) * column / segments;
  const scenePosition = (latDeg, lonDeg, elevationM) => {
    const lat = THREE.MathUtils.degToRad(latDeg), angle = gmst + THREE.MathUtils.degToRad(lonDeg);
    const primeVerticalKm = WGS84_EQUATORIAL_RADIUS_KM / Math.sqrt(1 - WGS84_ECCENTRICITY_SQUARED * Math.sin(lat) ** 2);
    const heightKm = elevationM / 1000;
    return icrsToScene(
      (primeVerticalKm + heightKm) * Math.cos(lat) * Math.cos(angle) / KILOMETERS_PER_LIGHT_YEAR,
      (primeVerticalKm + heightKm) * Math.cos(lat) * Math.sin(angle) / KILOMETERS_PER_LIGHT_YEAR,
      (primeVerticalKm * (1 - WGS84_ECCENTRICITY_SQUARED) + heightKm) * Math.sin(lat) / KILOMETERS_PER_LIGHT_YEAR
    );
  };
  for (let row = 0; row <= segments; row++) for (let column = 0; column <= segments; column++) {
    const i = row * rasterWidth + column;
    const elevation = heights[i];
    const safeElevation = isValidHeight(elevation) ? elevation : 0;
    const point = scenePosition(latitudeAt(row), longitudeAt(column), safeElevation);
    positions.set([point.x, point.y, point.z], i * 3);
    uvs.set([column / segments, row / segments], i * 2);
  }
  const indices = new Uint32Array(segments * segments * 6);
  let offset = 0;
  for (let row = 0; row < segments; row++) for (let column = 0; column < segments; column++) {
    const a = row * rasterWidth + column, b = a + rasterWidth, c = a + 1, d = b + 1;
    indices.set([a, b, c, c, b, d], offset); offset += 6;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  geometry.computeVertexNormals();
  const material = new THREE.MeshStandardMaterial({ map: texture, roughness: 1, metalness: 0, side: THREE.DoubleSide });
  const terrain = new THREE.Mesh(geometry, material);
  terrain.frustumCulled = false;
  terrain.renderOrder = 1;
  return {
    terrain, geometry, material, texture, validSamples, sampleCount: heights.length,
    centerElevationM: (() => {
      const center = heights[(rasterWidth >> 1) * rasterWidth + (rasterWidth >> 1)];
      if (isValidHeight(center)) return center;
      const valid = Array.from(heights).filter(isValidHeight).sort((a, b) => a - b);
      return valid[Math.floor(valid.length / 2)];
    })(),
    resolutionM: radiusM * 2 / size
  };
}

async function loadParallaxStars(limitingMagnitude, observerUp) {
  const [catalogResponse, gaiaResponse] = await Promise.all([fetch(SKY_CATALOG_URL), fetch(M16_GAIA_URL)]);
  if (!catalogResponse.ok) throw new Error(`Astrarium star catalog unavailable (${catalogResponse.status})`);
  if (!gaiaResponse.ok) throw new Error(`M16 Gaia DR3 sources unavailable (${gaiaResponse.status})`);
  const [{ stars = [] }, gaia = {}] = await Promise.all([catalogResponse.json(), gaiaResponse.json()]);
  const centerRa = M16_RA;
  const centerDec = M16_DEC;
  const catalogStars = stars.filter(star => star.length > 6 && Number.isFinite(Number(star[6])) && Number(star[6]) > 0)
    .map(star => ({ ra: Number(star[0]), dec: Number(star[1]), magnitude: Number(star[2]), colorIndex: Number(star[3]), distancePc: Number(star[6]) }));
  const gaiaCenter = gaia.center_icrs_deg || [274.6995, -13.79];
  const gaiaRadiusDeg = Number(gaia.radius_deg) || 0;
  const gaiaStars = (gaia.stars || []).filter(star => {
    if (!(Number(star.parallax_mas) > 0)) return false;
    const ra = THREE.MathUtils.degToRad(Number(star.ra_deg));
    const dec = THREE.MathUtils.degToRad(Number(star.dec_deg));
    const tileRa = THREE.MathUtils.degToRad(Number(gaiaCenter[0]));
    const tileDec = THREE.MathUtils.degToRad(Number(gaiaCenter[1]));
    const dra = THREE.MathUtils.euclideanModulo(ra - tileRa + Math.PI, Math.PI * 2) - Math.PI;
    const cosc = Math.sin(tileDec) * Math.sin(dec) + Math.cos(tileDec) * Math.cos(dec) * Math.cos(dra);
    return gaiaRadiusDeg > 0 && cosc >= Math.cos(THREE.MathUtils.degToRad(gaiaRadiusDeg));
  })
    .map(star => ({
      ra: Number(star.ra_deg) / 15, dec: Number(star.dec_deg), magnitude: Number(star.g_mag),
      colorIndex: Number.isFinite(Number(star.bp_rp)) ? Number(star.bp_rp) - 0.2 : 0.7,
      distancePc: 1000 / Number(star.parallax_mas), localGaia: true
    }));
  // Keep catalog stars across the full field. Gaia entries replace only an
  // effectively coincident HYG entry, so the local catalog does not create holes.
  // Hash the local Gaia tile on a one-arcsecond grid to replace coincident
  // bright catalog entries without an O(N×M) scan of the full tile.
  const skyCell = (raHours, dec) => {
    const deltaRaDeg = THREE.MathUtils.euclideanModulo((raHours * 15 - THREE.MathUtils.radToDeg(centerRa)) + 180, 360) - 180;
    return [deltaRaDeg * Math.cos(centerDec) * 3600, (dec - THREE.MathUtils.radToDeg(centerDec)) * 3600];
  };
  const gaiaGrid = new Map();
  for (const star of gaiaStars) {
    const [x, y] = skyCell(star.ra, star.dec), key = `${Math.floor(x)},${Math.floor(y)}`;
    if (!gaiaGrid.has(key)) gaiaGrid.set(key, []);
    gaiaGrid.get(key).push([x, y]);
  }
  const visible = catalogStars.filter(star => {
    const [x, y] = skyCell(star.ra, star.dec), ix = Math.floor(x), iy = Math.floor(y);
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
      for (const [gx, gy] of gaiaGrid.get(`${ix + dx},${iy + dy}`) || []) if (Math.hypot(gx - x, gy - y) < 1) return false;
    }
    return true;
  }).concat(gaiaStars);
  const positions = new Float32Array(visible.length * 3);
  const colors = new Float32Array(visible.length * 3);
  const absoluteMagnitudes = new Float32Array(visible.length);
  const blueStar = new THREE.Color(0x9cbcff), warmStar = new THREE.Color(0xff9c57), starColor = new THREE.Color();
  let maxDistanceLy = 0;

  for (let i = 0; i < visible.length; i++) {
    const star = visible[i];
    const ra = THREE.MathUtils.degToRad(star.ra * 15);
    const dec = THREE.MathUtils.degToRad(star.dec);
    const distanceLy = star.distancePc * 3.26156;
    maxDistanceLy = Math.max(maxDistanceLy, distanceLy);
    // Positions use each catalog source's measured ICRS direction and distance.
    const sinDec = Math.sin(dec), cosDec = Math.cos(dec);
    const scenePosition = icrsToScene(cosDec * Math.cos(ra), cosDec * Math.sin(ra), sinDec).multiplyScalar(distanceLy);
    positions[i * 3] = scenePosition.x;
    positions[i * 3 + 1] = scenePosition.y;
    positions[i * 3 + 2] = scenePosition.z;

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
      uniforms: {
        limitingMagnitude: { value: limitingMagnitude },
        atmosphereDensity: { value: 1 },
        observerUp: { value: observerUp.clone() },
        skyMagnitudeLimit: { value: 6.5 }
      },
      transparent: true, depthWrite: false, vertexColors: true, toneMapped: false,
      vertexShader: '#include <common>\n#include <logdepthbuf_pars_vertex>\nuniform float limitingMagnitude;uniform float atmosphereDensity;uniform vec3 observerUp;uniform float skyMagnitudeLimit;attribute float absoluteMagnitude;varying vec3 vColor;varying float vFlux;varying float vVisible;void main(){vColor=color;vec4 mv=modelViewMatrix*vec4(position,1.0);float distancePc=max(length(mv.xyz)/3.26156,0.000001);float apparentMagnitude=absoluteMagnitude+5.0*log(distancePc/10.0)/log(10.0);vec3 direction=normalize(position-cameraPosition);float elevation=degrees(asin(clamp(dot(direction,normalize(observerUp)),-1.0,1.0)));float sineElevation=max(sin(radians(max(elevation,-5.0))),0.01);float airmass=1.0/(sineElevation+0.50572*pow(max(elevation+6.07995,0.01),-1.6364));float extinction=0.18*max(airmass-1.0,0.0)*atmosphereDensity;float observedMagnitude=apparentMagnitude+extinction;float visibilityLimit=min(limitingMagnitude,skyMagnitudeLimit);vVisible=step(observedMagnitude,visibilityLimit);float relativeFlux=pow(10.0,-0.4*(observedMagnitude-visibilityLimit));vFlux=1.0-exp(-0.22*relativeFlux);gl_Position=projectionMatrix*mv;gl_PointSize=2.8;\n#include <logdepthbuf_vertex>\n}',
      fragmentShader: '#include <common>\n#include <logdepthbuf_pars_fragment>\nvarying vec3 vColor;varying float vFlux;varying float vVisible;void main(){if(vVisible<0.5)discard;float r=length(gl_PointCoord-vec2(0.5));if(r>0.5)discard;\n#include <logdepthbuf_fragment>\nfloat psf=1.0-smoothstep(0.15,0.5,r);gl_FragColor=vec4(vColor,psf*vFlux);\n#include <colorspace_fragment>}'
    });
    const layerPoints = new THREE.Points(layerGeometry, layerMaterial);
  layerPoints.frustumCulled = false; layerPoints.renderOrder = 2;
  return {
    points: layerPoints, geometry: layerGeometry, material: layerMaterial, count: visible.length,
    gaiaCount: gaiaStars.length, gaiaRadiusDeg, maxDistanceLy
  };
}

async function loadLocalSkyWeather(latitude, longitude) {
  const url = new URL('https://api.open-meteo.com/v1/forecast');
  url.search = new URLSearchParams({
    latitude: String(latitude), longitude: String(longitude),
    current: 'cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high,relative_humidity_2m,visibility', timezone: 'UTC'
  }).toString();
  const response = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(8000) });
  if (!response.ok) throw new Error(`weather service returned ${response.status}`);
  const payload = await response.json();
  const current = payload.current;
  if (!current || !Number.isFinite(Number(current.cloud_cover))) throw new Error('weather response has no current cloud cover');
  return {
    cloudCover: THREE.MathUtils.clamp(Number(current.cloud_cover) / 100, 0, 1),
    lowCloudCover: THREE.MathUtils.clamp(Number(current.cloud_cover_low ?? current.cloud_cover) / 100, 0, 1),
    midCloudCover: THREE.MathUtils.clamp(Number(current.cloud_cover_mid ?? 0) / 100, 0, 1),
    highCloudCover: THREE.MathUtils.clamp(Number(current.cloud_cover_high ?? 0) / 100, 0, 1),
    humidity: THREE.MathUtils.clamp(Number(current.relative_humidity_2m) / 100 || 0, 0, 1),
    visibilityKm: THREE.MathUtils.clamp(Number(current.visibility) / 1000 || 20, 0.2, 100),
    time: current.time || new Date().toISOString()
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
  const telescopeFov = THREE.MathUtils.clamp(Number(params.get('telescopeFov')) || 12, 3, 42);
  const initialAspect = canvas.clientWidth > 0 && canvas.clientHeight > 0 ? canvas.clientWidth / canvas.clientHeight : 1;
  const hasExplicitEndFov = params.has('endFov');
  const matchedFieldFov = aspect => Math.max(
    M16_FIELD_HEIGHT_ARCSEC,
    M16_FIELD_WIDTH_ARCSEC / Math.max(aspect, 0.1)
  ) / 3600;
  let endFov = THREE.MathUtils.clamp(Number(params.get('endFov')) || matchedFieldFov(initialAspect), 0.005, 100);
  const observerLat = THREE.MathUtils.clamp(Number(params.get('observerLat')) || 0, -90, 90);
  const observerLon = THREE.MathUtils.euclideanModulo((Number(params.get('observerLon')) || 0) + 180, 360) - 180;
  const observerHeightM = Math.max(0, Number(params.get('observerHeightM')) || 2);
  const observatoryKey = params.get('observatory') === 'jwst' ? 'jwst' : 'hubble';
  const observatory = OBSERVATORIES[observatoryKey];
  const observationDate = params.has('observationTime') && Number.isFinite(Date.parse(params.get('observationTime')))
    ? new Date(params.get('observationTime')) : new Date(observatory.time);
  const observationPosition = icrsToScene(...observatory.positionKm.map(value => value / KILOMETERS_PER_LIGHT_YEAR));
  const startDate = params.has('startTime') && Number.isFinite(Date.parse(params.get('startTime'))) ? new Date(params.get('startTime')) : new Date();
  const gmst = gmstRadians(startDate), siteLatitude = THREE.MathUtils.degToRad(observerLat);
  const siteLongitude = THREE.MathUtils.degToRad(observerLon), siteAngle = gmst + siteLongitude;
  const observerUp = icrsToScene(Math.cos(siteLatitude) * Math.cos(siteAngle), Math.cos(siteLatitude) * Math.sin(siteAngle), Math.sin(siteLatitude)).normalize();
  const siteSurfacePosition = wgs84SurfacePosition(observerLat, observerLon, gmst);
  const earthReferenceRadiusLy = siteSurfacePosition.length();
  const startPosition = vectorParam('start', siteSurfacePosition.clone().addScaledVector(observerUp, observerHeightM / 1000 / KILOMETERS_PER_LIGHT_YEAR).toArray());
  const targetDirection = icrsToScene(M16_CENTER.x, M16_CENTER.y, M16_CENTER.z).normalize();
  const initialHorizontal = targetDirection.clone().addScaledVector(observerUp, -targetDirection.dot(observerUp));
  if (initialHorizontal.lengthSq() < 1e-12) initialHorizontal.set(1, 0, 0);
  initialHorizontal.normalize().addScaledVector(observerUp, 0.035).normalize();
  const surfaceLookAt = startPosition.map((value, index) => value + initialHorizontal.toArray()[index] * 1000);
  const startLookAt = vectorParam('startLookAt', surfaceLookAt);
  const endPosition = vectorParam('end', observationPosition.toArray());
  const endLookAt = vectorParam('endLookAt', [0, 0, M16_DISTANCE_LY]);
  const limitingMagnitude = THREE.MathUtils.clamp(Number(params.get('limitingMagnitude')) || 20.5, 5, 25);
  const destinationFrameVisible = params.get('destinationFrame') === '1';
  const duration = THREE.MathUtils.clamp(params.has('duration') ? Number(params.get('duration')) : 60, 1, 600);
  const waypointText = params.get('waypoints');
  const waypoints = waypointText ? waypointText.split(';').map(value => {
    const point = value.split(',').map(Number);
    return point.length === 3 && point.every(Number.isFinite) ? point : null;
  }).filter(Boolean) : [
    siteSurfacePosition.clone().addScaledVector(observerUp, 120 / KILOMETERS_PER_LIGHT_YEAR).toArray(),
    siteSurfacePosition.clone().addScaledVector(observerUp, 1000000 / KILOMETERS_PER_LIGHT_YEAR).toArray()
  ];
  const customWaypoints = Boolean(waypointText);
  const surfacePauseSeconds = THREE.MathUtils.clamp(params.has('surfaceSeconds') ? Number(params.get('surfaceSeconds')) : 6, 0, 60);
  const phaseTimes = [
    params.has('approachSeconds') ? Number(params.get('approachSeconds')) : duration * 0.3,
    params.has('telescopeSeconds') ? Number(params.get('telescopeSeconds')) : duration * 0.14,
    params.has('eyeSeconds') ? Number(params.get('eyeSeconds')) : duration * 0.08
  ].map(value => Math.max(duration * 0.04, Number.isFinite(value) ? value : 0));
  const phaseScale = Math.min(1, duration * 0.85 / phaseTimes.reduce((sum, value) => sum + value, 0));
  const [approachDuration, telescopeDuration, eyeDuration] = phaseTimes.map(value => value * phaseScale);
  const deepSpaceDuration = Math.max(0.5, duration - approachDuration - telescopeDuration - eyeDuration);
  const autoPlay = params.get('autoplay') !== '0';
  const startZoom = THREE.MathUtils.clamp(Number(params.get('startZoom')) || 1, 0.25, 4);
  const endZoom = THREE.MathUtils.clamp(Number(params.get('endZoom')) || 1, 0.25, 4);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power', logarithmicDepthBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x02040a);
  const camera = new THREE.PerspectiveCamera(viewFov, 1, 0.0000000000000001, 100000);
  camera.position.fromArray(autoPlay ? startPosition : endPosition);
  camera.zoom = autoPlay ? startZoom : endZoom;
  const orbitTarget = new THREE.Vector3(...(autoPlay ? startLookAt : endLookAt));
  camera.up.copy(autoPlay ? observerUp : new THREE.Vector3(0, 1, 0));
  camera.lookAt(orbitTarget);
  scene.add(camera);
  scene.add(new THREE.AmbientLight(0xffffff, 0.28));
  const solarLight = new THREE.DirectionalLight(0xffffff, 2.2);
  solarLight.position.copy(icrsToScene(...solarIcrsDirection(observationDate).toArray()).normalize()).multiplyScalar(1e-5);
  scene.add(solarLight);
  const telescope = new THREE.Group();
  telescope.visible = false;
  const telescopeMaterials = [];
  let telescopeModelLoaded = false;
  const att = observatory.attitude;
  const boresightRa = THREE.MathUtils.degToRad(att.raV1 ?? att.ra);
  const boresightDec = THREE.MathUtils.degToRad(att.decV1 ?? att.dec);
  const boresight = icrsToScene(Math.cos(boresightDec) * Math.cos(boresightRa), Math.cos(boresightDec) * Math.sin(boresightRa), Math.sin(boresightDec)).normalize();
  const attitudeEast = icrsToScene(-Math.sin(boresightRa), Math.cos(boresightRa), 0).normalize();
  const attitudeNorth = icrsToScene(-Math.sin(boresightDec) * Math.cos(boresightRa), -Math.sin(boresightDec) * Math.sin(boresightRa), Math.cos(boresightDec)).normalize();
  const roll = THREE.MathUtils.degToRad(att.paV3);
  const attitudeRight = attitudeEast.clone().multiplyScalar(Math.cos(roll)).addScaledVector(attitudeNorth, Math.sin(roll)).normalize();
  const attitudeUp = attitudeNorth.clone().multiplyScalar(Math.cos(roll)).addScaledVector(attitudeEast, -Math.sin(roll)).normalize();
  const telescopeWorldQuaternion = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(attitudeRight, attitudeUp, boresight));
  const telescopePosition = new THREE.Vector3(...endPosition);
  telescope.position.copy(telescopePosition);
  telescope.quaternion.copy(telescopeWorldQuaternion);
  telescope.userData.globalPositionKm = observatory.positionKm;
  scene.add(telescope);
  const modelApproachDistanceLy = observatory.modelSizeM * 12 / 1000 / KILOMETERS_PER_LIGHT_YEAR;
  const exteriorPosition = telescopePosition.clone().addScaledVector(boresight, -modelApproachDistanceLy);
  const routePositions = [startPosition, ...waypoints, exteriorPosition.toArray()];
  const routePoints = routePositions.map(position => new THREE.Vector3(...position));
  const initialLookAt = new THREE.Vector3(...startLookAt);
  const fieldCenter = new THREE.Vector3(...endLookAt);
  const fieldDirection = fieldCenter.clone().sub(telescopePosition).normalize();
  const imageUp = new THREE.Vector3(0, 1, 0);
  const visibleHalfHeightAtAspect = aspect => Math.max(imageHeightLy, imageWidthLy / Math.max(aspect, 0.1)) / 2;
  // The calibrated gas samples have an angular field but no measured depth.
  // End the camera path just before their globally positioned observation plane.
  let fieldArrivalPosition = fieldCenter.clone();
  const updateFieldArrivalPosition = aspect => {
    const distance = visibleHalfHeightAtAspect(aspect) * endZoom / Math.tan(THREE.MathUtils.degToRad(viewFov) / 2);
    fieldArrivalPosition.copy(fieldCenter).addScaledVector(fieldDirection, -distance);
  };
  updateFieldArrivalPosition(initialAspect);
  const cameraOrientation = (position, target, up) => {
    const pose = new THREE.PerspectiveCamera();
    pose.position.copy(position); pose.up.copy(up); pose.lookAt(target);
    return pose.quaternion.clone();
  };
  const exteriorOrientation = cameraOrientation(exteriorPosition, telescopePosition, attitudeUp);
  const eyeOrientation = cameraOrientation(telescopePosition, fieldCenter, imageUp);
  function setTelescopeOpacity(opacity) {
    for (const entry of telescopeMaterials) entry.material.opacity = entry.baseOpacity * opacity;
  }
  const telescopeReady = new Promise(resolve => {
    const loader = new GLTFLoader();
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath(new URL('vendor/draco/', observationHost).href);
    loader.setDRACOLoader(dracoLoader);
    loader.load(observatory.modelUrl, gltf => {
      const model = gltf.scene;
      const box = new THREE.Box3().setFromObject(model);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      const unitScale = (observatoryKey === 'hubble' ? 0.0254 : observatory.modelSizeM / Math.max(size.x, size.y, size.z)) / 1000 / KILOMETERS_PER_LIGHT_YEAR;
      model.position.set(-center.x * unitScale, -center.y * unitScale, -center.z * unitScale);
      model.scale.setScalar(unitScale);
      model.traverse(node => {
        if (!node.isMesh) return;
        node.frustumCulled = false;
        const prepareMaterial = source => {
          const material = source.clone();
          telescopeMaterials.push({ material, baseOpacity: material.opacity });
          material.side = THREE.DoubleSide; material.transparent = true; material.depthWrite = false;
          return material;
        };
        if (node.material) node.material = Array.isArray(node.material) ? node.material.map(prepareMaterial) : prepareMaterial(node.material);
      });
      telescope.add(model);
      telescopeModelLoaded = true;
      resolve(true);
    }, undefined, error => { console.warn(`${observatory.name} model unavailable`, error); resolve(false); });
  });
  const atmosphereUniforms = {
    observerUp: { value: observerUp.clone() },
    sunDirection: { value: icrsToScene(...solarIcrsDirection(startDate).toArray()).normalize() },
    density: { value: 1 },
    cloudCover: { value: 0 },
    haze: { value: 0 }
  };
  const atmosphereRadiusLy = WGS84_EQUATORIAL_RADIUS_KM / KILOMETERS_PER_LIGHT_YEAR + 120 / KILOMETERS_PER_LIGHT_YEAR;
  const atmosphere = new THREE.Mesh(new THREE.SphereGeometry(atmosphereRadiusLy, 48, 32), new THREE.ShaderMaterial({
    uniforms: atmosphereUniforms, side: THREE.BackSide, depthTest: false, depthWrite: false, toneMapped: false,
    vertexShader: 'varying vec3 vDirection; void main(){vec4 world=modelMatrix*vec4(position,1.0);vDirection=world.xyz-cameraPosition;gl_Position=projectionMatrix*viewMatrix*world;}',
    fragmentShader: 'uniform vec3 observerUp;uniform vec3 sunDirection;uniform float density;uniform float cloudCover;uniform float haze;varying vec3 vDirection;void main(){vec3 ray=normalize(vDirection);float elevation=dot(ray,normalize(observerUp));float sunElevation=dot(normalize(sunDirection),normalize(observerUp));float day=smoothstep(-0.30,0.0,sunElevation);float twilight=smoothstep(-0.32,-0.02,sunElevation)*(1.0-smoothstep(-0.14,0.08,sunElevation));float horizon=pow(1.0-abs(elevation),3.0);vec3 night=vec3(0.0015,0.003,0.009);vec3 zenith=vec3(0.018,0.12,0.38);vec3 sky=mix(night,mix(zenith,vec3(0.10,0.28,0.58),horizon),day*density);vec3 dusk=mix(vec3(0.03,0.05,0.14),vec3(0.70,0.20,0.045),horizon);sky=mix(sky,dusk,twilight*density);float sunGlow=pow(max(dot(ray,normalize(sunDirection)),0.0),18.0)*day*density;sky+=vec3(1.0,0.58,0.24)*sunGlow*0.8;vec3 overcast=mix(vec3(0.006,0.008,0.013),vec3(0.28,0.31,0.34),day);sky=mix(sky,overcast,cloudCover*density*0.88);sky=mix(sky,vec3(0.32,0.34,0.36),haze*density*0.3);gl_FragColor=vec4(sky,1.0);}'
  }));
  atmosphere.renderOrder = -10;
  scene.add(atmosphere);
  const group = new THREE.Group();
  scene.add(group);
  const destinationFrame = new THREE.Group();
  const halfWidth = imageWidthLy / 2, halfHeight = imageHeightLy / 2, frameZ = M16_DISTANCE_LY;
  const frameGeometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-halfWidth, -halfHeight, frameZ), new THREE.Vector3(halfWidth, -halfHeight, frameZ),
    new THREE.Vector3(halfWidth, halfHeight, frameZ), new THREE.Vector3(-halfWidth, halfHeight, frameZ)
  ]);
  const frameMaterial = new THREE.LineBasicMaterial({ color: 0xffa500, transparent: true, opacity: 0.9, depthTest: false, depthWrite: false });
  destinationFrame.add(new THREE.LineLoop(frameGeometry, frameMaterial));
  const tick = Math.min(imageWidthLy, imageHeightLy) * 0.025;
  const crosshairGeometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-tick, 0, frameZ), new THREE.Vector3(tick, 0, frameZ),
    new THREE.Vector3(0, -tick, frameZ), new THREE.Vector3(0, tick, frameZ)
  ]);
  destinationFrame.add(new THREE.LineSegments(crosshairGeometry, frameMaterial));
  destinationFrame.visible = destinationFrameVisible;
  scene.add(destinationFrame);

  let earthMapState = 'loading', resolveEarthMap;
  const earthMapReady = new Promise(resolve => { resolveEarthMap = resolve; });
  const earthMap = new THREE.TextureLoader().load(EARTH_MAP_URL,
    () => { earthMapState = 'ready'; updateModelStatus(); resolveEarthMap(true); },
    undefined,
    () => { earthMapState = 'failed'; updateModelStatus(); resolveEarthMap(false); }
  );
  earthMap.colorSpace = THREE.SRGBColorSpace;
  const siteSolarElevation = atmosphereUniforms.sunDirection.value.dot(observerUp);
  const surfaceIllumination = THREE.MathUtils.smoothstep(siteSolarElevation, -0.08, 0.05);
  const earthAlbedo = new THREE.Color().setScalar(0.025 + 0.975 * surfaceIllumination);
  const earth = new THREE.Mesh(
    new THREE.SphereGeometry(WGS84_EQUATORIAL_RADIUS_KM / KILOMETERS_PER_LIGHT_YEAR, 96, 64),
    new THREE.MeshBasicMaterial({ map: earthMap, color: earthAlbedo, toneMapped: false, side: THREE.DoubleSide })
  );
  earth.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(
    icrsToScene(Math.cos(gmst), Math.sin(gmst), 0),
    icrsToScene(0, 0, 1),
    icrsToScene(Math.sin(gmst), -Math.cos(gmst), 0)
  ));
  earth.scale.y = WGS84_POLAR_RADIUS_KM / WGS84_EQUATORIAL_RADIUS_KM;
  earth.frustumCulled = false;
  scene.add(earth);

  let starsState = 'loading', projectionState = 'loading', starsCount = 0, projectionCount = 0;
  let localWeather = null, weatherState = 'loading live weather…';
  let earthTerrainState = 'loading USGS terrain…', earthTerrainPatch = null;
  const updateModelStatus = () => {
    if (!modelStatus) return;
    const states = [
      starsState === 'ready' ? `${starsCount.toLocaleString()} catalog stars` : `stars ${starsState}`,
      projectionState === 'ready' ? `${projectionCount.toLocaleString()} Hubble IR samples · ${M16_DISTANCE_LY.toLocaleString()} ly · depth unknown` : `IR data ${projectionState}`,
      `${observerLat.toFixed(2)}°, ${observerLon.toFixed(2)}° · ${observationDate.toISOString()}`,
      `stellar limit ${limitingMagnitude.toFixed(1)} mag`,
      `Earth texture ${earthMapState}`,
      earthTerrainState,
      weatherState
    ];
    modelStatus.textContent = states.join(' · ');
  };
  updateModelStatus();
  const weatherPromise = loadLocalSkyWeather(observerLat, observerLon).then(weather => {
    localWeather = weather;
    atmosphereUniforms.cloudCover.value = weather.cloudCover;
    const poorVisibility = 1 - THREE.MathUtils.clamp((weather.visibilityKm - 1) / 19, 0, 1);
    atmosphereUniforms.haze.value = Math.max(poorVisibility, Math.max(0, weather.humidity - 0.72) * 0.55);
    weatherState = `live weather ${weather.time} · clouds ${Math.round(weather.cloudCover * 100)}% · visibility ${weather.visibilityKm.toFixed(1)} km`;
    updateModelStatus();
    return weather;
  }).catch(error => {
    weatherState = `live weather unavailable (${error.message || error})`;
    updateModelStatus();
    console.warn('Could not load local sky weather:', error);
    return null;
  });
  const weatherRefreshInterval = setInterval(() => {
    loadLocalSkyWeather(observerLat, observerLon).then(weather => {
      localWeather = weather;
      atmosphereUniforms.cloudCover.value = weather.cloudCover;
      const poorVisibility = 1 - THREE.MathUtils.clamp((weather.visibilityKm - 1) / 19, 0, 1);
      atmosphereUniforms.haze.value = Math.max(poorVisibility, Math.max(0, weather.humidity - 0.72) * 0.55);
      weatherState = `live weather ${weather.time} · clouds ${Math.round(weather.cloudCover * 100)}% · visibility ${weather.visibilityKm.toFixed(1)} km`;
      updateModelStatus();
    }).catch(error => {
      weatherState = `weather refresh failed; using last conditions (${error.message || error})`;
      updateModelStatus();
    });
  }, 10 * 60 * 1000);
  const cloudCoverAbove = (weather, altitudeKm) => {
    if (!weather) return 0;
    const layers = [
      weather.lowCloudCover * (1 - THREE.MathUtils.smoothstep(altitudeKm, 2.5, 4)),
      weather.midCloudCover * (1 - THREE.MathUtils.smoothstep(altitudeKm, 7, 9)),
      weather.highCloudCover * (1 - THREE.MathUtils.smoothstep(altitudeKm, 12, 16))
    ];
    return 1 - layers.reduce((transmission, cover) => transmission * (1 - cover), 1);
  };
  const earthTerrainPromise = loadEarthSurfacePatch(observerLat, observerLon, gmst).then(patch => {
    earthTerrainPatch = patch;
    scene.add(patch.terrain);
    if (!params.has('start')) {
      const cameraWasAtEarthStart = camera.position.distanceTo(new THREE.Vector3(...startPosition)) < 1e-18;
      const terrainGroundPosition = wgs84SurfacePosition(observerLat, observerLon, gmst, patch.centerElevationM);
      const startHeightM = params.has('observerHeightM') ? Math.max(patch.centerElevationM + 2, observerHeightM) : patch.centerElevationM + 2;
      const correctedStart = wgs84SurfacePosition(observerLat, observerLon, gmst, startHeightM).toArray();
      correctedStart.forEach((value, index) => { startPosition[index] = value; });
      if (!params.has('startLookAt')) {
        const lookAt = new THREE.Vector3(...startPosition).addScaledVector(initialHorizontal, 1000).toArray();
        lookAt.forEach((value, index) => { startLookAt[index] = value; });
      }
      initialLookAt.fromArray(startLookAt);
      routePoints[0].fromArray(startPosition);
      routePositions[0] = [...startPosition];
      if (!customWaypoints) {
        const earthClearance = [120, 1000000].map(km => terrainGroundPosition.clone().addScaledVector(observerUp, km / KILOMETERS_PER_LIGHT_YEAR));
        for (let index = 0; index < earthClearance.length; index++) {
          waypoints[index] = earthClearance[index].toArray();
          routePositions[index + 1] = [...waypoints[index]];
          routePoints[index + 1].copy(earthClearance[index]);
        }
      }
      if (cameraWasAtEarthStart || (tourRunning && (performance.now() - tourStartedAt) / 1000 < surfacePauseSeconds + 1)) {
        camera.position.fromArray(startPosition);
        orbitTarget.fromArray(startLookAt);
        camera.lookAt(orbitTarget);
      }
    }
    earthTerrainState = `USGS 3DEP ground + NAIP aerial · ${Math.round(patch.resolutionM * 10) / 10} m/pixel`;
    updateModelStatus();
    return patch;
  }).catch(error => {
    earthTerrainState = `local USGS terrain unavailable (${error.message || error})`;
    updateModelStatus();
    console.warn('Could not load local USGS 3DEP terrain:', error);
    return null;
  });
  let parallaxStars = null;
  const starsPromise = loadParallaxStars(limitingMagnitude, observerUp).then(layer => {
    parallaxStars = layer;
    scene.add(layer.points);
    layer.material.uniforms.limitingMagnitude.value = limitingMagnitude;
    const routeExtent = Math.max(...routePoints.map(position => position.length()), fieldArrivalPosition.length());
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
    layer.material.uniforms.viewportHeight.value = Math.max(1, canvas.clientHeight) * renderer.getPixelRatio();
    projectionState = 'ready'; projectionCount = layer.count; updateModelStatus();
    return layer;
  }).catch(error => {
    projectionState = `failed (${error.message || error})`; updateModelStatus();
    console.warn('Could not load calibrated Hubble infrared samples:', error);
    return null;
  });
  let disposed = false, tourStartedAt = 0, tourRunning = false, tourFinished = false, endpointView = !autoPlay;

  let dragging = false, previousX = 0, previousY = 0, surfaceLookActive = autoPlay;
  canvas.style.cursor = 'grab';
  canvas.addEventListener('pointerdown', event => {
    tourRunning = false;
    endpointView = false;
    dragging = true; previousX = event.clientX; previousY = event.clientY;
    canvas.setPointerCapture(event.pointerId); canvas.style.cursor = 'grabbing';
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging) return;
    if (surfaceLookActive) {
      camera.rotateOnWorldAxis(observerUp, -(event.clientX - previousX) * 0.004);
      camera.rotateX(-(event.clientY - previousY) * 0.004);
      previousX = event.clientX; previousY = event.clientY;
      return;
    }
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
    if (surfaceLookActive) {
      camera.zoom = THREE.MathUtils.clamp(camera.zoom * Math.exp(-event.deltaY * 0.001), 0.35, 4);
      camera.updateProjectionMatrix();
      return;
    }
    const offset = camera.position.clone().sub(orbitTarget);
    offset.setLength(THREE.MathUtils.clamp(offset.length() * Math.exp(event.deltaY * 0.001), 0.0001, 50000));
    camera.position.copy(orbitTarget).add(offset);
  }, { passive: false });
  function resetView() {
    tourRunning = false;
    telescope.visible = false;
    setTelescopeOpacity(1);
    surfaceLookActive = false;
    tourFinished = false;
    endpointView = true;
    group.rotation.set(0, 0, 0); camera.up.set(0, 1, 0); camera.position.fromArray(endPosition); orbitTarget.fromArray(endLookAt); camera.lookAt(orbitTarget);
    camera.fov = endFov; camera.zoom = endZoom; camera.updateProjectionMatrix();
  }

  function travelFromEarth() {
    endpointView = false;
    group.rotation.set(0, 0, 0);
    telescope.visible = false;
    setTelescopeOpacity(1);
    tourFinished = false;
    surfaceLookActive = true;
    camera.up.copy(observerUp);
    camera.position.fromArray(startPosition); orbitTarget.fromArray(startLookAt); camera.lookAt(orbitTarget);
    camera.fov = viewFov; camera.zoom = startZoom; camera.updateProjectionMatrix();
    tourStartedAt = performance.now(); tourRunning = true;
  }
  function smooth(t) { const x = THREE.MathUtils.clamp(t, 0, 1); return x * x * (3 - 2 * x); }
  function updateTour(now) {
    if (!tourRunning) return;
    const elapsed = (now - tourStartedAt) / 1000;
    if (elapsed < surfacePauseSeconds) return;
    const flightElapsed = elapsed - surfacePauseSeconds;
    const mixVectors = (a, b, t) => a.clone().lerp(b, t);
    const applyFraming = () => { camera.updateProjectionMatrix(); };
    if (flightElapsed < approachDuration) {
      telescope.visible = false;
      const routeProgress = smooth(flightElapsed / approachDuration) * (routePositions.length - 1);
      const routeIndex = Math.min(routePositions.length - 2, Math.floor(routeProgress));
      const routeMix = smooth(routeProgress - routeIndex);
      camera.position.copy(routePoints[routeIndex]).lerp(routePoints[routeIndex + 1], routeMix);
      const approachProgress = flightElapsed / approachDuration;
      orbitTarget.copy(mixVectors(initialLookAt, fieldCenter, smooth(approachProgress)));
      const altitudeKm = Math.max(0, (camera.position.length() - earthReferenceRadiusLy) * KILOMETERS_PER_LIGHT_YEAR);
      const atmoClearance = smooth(altitudeKm / 120);
      camera.up.copy(observerUp).lerp(imageUp, atmoClearance).normalize();
      const telescopeTurn = smooth((approachProgress - 0.82) / 0.18);
      orbitTarget.lerp(telescopePosition, telescopeTurn);
      camera.up.lerp(attitudeUp, telescopeTurn).normalize();
      surfaceLookActive = altitudeKm < 120;
      camera.lookAt(orbitTarget);
      camera.zoom = THREE.MathUtils.lerp(startZoom, 1, smooth(flightElapsed / approachDuration));
      camera.fov = THREE.MathUtils.lerp(viewFov, telescopeFov, telescopeTurn);
      applyFraming();
      return;
    }
    const poseElapsed = flightElapsed - approachDuration;
    if (poseElapsed < telescopeDuration) {
      telescope.visible = telescopeModelLoaded;
      camera.position.copy(exteriorPosition);
      camera.up.copy(attitudeUp);
      camera.lookAt(telescopePosition);
      camera.zoom = 1;
      camera.fov = telescopeFov;
      applyFraming();
      return;
    }
    const eyeElapsed = poseElapsed - telescopeDuration;
    if (eyeElapsed < eyeDuration) {
      const blend = smooth(eyeElapsed / eyeDuration);
      camera.position.copy(exteriorPosition).lerp(telescopePosition, blend);
      camera.quaternion.copy(exteriorOrientation).slerp(eyeOrientation, blend);
      camera.fov = THREE.MathUtils.lerp(telescopeFov, endFov, blend);
      camera.zoom = 1;
      setTelescopeOpacity(1 - smooth((blend - 0.35) / 0.55));
      telescope.visible = telescopeModelLoaded && blend < 0.96;
      surfaceLookActive = false;
      applyFraming();
      return;
    }
    setTelescopeOpacity(1);
    telescope.visible = false;
    surfaceLookActive = false;
    const deepElapsed = eyeElapsed - eyeDuration;
    const deepProgress = smooth(THREE.MathUtils.clamp(deepElapsed / deepSpaceDuration, 0, 1));
    camera.position.copy(telescopePosition).lerp(fieldArrivalPosition, deepProgress);
    orbitTarget.copy(fieldCenter);
    camera.quaternion.copy(eyeOrientation);
    const fieldDistance = Math.max(camera.position.distanceTo(fieldCenter), 1e-9);
    const visibleHalfHeight = visibleHalfHeightAtAspect(camera.aspect);
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(visibleHalfHeight / fieldDistance));
    camera.zoom = 1;
    applyFraming();
    if (deepElapsed >= deepSpaceDuration) { tourRunning = false; tourFinished = true; }
  }

  function resize() {
    const width = Math.max(1, canvas.clientWidth), height = Math.max(1, canvas.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    updateFieldArrivalPosition(camera.aspect);
    if (!hasExplicitEndFov) endFov = THREE.MathUtils.clamp(matchedFieldFov(camera.aspect), 0.005, 100);
    if (endpointView) { camera.position.fromArray(endPosition); orbitTarget.fromArray(endLookAt); camera.lookAt(orbitTarget); camera.fov = endFov; }
    else if (tourFinished) { camera.position.copy(fieldArrivalPosition); orbitTarget.copy(fieldCenter); camera.quaternion.copy(eyeOrientation); camera.fov = viewFov; camera.zoom = 1; }
    if (hubbleProjection) hubbleProjection.material.uniforms.viewportHeight.value = height * renderer.getPixelRatio();
    camera.updateProjectionMatrix();
  }
  const observer = new ResizeObserver(resize); observer.observe(canvas); resize();
  const update = () => {};
  let active = true;
  const frame = now => {
    if (disposed) return;
    updateTour(now);
    const altitudeKm = Math.max(0, (camera.position.length() - earthReferenceRadiusLy) * KILOMETERS_PER_LIGHT_YEAR);
    const atmosphereDensity = altitudeKm >= 120 ? 0 : Math.exp(-altitudeKm / 8.5);
    atmosphereUniforms.density.value = atmosphereDensity;
    atmosphere.visible = atmosphereDensity > 0.0001;
    if (parallaxStars) {
      const sunElevation = Math.asin(THREE.MathUtils.clamp(atmosphereUniforms.sunDirection.value.dot(observerUp), -1, 1));
      const daylight = THREE.MathUtils.smoothstep(sunElevation, THREE.MathUtils.degToRad(-18), THREE.MathUtils.degToRad(0));
      const clearSkyLimit = 6.5 - 10.5 * daylight;
      const weather = localWeather;
      const cloudFraction = cloudCoverAbove(weather, altitudeKm);
      const weatherPenalty = weather ? 5.4 * Math.pow(cloudFraction, 1.35) + Math.max(0, (20 - weather.visibilityKm) * 0.12) : 0;
      atmosphereUniforms.cloudCover.value = cloudFraction;
      parallaxStars.material.uniforms.atmosphereDensity.value = atmosphereDensity;
      parallaxStars.material.uniforms.skyMagnitudeLimit.value = limitingMagnitude + (clearSkyLimit - weatherPenalty - limitingMagnitude) * atmosphereDensity;
    }
    if (active) renderer.render(scene, camera);
    requestAnimationFrame(frame);
  };
  frame();
  return {
    update,
    ready: Promise.all([starsPromise, projectionPromise, earthMapReady, telescopeReady, earthTerrainPromise, weatherPromise]).then(([starLayer, projectionLayer, earthLoaded, telescopeLoaded, terrainPatch, weather]) => {
      if (!starLayer) throw new Error('Catalog star field did not load');
      if (!projectionLayer) throw new Error('Calibrated Hubble WFC3/IR projection did not load');
      if (!earthLoaded || earthMapState !== 'ready') throw new Error('Earth texture did not load');
      if (!telescopeLoaded) throw new Error(`${observatory.name} 3D model did not load`);
      return {
        stars: starLayer.count, gaiaStars: starLayer.gaiaCount, gaiaRadiusDeg: starLayer.gaiaRadiusDeg,
        diffuseSamples: projectionLayer.count, distanceLy: M16_DISTANCE_LY, fieldWidthLy: imageWidthLy,
        fieldHeightLy: imageHeightLy, infraredFilter: 'HST WFC3/IR F110W + F160W', limitingMagnitude,
        observerLat, observerLon, observationTime: observationDate.toISOString(),
        skyWeather: weather,
        earthTerrain: Boolean(terrainPatch), earthTerrainResolutionM: terrainPatch?.resolutionM || null,
        observatory: observatory.name, observatoryPositionKm: observatory.positionKm,
        observatoryPositionSource: observatory.positionSource, observatoryTimeBasis: observatory.timeBasis,
        observatoryAttitude: observatory.attitude, observatoryModelSizeM: observatory.modelSizeM
      };
    }),
    travelFromEarth,
    resetView,
    setDestinationFrame(value) { destinationFrame.visible = Boolean(value); },
    destinationFrameVisible: () => destinationFrame.visible,
    stopTour() { tourRunning = false; },
    setActive(value) { active = Boolean(value); },
    dispose() {
      disposed = true; observer.disconnect(); clearInterval(weatherRefreshInterval); renderer.dispose();
      earth.geometry.dispose(); earth.material.dispose(); earthMap.dispose();
      if (earthTerrainPatch) {
        scene.remove(earthTerrainPatch.terrain);
        earthTerrainPatch.geometry.dispose(); earthTerrainPatch.material.dispose(); earthTerrainPatch.texture.dispose();
        earthTerrainPatch.texture.image?.close?.();
      }
      atmosphere.geometry.dispose(); atmosphere.material.dispose();
      frameGeometry.dispose(); crosshairGeometry.dispose(); frameMaterial.dispose();
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
