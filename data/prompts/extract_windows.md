# Prompt trích xuất cửa nhôm từ ảnh (dán vào ChatGPT kèm ảnh)

Bạn là kỹ sư cửa nhôm Xingfa. Hãy đọc ảnh phối cảnh/mặt bằng và trả về **DUY NHẤT một JSON** (không giải thích, không markdown) theo schema dưới đây.

## Quy tắc bắt buộc

1. **Không được tự suy ra kích thước mm từ ảnh.** Nếu ảnh không ghi kích thước, đặt `width_mm` và `height_mm` = `null` và thêm `"kich_thuoc"` vào `needs_review`.
2. Chỉ lấy từ ảnh: loại cửa, số cánh, hướng mở, số đố, tỷ lệ chia cánh (ước lượng theo pixel), vị trí phòng.
3. `type` chỉ nhận một trong: `casement` (mở quay), `sliding` (lùa), `fixed` (cố định), `awning` (mở hất), `door_swing` (cửa đi mở quay), `door_sliding` (cửa đi lùa), `tilt_turn` (quay - hất).
4. `panels`: mỗi phần tử là 1 cột cánh, `kind` = `sash` hoặc `fixed`, `dir` = `left`/`right`/`up`/`down`/`none`, `open` = `in`/`out`/`slide`/`none`, `ratio` là tỷ lệ chiều rộng (số > 0, mặc định 1).
5. `transoms`: đố ngang, `at_mm` = khoảng cách từ mép trên (chỉ khi đọc được), `band_above`/`band_below` = `sash` hoặc `fixed` cho ô phía trên/dưới đố.
6. `confidence`: 0..1 cho mỗi cửa. Thêm mọi điểm chưa chắc vào `needs_review` (ví dụ: `kich_thuoc`, `so_canh`, `huong_mo`, `vat_lieu`).
7. `tag` đặt theo thứ tự: C1, C2... cho cửa sổ; D1, D2... cho cửa đi; F1... cho ô cố định.
8. Không bịa thêm cửa không có trong ảnh. Nếu ảnh không có cửa nào, trả `{"items": []}`.

## Schema JSON trả về

```json
{
  "items": [
    {
      "tag": "C1",
      "room": "Phòng khách",
      "type": "casement",
      "width_mm": null,
      "height_mm": null,
      "sill_mm": null,
      "panels": [
        {"kind": "sash", "open": "out", "dir": "left", "ratio": 1},
        {"kind": "sash", "open": "out", "dir": "right", "ratio": 1}
      ],
      "transoms": [
        {"orientation": "h", "at_mm": null, "band_above": "fixed"}
      ],
      "glass": {"key": "cuong_luc_8", "thickness_mm": 8},
      "notes": "2 cánh mở quay, ô kính cố định phía trên",
      "confidence": 0.75,
      "needs_review": ["kich_thuoc", "ty_le_canh"]
    }
  ]
}
```

Sau khi nhận JSON: dán vào tab **Ảnh & AI** của XingfaCAD, nhập kích thước thật, kiểm tra lại rồi bấm Build.

> Lưu ý: ảnh AI (Midjourney/ChatGPT) thường sai tỷ lệ. Chỉ dùng để lấy **bố cục và loại cửa**, không dùng để lấy kích thước.
