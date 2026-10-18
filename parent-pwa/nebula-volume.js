import * as THREE from './vendor/three.module.js';

const observationHost = ['localhost', '127.0.0.1'].includes(location.hostname)
  ? `${location.origin}/`
  : 'https://astrarium.castalia.institute/lcars/';
const MODEL_URL = new URL('observations/m16-jwst/pillars-stsci-mesh.bin.gz', observationHost).href;

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

async function loadSciencePointCloud() {
  const response = await fetch(new URL('observations/m16-jwst/m16-science-points.bin.gz', observationHost));
  if (!response.ok) throw new Error(`JWST science point cloud unavailable (${response.status})`);
  if (!('DecompressionStream' in window)) throw new Error('This browser cannot decompress JWST point data');
  const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
  const bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  if (new TextDecoder().decode(bytes.subarray(0, 8)) !== 'ASTPTS1\0') throw new Error('JWST point cloud has an unknown format');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const count = view.getUint32(8, true), positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3), sizes = new Float32Array(count);
  for (let i = 0, offset = 12; i < count; i++, offset += 8) {
    positions[i * 3] = (view.getUint16(offset, true) / 65535 - 0.5) * 2.1;
    positions[i * 3 + 1] = (0.5 - view.getUint16(offset + 2, true) / 65535) * 2.1;
    positions[i * 3 + 2] = -0.6;
    colors[i * 3] = view.getUint8(offset + 4) / 255;
    colors[i * 3 + 1] = view.getUint8(offset + 5) / 255;
    colors[i * 3 + 2] = view.getUint8(offset + 6) / 255;
    sizes[i] = Math.max(1, view.getUint8(offset + 7));
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
  const material = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, vertexColors: true, toneMapped: false,
    vertexShader: 'attribute float size; varying vec3 vColor; void main(){vColor=color;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=size;}',
    fragmentShader: 'varying vec3 vColor; void main(){float r=length(gl_PointCoord-vec2(0.5));if(r>0.5)discard;float a=0.92*(1.0-smoothstep(0.34,0.5,r));gl_FragColor=vec4(vColor,a);}'
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  points.renderOrder = 1;
  return { points, geometry, material, count };
}

/** Show the observed telescope frame and the source-attributed STScI 3D model.
 * The model's depth is an authored scientific visualization, not tomography.
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
  const viewFov = THREE.MathUtils.clamp(Number(params.get('viewFov')) || 42, 10, 100);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x02040a);
  const camera = new THREE.PerspectiveCamera(viewFov, 1, 0.01, 500);
  camera.position.set(0, 0, 6.4);
  scene.add(new THREE.AmbientLight(0xb9c9d8, 1.8));
  const keyLight = new THREE.DirectionalLight(0xffd9ae, 2.5);
  keyLight.position.set(4, 7, 8);
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0x377eb4, 1.6);
  rimLight.position.set(-5, -2, -4);
  scene.add(rimLight);
  const group = new THREE.Group();
  scene.add(group);

  const earth = new THREE.Mesh(new THREE.SphereGeometry(1.25, 48, 32), new THREE.MeshPhongMaterial({ color: 0x3479ac, shininess: 8 }));
  earth.position.set(1.8, 0.25, 20.5);
  scene.add(earth);
  let sciencePointCloud = null;
  const sciencePromise = loadSciencePointCloud().then(layer => {
    sciencePointCloud = layer;
    group.add(layer.points);
    if (modelStatus) modelStatus.textContent = `JWST science points ready · ${layer.count.toLocaleString()} samples`;
    return layer;
  }).catch(error => {
    if (modelStatus) modelStatus.textContent = `JWST point data unavailable · ${error.message || error}`;
    return null;
  });

  let model = null, modelMaterial = null, disposed = false, tourStartedAt = 0, tourRunning = false;
  const modelPromise = loadPillarsGeometry();
  const placeholder = new THREE.Mesh(new THREE.SphereGeometry(0.6, 12, 8), new THREE.MeshBasicMaterial({ color: 0x86b8d9 }));
  group.add(placeholder);
  modelPromise.then(geometry => {
    if (disposed) { geometry.dispose(); return; }
    modelMaterial = new THREE.MeshStandardMaterial({ color: 0xb5c7d0, roughness: 0.96, metalness: 0, side: THREE.DoubleSide });
    model = new THREE.Mesh(geometry, modelMaterial);
    const box = geometry.boundingBox;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const scale = 2.1 / Math.max(size.x, size.y, size.z);
    geometry.translate(-center.x, -center.y, -center.z);
    model.scale.setScalar(scale);
    model.position.set(0, 0, 0);
    model.rotation.x = -Math.PI / 2; // Rotate NASA's Z-up mesh into Three.js Y-up; source parts keep their shared placement.
    group.add(model);
    if (modelStatus) modelStatus.textContent = `NASA/STScI model ready · ${Math.round(geometry.index.count / 3).toLocaleString()} triangles`;
    group.remove(placeholder);
    placeholder.geometry.dispose(); placeholder.material.dispose();
  }).catch(error => {
    placeholder.material.color.set(0xf1a261);
    if (modelStatus) modelStatus.textContent = `NASA/STScI mesh unavailable · ${error.message || error}`;
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

  async function travelFromEarth() {
    await Promise.all([modelPromise, sciencePromise]);
    group.rotation.set(0, 0, 0);
    camera.position.fromArray(startPosition); camera.lookAt(...startLookAt);
    tourStartedAt = performance.now(); tourRunning = true;
  }
  function smooth(t) { const x = THREE.MathUtils.clamp(t, 0, 1); return x * x * (3 - 2 * x); }
  function updateTour(now) {
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
    travelFromEarth,
    resetView,
    stopTour() { tourRunning = false; },
    setActive(value) { active = Boolean(value); },
    dispose() {
      disposed = true; observer.disconnect(); renderer.dispose();
      if (model) { model.geometry.dispose(); modelMaterial.dispose(); }
      earth.geometry.dispose(); earth.material.dispose();
      if (sciencePointCloud) { group.remove(sciencePointCloud.points); sciencePointCloud.geometry.dispose(); sciencePointCloud.material.dispose(); }
      placeholder.geometry.dispose(); placeholder.material.dispose();
    }
  };
}
