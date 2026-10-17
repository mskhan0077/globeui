/* Day/night island scene for the opening screen: one canvas and camera show the
   island with renewables by day (left of the divider) and on diesel at night
   (right). Ported from BlenderEarth's IslandScene.tsx.

   const scene = createIslandScene(host);   // host: positioned element to fill
   scene.setTransition(0.5);                // divider position, 0..1
   scene.dispose();                         */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { buildIslandWorld } from './island-world.js';

const ENERGY_KIT_URL = '/assets/models/blue-grid-energy-kit.glb';

export function createIslandScene(host, initialTransition = 0.5) {
  let target = clamp01(initialTransition);
  host.classList.add('island-scene');
  host.setAttribute('role', 'img');
  host.setAttribute('aria-label', 'A draggable day and night comparison of the same conceptual island: floating solar, offshore wind, wave buoys, OTEC and battery storage in daylight on the left; a diesel station, tanker and illuminated village at night on the right.');
  host.insertAdjacentHTML('afterbegin', fallbackSvg());
  const fallback = host.querySelector('.island-scene__fallback');
  const setFallbackSplit = () => {
    fallback.querySelector('[data-clip=left] rect').setAttribute('width', 960 * target);
    const right = fallback.querySelector('[data-clip=right] rect');
    right.setAttribute('x', 960 * target);
    right.setAttribute('width', 960 * (1 - target));
  };
  setFallbackSplit();

  // Leaves the host as it was, so a new scene can be created in it later.
  function cleanHost() {
    fallback.remove();
    host.querySelector('.island-scene__fallback-note')?.remove();
    host.classList.remove('is-ready');
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
  } catch {
    showUnavailable();
    return { setTransition(v) { target = clamp01(v); setFallbackSplit(); }, dispose: cleanHost };
  }

  let stopped = false, frame = 0, visible = !document.hidden, contextLost = false;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.autoClear = false;
  renderer.setClearColor(0x000000, 0);
  renderer.domElement.className = 'island-scene__canvas';
  renderer.domElement.setAttribute('aria-hidden', 'true');
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-17, 17, 12, -12, 0.1, 100);
  camera.position.set(20, 21, 29);
  camera.lookAt(0, 0.8, 0);
  const hemisphere = new THREE.HemisphereLight('#b4e1e8', '#294b54', 2.3);
  scene.add(hemisphere);
  const sun = new THREE.DirectionalLight('#fff0d0', 3.1);
  sun.position.set(-10, 18, 12);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 14, bottom: -14, near: 0.1, far: 65 });
  sun.shadow.bias = -0.0007;
  sun.shadow.normalBias = 0.025;
  sun.shadow.radius = 3;
  scene.add(sun);
  const rim = new THREE.DirectionalLight('#68bfd1', 1.4);
  rim.position.set(10, 10, -14);
  scene.add(rim);

  const model = buildIslandWorld();
  scene.add(model.world);
  host.dataset.assets = 'procedural';
  new GLTFLoader().load(ENERGY_KIT_URL, (gltf) => {
    if (stopped) { disposeObject(gltf.scene); return; }
    model.attachBlenderAsset(gltf.scene);
    host.dataset.assets = 'blender-glb';
    resume();
  }, undefined, () => { if (!stopped) host.dataset.assets = 'procedural-fallback'; });

  const motionMedia = window.matchMedia('(prefers-reduced-motion: reduce)');
  let motion = !motionMedia.matches, lastTime = performance.now(), elapsed = 0;
  let canvasWidth = 1, canvasHeight = 1;

  function draw(now) {
    frame = 0;
    if (stopped || contextLost) return;
    // RAF's timestamp can precede performance.now() on the first paint; clamp both ends.
    const delta = THREE.MathUtils.clamp((now - lastTime) / 1000, 0, 0.05);
    lastTime = now;
    if (motion) elapsed += delta;
    const split = Math.round(canvasWidth * target);
    renderer.setScissorTest(true);
    if (split > 0) { // day
      renderer.setScissor(0, 0, split, canvasHeight); renderer.clear();
      hemisphere.color.set('#c0e5ea'); hemisphere.groundColor.set('#294b54'); hemisphere.intensity = 2.35;
      sun.color.set('#fff1d3'); sun.intensity = 3.5; rim.color.set('#68bfd1'); rim.intensity = 1.4;
      renderer.toneMappingExposure = 1.08; model.update(elapsed, 1, motion); renderer.render(scene, camera);
    }
    if (split < canvasWidth) { // night
      renderer.setScissor(split, 0, canvasWidth - split, canvasHeight); renderer.clear();
      hemisphere.color.set('#65799f'); hemisphere.groundColor.set('#162b42'); hemisphere.intensity = 0.78;
      sun.color.set('#f0a976'); sun.intensity = 0.8; rim.color.set('#5d8bd2'); rim.intensity = 1.25;
      renderer.toneMappingExposure = 0.86; model.update(elapsed, 0, motion); renderer.render(scene, camera);
    }
    renderer.setScissorTest(false);
    if (visible && motion) frame = requestAnimationFrame(draw);
  }

  function resume() {
    if (!stopped && !contextLost && !frame && visible) {
      lastTime = performance.now();
      frame = requestAnimationFrame(draw);
    }
  }

  function resize() {
    const width = Math.max(host.clientWidth, 1), height = Math.max(host.clientHeight, 1), aspect = width / height;
    canvasWidth = width; canvasHeight = height;
    const span = aspect < 1 ? 27 / aspect : aspect < 1.4 ? 27 : 21.5;
    // Centred; the wider span keeps the turbine tips and the Explore button clear.
    model.world.position.set(0, 0, 0);
    camera.left = -span * aspect / 2; camera.right = span * aspect / 2;
    camera.top = span / 2; camera.bottom = -span / 2;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    resume();
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  const onVisibility = () => {
    visible = !document.hidden;
    if (visible) resume();
    else if (frame) { cancelAnimationFrame(frame); frame = 0; }
  };
  const onMotion = () => { motion = !motionMedia.matches; resume(); };
  const onLost = (event) => {
    event.preventDefault();
    contextLost = true;
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    host.classList.remove('is-ready');
    showUnavailable();
  };
  const onRestored = () => {
    contextLost = false;
    host.querySelector('.island-scene__fallback-note')?.remove();
    host.classList.add('is-ready');
    resume();
  };
  document.addEventListener('visibilitychange', onVisibility);
  motionMedia.addEventListener('change', onMotion);
  renderer.domElement.addEventListener('webglcontextlost', onLost);
  renderer.domElement.addEventListener('webglcontextrestored', onRestored);

  resize();
  if (frame) { cancelAnimationFrame(frame); frame = 0; }
  draw(performance.now());
  host.classList.add('is-ready');

  function showUnavailable() {
    if (host.querySelector('.island-scene__fallback-note')) return;
    host.insertAdjacentHTML('beforeend',
      '<span class="island-scene__fallback-note">Static scene · interactive controls remain available</span>');
  }

  return {
    setTransition(value) {
      target = clamp01(value);
      setFallbackSplit();
      resume(); // redraws once even when motion is reduced
    },
    dispose() {
      stopped = true;
      if (frame) cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      motionMedia.removeEventListener('change', onMotion);
      renderer.domElement.removeEventListener('webglcontextlost', onLost);
      renderer.domElement.removeEventListener('webglcontextrestored', onRestored);
      model.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
      cleanHost();
    },
  };
}

function clamp01(v) { return Math.min(1, Math.max(0, v)); }

function disposeObject(root) {
  root.traverse((object) => {
    if (object instanceof THREE.Mesh) {
      object.geometry.dispose();
      (Array.isArray(object.material) ? object.material : [object.material]).forEach((m) => m.dispose());
    }
  });
}

// Static SVG island shown until WebGL is ready, or instead of it when WebGL is unavailable.
function fallbackSvg() {
  const turbines = [290, 470, 648].map((x, i) => `<g transform="translate(${x} ${258 + i * 6})" fill="#dce9e3"><path d="M-4 0 4 0 3-113-6 0Z"/><g transform="translate(0 -113) rotate(${i * 42})"><path d="m-2 0 7-66 5 0-3 66Z"/>${[120, 240].map((a) => `<path d="m-2 0 7-66 5 0-3 66Z" transform="rotate(${a})"/>`).join('')}<circle r="6"/></g></g>`).join('');
  const panels = [0, 1, 2, 3].map((i) => `<rect x="${i * 24}" y="0" width="21" height="67"/>`).join('');
  const batteries = [0, 1, 2].map((i) => `<g transform="translate(${325 + i * 30} ${345 + i * 6})"><path d="m0 0 20-11 20 11-20 11Z" fill="#ecf0e6"/><path d="m0 0 20 11v47L0 47Z" fill="#92b7b7"/><path d="m20 11 20-11v47l-20 11Z" fill="#d9e5d9"/></g>`).join('');
  const houses = [0, 1, 2, 3, 4, 5].map((i) => `<g transform="translate(${491 + (i % 3) * 53} ${366 + Math.floor(i / 3) * 43})"><path d="m0 0 21-15 21 24-21 10Z" fill="#46666a"/><path d="m0 0 21 19v27L0 30Z" fill="#e0e6d7"/><path d="m21 19 21-10v27l-21 10Z" fill="#9ebcb1"/><path d="M6 15v8m24 1v8" stroke="#a3d8cf" stroke-width="5"/></g>`).join('');
  const palms = [249, 700, 439].map((x, i) => `<g transform="translate(${x} ${375 + i * 22})"><path d="m0 0 8-61" stroke="#aa9878" stroke-width="5"/><path d="m8-61-27 2 27-8 23 17-23-9-6 26-2-27-20-13Z" fill="#407864"/></g>`).join('');
  return `<svg class="island-scene__fallback" viewBox="0 0 960 650" aria-hidden="true">
    <defs>
      <radialGradient id="isl-sea"><stop stop-color="#287d81" stop-opacity=".65"/><stop offset="1" stop-color="#0d3e51" stop-opacity="0"/></radialGradient>
      <linearGradient id="isl-grass" x1="0" x2="1"><stop stop-color="#90b594"/><stop offset="1" stop-color="#437c74"/></linearGradient>
      <clipPath id="isl-left" data-clip="left"><rect width="480" height="650"/></clipPath>
      <clipPath id="isl-right" data-clip="right"><rect x="480" width="480" height="650"/></clipPath>
    </defs>
    <ellipse cx="490" cy="370" rx="450" ry="245" fill="url(#isl-sea)"/>
    <path d="M170 348 262 272 424 253 616 275 764 364 770 423 670 481 448 502 277 453 185 397Z" fill="#d5c5a2"/>
    <path d="M190 344 277 286 428 267 613 289 743 366 746 413 663 464 449 485 287 438 201 389Z" fill="url(#isl-grass)"/>
    <path d="m279 364 154-24 95 42 139 30m-139-30 35-73 110 58m-145 15-30 71-98-29" stroke="#c2c7aa" stroke-width="5" fill="none" opacity=".8"/>
    <g clip-path="url(#isl-left)">${turbines}<g transform="translate(134 390) skewY(18)" fill="#25618b" stroke="#a5c7cd" stroke-width="1.5">${panels}</g>${batteries}</g>
    <g clip-path="url(#isl-right)"><g transform="translate(250 -15)"><path d="m292 357 84-33 65 29-85 32Z" fill="#c18b63"/><path d="m292 357 64 28v50l-64-28Z" fill="#566a6c"/><path d="m356 385 85-32v47l-85 35Z" fill="#a7b6ac"/><path d="M321 352v-62m29 51v-62" stroke="#3b545c" stroke-width="10"/></g><ellipse cx="729" cy="484" rx="67" ry="18" fill="#304952"/><rect x="684" y="460" width="90" height="22" rx="9" fill="#a1b1ac"/></g>
    ${houses}${palms}
    <rect width="960" height="650" fill="#031126" opacity=".55" clip-path="url(#isl-right)"/>
  </svg>`;
}
