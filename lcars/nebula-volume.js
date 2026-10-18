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

function makeStarLayer(rows, centerRaHours, centerDecDegrees) {
  if (!Array.isArray(rows) || !rows.length) return null;
  const ra0 = centerRaHours * Math.PI / 12, dec0 = centerDecDegrees * Math.PI / 180;
  const positions = [], colors = [], sizes = [];
  const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
  for (const star of rows.slice(1)) {
    const ra = Number(star[0]) * Math.PI / 12, dec = Number(star[1]) * Math.PI / 180, mag = Number(star[2]);
    if (!Number.isFinite(ra) || !Number.isFinite(dec) || !Number.isFinite(mag)) continue;
    const dra = ((ra - ra0 + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    const cosDec = Math.cos(dec), sinDec = Math.sin(dec), cosDec0 = Math.cos(dec0), sinDec0 = Math.sin(dec0);
    const cosc = sinDec0 * sinDec + cosDec0 * cosDec * Math.cos(dra);
    if (cosc <= 0.12) continue;
    const x = 20 * cosDec * Math.sin(dra) / cosc;
    const y = 20 * (cosDec0 * sinDec - sinDec0 * cosDec * Math.cos(dra)) / cosc;
    positions.push(x, y, 0);
    const bv = Number(star[3]);
    let rgb = [0.79, 0.84, 1.0];
    if (Number.isFinite(bv)) rgb = bv < 0.65
      ? mix([0.46, 0.64, 1], [0.86, 0.91, 1], Math.max(0, Math.min(1, (bv + 0.3) / 0.95)))
      : mix([0.86, 0.91, 1], [1, 0.62, 0.31], Math.min(1, (bv - 0.65) / 1.1));
    const brightness = Math.max(0.12, Math.min(1, Math.pow(10, (4.5 - mag) * 0.2)));
    colors.push(rgb[0] * brightness, rgb[1] * brightness, rgb[2] * brightness);
    sizes.push(Math.max(0.8, Math.min(4.2, 3.4 - (mag + 1.4) * 0.25)));
  }
  if (!positions.length) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  geometry.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));
  const material = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false,
    vertexShader: 'attribute float size; varying vec3 vColor; void main(){vColor=color;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=size;}',
    fragmentShader: 'varying vec3 vColor; void main(){float r=length(gl_PointCoord-vec2(0.5));float halo=exp(-r*10.0);float core=1.0-smoothstep(0.08,0.22,r);float alpha=max(halo*0.24,core);gl_FragColor=vec4(vColor*max(halo*0.55,core),alpha);}'
  });
  const points = new THREE.Points(geometry, material);
  points.position.z = -20;
  points.frustumCulled = false;
  return { points, geometry, material, count: positions.length / 3 };
}

/** Show the observed telescope frame and the source-attributed STScI 3D model.
 * The model's depth is an authored scientific visualization, not tomography.
 */
export function createNebulaVolume({ sourceCanvas, canvas, depthInput, referenceButton, modelStatus, centerRaHours = 18.3133, centerDecDegrees = -13.79 }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x02040a);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 500);
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

  const earth = new THREE.Mesh(new THREE.SphereGeometry(1.25, 48, 32), new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: 8 }));
  earth.position.set(1.8, 0.25, 20.5);
  scene.add(earth);
  const earthPromise = new THREE.TextureLoader().loadAsync(new URL('earth.png', observationHost).href).then(earthTexture => {
    earthTexture.colorSpace = THREE.SRGBColorSpace;
    earth.material.map = earthTexture;
    earth.material.needsUpdate = true;
    return earthTexture;
  });
  earthPromise.catch(error => { if (modelStatus) modelStatus.textContent = `Earth texture unavailable · ${error.message || error}`; });

  const texture = new THREE.CanvasTexture(sourceCanvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  const frameGeometry = new THREE.PlaneGeometry(1, 1);
  const frameMaterial = new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide, transparent: true, opacity: 1, depthWrite: false });
  const imageFrame = new THREE.Mesh(frameGeometry, frameMaterial);
  imageFrame.position.z = 2.7;
  group.add(imageFrame);
  // Project real catalog stars onto a distant sky plane around the target.
  // Their individual depths are not inferred from the 2D telescope image.
  let starLayer = null;
  const starCatalogPromise = fetch(new URL('stars.json', observationHost)).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).then(data => {
    starLayer = makeStarLayer(data.stars, centerRaHours, centerDecDegrees);
    if (starLayer) scene.add(starLayer.points);
    return starLayer;
  }).catch(error => {
    if (modelStatus) modelStatus.textContent = `Star catalog unavailable · ${error.message || error}`;
    return null;
  });

  let hubbleMaterial = null;
  const hubblePromise = new THREE.TextureLoader().loadAsync(new URL('observations/m16-hst/m16-wfc3uvis-mast-composite.png', observationHost).href).then(hubbleTexture => {
    hubbleTexture.colorSpace = THREE.SRGBColorSpace;
    hubbleTexture.minFilter = THREE.LinearFilter;
    hubbleTexture.magFilter = THREE.LinearFilter;
    const material = new THREE.MeshBasicMaterial({ map: hubbleTexture, side: THREE.DoubleSide, transparent: true, opacity: 0, depthWrite: false });
    hubbleMaterial = material;
    const frame = new THREE.Mesh(frameGeometry, material);
    frame.position.z = 2.69;
    group.add(frame);
    return { texture: hubbleTexture, material, frame };
  }).catch(error => {
    if (modelStatus) modelStatus.textContent = `Hubble transition image unavailable · ${error.message || error}`;
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
  depthInput.min = '0'; depthInput.max = '1'; depthInput.step = '0.01'; depthInput.value = '1';
  depthInput.addEventListener('input', () => {
    // Slider controls the exact telescope projection layer: 0 = model-only,
    // 1 = registered observation fully visible over the NASA model.
    frameMaterial.opacity = Number(depthInput.value);
  });
  function resetReference() {
    tourRunning = false;
    group.rotation.set(0, 0, 0); camera.position.set(0, 0, 6.4); camera.lookAt(0, 0, 0);
    depthInput.value = '1'; frameMaterial.opacity = 1;
    if (hubbleMaterial) hubbleMaterial.opacity = 0;
  }
  referenceButton.addEventListener('click', resetReference);

  async function travelFromEarth() {
    await Promise.all([modelPromise, earthPromise.catch(() => null), starCatalogPromise]);
    group.rotation.set(0, 0, 0);
    camera.position.set(0, 0, 26); camera.lookAt(0, 0, 0);
    frameMaterial.opacity = 0;
    depthInput.value = '0';
    if (hubbleMaterial) hubbleMaterial.opacity = 0;
    tourStartedAt = performance.now(); tourRunning = true;
  }
  function smooth(t) { const x = THREE.MathUtils.clamp(t, 0, 1); return x * x * (3 - 2 * x); }
  const tourPath = [
    { t: 0,  p: [0, 0, 26] },
    { t: 6,  p: [0, 0, 19] },
    { t: 13, p: [0, 0, 11] },
    { t: 22, p: [0, 0, 6.4] }
  ];
  function updateTour(now) {
    if (!tourRunning) return;
    const elapsed = (now - tourStartedAt) / 1000;
    earth.rotation.y += 0.0008;
    if (elapsed >= 22) {
      tourRunning = false;
      group.rotation.set(0, 0, 0); camera.position.set(0, 0, 6.4); camera.lookAt(0, 0, 0);
      frameMaterial.opacity = 0; depthInput.value = '0';
      if (hubbleMaterial) hubbleMaterial.opacity = 0;
      return;
    }
    let index = 0;
    while (index < tourPath.length - 2 && elapsed > tourPath[index + 1].t) index++;
    const a = tourPath[index], b = tourPath[index + 1], u = smooth((elapsed - a.t) / (b.t - a.t));
    const mix = (x, y) => x + (y - x) * u;
    camera.position.set(mix(a.p[0], b.p[0]), mix(a.p[1], b.p[1]), mix(a.p[2], b.p[2]));
    camera.lookAt(0, 0, 0);
  }

  function resize() {
    const width = Math.max(1, canvas.clientWidth), height = Math.max(1, canvas.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    // Match the image aspect and fit the same WCS-registered frame in reference view.
    const aspect = sourceCanvas.width / Math.max(1, sourceCanvas.height);
    const frameHeight = 2.1;
    imageFrame.scale.set(frameHeight * aspect, frameHeight, 1);
    starfieldFrame.scale.set(frameHeight * aspect * 28, frameHeight * 28, 1);
  }
  const observer = new ResizeObserver(resize); observer.observe(canvas); resize();
  const update = () => { texture.needsUpdate = true; };
  sourceCanvas.addEventListener?.('astrarium-image-updated', update);
  let active = true;
  const frame = now => { if (!disposed) { updateTour(now); if (active) renderer.render(scene, camera); requestAnimationFrame(frame); } };
  frame();
  return {
    update,
    travelFromEarth,
    stopTour() { tourRunning = false; },
    setActive(value) { active = Boolean(value); },
    dispose() {
      disposed = true; observer.disconnect(); renderer.dispose(); texture.dispose();
      frameGeometry.dispose(); frameMaterial.dispose();
      starfieldMaterial.map?.dispose(); starfieldMaterial.dispose();
      if (model) { model.geometry.dispose(); modelMaterial.dispose(); }
      if (hubbleMaterial) { hubbleMaterial.map?.dispose(); hubbleMaterial.dispose(); }
      earth.geometry.dispose(); earth.material.map?.dispose(); earth.material.dispose();
      if (starLayer) { scene.remove(starLayer.points); starLayer.geometry.dispose(); starLayer.material.dispose(); }
      placeholder.geometry.dispose(); placeholder.material.dispose();
    }
  };
}
