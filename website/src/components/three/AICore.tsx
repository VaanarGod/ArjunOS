import { useRef, useMemo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Icosahedron, Torus, Points, PointMaterial, Stars, Line } from '@react-three/drei'
import * as THREE from 'three'

function ParallaxGroup({ children }: { children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null!)
  const { pointer } = useThree()

  useFrame(() => {
    if (ref.current) {
      // Subtle mouse parallax
      ref.current.rotation.x = THREE.MathUtils.lerp(ref.current.rotation.x, pointer.y * 0.1, 0.05)
      ref.current.rotation.y = THREE.MathUtils.lerp(ref.current.rotation.y, pointer.x * 0.1, 0.05)
    }
  })

  return <group ref={ref}>{children}</group>
}

function Core() {
  const mesh = useRef<THREE.Mesh>(null!)
  const ring1 = useRef<THREE.Mesh>(null!)
  const ring2 = useRef<THREE.Mesh>(null!)
  const ring3 = useRef<THREE.Mesh>(null!)

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (mesh.current) {
      mesh.current.rotation.y = t * 0.15
      mesh.current.rotation.x = Math.sin(t * 0.2) * 0.1
    }
    if (ring1.current) ring1.current.rotation.z = t * 0.15
    if (ring2.current) ring2.current.rotation.x = t * 0.1
    if (ring3.current) ring3.current.rotation.y = t * 0.2
  })

  return (
    <group>
      {/* Inner glowing core */}
      <Icosahedron ref={mesh} args={[1.2, 2]}>
        <meshStandardMaterial
          color="#02040a"
          emissive="#22d3ee"
          emissiveIntensity={0.4}
          wireframe
          transparent
          opacity={0.6}
        />
      </Icosahedron>
      
      {/* Solid center */}
      <Icosahedron args={[0.6, 1]}>
        <meshStandardMaterial
          color="#a5f3fc"
          emissive="#22d3ee"
          emissiveIntensity={2}
          transparent
          opacity={0.3}
          roughness={0.1}
          metalness={0.9}
        />
      </Icosahedron>

      {/* Orbital Rings */}
      <Torus ref={ring1} args={[2.0, 0.015, 16, 100]} rotation={[Math.PI / 2.5, 0, 0]}>
        <meshBasicMaterial color="#22d3ee" transparent opacity={0.4} />
      </Torus>
      <Torus ref={ring2} args={[2.6, 0.008, 16, 100]} rotation={[Math.PI / 1.8, 0.4, 0]}>
        <meshBasicMaterial color="#8b5cf6" transparent opacity={0.3} />
      </Torus>
      <Torus ref={ring3} args={[1.6, 0.02, 16, 100]} rotation={[Math.PI / 3, 0.8, 0]}>
        <meshBasicMaterial color="#a5f3fc" transparent opacity={0.2} />
      </Torus>
    </group>
  )
}

function FloatingGeometries() {
  const group = useRef<THREE.Group>(null!)
  
  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (group.current) {
      group.current.children.forEach((child, i) => {
        child.position.y = Math.sin(t * 0.5 + i) * 0.3
        child.rotation.x = t * 0.1 + i
        child.rotation.y = t * 0.15 + i
      })
    }
  })

  return (
    <group ref={group}>
      {/* Frosted Glass Cubes */}
      <mesh position={[3, 1, -2]}>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshPhysicalMaterial color="#ffffff" transmission={0.9} opacity={1} transparent roughness={0.2} thickness={0.5} />
      </mesh>
      <mesh position={[-3.5, -1.5, -1]}>
        <boxGeometry args={[0.8, 0.8, 0.8]} />
        <meshPhysicalMaterial color="#22d3ee" transmission={0.9} opacity={1} transparent roughness={0.1} thickness={0.5} />
      </mesh>
      {/* Wireframe geometries */}
      <mesh position={[2.5, -2, 1]}>
        <octahedronGeometry args={[0.4, 0]} />
        <meshBasicMaterial color="#8b5cf6" wireframe transparent opacity={0.5} />
      </mesh>
    </group>
  )
}

function NeuralNetwork() {
  // Generate random points for a neural network
  const points = useMemo(() => {
    const pts = []
    for (let i = 0; i < 25; i++) {
      pts.push(new THREE.Vector3(
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 8 - 2
      ))
    }
    return pts
  }, [])

  // Connect nearby points
  const lines = useMemo(() => {
    const l = []
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        if (points[i].distanceTo(points[j]) < 3) {
          l.push([points[i], points[j]])
        }
      }
    }
    return l
  }, [points])

  const group = useRef<THREE.Group>(null!)
  useFrame((state) => {
    if (group.current) {
      group.current.rotation.y = state.clock.elapsedTime * 0.02
      group.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.1) * 0.1
    }
  })

  return (
    <group ref={group}>
      {points.map((p, i) => (
        <mesh key={`pt-${i}`} position={p}>
          <sphereGeometry args={[0.04, 8, 8]} />
          <meshBasicMaterial color="#a5f3fc" />
        </mesh>
      ))}
      {lines.map(([start, end], i) => (
        <Line key={`line-${i}`} points={[start, end]} color="#22d3ee" lineWidth={0.5} transparent opacity={0.15} />
      ))}
    </group>
  )
}

function Particles() {
  const ref = useRef<THREE.Points>(null!)
  const positions = useMemo(() => {
    const pos = new Float32Array(1500 * 3)
    for (let i = 0; i < 1500; i++) {
      const r = 4 + Math.random() * 8
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i * 3 + 2] = r * Math.cos(phi)
    }
    return pos
  }, [])

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.02
  })

  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled>
      <PointMaterial
        transparent
        color="#a5f3fc"
        size={0.03}
        sizeAttenuation
        depthWrite={false}
        opacity={0.6}
      />
    </Points>
  )
}

export default function AICore() {
  return (
    <div className="h-full w-full">
      <Canvas
        camera={{ position: [0, 0, 7], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      >
        <fog attach="fog" args={['#02040a', 5, 15]} />
        <ambientLight intensity={0.2} />
        <pointLight position={[6, 6, 6]} intensity={1.5} color="#22d3ee" />
        <pointLight position={[-6, -4, -6]} intensity={1} color="#8b5cf6" />
        
        <Stars radius={50} depth={50} count={2000} factor={4} saturation={0} fade speed={1} />
        
        <ParallaxGroup>
          <Core />
          <FloatingGeometries />
          <NeuralNetwork />
          <Particles />
        </ParallaxGroup>
      </Canvas>
    </div>
  )
}
