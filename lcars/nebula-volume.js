import * as THREE from './vendor/three.module.js';

const MODEL_URL = 'https://astrarium.castalia.institute/lcars/observations/m16-jwst/pillars-stsci-mesh.bin.gz';

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

  let model = null, modelMaterial = null, disposed = false;
  const placeholder = new THREE.Mesh(new THREE.SphereGeometry(0.6, 12, 8), new THREE.MeshBasicMaterial({ color: 0x86b8d9 }));
  group.add(placeholder);
  loadPillarsGeometry().then(geometry => {
    if (disposed) { geometry.dispose(); return; }
    modelMaterial = new THREE.MeshStandardMaterial({ color: 0xb5c7d0, roughness: 0.96, metalness: 0, side: THREE.DoubleSide });
    model = new THREE.Mesh(geometry, modelMaterial);
    const box = geometry.boundingBox;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const scale = 2.1 / Math.max(size.x, size.y, size.z);
    model.position.copy(center).multiplyScalar(-scale);
    model.scale.setScalar(scale);
    model.rotation.x = 0; // NASA visualization coordinates; orientation can be tuned against MUSE constraints.
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
    camera.position.z = THREE.MathUtils.clamp(camera.position.z + event.deltaY * 0.035, 2.5, 30);
  }, { passive: false });
  depthInput.min = '0'; depthInput.max = '1'; depthInput.step = '0.01'; depthInput.value = '1';
  depthInput.addEventListener('input', () => {
    // Slider controls the exact telescope projection layer: 0 = model-only,
    // 1 = registered observation fully visible over the NASA model.
    frameMaterial.opacity = Number(depthInput.value);
  });
  referenceButton.addEventListener('click', () => {
    group.rotation.set(0, 0, 0); camera.position.set(0, 0, 6.4); camera.lookAt(0, 0, 0);
    depthInput.value = '1'; frameMaterial.opacity = 1;
  });

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
  const frame = () => { if (!disposed) { if (active) renderer.render(scene, camera); requestAnimationFrame(frame); } };
  frame();
  return {
    update,
    setActive(value) { active = Boolean(value); },
    dispose() {
      disposed = true; observer.disconnect(); renderer.dispose(); texture.dispose();
      frameGeometry.dispose(); frameMaterial.dispose();
      if (model) { model.geometry.dispose(); modelMaterial.dispose(); }
      placeholder.geometry.dispose(); placeholder.material.dispose();
    }
  };
}
