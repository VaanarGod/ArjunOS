import { useRef, useMemo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Icosahedron, Torus, Points, PointMaterial, Stars, Line, Html } from '@react-three/drei'
import * as THREE from 'three'

// --- SHARED INTERACTION WRAPPER ---
function SceneWrapper({ children }: { children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null!)
  const { pointer } = useThree()
  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.x = THREE.MathUtils.lerp(ref.current.rotation.x, pointer.y * 0.05, 0.05)
      ref.current.rotation.y = THREE.MathUtils.lerp(ref.current.rotation.y, pointer.x * 0.05, 0.05)
      const scrollY = window.scrollY
      ref.current.position.y = THREE.MathUtils.lerp(ref.current.position.y, scrollY * 0.002, 0.05)
    }
  })
  return <group ref={ref}>{children}</group>
}

// --- ENVIRONMENT PARTICLES ---
function AmbientParticles({ count = 2000 }) {
  const ref = useRef<THREE.Points>(null!)
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const r = 6 + Math.random() * 15
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i * 3 + 2] = r * Math.cos(phi)
    }
    return pos
  }, [count])

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.02
  })

  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled>
      <PointMaterial transparent color="#22d3ee" size={0.03} sizeAttenuation depthWrite={false} opacity={0.4} />
    </Points>
  )
}

// --- 1. HOME: CENTRAL CORE ---
function CoreScene() {
  const mesh = useRef<THREE.Mesh>(null!)
  const ring1 = useRef<THREE.Mesh>(null!)
  const ring2 = useRef<THREE.Mesh>(null!)
  
  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (mesh.current) { mesh.current.rotation.y = t * 0.1; mesh.current.rotation.x = Math.sin(t * 0.2) * 0.1 }
    if (ring1.current) ring1.current.rotation.z = t * 0.15
    if (ring2.current) ring2.current.rotation.x = t * 0.1
  })

  const panels = [
    { text: "LOCAL INTELLIGENCE", pos: [-3, 2, 0] },
    { text: "MODEL ENGINE", pos: [3, 3.5, -1] },
    { text: "MEMORY SYSTEM", pos: [5, -1.5, 1] },
    { text: "AGENT NETWORK", pos: [-2, -3, 0.5] },
  ]

  return (
    <group position={[3, 0, 0]}>
      <Icosahedron ref={mesh} args={[2.2, 2]}>
        <meshStandardMaterial color="#02040a" emissive="#22d3ee" emissiveIntensity={0.5} wireframe transparent opacity={0.3} />
      </Icosahedron>
      <Icosahedron args={[1.2, 2]}>
        <meshStandardMaterial color="#a5f3fc" emissive="#22d3ee" emissiveIntensity={2.5} transparent opacity={0.15} />
      </Icosahedron>
      <Torus ref={ring1} args={[3.5, 0.02, 16, 100]} rotation={[Math.PI / 2.5, 0, 0]}>
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.4} />
      </Torus>
      <Torus ref={ring2} args={[4.2, 0.01, 16, 100]} rotation={[Math.PI / 1.8, 0.4, 0]}>
        <meshBasicMaterial color="#8b5cf6" transparent opacity={0.3} />
      </Torus>
      {panels.map((p, i) => (
        <Html key={i} position={p.pos as [number, number, number]} center>
          <div className="holo-panel">{p.text}</div>
        </Html>
      ))}
    </group>
  )
}

// --- 2. FEATURES: NEURAL NETWORK ---
function NeuralScene() {
  const points = useMemo(() => {
    const pts = []
    for (let i = 0; i < 40; i++) {
      pts.push(new THREE.Vector3((Math.random() - 0.5) * 12, (Math.random() - 0.5) * 12, (Math.random() - 0.5) * 8 - 2))
    }
    return pts
  }, [])

  const lines = useMemo(() => {
    const l = []
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        if (points[i].distanceTo(points[j]) < 3.5) l.push([points[i], points[j]])
      }
    }
    return l
  }, [points])

  const group = useRef<THREE.Group>(null!)
  useFrame((state) => { if (group.current) group.current.rotation.y = state.clock.elapsedTime * 0.05 })

  return (
    <group ref={group} position={[0, 0, 0]}>
      {points.map((p, i) => (
        <mesh key={`pt-${i}`} position={p}>
          <sphereGeometry args={[0.06, 8, 8]} />
          <meshBasicMaterial color="#a5f3fc" transparent opacity={0.8} />
        </mesh>
      ))}
      {lines.map(([start, end], i) => (
        <Line key={`line-${i}`} points={[start, end]} color="#22d3ee" lineWidth={1} transparent opacity={0.2} />
      ))}
    </group>
  )
}

// --- 3. PRODUCT: BLUEPRINT ---
function BlueprintScene() {
  const group = useRef<THREE.Group>(null!)
  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (group.current) {
      group.current.position.y = Math.sin(t * 0.5) * 0.2
      group.current.rotation.y = Math.sin(t * 0.2) * 0.2
    }
  })

  return (
    <group ref={group} position={[2, 0, 0]}>
      <gridHelper args={[20, 20, '#0a1022', '#0a1022']} position={[0, -3, 0]} />
      <mesh position={[-1, 0, 0]}>
        <boxGeometry args={[4, 3, 0.1]} />
        <meshBasicMaterial color="#22d3ee" wireframe transparent opacity={0.3} />
      </mesh>
      <mesh position={[2.5, 1, 1]}>
        <boxGeometry args={[2.5, 4, 0.1]} />
        <meshBasicMaterial color="#8b5cf6" wireframe transparent opacity={0.2} />
      </mesh>
    </group>
  )
}

// --- 4. DOWNLOAD: LAUNCH SEQUENCE ---
function LaunchScene() {
  const ring1 = useRef<THREE.Mesh>(null!)
  const ring2 = useRef<THREE.Mesh>(null!)
  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (ring1.current) { ring1.current.scale.setScalar(1 + Math.sin(t * 2) * 0.05); ring1.current.rotation.z = t * 0.5 }
    if (ring2.current) { ring2.current.scale.setScalar(1 + Math.cos(t * 2) * 0.05); ring2.current.rotation.z = -t * 0.3 }
  })

  return (
    <group position={[0, 0, 0]}>
      <Torus ref={ring1} args={[2.5, 0.02, 16, 100]}>
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.6} />
      </Torus>
      <Torus ref={ring2} args={[3.5, 0.01, 16, 100]}>
        <meshBasicMaterial color="#8b5cf6" transparent opacity={0.4} />
      </Torus>
    </group>
  )
}

// --- 5. DOCS: KNOWLEDGE ARCHITECTURE ---
function KnowledgeScene() {
  const group = useRef<THREE.Group>(null!)
  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (group.current) {
      group.current.children.forEach((child, i) => {
        child.rotation.x = Math.sin(t * 0.2 + i) * 0.1
        child.rotation.y = Math.cos(t * 0.2 + i) * 0.1
      })
    }
  })

  return (
    <group ref={group} position={[4, 0, 0]}>
      <mesh position={[0, 1, 0]} rotation={[Math.PI / 6, Math.PI / 4, 0]}>
        <boxGeometry args={[3, 3, 0.05]} />
        <meshPhysicalMaterial color="#22d3ee" transparent opacity={0.1} roughness={0.1} transmission={0.9} />
      </mesh>
      <mesh position={[0, -1, 1]} rotation={[Math.PI / 3, -Math.PI / 4, 0]}>
        <boxGeometry args={[4, 4, 0.05]} />
        <meshPhysicalMaterial color="#8b5cf6" transparent opacity={0.1} roughness={0.1} transmission={0.9} />
      </mesh>
    </group>
  )
}

// --- 6. CHANGELOG: TIMELINE ---
function TimelineScene() {
  const group = useRef<THREE.Group>(null!)
  useFrame((state) => { if (group.current) group.current.rotation.y = state.clock.elapsedTime * 0.05 })

  return (
    <group ref={group} position={[0, 0, 0]} rotation={[0, 0, Math.PI / 8]}>
      <Line points={[[-10, 0, 0], [10, 0, 0]]} color="#22d3ee" lineWidth={2} transparent opacity={0.4} />
      {[-4, -1, 2, 5, 8].map((x, i) => (
        <mesh key={i} position={[x, 0, 0]}>
          <sphereGeometry args={[0.15, 16, 16]} />
          <meshBasicMaterial color={i % 2 === 0 ? "#22d3ee" : "#8b5cf6"} />
        </mesh>
      ))}
    </group>
  )
}

// --- 7. ABOUT: GALAXY ---
function GalaxyScene() {
  const group = useRef<THREE.Group>(null!)
  useFrame((state) => { if (group.current) group.current.rotation.y = state.clock.elapsedTime * 0.03 })

  return (
    <group ref={group} position={[2, 0, 0]}>
      <Torus args={[3, 0.01, 16, 100]} rotation={[Math.PI / 2, 0, 0]}>
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.2} />
      </Torus>
      <Torus args={[5, 0.01, 16, 100]} rotation={[Math.PI / 3, 0.5, 0]}>
        <meshBasicMaterial color="#8b5cf6" transparent opacity={0.2} />
      </Torus>
      <Icosahedron args={[0.8, 1]}>
        <meshStandardMaterial color="#a5f3fc" emissive="#22d3ee" emissiveIntensity={2} transparent opacity={0.3} />
      </Icosahedron>
    </group>
  )
}

export default function Scene3D({ variant = 'core' }: { variant?: 'core' | 'neural' | 'blueprint' | 'launch' | 'knowledge' | 'timeline' | 'galaxy' }) {
  return (
    <div className="h-full w-full pointer-events-none">
      <Canvas camera={{ position: [0, 0, 10], fov: 45 }} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}>
        <fog attach="fog" args={['#000000', 8, 25]} />
        <ambientLight intensity={1.5} color="#ffffff" />
        
        
        <Stars radius={60} depth={50} count={3000} factor={5} saturation={0} fade speed={1} />
        
        <SceneWrapper>
          {variant === 'core' && <CoreScene />}
          {variant === 'neural' && <NeuralScene />}
          {variant === 'blueprint' && <BlueprintScene />}
          {variant === 'launch' && <LaunchScene />}
          {variant === 'knowledge' && <KnowledgeScene />}
          {variant === 'timeline' && <TimelineScene />}
          {variant === 'galaxy' && <GalaxyScene />}
          <AmbientParticles count={1500} />
        </SceneWrapper>
      </Canvas>
    </div>
  )
}
