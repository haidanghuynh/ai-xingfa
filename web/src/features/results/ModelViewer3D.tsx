import * as React from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RotateCcw } from 'lucide-react'
import { Button, CheckField } from '@/components/ui/primitives'
import type { PlanItem } from '@/types/plan'

const BAR_COLORS: Record<string, string> = {
  frame: '#cfd6dd',
  sash: '#e9edf2',
  mullion: '#c3ccd6',
  transom: '#cad3dc',
  track_top: '#b8c2cc',
  track_bottom: '#aeb9c4',
  bead: '#dde3e9',
}

const HARDWARE_COLORS: Record<string, string> = {
  hinge: '#94a3b8',
  lock: '#374151',
  handle: '#111827',
  wheel: '#111827',
}

interface ViewerApi {
  reset: () => void
  setGlass: (visible: boolean) => void
  setHardware: (visible: boolean) => void
}

interface ModelViewer3DProps {
  item: PlanItem | null
  fallbackUrl?: string
  height?: number
}

export default function ModelViewer3D({ item, fallbackUrl, height = 460 }: ModelViewer3DProps) {
  const mountRef = React.useRef<HTMLDivElement>(null)
  const apiRef = React.useRef<ViewerApi | null>(null)
  const [showGlass, setShowGlass] = React.useState(true)
  const [showHardware, setShowHardware] = React.useState(true)
  const [failed, setFailed] = React.useState(false)

  React.useEffect(() => {
    const mount = mountRef.current
    if (!mount || !item) return undefined

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true })
    } catch {
      setFailed(true)
      return undefined
    }

    const width = mount.clientWidth || 640
    const heightPx = mount.clientHeight || height
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.setSize(width, heightPx)
    mount.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#f7f9fb')
    const camera = new THREE.PerspectiveCamera(38, width / heightPx, 1, 200000)

    scene.add(new THREE.HemisphereLight(0xffffff, 0x8fa0b3, 1.6))
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.1)
    keyLight.position.set(-1400, -2200, 2600)
    scene.add(keyLight)
    const fillLight = new THREE.DirectionalLight(0xdbe6f3, 0.9)
    fillLight.position.set(1800, 1400, 1000)
    scene.add(fillLight)

    const group = new THREE.Group()
    group.rotation.x = -Math.PI / 2 // model Z-up -> world Y-up
    scene.add(group)

    const barMaterials = new Map<string, THREE.MeshStandardMaterial>()
    const barMaterial = (key: string) => {
      let material = barMaterials.get(key)
      if (!material) {
        material = new THREE.MeshStandardMaterial({
          color: new THREE.Color(BAR_COLORS[key] ?? '#d5dbe1'),
          roughness: 0.55,
          metalness: 0.35,
        })
        barMaterials.set(key, material)
      }
      return material
    }

    for (const bar of item.bars ?? []) {
      if (!bar.polygon?.length) continue
      const shape = new THREE.Shape()
      bar.polygon.forEach(([x, z], index) => {
        if (index === 0) shape.moveTo(x, z)
        else shape.lineTo(x, z)
      })
      shape.closePath()
      const depth = Math.max(bar.y1 - bar.y0, 0.6)
      const geometry = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false })
      const mesh = new THREE.Mesh(geometry, barMaterial(bar.group))
      mesh.rotation.x = Math.PI / 2 // shape (x,z) -> world (x, ?, z), extrusion -> -Y
      mesh.position.y = bar.y1
      group.add(mesh)
    }

    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color('#8fc6e8'),
      transparent: true,
      opacity: 0.3,
      roughness: 0.08,
      metalness: 0,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
    const glassMeshes: THREE.Mesh[] = []
    for (const pane of item.panes ?? []) {
      const geometry = new THREE.BoxGeometry(pane.w, pane.t, pane.h)
      const mesh = new THREE.Mesh(geometry, glassMaterial)
      mesh.position.set(pane.x + pane.w / 2, pane.y + pane.t / 2, pane.z + pane.h / 2)
      group.add(mesh)
      glassMeshes.push(mesh)
    }

    const hardwareMeshes: THREE.Mesh[] = []
    const hardwareMaterials = new Map<string, THREE.MeshStandardMaterial>()
    for (const hardware of item.hardware ?? []) {
      let material = hardwareMaterials.get(hardware.kind)
      if (!material) {
        material = new THREE.MeshStandardMaterial({
          color: new THREE.Color(HARDWARE_COLORS[hardware.kind] ?? '#475569'),
          roughness: 0.32,
          metalness: 0.75,
        })
        hardwareMaterials.set(hardware.kind, material)
      }
      const geometry = new THREE.BoxGeometry(hardware.w, hardware.d, hardware.h)
      const mesh = new THREE.Mesh(geometry, material)
      mesh.position.set(hardware.x + hardware.w / 2, hardware.y + hardware.d / 2, hardware.z + hardware.h / 2)
      group.add(mesh)
      hardwareMeshes.push(mesh)
    }

    group.updateMatrixWorld(true)
    const box = new THREE.Box3().setFromObject(group)
    const size = new THREE.Vector3()
    const center = new THREE.Vector3()
    box.getSize(size)
    box.getCenter(center)
    const maxDim = Math.max(size.x, size.y, size.z, 100)
    const fitDistance = maxDim / (2 * Math.tan((camera.fov * Math.PI) / 360))
    const distance = fitDistance * 1.18
    const viewDirection = new THREE.Vector3(-0.36, 0.2, 0.91).normalize()
    const initialPosition = center.clone().addScaledVector(viewDirection, distance)

    camera.near = Math.max(maxDim / 400, 1)
    camera.far = maxDim * 30
    camera.position.copy(initialPosition)
    camera.updateProjectionMatrix()

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.copy(center)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.minDistance = maxDim * 0.28
    controls.maxDistance = maxDim * 3.5
    controls.maxPolarAngle = Math.PI * 0.98
    controls.update()

    let frameId = 0
    const animate = () => {
      frameId = window.requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const observer = new ResizeObserver(() => {
      const nextWidth = mount.clientWidth
      const nextHeight = mount.clientHeight
      if (!nextWidth || !nextHeight) return
      renderer.setSize(nextWidth, nextHeight)
      camera.aspect = nextWidth / nextHeight
      camera.updateProjectionMatrix()
    })
    observer.observe(mount)

    apiRef.current = {
      reset: () => {
        camera.position.copy(initialPosition)
        controls.target.copy(center)
        controls.update()
      },
      setGlass: (visible) => glassMeshes.forEach((mesh) => (mesh.visible = visible)),
      setHardware: (visible) => hardwareMeshes.forEach((mesh) => (mesh.visible = visible)),
    }
    apiRef.current.setGlass(showGlass)
    apiRef.current.setHardware(showHardware)

    return () => {
      window.cancelAnimationFrame(frameId)
      observer.disconnect()
      controls.dispose()
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose()
          const material = object.material
          if (Array.isArray(material)) material.forEach((entry) => entry.dispose())
          else material.dispose()
        }
      })
      renderer.dispose()
      if (renderer.domElement.parentElement === mount) mount.removeChild(renderer.domElement)
      apiRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item])

  React.useEffect(() => {
    apiRef.current?.setGlass(showGlass)
  }, [showGlass])

  React.useEffect(() => {
    apiRef.current?.setHardware(showHardware)
  }, [showHardware])

  if (!item) {
    return (
      <div className="grid place-items-center rounded-lg border border-dashed border-input py-16 text-xs text-muted-foreground">
        Chọn một hạng mục để xem 3D
      </div>
    )
  }

  if (failed) {
    return fallbackUrl ? (
      <img src={fallbackUrl} alt={item.tag} className="w-full rounded-lg border border-border bg-white" />
    ) : (
      <div className="grid place-items-center rounded-lg border border-dashed border-input py-16 text-xs text-muted-foreground">
        Trình duyệt không hỗ trợ WebGL
      </div>
    )
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-3">
        <Button variant="outline" size="sm" onClick={() => apiRef.current?.reset()}>
          <RotateCcw className="h-3.5 w-3.5" /> Đặt lại góc nhìn
        </Button>
        <CheckField label="Kính" checked={showGlass} onChange={(event) => setShowGlass(event.target.checked)} />
        <CheckField
          label="Phụ kiện (bản lề / khóa)"
          checked={showHardware}
          onChange={(event) => setShowHardware(event.target.checked)}
        />
        <span className="text-[11px] text-muted-foreground">
          Kéo chuột để xoay · lăn chuột để zoom · chuột phải để dịch
        </span>
      </div>
      <div
        ref={mountRef}
        style={{ height }}
        className="w-full cursor-grab overflow-hidden rounded-lg border border-border bg-[#f7f9fb] active:cursor-grabbing"
      />
    </div>
  )
}
