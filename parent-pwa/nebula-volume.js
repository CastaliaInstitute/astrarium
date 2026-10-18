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

/** Show the observed telescope frame and the source-attributed STScI 3D model.
 * The model's depth is an authored scientific visualization, not tomography.
 */
export function createNebulaVolume({ sourceCanvas, canvas, depthInput, referenceButton, modelStatus }) {
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

  const texture = new THREE.CanvasTexture(sourceCanvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  const frameGeometry = new THREE.PlaneGeometry(1, 1);
  const frameMaterial = new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide, transparent: true, opacity: 1, depthWrite: false });
  const imageFrame = new THREE.Mesh(frameGeometry, frameMaterial);
  imageFrame.position.z = 2.7;
  group.add(imageFrame);

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

  async function playTour() {
    await Promise.all([modelPromise, hubblePromise]);
    group.rotation.set(0, 0, 0);
    camera.position.set(0, 0, 7.2); camera.lookAt(0, 0, 0);
    frameMaterial.opacity = 0;
    depthInput.value = '0';
    const hubble = await hubblePromise;
    if (hubble) hubble.material.opacity = 1;
    tourStartedAt = performance.now(); tourRunning = true;
  }
  function smooth(t) { const x = THREE.MathUtils.clamp(t, 0, 1); return x * x * (3 - 2 * x); }
  const tourPath = [
    { t: 0,  p: [0, 0, 7.2], r: [0, 0, 0] },
    { t: 12, p: [0.1, 0.05, 5.1], r: [0.02, 0.1, 0] },
    { t: 28, p: [-0.15, 0.05, 3.5], r: [-0.04, 0.24, 0.03] },
    { t: 43, p: [-1.15, 0.55, 1.9], r: [0.08, 0.52, -0.05] },
    { t: 58, p: [0.95, 0.6, -1.35], r: [-0.06, 1.05, 0.08] },
    { t: 72, p: [1.15, -0.6, 1.6], r: [-0.12, 1.48, 0.04] },
    { t: 88, p: [0, 0, 6.4], r: [0, Math.PI * 2, 0] }
  ];
  function updateTour(now) {
    if (!tourRunning) return;
    const elapsed = (now - tourStartedAt) / 1000;
    if (elapsed >= 88) {
      tourRunning = false;
      group.rotation.set(0, 0, 0); camera.position.set(0, 0, 6.4); camera.lookAt(0, 0, 0);
      frameMaterial.opacity = 1; depthInput.value = '1';
      if (hubbleMaterial) hubbleMaterial.opacity = 0;
      if (modelStatus) modelStatus.textContent = 'Flythrough complete · JWST observation restored';
      return;
    }
    let index = 0;
    while (index < tourPath.length - 2 && elapsed > tourPath[index + 1].t) index++;
    const a = tourPath[index], b = tourPath[index + 1], u = smooth((elapsed - a.t) / (b.t - a.t));
    const mix = (x, y) => x + (y - x) * u;
    camera.position.set(mix(a.p[0], b.p[0]), mix(a.p[1], b.p[1]), mix(a.p[2], b.p[2]));
    camera.lookAt(0, 0, 0);
    group.rotation.set(mix(a.r[0], b.r[0]), mix(a.r[1], b.r[1]), mix(a.r[2], b.r[2]));
    let hubbleOpacity = 0, webbOpacity = 0;
    if (elapsed < 12) { hubbleOpacity = 1 - smooth(elapsed / 12); webbOpacity = smooth(elapsed / 12); }
    else if (elapsed < 24) webbOpacity = 1 - smooth((elapsed - 12) / 12);
    else if (elapsed >= 72) webbOpacity = smooth((elapsed - 72) / 16);
    frameMaterial.opacity = webbOpacity; depthInput.value = webbOpacity.toFixed(2);
    if (hubbleMaterial) hubbleMaterial.opacity = hubbleOpacity;
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
  }
  const observer = new ResizeObserver(resize); observer.observe(canvas); resize();
  const update = () => { texture.needsUpdate = true; };
  sourceCanvas.addEventListener?.('astrarium-image-updated', update);
  let active = true;
  const frame = now => { if (!disposed) { updateTour(now); if (active) renderer.render(scene, camera); requestAnimationFrame(frame); } };
  frame();
  return {
    update,
    playTour,
    stopTour() { tourRunning = false; },
    setActive(value) { active = Boolean(value); },
    dispose() {
      disposed = true; observer.disconnect(); renderer.dispose(); texture.dispose();
      frameGeometry.dispose(); frameMaterial.dispose();
      if (model) { model.geometry.dispose(); modelMaterial.dispose(); }
      if (hubbleMaterial) { hubbleMaterial.map?.dispose(); hubbleMaterial.dispose(); }
      placeholder.geometry.dispose(); placeholder.material.dispose();
    }
  };
}
