import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Icosahedron, Torus, Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'

function Core() {
  const mesh = useRef<THREE.Mesh>(null!)
  const ring1 = useRef<THREE.Mesh>(null!)
  const ring2 = useRef<THREE.Mesh>(null!)

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (mesh.current) {
      mesh.current.rotation.y = t * 0.18
      mesh.current.rotation.x = Math.sin(t * 0.2) * 0.15
    }
    if (ring1.current) ring1.current.rotation.z = t * 0.2
    if (ring2.current) ring2.current.rotation.x = t * 0.15
  })

  return (
    <group>
      <Icosahedron ref={mesh} args={[1.35, 1]}>
        <meshStandardMaterial
          color="#0a1022"
          emissive="#22d3ee"
          emissiveIntensity={0.25}
          wireframe
          transparent
          opacity={0.85}
        />
      </Icosahedron>
      <Icosahedron args={[0.7, 0]}>
        <meshStandardMaterial
          color="#22d3ee"
          emissive="#22d3ee"
          emissiveIntensity={1.8}
          transparent
          opacity={0.25}
        />
      </Icosahedron>
      <Torus ref={ring1} args={[2.1, 0.012, 16, 100]} rotation={[Math.PI / 2.5, 0, 0]}>
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.35} />
      </Torus>
      <Torus ref={ring2} args={[2.6, 0.008, 16, 100]} rotation={[Math.PI / 1.8, 0.4, 0]}>
        <meshBasicMaterial color="#8b5cf6" transparent opacity={0.3} />
      </Torus>
    </group>
  )
}

function Particles() {
  const ref = useRef<THREE.Points>(null!)
  const positions = new Float32Array(600 * 3)
  for (let i = 0; i < 600; i++) {
    const r = 3 + Math.random() * 4
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = r * Math.cos(phi)
  }

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.03
  })

  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled>
      <PointMaterial
        transparent
        color="#a5f3fc"
        size={0.025}
        sizeAttenuation
        depthWrite={false}
        opacity={0.7}
      />
    </Points>
  )
}

export default function AICore() {
  return (
    <div className="h-full w-full">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      >
        <ambientLight intensity={0.3} />
        <pointLight position={[6, 6, 6]} intensity={1.2} color="#22d3ee" />
        <pointLight position={[-6, -4, -6]} intensity={0.8} color="#8b5cf6" />
        <Core />
        <Particles />
      </Canvas>
    </div>
  )
}
