import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
} from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Html, Stars, useGLTF, useProgress } from '@react-three/drei'
import {
  AdditiveBlending,
  Box3,
  CanvasTexture,
  Color,
  Group,
  MathUtils,
  Mesh,
  MeshStandardMaterial,
  SRGBColorSpace,
  Vector3,
} from 'three'
import './App.css'

const MODEL_URL = '/assets/lunar-base.glb'

function makeEarthTexture() {
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 512
  const ctx = canvas.getContext('2d')

  if (!ctx) {
    return null
  }

  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height)
  gradient.addColorStop(0, '#0b2f67')
  gradient.addColorStop(0.4, '#1b5fa8')
  gradient.addColorStop(1, '#0e2045')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.globalAlpha = 0.9
  ctx.fillStyle = '#2d7b52'
  const continents = [
    [160, 150, 150, 70, 0.3],
    [315, 130, 135, 55, -0.2],
    [515, 175, 190, 60, 0.1],
    [710, 145, 120, 50, -0.35],
    [585, 330, 150, 65, 0.2],
  ] as const
  for (const [x, y, w, h, rot] of continents) {
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.beginPath()
    ctx.ellipse(0, 0, w, h, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }

  ctx.globalAlpha = 0.3
  ctx.fillStyle = '#7db18b'
  for (const [x, y, w, h, rot] of continents) {
    ctx.save()
    ctx.translate(x + 20, y - 10)
    ctx.rotate(rot * 1.15)
    ctx.beginPath()
    ctx.ellipse(0, 0, w * 0.55, h * 0.45, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }

  ctx.globalAlpha = 0.75
  ctx.fillStyle = 'rgba(255,255,255,0.82)'
  const cloudBands = [
    [180, 120, 250, 26, 0.2],
    [380, 230, 330, 30, -0.12],
    [690, 200, 250, 24, 0.1],
    [530, 78, 220, 18, -0.08],
  ] as const
  for (const [x, y, w, h, rot] of cloudBands) {
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.beginPath()
    ctx.ellipse(0, 0, w, h, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.needsUpdate = true
  return texture
}

function LoadingOverlay() {
  const { progress } = useProgress()

  return (
    <Html center>
      <div className="loader-shell">
        <div className="loader-ring" />
        <p>Streaming lunar scene {Math.round(progress)}%</p>
      </div>
    </Html>
  )
}

function ForegroundSolarArray({
  position,
  rotation,
  mirrored = false,
}: {
  position: [number, number, number]
  rotation: [number, number, number]
  mirrored?: boolean
}) {
  const columns = mirrored ? [-1.25, 0, 1.25] : [-1.3, 0, 1.3]

  return (
    <group position={position} rotation={rotation}>
      <mesh receiveShadow castShadow position={[0, -0.25, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.08, 0.11, 1.2, 10]} />
        <meshStandardMaterial color="#747b84" roughness={0.7} metalness={0.35} />
      </mesh>
      <mesh receiveShadow castShadow position={[0, 0.5, 0]}>
        <boxGeometry args={[4.5, 0.08, 1.9]} />
        <meshStandardMaterial color="#646d79" roughness={0.52} metalness={0.4} />
      </mesh>
      {columns.map((x) => (
        <mesh key={x} receiveShadow castShadow position={[x, 0.63, 0]}>
          <boxGeometry args={[1.1, 0.03, 1.6]} />
          <meshStandardMaterial
            color="#1f4d9e"
            roughness={0.24}
            metalness={0.2}
            emissive="#133265"
            emissiveIntensity={0.25}
          />
        </mesh>
      ))}
    </group>
  )
}

function Earth() {
  const earthTexture = useMemo(() => makeEarthTexture(), [])
  const group = useRef<Group>(null)
  const { camera } = useThree()

  useFrame((state, delta) => {
    if (!group.current) {
      return
    }

    const forward = new Vector3()
    camera.getWorldDirection(forward)
    const right = new Vector3().crossVectors(forward, camera.up).normalize()
    const up = camera.up.clone().normalize()
    const target = camera.position
      .clone()
      .add(forward.multiplyScalar(42))
      .add(right.multiplyScalar(10.5))
      .add(up.multiplyScalar(9.2))

    group.current.position.lerp(target, 1 - Math.exp(-delta * 2.4))
    group.current.lookAt(
      camera.position.clone().add(camera.getWorldDirection(new Vector3()).multiplyScalar(60)),
    )
    group.current.rotateY(state.clock.elapsedTime * 0.0008)
  })

  return (
    <group ref={group}>
      <mesh castShadow>
        <sphereGeometry args={[4.1, 64, 64]} />
        <meshStandardMaterial
          map={earthTexture ?? undefined}
          color="#8dbdff"
          metalness={0}
          roughness={0.9}
          emissive="#0b1636"
          emissiveIntensity={0.18}
        />
      </mesh>
      <mesh scale={1.08}>
        <sphereGeometry args={[4.1, 48, 48]} />
        <meshBasicMaterial
          color="#9ed1ff"
          transparent
          opacity={0.32}
          blending={AdditiveBlending}
          side={1}
        />
      </mesh>
    </group>
  )
}

function LunarBaseModel({
  pointer,
}: {
  pointer: MutableRefObject<{ x: number; y: number }>
}) {
  const gltf = useGLTF(MODEL_URL)
  const container = useRef<Group>(null)

  const { scene, scale, center } = useMemo(() => {
    const cloned = gltf.scene.clone(true)
    cloned.traverse((object) => {
      if (object instanceof Mesh) {
        object.castShadow = true
        object.receiveShadow = true
        const material = object.material
        if (Array.isArray(material)) {
          material.forEach((entry) => tweakMaterial(entry))
        } else if (material) {
          tweakMaterial(material)
        }
      }
    })

    const bounds = new Box3().setFromObject(cloned)
    const size = bounds.getSize(new Vector3())
    const modelCenter = bounds.getCenter(new Vector3())
    const longest = Math.max(size.x, size.y, size.z)

    return {
      scene: cloned,
      scale: 34 / Math.max(longest, 1),
      center: modelCenter,
    }
  }, [gltf.scene])

  useFrame((_, delta) => {
    if (!container.current) {
      return
    }
    container.current.rotation.y = MathUtils.lerp(
      container.current.rotation.y,
      -0.52 + pointer.current.x * 0.08,
      1 - Math.exp(-delta * 2.4),
    )
    container.current.rotation.x = MathUtils.lerp(
      container.current.rotation.x,
      0.02 + pointer.current.y * 0.025,
      1 - Math.exp(-delta * 2.2),
    )
  })

  return (
    <group
      ref={container}
      scale={scale}
      position={[-center.x * scale - 1.1, -center.y * scale - 2.5, -center.z * scale + 0.4]}
      rotation={[0.04, -0.66, 0]}
    >
      <primitive object={scene} />
    </group>
  )
}

function tweakMaterial(material: unknown) {
  if (!(material instanceof MeshStandardMaterial)) {
    return
  }

  const name = material.name.toLowerCase()

  if (name.includes('regolith')) {
    material.color = new Color('#68645f')
    material.roughness = 1
    material.metalness = 0
  } else if (name.includes('white')) {
    material.color = new Color('#c8c7c3')
    material.roughness = 0.72
    material.metalness = 0.1
  } else if (name.includes('panel')) {
    material.color = new Color('#295bb6')
    material.roughness = 0.3
    material.metalness = 0.18
    material.emissive = new Color('#163a86')
    material.emissiveIntensity = 0.18
  } else if (name.includes('dark')) {
    material.color = new Color('#4d545f')
    material.roughness = 0.64
    material.metalness = 0.22
  } else if (name.includes('visor')) {
    material.color = new Color('#c9d5e8')
    material.roughness = 0.18
    material.metalness = 0.02
  }

  material.needsUpdate = true
}

function CameraRig({
  pointer,
}: {
  pointer: MutableRefObject<{ x: number; y: number }>
}) {
  const { camera } = useThree()
  const cameraRef = useRef(camera)
  const focus = useMemo(() => new Vector3(0, -1.4, 0), [])

  useEffect(() => {
    cameraRef.current = camera
  }, [camera])

  useFrame((state, delta) => {
    const activeCamera = cameraRef.current
    const t = state.clock.elapsedTime * 0.08
    const baseX = -8.6 + Math.sin(t * 1.7) * 0.55
    const baseY = 4.7 + Math.cos(t * 1.2) * 0.25
    const baseZ = 16.2 + Math.sin(t) * 0.65

    activeCamera.position.x = MathUtils.lerp(
      activeCamera.position.x,
      baseX + pointer.current.x * 1.8,
      1 - Math.exp(-delta * 2.8),
    )
    activeCamera.position.y = MathUtils.lerp(
      activeCamera.position.y,
      baseY + pointer.current.y * 0.8,
      1 - Math.exp(-delta * 2.6),
    )
    activeCamera.position.z = MathUtils.lerp(
      activeCamera.position.z,
      baseZ + pointer.current.y * 0.75,
      1 - Math.exp(-delta * 2.6),
    )

    const look = focus.clone()
    look.x += pointer.current.x * 0.45
    look.y += pointer.current.y * 0.2
    activeCamera.lookAt(look)
  })

  return null
}

function Scene({
  pointer,
}: {
  pointer: MutableRefObject<{ x: number; y: number }>
}) {
  return (
    <>
      <color attach="background" args={['#05070d']} />
      <fog attach="fog" args={['#05070d', 34, 82]} />
      <ambientLight intensity={0.18} color="#8fa4c9" />
      <directionalLight
        castShadow
        intensity={2.7}
        color="#fff8ea"
        position={[18, 22, 12]}
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-bias={-0.00012}
      />
      <directionalLight intensity={0.35} color="#8cabff" position={[-14, 8, -18]} />
      <Stars
        radius={120}
        depth={48}
        count={1400}
        factor={2.5}
        saturation={0}
        fade
        speed={0.12}
      />
      <Suspense fallback={<LoadingOverlay />}>
        <LunarBaseModel pointer={pointer} />
        <Earth />
      </Suspense>
      <ForegroundSolarArray position={[-6.9, -2.5, 6.8]} rotation={[0.18, 0.92, -0.1]} />
      <ForegroundSolarArray position={[7.2, -2.2, 5.8]} rotation={[0.18, -0.74, 0.08]} mirrored />
      <CameraRig pointer={pointer} />
    </>
  )
}

function App() {
  const pointer = useRef({ x: 0, y: 0 })
  const [ready, setReady] = useState(false)

  useEffect(() => {
    useGLTF.preload(MODEL_URL)
    const timeout = window.setTimeout(() => setReady(true), 400)
    return () => window.clearTimeout(timeout)
  }, [])

  return (
    <main
      className="app-shell"
      onPointerMove={(event) => {
        pointer.current.x = (event.clientX / window.innerWidth - 0.5) * 2
        pointer.current.y = (event.clientY / window.innerHeight - 0.5) * -2
      }}
      onPointerLeave={() => {
        pointer.current.x = 0
        pointer.current.y = 0
      }}
    >
      <section className="hero-copy">
        <p className="eyebrow">3DMoonX</p>
        <h1>Futuristic lunar power outpost, rebuilt for the browser.</h1>
        <p className="lede">
          A cinematic React Three Fiber recreation of the lunar industrial base,
          driven by Blender source assets and tuned for web delivery.
        </p>
        <div className="actions">
          <a href="https://github.com/zrt219/3DMoonX" target="_blank" rel="noreferrer">
            GitHub
          </a>
          <span>{ready ? 'Autoplay camera active' : 'Preparing scene...'}</span>
        </div>
      </section>

      <div className="hero-stage">
        <Canvas
          shadows
          dpr={[1, 1.75]}
          camera={{ position: [-8.6, 4.7, 16.2], fov: 26, near: 0.1, far: 200 }}
        >
          <Scene pointer={pointer} />
        </Canvas>
      </div>

      <section className="legend">
        <div>
          <h2>Hybrid fidelity</h2>
          <p>Browser-side Earth, autoplay hero camera, and a lightweight GLB exported from the Blender source scene.</p>
        </div>
        <div>
          <h2>Web-ready asset</h2>
          <p>Cooling towers, modular base, solar arrays, vehicles, and astronauts are preserved in the shipped scene asset.</p>
        </div>
      </section>
    </main>
  )
}

export default App
