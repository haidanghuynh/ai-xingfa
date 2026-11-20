/**
 * Chụp ảnh giao diện bằng Chrome headless qua CDP (dev tool).
 * Dùng: node scripts/capture.mjs <thư-mục-ảnh>  [APP_URL] [CDP_PORT]
 * Yêu cầu: Chrome/Edge đang chạy với --remote-debugging-port=9333
 */
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'

const outDir = process.argv[2] ?? '.'
const APP_URL = process.argv[3] ?? 'http://127.0.0.1:8013/'
const CDP_PORT = process.argv[4] ?? '9333'

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const targets = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json()
const page = targets.find((target) => target.type === 'page')
if (!page) throw new Error('Không tìm thấy tab Chrome để điều khiển')

const socket = new WebSocket(page.webSocketDebuggerUrl)
await new Promise((resolve) => socket.addEventListener('open', resolve, { once: true }))

let sequence = 0
const pending = new Map()
socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data)
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message)
    pending.delete(message.id)
  }
})

const send = (method, params = {}) => {
  const id = ++sequence
  socket.send(JSON.stringify({ id, method, params }))
  return new Promise((resolve) => pending.set(id, resolve))
}

const evaluate = async (expression) => {
  const response = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  return response.result?.result?.value
}

const shot = async (name) => {
  const response = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
  const file = join(outDir, `${name}.png`)
  writeFileSync(file, Buffer.from(response.result.data, 'base64'))
  console.log('saved', name)
}

const clickByText = (text, selector = 'button') =>
  evaluate(`(() => {
    const nodes = [...document.querySelectorAll(${JSON.stringify(selector)})];
    const node = nodes.find((item) => (item.textContent || '').includes(${JSON.stringify(text)}));
    if (!node) return false;
    node.click();
    return true;
  })()`)

await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: 1500,
  height: 1150,
  deviceScaleFactor: 1,
  mobile: false,
})
await send('Page.navigate', { url: APP_URL })
await wait(3000)
await shot('ui_project_empty')

console.log('demo:', await clickByText('Dự án mẫu'))
await wait(1800)
await shot('ui_project_demo')

console.log('dialog:', await evaluate(`(() => {
  const node = document.querySelector('button[title="Sửa"]');
  if (!node) return false;
  node.click();
  return true;
})()`))
await wait(900)
await shot('ui_item_dialog')
await clickByText('Hủy')
await wait(400)

console.log('build:', await clickByText('Build:'))
await wait(7000)
await shot('ui_results')

console.log('catalog:', await clickByText('Catalogue', '[role=tab]'))
await wait(1600)
await shot('ui_catalog')

console.log('pricing:', await clickByText('Giá thành', '[role=tab]'))
await wait(1800)
await shot('ui_pricing')

console.log('image:', await clickByText('Ảnh', '[role=tab]'))
await wait(900)
await shot('ui_image')

const sampleJson = JSON.stringify({
  items: [
    {
      tag: 'C1',
      room: 'Phòng khách',
      type: 'casement',
      width_mm: 1800,
      height_mm: 2200,
      sill_mm: 900,
      panels: [
        { kind: 'sash', open: 'out', dir: 'left', ratio: 1 },
        { kind: 'sash', open: 'out', dir: 'right', ratio: 1 },
      ],
      glass: { key: 'cuong_luc_8', thickness_mm: 8 },
      confidence: 0.82,
      needs_review: [],
    },
    {
      tag: 'D1',
      room: 'Lối vào',
      type: 'door_swing',
      width_mm: null,
      height_mm: null,
      sill_mm: 0,
      panels: [
        { kind: 'sash', open: 'out', dir: 'left', ratio: 1 },
        { kind: 'sash', open: 'out', dir: 'right', ratio: 1 },
      ],
      glass: { key: 'cuong_luc_8', thickness_mm: 8 },
      confidence: 0.55,
      needs_review: ['kich_thuoc'],
    },
  ],
})

console.log('fill_review:', await evaluate(`(() => {
  const areas = [...document.querySelectorAll('textarea')];
  const area = areas[areas.length - 1];
  if (!area) return false;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  setter.call(area, ${JSON.stringify(sampleJson)});
  area.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
})()`))
await wait(400)
console.log('parse_review:', await clickByText('Nạp JSON để duyệt'))
await wait(700)
await shot('ui_image_review')

console.log('back_results:', await clickByText('Kết quả', '[role=tab]'))
await wait(900)
console.log('c3:', await clickByText('C3', '[role=tab]'))
await wait(1300)
await shot('ui_results_c3')

const canvasBox = await evaluate(`(() => {
  const canvas = document.querySelector('canvas');
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
})()`)

if (canvasBox) {
  await send('Input.dispatchMouseEvent', {
    type: 'mousePressed', x: canvasBox.x, y: canvasBox.y, button: 'left', buttons: 1, clickCount: 1,
  })
  for (let step = 1; step <= 10; step += 1) {
    await send('Input.dispatchMouseEvent', {
      type: 'mouseMoved', x: canvasBox.x - step * 20, y: canvasBox.y + step * 6, button: 'left', buttons: 1,
    })
    await wait(40)
  }
  await send('Input.dispatchMouseEvent', {
    type: 'mouseReleased', x: canvasBox.x - 200, y: canvasBox.y + 60, button: 'left', buttons: 0, clickCount: 1,
  })
  await wait(1000)
  await shot('ui_results_rotated')
}

socket.close()
