/* The opening scene's island, energy kit and animation (Three.js).
   Converted from BlenderEarth src/components/story/buildIslandWorld.ts
   (~/BlueGrid/UIUX/BlenderEarth) with esbuild: types stripped, logic unchanged except
   WIND_FIXES (a turbine that stood on a solar raft). */
import * as THREE from "three";
// The Blender model's Wind_2 stands on Floating_PV_0 (raft at x -9.6..-6.6, z -0.7..2.3);
// move it into open water between the raft and the islet behind (x -10.8..-6.1, z -6.8..-3.6). [node name, x, z]
const WIND_FIXES = [["Wind_2", -9.6, -2.2]];

function buildIslandWorld() {
  const world = new THREE.Group();
  world.rotation.y = -0.2;
  const renewable = new THREE.Group();
  const diesel = new THREE.Group();
  diesel.position.set(5, 0, -1.5);
  world.add(renewable, diesel);
  const materials = /* @__PURE__ */ new Set();
  const geometries = /* @__PURE__ */ new Set();
  const fades = { renewable: [], diesel: [] };
  let currentFade;
  const geometry = (g) => {
    geometries.add(g);
    return g;
  };
  const material = (color, params = {}) => {
    const m = new THREE.MeshStandardMaterial({ color, roughness: 0.78, metalness: 0.04, ...params });
    materials.add(m);
    if (currentFade) {
      m.transparent = true;
      currentFade.push({ material: m, opacity: m.opacity });
    }
    return m;
  };
  const base = {
    wall: material("#d8e3da"),
    roof: material("#627a7c"),
    sand: material("#decdaa"),
    stone: material("#4e747b"),
    timber: material("#8d8571"),
    window: material("#9ddfdd", { emissive: "#2a7b7d", emissiveIntensity: 0.15 }),
    leaf: material("#488b70"),
    grass: material("#739a7a"),
    road: material("#bec2ab"),
    trunk: material("#96846b")
  };
  const mesh = (g, m, parent, x, y, z) => {
    const object = new THREE.Mesh(g, m);
    object.position.set(x, y, z);
    object.castShadow = true;
    object.receiveShadow = true;
    parent.add(object);
    return object;
  };
  const box = (w, h, d, m, x = 0, y = 0, z = 0, parent = world) => mesh(geometry(new THREE.BoxGeometry(w, h, d)), m, parent, x, y, z);
  const cylinder = (top, bottom, h, m, x = 0, y = 0, z = 0, parent = world) => mesh(geometry(new THREE.CylinderGeometry(top, bottom, h, 12)), m, parent, x, y, z);
  const sphereGeometry = geometry(new THREE.SphereGeometry(1, 10, 7));
  const sphere = (m, x, y, z, sx, sy = sx, sz = sx, parent = world) => {
    const s = mesh(sphereGeometry, m, parent, x, y, z);
    s.scale.set(sx, sy, sz);
    return s;
  };
  const curveMesh = (points, m, radius, parent = world) => {
    const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(p[0], p[1], p[2])));
    mesh(geometry(new THREE.TubeGeometry(curve, 35, radius, 6, false)), m, parent, 0, 0, 0);
    return curve;
  };
  const line = (points, color, opacity, parent = world) => {
    const m = new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false });
    materials.add(m);
    if (currentFade) currentFade.push({ material: m, opacity });
    const object = new THREE.Line(geometry(new THREE.BufferGeometry().setFromPoints(points)), m);
    parent.add(object);
    return object;
  };
  const waterMaterial = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: { uTime: { value: 0 }, uTransition: { value: 1 } },
    vertexShader: `varying vec2 vUv;
      void main() { vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `varying vec2 vUv; uniform float uTime; uniform float uTransition;
      void main() {
        vec2 p=(vUv-.5)*2.;
        float r=length(p*vec2(.94,1.));
        float edge=1.-smoothstep(.62,1.,r);
        float swells=sin(p.x*43.+p.y*17.+uTime*.3)*sin(p.y*54.-uTime*.2);
        float glint=pow(max(0.,sin(p.x*145.+p.y*51.+sin(p.y*33.+uTime*.4)))*max(0.,sin(p.y*230.-uTime*.6)),20.);
        float contour=pow(max(0.,sin(r*125.-uTime*.24)),26.)*.008;
        vec3 deep=mix(vec3(.022,.07,.1),vec3(.017,.13,.19),uTransition);
        vec3 shallow=mix(vec3(.05,.15,.17),vec3(.055,.32,.35),uTransition);
        vec3 col=mix(deep,shallow,(1.-smoothstep(.16,.71,r))*.55);
        col+=swells*.008+glint*.13+contour;
        gl_FragColor=vec4(col,edge*.8);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`
  });
  materials.add(waterMaterial);
  const water = new THREE.Mesh(geometry(new THREE.PlaneGeometry(43, 37)), waterMaterial);
  water.rotation.x = -Math.PI / 2;
  water.position.y = -0.23;
  water.renderOrder = -10;
  water.receiveShadow = true;
  world.add(water);
  const coastPoints = (rx, rz, phase = 0) => Array.from({ length: 76 }, (_, i) => {
    const a = i / 76 * Math.PI * 2;
    const edge = 1 + 0.045 * Math.sin(a * 5 + phase) + 0.029 * Math.cos(a * 8 + phase);
    return new THREE.Vector2(Math.cos(a) * rx * edge, Math.sin(a) * rz * edge);
  });
  const reefMaterials = [];
  function island(x, z, rx, rz, phase) {
    const group = new THREE.Group();
    group.position.set(x, 0, z);
    world.add(group);
    const coast = coastPoints(rx, rz, phase);
    const layer = (scale, y, thickness, m) => {
      const outline = coast.map((p) => p.clone().multiplyScalar(scale));
      const shape = new THREE.Shape(outline);
      const g = geometry(new THREE.ExtrudeGeometry(shape, { depth: thickness, bevelEnabled: false }));
      g.rotateX(-Math.PI / 2);
      g.translate(0, y - thickness, 0);
      return mesh(g, m, group, 0, 0, 0);
    };
    const reef = material("#339a9b", { transparent: true, opacity: 0.15, depthWrite: false });
    reefMaterials.push(reef);
    layer(1.24, -0.15, 0.02, reef);
    layer(1.035, 0.17, 0.28, base.sand);
    layer(0.945, 0.3, 0.14, base.grass);
    for (let j = 0; j < 3; j++) {
      const points = coast.map((p) => new THREE.Vector3(p.x * (1.05 + j * 0.06), -0.12, p.y * (1.05 + j * 0.06)));
      points.push(points[0].clone());
      line(points, "#9ac5b5", 0.3 - j * 0.07, group);
    }
    return group;
  }
  island(1.5, 1, 6.9, 4, 0.4);
  island(-8.4, -5.2, 2.35, 1.55, 1.7);
  island(8.6, -5.3, 2.8, 1.45, 2.1);
  island(11.5, 3.8, 1.25, 0.7, 1);
  curveMesh([[-4, 0.33, 1.6], [-2, 0.34, 1], [0.5, 0.34, 0.8], [3, 0.34, 1.5], [5.7, 0.34, 2.1], [7, 0.34, 1.2]], base.road, 0.13);
  curveMesh([[1, 0.34, 0.9], [0.4, 0.34, 2.3], [1.2, 0.34, 3.6], [3.3, 0.34, 3.4], [5.7, 0.34, 2.1]], base.road, 0.1);
  curveMesh([[0.6, 0.34, 0.8], [1.4, 0.34, -0.9], [4, 0.34, -1.2], [6, 0.34, 0.2], [5.7, 0.34, 2.1]], base.road, 0.1);
  function house(x, z, scale, roof = base.roof) {
    const h = new THREE.Group();
    h.position.set(x, 0.33, z);
    h.scale.setScalar(scale);
    world.add(h);
    box(0.7, 0.7, 0.88, base.wall, 0, 0.35, 0, h);
    const roofObject = mesh(geometry(new THREE.ConeGeometry(0.71, 0.34, 4)), roof, h, 0, 0.88, 0);
    roofObject.rotation.y = Math.PI / 4;
    roofObject.scale.z = 1.2;
    box(0.16, 0.31, 0.03, base.timber, -0.1, 0.16, 0.45, h);
    for (const wx of [-0.23, 0.23]) box(0.14, 0.18, 0.035, base.window, wx, 0.49, 0.45, h);
    box(0.027, 0.2, 0.22, base.window, 0.36, 0.48, 0.1, h);
    box(0.09, 0.18, 0.12, base.sand, 0.2, 0.88, -0.13, h);
  }
  [[1.5, 2.15, 1], [2.8, 2.7, 0.85], [4.2, 3.1, 1.05], [5.6, 1.15, 0.92], [6.8, 0.2, 0.82], [4.8, -0.2, 0.88], [3.1, -0.7, 0.95], [1.6, -0.9, 0.8], [0.1, 3.2, 0.9], [-1.3, 2.4, 0.84], [-2.6, 1.9, 0.9]].forEach((p) => house(p[0], p[1], p[2]));
  box(1.3, 0.85, 1.25, base.wall, 1, 0.76, 0.05);
  box(1.46, 0.13, 1.38, base.roof, 1, 1.24, 0.05);
  box(0.68, 0.43, 0.04, base.window, 1, 0.78, 0.69);
  cylinder(0.34, 0.34, 0.72, base.wall, 5.5, 0.72, -1.1);
  cylinder(0.38, 0.38, 0.08, base.roof, 5.5, 1.13, -1.1);
  const frondGeometry = geometry(new THREE.SphereGeometry(1, 7, 4));
  const palms = new THREE.Group();
  world.add(palms);
  function palm(x, z, h, lean) {
    const p = new THREE.Group();
    p.position.set(x, 0.31, z);
    p.rotation.z = lean;
    palms.add(p);
    cylinder(0.04, 0.075, h, base.trunk, 0, h / 2, 0, p);
    for (let k = 0; k < 7; k++) {
      const a = k * Math.PI * 2 / 7;
      const leaf = mesh(frondGeometry, base.leaf, p, Math.sin(a) * 0.36, h - 0.03, Math.cos(a) * 0.36);
      leaf.scale.set(0.115, 0.055, 0.62);
      leaf.rotation.y = a;
      leaf.rotation.x = 0.15;
    }
    sphere(base.leaf, 0, h - 0.03, 0, 0.17, 0.12, 0.17, p);
  }
  [[-4.6, 1.4, 1.3, -0.14], [-3.7, 2.8, 1.55, 0.1], [-1.8, 3.8, 1.4, -0.1], [0.2, 4.5, 1.6, 0.1], [3, 4.2, 1.35, -0.1], [6, 3, 1.6, 0.1], [7.4, 1, 1.25, -0.12], [6.7, -0.9, 1.4, 0.12], [-3.8, -0.8, 1.3, 0.14], [-1.9, -1.7, 1.35, -0.1], [-8.4, -5.3, 1.7, -0.12], [-7.5, -4.9, 1.25, 0.1], [8.5, -5.1, 1.5, 0.1], [9.6, -5.4, 1.65, -0.1], [11.5, 3.8, 1.2, 0.12]].forEach((p) => palm(p[0], p[1], p[2], p[3]));
  for (let i = 0; i < 24; i++) {
    const a = i * 2.39996, r = 3.2 + i % 3 * 1.15;
    const x = 1.5 + Math.cos(a) * r, z = 1 + Math.sin(a) * r * 0.56;
    sphere(base.leaf, x, 0.4, z, 0.22 + i % 3 * 0.06, 0.18, 0.24);
  }
  box(1.05, 0.12, 2.9, base.timber, 7.5, 0.14, 3.6);
  box(2, 0.12, 0.55, base.timber, 7.5, 0.14, 5.1);
  for (let i = 0; i < 8; i++) box(1.05, 0.012, 0.022, base.sand, 7.5, 0.208, 2.3 + i * 0.35);
  for (const x of [7.06, 7.94]) for (const z of [2.4, 3.65, 4.9]) cylinder(0.035, 0.035, 0.6, base.stone, x, -0.02, z);
  currentFade = fades.diesel;
  const dm = { dark: material("#3f5358"), orange: material("#bd8050"), metal: material("#a5b1ae"), black: material("#2b3d43"), light: material("#e1bd7f", { emissive: "#a96f31", emissiveIntensity: 0.22 }) };
  box(3.5, 0.1, 2.4, dm.dark, -2.6, 0.36, -0.15, diesel);
  box(2.15, 0.9, 1.3, dm.metal, -2.7, 0.86, -0.1, diesel);
  box(2.35, 0.12, 1.48, dm.orange, -2.7, 1.36, -0.1, diesel);
  for (const x of [-3.35, -2.65, -1.95]) {
    box(0.48, 0.48, 0.07, dm.black, x, 0.85, 0.59, diesel);
    for (let i = 0; i < 4; i++) box(0.38, 0.018, 0.035, dm.metal, x, 0.69 + i * 0.1, 0.64, diesel);
  }
  for (const x of [-3.25, -2.35]) {
    cylinder(0.09, 0.11, 1.65, dm.dark, x, 1.92, -0.48, diesel);
    cylinder(0.13, 0.13, 0.08, dm.metal, x, 2.78, -0.48, diesel);
  }
  const fuelTank = cylinder(0.4, 0.4, 0.85, dm.metal, -0.8, 0.87, -0.3, diesel);
  fuelTank.rotation.z = Math.PI / 2;
  box(0.22, 0.23, 0.22, dm.dark, -1.12, 0.51, -0.3, diesel);
  box(0.22, 0.23, 0.22, dm.dark, -0.48, 0.51, -0.3, diesel);
  const smoke = [];
  for (let i = 0; i < 12; i++) {
    const m = material("#75818d", { transparent: true, opacity: 0.15 + i % 3 * 0.05, depthWrite: false, roughness: 1 });
    const x = i % 2 ? -3.25 : -2.35;
    const object = sphere(m, x, 3 + i % 6 * 0.35, -0.48, 0.24, 0.3, 0.24, diesel);
    object.castShadow = false;
    smoke.push({ object, phase: i % 6 / 6, x });
  }
  const tanker = new THREE.Group();
  tanker.position.set(5.5, -0.01, 7);
  tanker.rotation.y = -0.35;
  diesel.add(tanker);
  const hull = mesh(geometry(new THREE.CapsuleGeometry(0.5, 2.8, 4, 8)), dm.dark, tanker, 0, 0.05, 0);
  hull.rotation.z = Math.PI / 2;
  hull.scale.z = 0.72;
  box(3.7, 0.17, 0.74, dm.orange, 0, 0.35, 0, tanker);
  for (const x of [-1, -0.3, 0.4]) {
    const tank = cylinder(0.28, 0.28, 0.72, dm.metal, x, 0.55, 0, tanker);
    tank.rotation.x = Math.PI / 2;
  }
  box(0.64, 0.65, 0.65, dm.metal, 1.3, 0.71, 0, tanker);
  box(0.53, 0.18, 0.69, dm.black, 1.3, 0.91, 0, tanker);
  cylinder(0.025, 0.025, 1.1, dm.dark, 1.33, 1.58, 0, tanker);
  line([new THREE.Vector3(5.4, 0.03, 7), new THREE.Vector3(2, 0.03, 5), new THREE.Vector3(-1, 0.38, 1)], "#667b76", 0.75, diesel);
  const slickMaterial = material("#555d47", { transparent: true, opacity: 0.14, depthWrite: false });
  const slick = new THREE.Mesh(geometry(new THREE.CircleGeometry(2.6, 48)), slickMaterial);
  slick.rotation.x = -Math.PI / 2;
  slick.scale.y = 0.56;
  slick.position.set(5, -0.17, 7.5);
  diesel.add(slick);
  currentFade = void 0;
  for (const x of [-4.2, 0.4, 4.8]) {
    cylinder(0.04, 0.065, 1.65, base.stone, x, 1.1, 0.6);
    box(0.72, 0.05, 0.065, base.stone, x, 1.86, 0.6);
    for (const dx of [-0.27, 0.27]) cylinder(0.055, 0.055, 0.1, base.wall, x + dx, 1.91, 0.6);
  }
  curveMesh([[-4.47, 1.94, 0.6], [-2.2, 1.57, 0.6], [0.13, 1.94, 0.6], [2.4, 1.57, 0.6], [4.53, 1.94, 0.6]], base.stone, 0.012);
  currentFade = fades.renewable;
  const rm = { white: material("#e5eeeb", { roughness: 0.55 }), metal: material("#51777f", { metalness: 0.5, roughness: 0.45 }), dark: material("#1c5062"), panel: material("#175d8c", { metalness: 0.5, roughness: 0.28 }), cell: material("#87c3d0", { roughness: 0.4 }), aqua: material("#74ddd1", { emissive: "#44b7ac", emissiveIntensity: 0.2 }), yellow: material("#cbb272") };
  const rotors = [];
  function turbine(x, z, height, phase) {
    const t = new THREE.Group();
    t.position.set(x, -0.12, z);
    renewable.add(t);
    cylinder(0.24, 0.38, 0.28, rm.metal, 0, 0.16, 0, t);
    cylinder(0.08, 0.15, height, rm.white, 0, height / 2 + 0.18, 0, t);
    box(0.2, 0.22, 0.64, rm.white, 0, height + 0.18, 0.02, t);
    const rotor = new THREE.Group();
    rotor.position.set(0, height + 0.18, 0.37);
    rotor.rotation.z = phase;
    t.add(rotor);
    rotors.push(rotor);
    const shape = new THREE.Shape();
    shape.moveTo(-0.06, 0.06);
    shape.lineTo(-0.14, 0.52);
    shape.lineTo(0.025, 1.82);
    shape.lineTo(0.09, 1.85);
    shape.lineTo(0.12, 0.41);
    shape.closePath();
    const bladeGeometry = geometry(new THREE.ExtrudeGeometry(shape, { depth: 0.026, bevelEnabled: false }));
    for (let k = 0; k < 3; k++) {
      const blade = mesh(bladeGeometry, rm.white, rotor, 0, 0, 0);
      blade.rotation.z = k * Math.PI * 2 / 3;
    }
    sphere(rm.white, 0, 0, 0.04, 0.15, 0.15, 0.13, rotor);
    const points = Array.from({ length: 50 }, (_, i) => new THREE.Vector3(Math.cos(i / 49 * Math.PI * 2) * 0.57, -0.04, Math.sin(i / 49 * Math.PI * 2) * 0.57));
    line(points, "#82c2bf", 0.2, t);
  }
  // Third turbine moved from (-8.9, 0.3), which is inside the big solar raft below, into
  // open water behind it; WIND_FIXES moves the Blender model's copy to match.
  [[-15.2, -2.4, 4, 1], [-11.9, -0.3, 4.5, 0.2], [-9.6, -2.2, 4.7, 2.1]].forEach((p) => turbine(p[0], p[1], p[2], p[3]));
  const floating = [];
  function pv(x, z, columns, rows) {
    const p = new THREE.Group();
    p.position.set(x, 0.02, z);
    p.rotation.y = -0.1;
    renewable.add(p);
    floating.push({ group: p, y: 0.02, phase: x });
    box(columns * 0.72 + 0.14, 0.12, rows * 0.99 + 0.14, rm.dark, (columns - 1) * 0.36, -0.03, (rows - 1) * 0.495, p);
    for (let r = 0; r < rows; r++) for (let c = 0; c < columns; c++) {
      const panel = new THREE.Group();
      panel.position.set(c * 0.72, 0.13, r * 0.99);
      panel.rotation.x = -0.17;
      p.add(panel);
      box(0.68, 0.055, 0.94, rm.white, 0, 0, 0, panel);
      box(0.62, 0.018, 0.88, rm.panel, 0, 0.037, 0, panel);
      for (let j = 1; j < 4; j++) box(0.62, 6e-3, 8e-3, rm.cell, 0, 0.049, -0.44 + j * 0.22, panel);
      box(8e-3, 6e-3, 0.88, rm.cell, 0, 0.049, 0, panel);
    }
    for (const lx of [-0.36, columns * 0.72 - 0.36]) for (const lz of [-0.5, rows * 0.99 - 0.5]) sphere(rm.aqua, lx, -0.03, lz, 0.1, 0.08, 0.1, p);
  }
  pv(-9.2, -0.2, 4, 3);
  pv(-8.1, 4, 4, 2);
  curveMesh([[-7.7, 0.02, 0.8], [-6.1, 0.02, 0.4], [-4.5, 0.34, 0.25], [-2.4, 0.38, 0.1]], rm.aqua, 0.035, renewable);
  box(3.6, 0.1, 2.1, rm.metal, -2.4, 0.37, -0.2, renewable);
  for (let i = 0; i < 3; i++) {
    const x = -3.55 + i * 1.1;
    box(0.88, 1.12, 1.48, rm.white, x, 0.98, -0.2, renewable);
    box(0.91, 0.07, 1.53, rm.metal, x, 1.58, -0.2, renewable);
    box(0.75, 0.91, 0.03, rm.dark, x, 0.97, 0.56, renewable);
    for (let j = 0; j < 6; j++) box(0.58, 0.035, 0.04, rm.metal, x, 0.66 + j * 0.12, 0.585, renewable);
    box(0.19, 0.06, 0.04, rm.aqua, x + 0.18, 1.38, 0.59, renewable);
    for (let j = 0; j < 7; j++) box(0.012, 0.85, 0.018, rm.cell, x - 0.36 + j * 0.12, 1, -0.95, renewable);
  }
  box(0.75, 0.65, 0.85, rm.white, -0.25, 0.73, -0.2, renewable);
  for (const x of [-0.5, -0.25, 0]) cylinder(0.07, 0.07, 0.29, rm.metal, x, 1.2, -0.2, renewable);
  box(0.91, 0.03, 1.1, rm.panel, 1, 1.34, 0.05, renewable);
  const otec = new THREE.Group();
  otec.position.set(0.7, 0.02, 6.5);
  otec.rotation.y = -0.2;
  renewable.add(otec);
  floating.push({ group: otec, y: 0.02, phase: 1 });
  box(2.55, 0.18, 1.65, rm.metal, 0, 0.12, 0, otec);
  box(1.1, 0.72, 1.1, rm.white, 0.38, 0.57, 0, otec);
  box(1.2, 0.08, 1.2, rm.dark, 0.38, 0.98, 0, otec);
  for (const x of [-0.85, -0.3]) {
    cylinder(0.22, 0.22, 0.65, rm.white, x, 0.55, -0.15, otec);
    cylinder(0.23, 0.23, 0.06, rm.aqua, x, 0.9, -0.15, otec);
  }
  for (const x of [-1.18, 1.18]) box(0.035, 0.35, 1.5, rm.white, x, 0.36, 0, otec);
  cylinder(0.13, 0.13, 1.3, rm.dark, -0.85, -0.65, 0.4, otec);
  curveMesh([[0.7, -0.04, 6.5], [2.8, -0.03, 5.9], [4.3, 0.03, 4.8], [6.2, 0.32, 3]], rm.aqua, 0.04, renewable);
  const buoys = [];
  for (let i = 0; i < 5; i++) {
    const b = new THREE.Group();
    b.position.set(-2.1 + i * 1.03, -0.02, 7.1 + Math.sin(i) * 0.26);
    renewable.add(b);
    buoys.push(b);
    floating.push({ group: b, y: -0.02, phase: i });
    cylinder(0.24, 0.3, 0.13, rm.yellow, 0, 0.04, 0, b);
    cylinder(0.12, 0.14, 0.4, rm.white, 0, 0.29, 0, b);
    sphere(rm.aqua, 0, 0.5, 0, 0.11, 0.09, 0.11, b);
    const wave = geometry(new THREE.RingGeometry(0.47, 0.48, 40));
    const m = new THREE.MeshBasicMaterial({ color: "#88c5be", transparent: true, opacity: 0.25, side: THREE.DoubleSide, depthWrite: false });
    materials.add(m);
    fades.renewable.push({ material: m, opacity: 0.25 });
    const ring = new THREE.Mesh(wave, m);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = -0.05;
    b.add(ring);
  }
  line(buoys.map((b) => b.position.clone()), "#79b6b4", 0.45, renewable);
  const boat = new THREE.Group();
  boat.position.set(9.3, 0.02, 5.4);
  boat.rotation.y = -0.3;
  renewable.add(boat);
  floating.push({ group: boat, y: 0.02, phase: 2 });
  const boatHull = mesh(geometry(new THREE.CapsuleGeometry(0.28, 1.1, 4, 8)), rm.white, boat, 0, 0.1, 0);
  boatHull.rotation.z = Math.PI / 2;
  boatHull.scale.z = 0.68;
  box(0.65, 0.3, 0.43, rm.dark, 0.1, 0.34, 0, boat);
  box(0.22, 0.15, 0.38, rm.cell, 0.26, 0.56, 0, boat);
  cylinder(0.018, 0.018, 0.65, rm.white, 0.12, 0.88, 0, boat);
  currentFade = void 0;
  const glints = [];
  for (let i = 0; i < 70; i++) {
    const a = i * 2.399963, r = 8 + i % 9 * 1.1, x = Math.cos(a) * r, z = Math.sin(a) * r * 0.75;
    const points = Array.from({ length: 7 }, (_, k) => new THREE.Vector3(x + (k / 6 - 0.5) * (0.25 + i % 4 * 0.15), -0.16, z + Math.sin(k / 6 * Math.PI) * 0.03));
    const opacity = 0.09 + i % 4 * 0.025;
    glints.push({ object: line(points, "#85c3c4", opacity), opacity });
  }
  const electric = material("#93e5db", { emissive: "#63c4bb", emissiveIntensity: 0.4, transparent: true, opacity: 0.8, depthWrite: false });
  const flowPath = new THREE.CatmullRomCurve3([new THREE.Vector3(-4.2, 0.48, 0.55), new THREE.Vector3(-1.5, 0.48, 0.5), new THREE.Vector3(0.8, 0.48, 0.8), new THREE.Vector3(3.7, 0.48, 1.7), new THREE.Vector3(5.7, 0.48, 2)]);
  const particles = Array.from({ length: 7 }, () => sphere(electric, 0, 0, 0, 0.035));
  let blenderAsset = null;
  const assetRotors = [];
  const assetFloating = [];
  function attachBlenderAsset(asset) {
    blenderAsset = asset;
    const registered = /* @__PURE__ */ new Set();
    asset.traverse((object) => {
      if (!(object instanceof THREE.Mesh) && object.name.startsWith("Rotor_")) assetRotors.push(object);
      if (!(object instanceof THREE.Mesh) && (object.name.startsWith("Floating_PV_") || object.name.startsWith("Wave_Buoy_") || object.name === "OTEC_Facility")) assetFloating.push({ object, y: object.position.y, phase: assetFloating.length });
      if (object instanceof THREE.Mesh) {
        geometries.add(object.geometry);
        object.castShadow = true;
        object.receiveShadow = true;
        const list = Array.isArray(object.material) ? object.material : [object.material];
        for (const m of list) if (!registered.has(m)) {
          registered.add(m);
          materials.add(m);
          m.transparent = true;
          fades.renewable.push({ material: m, opacity: m.opacity });
        }
      }
    });
    for (const [name, x, z] of WIND_FIXES) asset.getObjectByName(name)?.position.set(x, -0.12, z);
    world.add(asset);
    renewable.visible = false;
  }
  const darkGrass = new THREE.Color("#668778"), lightGrass = new THREE.Color("#82ad83");
  const darkLeaf = new THREE.Color("#3b7168"), lightLeaf = new THREE.Color("#4b9571");
  const darkReef = new THREE.Color("#2b7479"), lightReef = new THREE.Color("#49b8b1");
  function applyOpacity(items, amount) {
    for (const { material: m, opacity } of items) {
      m.opacity = opacity * amount;
      m.depthWrite = amount > 0.98 && opacity > 0.98;
    }
  }
  function update(time, transition, motion) {
    const t = motion ? time : 0;
    waterMaterial.uniforms.uTime.value = t;
    waterMaterial.uniforms.uTransition.value = transition;
    renewable.visible = !blenderAsset && transition > 2e-3;
    diesel.visible = transition < 0.998;
    if (blenderAsset) blenderAsset.visible = transition > 2e-3;
    applyOpacity(fades.renewable, transition);
    applyOpacity(fades.diesel, 1 - transition);
    base.grass.color.copy(darkGrass).lerp(lightGrass, transition);
    base.leaf.color.copy(darkLeaf).lerp(lightLeaf, transition);
    base.window.emissive.set(transition > 0.5 ? "#2a7b7d" : "#f8bd63");
    base.window.emissiveIntensity = transition > 0.5 ? 0.1 : 2.4;
    base.window.color.set(transition > 0.5 ? "#9ddfdd" : "#e8bb77");
    reefMaterials.forEach((m) => {
      m.color.copy(darkReef).lerp(lightReef, transition);
      m.opacity = 0.14 + transition * 0.1;
    });
    rotors.forEach((r, i) => {
      r.rotation.z = t * (0.3 + i * 0.015) + i * 1.1;
    });
    assetRotors.forEach((r, i) => {
      r.rotation.z = t * (0.3 + i * 0.015) + i * 1.1;
    });
    assetFloating.forEach((f) => {
      f.object.position.y = f.y + Math.sin(t * 0.7 + f.phase) * 0.027;
      f.object.rotation.z = Math.sin(t * 0.53 + f.phase) * 8e-3;
    });
    floating.forEach((f) => {
      f.group.position.y = f.y + Math.sin(t * 0.7 + f.phase) * 0.027;
      f.group.rotation.z = Math.sin(t * 0.53 + f.phase) * 8e-3;
    });
    smoke.forEach((s) => {
      const progress = (t * 0.11 + s.phase) % 1;
      s.object.position.set(s.x + progress * 0.8, 2.8 + progress * 2.8, -0.48 - progress * 0.25);
      s.object.scale.setScalar(0.17 + progress * 0.46);
    });
    glints.forEach(({ object, opacity }, i) => {
      object.material.opacity = opacity * (0.7 + Math.sin(t * 0.55 + i) * 0.3);
    });
    particles.forEach((p, i) => {
      p.position.copy(flowPath.getPointAt(THREE.MathUtils.euclideanModulo(t * 0.055 + i / particles.length, 1)));
      p.visible = transition > 0.15;
    });
    electric.opacity = transition * 0.8;
  }
  function dispose() {
    geometries.forEach((g) => g.dispose());
    materials.forEach((m) => m.dispose());
  }
  return { world, update, dispose, attachBlenderAsset };
}
export {
  buildIslandWorld
};
