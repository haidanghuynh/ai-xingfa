# XingfaCAD

Tự động hoá **cửa nhôm Xingfa**: nhập kích thước → **mô hình 3D FreeCAD** + **bản vẽ 2D sản xuất (DXF/SVG)** + **bảng cắt tối ưu** + **báo giá Excel**, tất cả trên **GUI web React** (Vite + TypeScript + Tailwind + shadcn/ui style).

```text
Ảnh (ChatGPT/Midjourney) ──► AI extractor ─┐
Nhập tay / Excel / JSON ───────────────────┼──► project.json ──► CORE ENGINE ──┬──► FreeCADCmd ──► .FCStd/.step/.stl
Catalogue Xingfa (UI) ─────────────────────┘        (bóc tách + báo giá)       ├──► ezdxf ─────► .dxf + .svg
                                                                                 ├──► openpyxl ──► bao_gia.xlsx
                                                                                 └──► OBJ/SVG ───► ảnh 3D xem trước

GUI: web/ (Vite + React + TS + Tailwind)  ──proxy /api──►  FastAPI (src/xingfacad/api.py)
```

## 1. Tính năng

| Nhóm | Nội dung |
|---|---|
| Giao diện | **React 18 + Vite + TypeScript + Tailwind + component shadcn/ui style** (`web/`): responsive, toast, dialog, tabs, badge; build JS chính ~78 KB gzip, CSS ~5 KB gzip |
| Nhập liệu | 5 tab: Dự án (form + bảng hạng mục + dialog sửa từng cửa), Catalogue Xingfa, **Giá thành & giá bán**, Ảnh & AI, Kết quả; lưu nháp localStorage; xuất/mở JSON |
| Catalogue Xingfa | Thêm/sửa/nhân bản/xoá hệ nhôm **ngay trên UI**: mã hệ, kiểu ghép (45°/90°), cây nhôm, mạch cắt, đầu kẹp, thông số công nghệ, bảng thanh profile (mặt cắt, chiều sâu, vách, kg/m, rãnh kính, giá/kg) |
| Bảng giá | Sửa JSON trực tiếp: giá nhôm/kg, hao hụt, % nhân công, % lợi nhuận, VAT, vật tư phụ, vận chuyển, giá kính, phụ kiện |
| Ảnh & AI | Upload ảnh → **AI đọc ảnh** (ChatGPT/OpenAI hoặc Google Gemini, chọn model ngay trên UI) trả JSON spec; **màn hình duyệt** cho sửa mã/loại cửa/kích thước, hiện độ tin cậy + cờ *thiếu kích thước / AI không chắc* rồi mới áp vào dự án. AI **không** suy ra mm và **không** vẽ CAD — bảng vẽ/bảng cắt vẫn do engine tất định sinh. Có log audit trong `out/_ai/`; không có API key vẫn dùng được bằng cách dán JSON từ ChatGPT |
| 3D | **Viewer 3D xoay/zoom** (three.js + OrbitControls): kéo chuột xoay mọi hướng, lăn chuột zoom, chuột phải dịch, đặt lại góc nhìn, bật/tắt kính & phụ kiện. Mô hình dựng từ `build_plan.json` (thanh nhôm đúng góc 45°, kính, **bản lề/khóa/bánh xe**). Export `.FCStd/.step/.stl` qua `FreeCADCmd` + **ảnh SVG/OBJ** cho hồ sơ |
| 2D sản xuất | DXF (layer chuẩn) + SVG: mặt đứng có ký hiệu hướng mở, kích thước tổng/cánh, chi tiết tiết diện, bảng cắt, bảng kính, bảng phụ kiện, ghi chú, khung tên |
| Báo giá | Excel 6 sheet: `01_BaoGia` (công thức sống), `02_BangCat`, `03_ToiUuCat`, `04_Kinh_PhuKien`, `05_TongHop` (VAT, chiết khấu, tỷ suất lãi), `06_CauHinh` (named ranges). **PDF báo giá A4** (reportlab, font Arial tiếng Việt, số tiền bằng chữ, điều khoản, chữ ký, phụ lục kính & phụ kiện). **Xem trước PDF ngay trên tab Kết quả** trước khi tải về |
| Thông tin báo giá | Sửa trực tiếp trên báo giá: **đơn vị yêu cầu báo giá** (+ người nhận, điện thoại) và **người báo giá** (+ điện thoại) — hiện ở phần đầu PDF, ô chữ ký và file Excel; bấm *Cập nhật & xem trước* để sinh lại PDF/Excel mà không cần build lại bản vẽ |
| Giá thành | **File Excel tính giá thành** `gia_thanh_<MÃ>.xlsx`: sheet `01_DauVao` (giá NCC: nhôm/kg, hao hụt, % nhân công, % lãi, VAT, vật tư, vận chuyển + bảng giá kính/phụ kiện), `02_GiaThanh` (công thức sống), `03_Nhom`, `04_Kinh`, `05_PhuKien`, `06_HuongDan`. Tải **file mẫu** về điền giá rồi **Nhập giá từ Excel** để cập nhật app |
| Bảng chi phí & giá bán | **Tab riêng theo nhóm sản phẩm** (cửa sổ mở quay / cửa đi / cửa sổ lùa / vách kính): bảng **giá thành đầu vào** (nhôm, kính, phụ kiện, vật tư, nhân công SX + lắp đặt, xưởng, đóng gói, vận chuyển, % bảo hành/quản lý/lãi vay) → **giá đến tay khách** 3 cấp (lẻ / đại lý / công trình), giá công bố **chưa VAT**, VAT cộng khi báo giá. Nút *Lấy định mức từ BOM mẫu* tự tính kg/m², m² kính/m², phụ kiện/bộ từ chính engine bóc tách. Xuất **Excel nội bộ** + **PDF bảng giá gửi khách** (không lộ giá vốn) |
| Tối ưu cắt | First-Fit-Decreasing theo từng mã thanh, tính mạch cắt + đầu kẹp, chọn cây 5.8/6.5 m ít phế nhất |
| Kiểm tra | Cảnh báo/lỗi: kích thước quá nhỏ/lớn, ô kính vượt diện tích, cánh hẹp, kính không vừa rãnh, hệ chưa xác nhận catalogue |

## 2. Cài đặt

Yêu cầu: **Python 3.10+** (đã test 3.13) và **Node 18+** (đã test Node 22) cho giao diện React.

```powershell
cd c:\Users\OS\Downloads\cad

# 1) Backend
python -m pip install -r requirements.txt
python -m pip install -e .        # tuỳ chọn: có lệnh `xfcad`

# 2) Frontend (React)
cd web
npm install
npm run build                     # -> web/dist (FastAPI sẽ tự phục vụ tại "/")
cd ..
```

> Không muốn dùng React? Vẫn còn giao diện vanilla cũ ở `static/` làm fallback: nếu chưa có `web/dist`, FastAPI tự phục vụ `static/index.html`.

> Nếu pip báo `xfcad.exe` không nằm trên PATH, thêm `%APPDATA%\Python\Python313\Scripts` vào PATH, hoặc dùng `python -m xingfacad ...` (không cần cài editable) hay chạy `.\run.ps1`.

**FreeCAD (cho 3D)** – không bắt buộc để chạy báo giá/bản vẽ:

```powershell
winget install FreeCAD.FreeCAD
# hoặc tải tại freecad.org, sau đó kiểm tra:
xfcad status
```

Nếu FreeCAD cài ở chỗ khác, đặt biến môi trường `FREECAD_CMD` trỏ tới `FreeCADCmd.exe`.

## 3. Chạy

```powershell
python -m xingfacad serve            # http://127.0.0.1:8010 (phục vụ web/dist)
# hoặc sau khi pip install -e .
xfcad serve --port 8010
```

**Chế độ dev giao diện** (HMR, 2 terminal):

```powershell
# terminal 1 - API
python -m xingfacad serve --port 8010

# terminal 2 - Vite (proxy /api -> 127.0.0.1:8010)
cd web
npm run dev                          # http://127.0.0.1:5173
```

Sau khi sửa UI: `cd web; npm run build` rồi F5 trang 8010 (hoặc dùng luôn cổng 5173 khi dev).

### 3.1 Cấu trúc giao diện (`web/`)

```text
web/
├─ index.html, vite.config.ts, tailwind.config.ts, tsconfig.json
├─ src/
│  ├─ main.tsx / App.tsx         layout, tab, state, gọi API
│  ├─ index.css                  tailwind + design tokens (shadcn style)
│  ├─ components/ui/
│  │  ├─ primitives.tsx          Button/Input/Select/Checkbox/Badge/Label (cva)
│  │  ├─ layout.tsx              Card/SectionCard/Table/Tabs/Metric
│  │  └─ overlays.tsx            Dialog + Toast provider
│  ├─ features/project/          ProjectTab + ItemDialog (sửa từng cửa)
│  ├─ features/catalog/          CatalogTab + ProfilesEditor + templates
│  ├─ features/image/            ImageTab (prompt ChatGPT / OpenAI)
│  ├─ features/results/          ResultsTab + ModelViewer3D (three.js, lazy-load)
│  ├─ lib/                       api.ts (fetch + ApiError), project.ts, panels.ts, format.ts
│  └─ types/api.ts               kiểu phản chiếu models.py; types/openapi.d.ts sinh tự động
└─ scripts/capture.mjs           chụp ảnh UI bằng Chrome headless (dev tool)
```

- Type từ backend: `npm run gen:types` (cần API đang chạy ở 8010) → `src/types/openapi.d.ts` để đối chiếu khi `models.py` thay đổi.
- `npm run typecheck` (tsc strict) và `npm run build` (tsc + vite) đều phải pass.
- Ảnh chụp giao diện (dev tool): `node scripts/capture.mjs ../out/_ui` khi có Chrome headless với `--remote-debugging-port=9333`.

CLI khác:

```powershell
xfcad status                          # kiểm tra FreeCAD, số hệ nhôm
xfcad systems                         # liệt kê hệ nhôm
xfcad demo --out data/specs/demo.json # tạo file spec mẫu
xfcad validate --spec data/specs/demo_nha_a.json
xfcad build --spec data/specs/demo_nha_a.json           # build đầy đủ
xfcad build --spec ... --no-3d                          # bỏ qua FreeCAD
```

Không cài editable vẫn chạy được: `$env:PYTHONPATH='src'; python -m xingfacad serve`.

**AI đọc ảnh (tuỳ chọn)** — đặt key trước khi chạy server rồi khởi động lại:

```powershell
$env:OPENAI_API_KEY='sk-...'      # ChatGPT (mặc định)
$env:GEMINI_API_KEY='...'         # Google Gemini
```

Không có key vẫn dùng được tab **Ảnh & AI**: bấm *Sinh prompt*, dán vào ChatGPT kèm ảnh, dán JSON trả về rồi *Nạp JSON để duyệt*.

### 3.2 Triển khai nhanh trên máy khác

**Linux / macOS / WSL / Git Bash** — clone xong chạy 2 lệnh:

```bash
git clone https://github.com/haidanghuynh/ai-xingfa.git
cd ai-xingfa
cp .env.example .env          # tuỳ chọn: điền OPENAI_API_KEY / GEMINI_API_KEY
./scripts/deploy.sh           # tạo .venv + pip + npm ci + npm run build + kiểm tra
./scripts/run.sh              # http://127.0.0.1:8010
# cho máy khác trong LAN truy cập:
HOST=0.0.0.0 PORT=8010 ./scripts/run.sh
```

- `./scripts/deploy.sh --no-web` nếu chưa cài Node (server dùng giao diện fallback `static/`).
- `./scripts/deploy.sh --skip-install` chỉ build lại giao diện.
- `./scripts/deploy.sh --check` chỉ kiểm tra Python ≥ 3.10 / Node ≥ 18.
- `run.sh` tự nạp `.env` (HOST, PORT, API key) — không cần `export` thủ công.

**Windows (PowerShell):**

```powershell
.\scripts\deploy.ps1          # -NoWeb / -SkipInstall
.\scripts\run.ps1             # hoặc .\run.ps1
```

**Docker (máy đích không cần Python/Node):**

```bash
cp .env.example .env
docker compose up -d --build      # http://localhost:8010
docker compose logs -f
```

Volume `./config` và `./out` giữ catalogue/bảng giá/bản vẽ khi rebuild. FreeCAD không có trong container → dùng viewer 3D + OBJ; cần `.FCStd/.step/.stl` thì cài FreeCAD trên host.

**Chạy nền trên VPS bằng systemd:**

```bash
sudo useradd -r -m -d /opt/xingfacad xingfa
sudo git clone https://github.com/haidanghuynh/ai-xingfa.git /opt/xingfacad
sudo chown -R xingfa:xingfa /opt/xingfacad
sudo -u xingfa /opt/xingfacad/scripts/deploy.sh
sudo cp /opt/xingfacad/deploy/xingfacad.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now xingfacad
```

Sửa `User=` / `WorkingDirectory=` trong `deploy/xingfacad.service` nếu đặt ở thư mục khác; mở firewall cổng 8010 nếu cần truy cập ngoài.

**Lưu ý chung:** `web/dist` và `out/` không commit → `deploy.sh` bắt buộc build lại giao diện; API key chỉ nằm trong `.env` (đã `.gitignore`).

## 4. Quy trình sử dụng trên GUI

1. **Tab 2 – Catalogue Xingfa**: chọn hệ (XF65/XF93/...) → sửa số liệu theo catalogue thật → tick *Đã xác nhận catalogue* → **Lưu hệ**. Sửa thêm **Bảng giá** (giá nhôm/kg, % nhân công, VAT...).
2. **Tab 3 – Giá thành & giá bán**: chọn nhóm sản phẩm → nhập định mức chi phí (hoặc *Lấy định mức từ BOM mẫu*) → chỉnh % lãi/chiết khấu/VAT ở phần **Cấp giá** → **Lưu bảng giá**. Tải **Excel nội bộ** (có giá vốn) hoặc **PDF gửi khách** (chỉ giá bán).
3. **Tab 1 – Dự án**: nhập mã/tên/khách hàng, hệ + kính mặc định. Bấm **Dự án mẫu** để xem ví dụ, hoặc **+ Thêm cửa**.
4. Nhập từng cửa: Rộng/Cao (mm), SL, cao độ, **Cánh**, **Đố ngang**:
   - `sash:L, sash:R` – 2 cánh mở quay (trái/phải)
   - `sash:L:0.6, sash:R:0.4` – chia tỷ lệ 60/40
   - `fixed` hoặc `sash:L, fixed` – ô cố định
   - `sash:slide, sash:slide` – cửa lùa
   - Đố ngang: `h@500:fixed; h@1500` (cách mép trên 500 mm, ô phía trên là kính cố định)
   - Để trống = tự động chia theo kích thước/loại cửa
5. **Kiểm tra dữ liệu** → sửa các lỗi/cảnh báo hiện ra.
6. **Cách tính giá** trên thanh công cụ: `Chi tiết BOM` (bóc tách từng thanh, như mặc định) hoặc `Theo bảng giá ban hành` (giá/m² × diện tích theo cấp giá đã chọn).
7. **Build** → tab 5 hiện: diện tích, kg nhôm, m² kính, giá vốn, doanh thu, VAT, tổng thanh toán; **khung xem trước báo giá PDF** (sửa đơn vị yêu cầu / người báo giá / điện thoại rồi bấm *Cập nhật & xem trước*), bảng file tải về; ảnh 3D + bản vẽ xem trước; tối ưu cắt; trạng thái FreeCAD.

## 5. Dữ liệu hệ nhôm (quan trọng)

Mỗi hệ là 1 file `config/systems/<mã>.json`. Trường quan trọng:

| Trường | Ý nghĩa | Ảnh hưởng |
|---|---|---|
| `joint` | `miter45` (hàn 45°) / `butt90` (ghép vuông) | Chiều dài cắt & hình học mối nối |
| `bar_length_mm` | Chiều dài cây nhôm | Tối ưu cắt |
| `kerf_mm`, `end_trim_mm` | Mạch cắt, đầu kẹp | Tối ưu cắt |
| `profiles.frame.width_mm / depth_mm` | Mặt cắt nhìn thấy / chiều sâu khung bao | Kích thước ô kính, hình học |
| `profiles.sash.width_mm / depth_mm` | Mặt cắt / chiều sâu cánh | Kích thước cánh, kính |
| `profiles.*.kg_per_m` | Khối lượng mét dài | Bảng cắt, tiền nhôm |
| `profiles.*.glass_groove_mm` | Rãnh kính | Cảnh báo kính không vừa |
| `rules.gap_frame_sash_mm` | Khe hở khung–cánh | Kích thước cánh |
| `rules.sash_overlap_mm` | Cánh chồng (cửa lùa) | Chia cánh lùa |
| `rules.glass_rebate_mm` | Ngậm kính vào rãnh | Kích thước kính |
| `rules.max_panel_area_m2` | Diện tích ô tối đa | Cảnh báo chia đố |

> Số liệu 4 hệ mẫu (`XF55`, `XF60`, `XF65`, `XF93`) là **ví dụ**, đang để `verified: false`. Hãy thay bằng catalogue nhà cung cấp thật rồi tick xác nhận.

### 5.1 Bản lề & khóa (chọn theo từng cửa)

Trong dialog sửa cửa có mục **Bản lề & khóa**:

| Trường | Ý nghĩa |
|---|---|
| `hinge_count` | **Số bản lề mỗi cánh**: để trống = tự động theo hệ (`per_leaf_by_type`), `0` = không bản lề, hoặc 2–6 cái. Gợi ý tự động theo chiều cao: ≤1200 mm → 2, ≤1800 mm → 3, >1800 mm → 4 |
| `hinge_type` | **Loại bản lề** (mã trong catalogue, xem bảng dưới) |
| `lock_type` | **Loại khóa** (mã trong catalogue), `none` = không khóa |

**Bộ mẫu phổ thông** (giá tham khảo thị trường, sửa lại tại tab *Catalogue → Bảng giá/Kính & phụ kiện*):

| Mã | Tên | Giá tham khảo | Ghi chú |
|---|---|---|---|
| `hinge_2d` | Bản lề 2D inox 304 | 35.000 đ/cái | Cửa nhẹ, cánh ≤ 1.2 m |
| `hinge_3d` | Bản lề 3D (cối) inox 304 | 55.000 | Phổ thông cho cửa sổ mở quay |
| `hinge_3d_304` | Bản lề 3D inox 304 cao cấp | 85.000 | Cửa lớn, tải nặng |
| `hinge_4in` | Bản lề 4 inch | 45.000 | Cánh 600–900 mm |
| `hinge_6in` | Bản lề 6 inch | 75.000 | Cửa đi, cánh nặng > 40 kg |
| `hinge_hidden` | Bản lề âm (hidden) | 180.000 | Thẩm mỹ cao |
| `hinge_weld` | Bản lề hàn chữ A | 30.000 | Hàn trực tiếp vào khung |
| `lock_single` | Khóa đơn điểm | 120.000 đ/bộ | Tay nắm + 1 chốt |
| `lock_multi2` | Khóa đa điểm 2 điểm | 450.000 | Cửa đi |
| `lock_multi3` | Khóa đa điểm 3 điểm | 650.000 | Cửa đi chính |
| `lock_snap` | Khóa sập / chốt sập | 45.000 | Cửa phụ |
| `lock_lever` | Tay gạt có khóa | 250.000 | Cửa đi |
| `lock_cylinder` | Tay nắm tròn + khóa bi | 180.000 | Cửa sổ, ban công |
| `lock_smart` | Khóa vân tay / thông minh | 2.500.000 | Tuỳ chọn cao cấp |

Cách hoạt động:

- Mặc định (không chọn gì) lấy theo `hardware.per_leaf_by_type` trong `config/catalog.json` — ví dụ cửa mở quay: 3 bản lề + 1 khóa + 1 tay nắm + 2 chặn hành trình **mỗi cánh**.
- Chọn loại khác → dùng đúng mã đó (giá & tên trong `hardware.components`), không cộng trùng với bản lề/khóa mặc định.
- Muốn thêm loại mới: thêm 1 key vào `hardware.components` (name/unit/price/note) rồi thêm key đó vào `hinge_options` hoặc `lock_options` — UI tự hiện trong dropdown.
- Kết quả: bảng phụ kiện trong Excel (`04_Kinh_PhuKien`) và bảng **BẢNG PHỤ KIỆN** trên bản vẽ DXF cập nhật theo lựa chọn; giá vốn/giá bán tính lại ngay.
- Kiểm tra tự động cảnh báo: cửa cố định/lùa mà chọn bản lề, cánh mở chọn 0 bản lề, cánh cao > 1800 mm chọn < 3 bản lề, hoặc mã phụ kiện không có trong catalogue.

## 6. Công thức bóc tách (theo cách làm xưởng)

| Hạng mục | Công thức |
|---|---|
| Khung bao hàn 45° | Ngang = `W`, Đứng = `H`, cắt 45°/45° |
| Khung bao ghép 90° | Ngang = `W - 2·w_frame`, Đứng = `H`, cắt 90° |
| Đố đứng | `H - 2·w_frame`, cắt 90° |
| Đố ngang | `W - 2·w_frame`, cắt 90° |
| Cánh mở quay | `leaf_w = (W - 2·w_frame - (n-1)·w_mullion)/n - 2·gap`, `leaf_h = H - 2·w_frame - 2·gap`; thanh cánh: 2×`leaf_w` + 2×`leaf_h`, hàn 45° |
| Cánh lùa | `leaf_w = (W - 2·w_frame + (n-1)·overlap)/n - 2·gap`, `leaf_h = H - h_ray_trên - h_ray_dưới - 2·gap` |
| Kính có cánh | `(leaf_w - 2·w_sash + 2·rebate - clearance) × (leaf_h - ...)` |
| Kính cố định | `(cell_w + 2·rebate - clearance) × (cell_h + 2·rebate - clearance)` |
| Khối lượng | `Σ(dài × SL) / 1000 × kg_per_m` |
| Tiền nhôm | `kg × đơn giá/kg × (1 + hao hụt%)` |
| Giá bán | `giá vốn × (1 + %lợi nhuận)`, làm tròn 1.000 đ |
| VAT | `doanh thu × %VAT` (sheet `05_TongHop`) |

Phụ kiện tính theo cánh (bản lề 3D, tay nắm, khoá, chặn hành trình, bánh xe lùa), gioăng = chu vi kính + 5%, silicone = số tuýp theo mét gioăng, vít/ke góc = 1 bộ/thanh hàn 45°. Tất cả nằm trong `config/catalog.json` (sửa được trên UI).

## 7. File sinh ra (trong `out/<MÃ DỰ ÁN>/`)

| File | Nội dung |
|---|---|
| `project.json` | Spec đã chuẩn hoá (mở lại được trên UI/CLI) |
| `<tag>.dxf` | Bản vẽ 2D sản xuất (mm, layer: frame/sash/glass/dim/text/table/title/note) |
| `<tag>_banve.svg` | Bản vẽ 2D dạng vector xem trên web/in nhanh |
| `<tag>_3d.svg` | Ảnh phối cảnh 3D (axonometric) |
| `<tag>.obj` + `.mtl` | Mô hình 3D (thanh nhôm + kính + bản lề/khóa) mở bằng mọi phần mềm |
| `cutlist.csv` | Bảng cắt toàn dự án (dấu `;`, UTF-8 BOM, mở Excel trực tiếp) |
| `bao_gia_<MÃ>.xlsx` | Báo giá 6 sheet + tối ưu cắt + cấu hình giá |
| `bao_gia_<MÃ>.pdf` | **Báo giá PDF A4** gửi khách: header công ty, bảng hạng mục, tổng + VAT, số tiền bằng chữ, điều khoản, chữ ký, phụ lục kính/phụ kiện |
| `gia_thanh_<MÃ>.xlsx` | **Bảng tính giá thành**: giá đầu vào + giá vốn/giá bán từng cửa + chi tiết nhôm/kính/phụ kiện + hướng dẫn |
| `build_plan.json` | Hợp đồng hình học cho viewer 3D + FreeCAD (bars, panes, hardware) |
| `<MÃ>.FCStd` / `.step` / `.stl` | Chỉ có khi cài FreeCAD và bật 3D |
| `freecad_report.json` | Số object, thể tích, cảnh báo hình học |
| `build_summary.json` | Tổng hợp số liệu lần build |

### 7.1 Báo giá PDF & file tính giá thành

**Báo giá PDF** (`bao_gia_<MÃ>.pdf`) — 2 trang A4:

1. Trang 1: header công ty (tên/địa chỉ/ĐT/MST), số báo giá + ngày, **đơn vị yêu cầu báo giá** (kèm người nhận & ĐT), khách hàng, công trình, địa chỉ, **người báo giá + ĐT**, bảng hạng mục (mô tả gồm hệ, kính, **bản lề/khóa đã chọn**), cộng tiền hàng, VAT, **tổng thanh toán**, **số tiền bằng chữ**, điều khoản (sửa được bằng `quote_terms` trong `config/pricing.json`), ô chữ ký 2 bên (kèm tên khách hàng & người báo giá), footer số trang.
2. Trang 2 (phụ lục): quy cách kính từng ô + danh sách phụ kiện (bản lề, khóa, tay nắm, bánh xe…).

Font: tự dùng **Arial** (Windows) hoặc DejaVu/Liberation (Linux) để hiển thị đúng dấu tiếng Việt; nếu không tìm thấy font sẽ fallback Helvetica.

**File tính giá thành** (`gia_thanh_<MÃ>.xlsx`):

| Sheet | Nội dung |
|---|---|
| `01_DauVao` | 7 ô **màu vàng** cần điền: `GIA_NHOM`, `HAO_HUT_PCT`, `NHAN_CONG_PCT`, `LOI_NHUAN_PCT`, `VAT_PCT`, `VATTU_M2`, `VAN_CHUYEN` + bảng giá kính & phụ kiện (named ranges) |
| `02_GiaThanh` | Từng cửa: DT, kg nhôm, tiền nhôm, kính, phụ kiện, nhân công, vật tư, vận chuyển, **giá vốn → lãi → giá bán → đơn giá/m²**, tổng + VAT + tổng thanh toán |
| `03_Nhom` | Tổng mét/khối lượng theo mã thanh + tỷ trọng + thành tiền |
| `04_Kinh` | Quy cách & tiền kính từng ô |
| `05_PhuKien` | Chi tiết phụ kiện (SL × đơn giá) |
| `06_HuongDan` | Hướng dẫn sử dụng |

Quy trình “file lúc đầu để tính giá thành”:

```text
Catalogue → [File tính giá thành]  ──►  mở Excel, điền giá NCC ở 01_DauVao
        ──►  (tuỳ chọn) nhập thêm dòng cửa ở 02_GiaThanh để tính thử
        ──►  lưu file  ──►  Catalogue → [Nhập giá từ Excel]
        ──►  app cập nhật 7 thông số giá  ──►  Dự án → Build → PDF/Excel dùng giá mới
```

API liên quan: `GET /api/template/costing.xlsx` (file mẫu), `POST /api/pricing/import` (nhận `file_base64`, đọc sheet `01_DauVao`).

### 7.2 Bảng chi phí giá thành & bảng giá đến tay khách

Dữ liệu nằm ở `config/pricing_book.json` (sửa trực tiếp trên tab **Giá thành & giá bán**). Chia theo **nhóm sản phẩm**, mỗi nhóm map sang các `item_types`:

| Nhóm | Loại cửa | Cửa mẫu mặc định |
|---|---|---|
| `CSMQ` | `casement`, `awning`, `tilt_turn` | 1800×2200, hệ XF65, 2 cánh |
| `CD` | `door_swing`, `door_sliding` | 1800×2400, 2 cánh, khóa đa điểm |
| `CL` | `sliding` | 2000×1600, hệ XF93, 2 cánh trượt |
| `VK` | `fixed` | 1200×2000 |

**Bảng A – giá thành đầu vào (đ/m²)**

| Dòng | Cách tính |
|---|---|
| Nhôm thanh | `kg/m² × đ/kg × (1 + hao hụt%)` |
| Kính | `m² kính/m² × đ/m² × (1 + hao hụt%)` |
| Phụ kiện | `Σ(định mức/bộ × đơn giá) ÷ diện tích cửa mẫu` |
| Vật tư phụ | đ/m² (gioăng, keo, vít) |
| Nhân công sản xuất / lắp đặt | đ/m² |
| Xưởng – khấu hao / đóng gói / vận chuyển | đ/m² |
| Bảo hành – quản lý – lãi vay | `% × cộng trực tiếp` |
| **Giá thành toàn bộ** | cộng 9 dòng + 3% phụ; **giá/bộ mẫu** = × diện tích mẫu |

**Bảng B – giá đến tay khách**

```text
Giá niêm yết  = Giá thành toàn bộ × (1 + % lãi)
Giá theo cấp  = Giá niêm yết × (1 − % chiết khấu)
Đến tay khách = Giá theo cấp × (1 + VAT)  → làm tròn (mặc định 1.000 đ)
```

Mặc định 3 cấp: **Khách lẻ** 20% lãi / 0% CK, **Đại lý cấp 1** 20% / 10%, **Công trình** 15% / 5%; giá công bố **chưa VAT 8%** (VAT cộng khi báo giá); mỗi cấp có công tắc *gồm lắp đặt* (tắt = trừ nhân công lắp đặt khỏi giá vốn).

**Chọn cột hiển thị trong bảng giá**: mỗi cấp có công tắc **Hiện bảng giá** (`show_in_quote`) — tắt thì cột giá đó bị bỏ khỏi bảng trên UI, file Excel và PDF gửi khách (vẫn dùng được để báo giá nội bộ, trong ô chọn cấp giá sẽ ghi *“ẩn bảng giá”*). Công tắc **Hiện cột “đã VAT”** (`settings.show_inc_vat`) quyết định in thêm cột giá đã VAT hay chỉ in giá chưa VAT.

Nút **Lấy định mức từ BOM mẫu** dùng chính engine bóc tách với cửa mẫu của nhóm: tự điền `kg nhôm/m²`, `m² kính/m²`, danh sách phụ kiện/bộ (bản lề, khóa, tay nắm…) và đơn giá từ catalogue.

File xuất (qua API, lưu ở `out/_templates/`):

| File | Nội dung |
|---|---|
| `bang_gia_thanh_va_gia_ban.xlsx` | 3 sheet: `01_ChiPhiDauVao` (chi phí × nhóm + giá thành/bộ), `02_GiaDenKhach` (giá/m² & giá/bộ theo cấp, chưa/đã VAT), `03_CauHinh` (định mức + cấp giá) — **nội bộ** |
| `bang_gia_ban.pdf` | A4 ngang gửi khách: bảng giá/m² theo cấp + giá trọn bộ + ghi chú, **không có cột giá vốn** |

Báo giá theo bảng giá: `POST /api/build` với `"pricing_mode": "book"`, `"price_level": "le"` (hoặc `dl1`, `ct`); CLI: `python -m xingfacad build --spec data/specs/demo_nha_a.json --pricing-mode book --price-level dl1`. Khi đó giá bán từng hạng mục = giá/m² của nhóm × diện tích × SL, VAT + làm tròn lấy theo bảng giá; giá vốn BOM vẫn được tính để đối chiếu lãi.

## 8. FreeCAD headless

- Kiến trúc: Python 3.13 sinh `build_plan.json` → chạy `FreeCADCmd.exe freecad_build.py --plan ... --out ...` bằng subprocess (vì FreeCAD có Python riêng, không import chéo được).
- Script `src/xingfacad/freecad_build.py` chỉ dùng stdlib + FreeCAD API: mỗi thanh = polygon tiết diện (đã có góc 45°) extrude theo chiều sâu → solid thật; kính = box; **bản lề/khóa/bánh xe = box** (cùng `hardware` trong `build_plan.json`).
- Kiểm tra tự động: nếu thể tích mô hình < 90% khối lượng BOM → ghi cảnh báo trong `freecad_report.json`.
- Không có FreeCAD vẫn build được Excel + DXF + SVG + OBJ (chỉ thiếu `.FCStd/.step/.stl`).

## 9. Ảnh & AI (tuỳ chọn)

Nguyên tắc: **AI chỉ đọc ảnh → JSON spec**, không suy ra mm và không sinh CAD/DXF. Bảng vẽ + bảng cắt vẫn do engine tất định sinh từ spec + catalogue.

**3 bước trên UI (tab Ảnh & AI):**

1. Chọn ảnh + chọn **provider/model** (OpenAI hoặc Gemini) → **Đọc ảnh bằng AI**.
2. Hoặc offline: **Sinh prompt** → copy → dán vào ChatGPT kèm ảnh → dán JSON → **Nạp JSON để duyệt**.
3. **Màn hình duyệt**: sửa mã / loại cửa / Rộng / Cao / SL, xem độ tin cậy và cờ *thiếu kích thước / loại cửa? / chia cánh? / AI không chắc*; tick chọn cửa rồi **Nhập N cửa đã chọn**.

**Cấu hình provider** — `config/ai.json` (đã có mặc định):

| Provider | Biến môi trường | Model mặc định | Ghi chú |
|---|---|---|---|
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | JSON ổn định, tiếng Việt tốt |
| `gemini` | `GEMINI_API_KEY` | `gemini-2.5-flash` | Ảnh lớn, chi phí thấp |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` | **Không đọc ảnh** (chỉ dùng cho text) |
| `local` | `LOCAL_AI_KEY` | `qwen2.5-vl` | OpenAI-compatible (Ollama/vLLM), chạy nội bộ |

Model đổi được ngay trên UI. Mỗi lần gọi AI, prompt + phản hồi + item đã chuẩn hoá được lưu vào `out/_ai/<thời-gian>_<provider>.json` để audit.

Chuẩn hoá phía server (`ai_vision.normalize_items`): loại cửa lạ → `casement` + cờ `loai_cua`; `width_mm/height_mm` thiếu → giữ `null` + cờ `kich_thuoc`; cửa đi mặc định cao độ 0, cửa sổ 900; tag trùng → tự đổi + cờ `trung_ma`; `confidence < 0.6` → cờ `do_tin_cay_thap`. Không bao giờ tự điền mm.

Prompt nằm ở `data/prompts/extract_windows.md` (yêu cầu AI để `null` nếu ảnh không có số đo). Cửa nhập từ AI vẫn ghi chú `[Cần nhập kích thước]` cho tới khi bạn điền Rộng/Cao.

## 10. API (dùng để tích hợp)

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/api/status` | Trạng thái FreeCAD/DXF/OpenAI, danh mục loại cửa |
| GET | `/api/ai` | Danh sách provider AI đọc ảnh, model, trạng thái khoá API (không lộ key) |
| GET/POST | `/api/systems` / `/api/systems/{code}` | Danh sách/lưu hệ nhôm |
| DELETE | `/api/systems/{code}` | Xoá hệ |
| POST | `/api/systems/{code}/duplicate` | Nhân bản hệ (`new_code`) |
| GET/PUT | `/api/catalog`, `/api/pricing` | Kính + phụ kiện, bảng giá |
| GET | `/api/template/costing.xlsx` | Tải file Excel mẫu tính giá thành |
| POST | `/api/pricing/import` | Đọc 7 thông số giá từ file Excel (`file_base64`) |
| GET/PUT | `/api/pricing-book` | Bảng chi phí giá thành đầu vào + bảng giá đến tay khách (kèm kết quả tính) |
| POST | `/api/pricing-book/derive/{code}` | Lấy định mức kg/m², m² kính/m², phụ kiện/bộ từ BOM cửa mẫu |
| GET | `/api/pricing-book/export.xlsx` / `export.pdf` | Excel nội bộ (có giá vốn) / PDF bảng giá gửi khách |
| GET | `/api/demo`, `/api/projects`, `/api/projects/{code}` | Dự án mẫu/đã build |
| POST | `/api/validate` | Kiểm tra spec, trả issues + tổng kg/m² |
| POST | `/api/build` | Build đầy đủ, trả summary + artifacts + cut plan |
| POST | `/api/quote` | Cập nhật thông tin báo giá (đơn vị yêu cầu, người báo giá…) → sinh lại `project.json` + Excel/PDF, giữ nguyên bản vẽ |
| GET | `/api/files/{code}/{name}` | Tải file (chặn path traversal); thêm `?inline=1` để nhúng PDF vào iframe xem trước |
| GET | `/api/prompt` | Prompt trích xuất ảnh |
| POST | `/api/extract` | Gọi AI vision (`provider`, `model` tuỳ chọn) → item đã chuẩn hoá + `needs_review` + log audit |

Ví dụ build bằng PowerShell:

```powershell
$spec = Get-Content data/specs/demo_nha_a.json -Raw | ConvertFrom-Json
$body = @{ project = $spec; with_3d = $false } | ConvertTo-Json -Depth 20
Invoke-RestMethod -Uri http://127.0.0.1:8010/api/build -Method Post -Body $body -ContentType 'application/json'
```

## 11. Test

```powershell
python -m pytest -q
```

79 test: bóc tách (khung/cánh/kính/lùa/đố), phụ kiện 3D, tối ưu cắt, pipeline (DXF/SVG/OBJ/XLSX/PDF/giá thành), API (CRUD hệ nhôm, validate, build, tải file, template & import giá, **cập nhật thông tin báo giá + xem trước inline**), **bảng chi phí giá thành & giá bán** (công thức giá vốn → 3 cấp giá, chiết khấu, VAT, làm tròn, derive từ BOM, xuất Excel/PDF, build theo bảng giá), **AI vision** (OpenAI/Gemini adapter, chuẩn hoá item, cờ needs_review, log audit, lỗi thiếu key/provider), model/catalogue.

## 12. Cấu trúc mã nguồn

```text
cad/
├─ config/            systems/*.json, catalog.json (kính + phụ kiện), pricing.json, pricing_book.json, ai.json
├─ data/              specs/demo_nha_a.json, prompts/extract_windows.md
├─ src/xingfacad/
│  ├─ models.py       pydantic: ProjectSpec, SystemDef, ItemResult...
│  ├─ catalog.py      đọc/ghi catalogue, bảng giá
│  ├─ layout.py       bóc tách: bảng cắt, kính, phụ kiện, hình học 3D
│  ├─ optimizer.py    tối ưu cắt cây (FFD + kerf + đầu kẹp)
│  ├─ validate.py     quy tắc kiểm tra
│  ├─ pricing.py      giá vốn/giá bán/VAT
│  ├─ drawing.py      dựng "sheet" 2D (mặt đứng, chi tiết, bảng, khung tên)
│  ├─ dxf_out.py      sheet → DXF (ezdxf)
│  ├─ svg_out.py      sheet → SVG
│  ├─ preview3d.py    axonometric → SVG + OBJ/MTL
│  ├─ quote.py        Excel 6 sheet
│  ├─ costing.py      Excel tính giá thành + template + đọc giá từ Excel
│  ├─ ai_vision.py    adapter AI đọc ảnh (OpenAI/Gemini) + chuẩn hoá JSON + log audit
│  ├─ pricing_book.py bảng chi phí giá thành + bảng giá đến tay khách theo nhóm sản phẩm
│  ├─ price_book_export.py Excel nội bộ + PDF bảng giá gửi khách
│  ├─ pdf_quote.py    PDF báo giá A4 (reportlab, số tiền bằng chữ)
│  ├─ freecad_plan.py sinh build_plan.json
│  ├─ freecad_build.py chạy trong FreeCAD (stdlib + FreeCAD API)
│  ├─ pipeline.py     điều phối build
│  ├─ api.py          FastAPI
│  └─ cli.py          xfcad serve/build/validate/systems/demo/status
├─ scripts/           deploy.sh / run.sh (bash), deploy.ps1 / run.ps1 (Windows) + công cụ dev
├─ deploy/            xingfacad.service (systemd unit)
├─ Dockerfile         build web + runtime Python (docker compose up -d --build)
├─ docker-compose.yml, .env.example
├─ static/            GUI fallback (vanilla JS) khi chưa build web/dist
├─ web/               GUI chính: Vite + React + TS + Tailwind (xem 3.1)
└─ tests/             pytest
```

## 13. Hướng phát triển tiếp (V2)

1. **Tiết diện thật** của từng mã Xingfa (polygon nhiều rãnh) thay cho mô hình envelope — dữ liệu đã sẵn sàng vì `ProfileDef` cho phép mở rộng.
2. Tối ưu cắt bằng OR-Tools CP-SAT (giảm thêm 1-3% phế với dự án lớn).
3. Bản vẽ TechDraw trong FreeCAD (PDF đúng tỷ lệ, khung tên tự động).
4. Nhiều đố đứng/hộp cánh, vách kính, cửa trượt nhiều ray, cửa xếp.
5. Đa dự án + phân quyền, lưu DB (SQLite/Postgres) thay vì file JSON.
6. Xuất PDF báo giá + hợp đồng, gửi email/Zalo.

## 14. Ghi chú kỹ thuật

- DXF dùng đơn vị **mm**, layer tiếng Việt không dấu (`frame`, `sash`, `glass`, `dim`, `text`, `table`, `title`), text style `VI` font Arial để hiển thị dấu tiếng Việt.
- Excel ghi **công thức thật**; mở bằng Excel/LibreOffice sẽ tự tính. Giá trị đã tính sẵn vẫn có trong `project.json`/API để đối chiếu.
- Mọi số liệu dùng chung một nguồn: `layout.py` → bảng cắt/kính/kg → `quote.py`/`drawing.py`/FreeCAD. Sửa 1 chỗ, tất cả cùng đổi.
- Giao diện React build ra `web/dist`: JS chính ~237 KB / **74 KB gzip**, CSS 5 KB gzip, **viewer 3D tách chunk riêng ~580 KB / 146 KB gzip** (chỉ tải khi mở tab Kết quả). FastAPI phục vụ tại `/`, API vẫn ở `/api/*` nên không cần CORS khi chạy cùng cổng; khi `npm run dev` thì Vite proxy `/api` → 8010.
- `scripts/` chứa công cụ dev: `smoke.py` (build demo + in tổng hợp), `check_outputs.py` (kiểm tra DXF/SVG/OBJ/XLSX), `render_png.py` (render PNG để soi bản vẽ), `check_ui_ids.py` (đối chiếu id UI vanilla).
