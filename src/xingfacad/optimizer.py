"""Tối ưu cắt cây nhôm 1D (first-fit decreasing, có tính mạch cắt và đầu kẹp)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PieceRef(BaseModel):
    tag: str
    profile_code: str
    profile_name: str = ""
    length_mm: float
    note: str = ""


class StockBar(BaseModel):
    index: int
    stock_mm: float
    pieces: list[PieceRef] = Field(default_factory=list)
    used_mm: float = 0.0
    waste_mm: float = 0.0

    def pattern(self, kerf_mm: float = 5) -> str:
        parts = [f"{piece.length_mm:.0f}" for piece in self.pieces]
        return " | ".join(parts) + f"   (phe {self.waste_mm:.0f}mm)"

    @property
    def fill_percent(self) -> float:
        return 100 * self.used_mm / self.stock_mm if self.stock_mm else 0.0


class BarGroup(BaseModel):
    profile_code: str
    profile_name: str = ""
    stock_mm: float
    bars: list[StockBar] = Field(default_factory=list)
    total_pieces: int = 0

    @property
    def total_used_mm(self) -> float:
        return sum(bar.used_mm for bar in self.bars)

    @property
    def total_waste_mm(self) -> float:
        return sum(bar.waste_mm for bar in self.bars)

    @property
    def stock_total_mm(self) -> float:
        return sum(bar.stock_mm for bar in self.bars)

    @property
    def waste_percent(self) -> float:
        return 100 * self.total_waste_mm / self.stock_total_mm if self.stock_total_mm else 0.0


def _pack(pieces: list[PieceRef], stock_mm: float, kerf_mm: float, end_trim_mm: float) -> list[StockBar]:
    usable = stock_mm - 2 * end_trim_mm
    if usable <= 0:
        usable = stock_mm
    bars: list[StockBar] = []
    for piece in sorted(pieces, key=lambda p: p.length_mm, reverse=True):
        need = piece.length_mm + kerf_mm
        if need > usable:
            # thanh dài hơn cây: vẫn tạo bar riêng để báo lỗi ở UI
            bar = StockBar(index=len(bars) + 1, stock_mm=stock_mm)
            bar.pieces.append(piece)
            bar.used_mm = piece.length_mm
            bar.waste_mm = 0.0
            bars.append(bar)
            continue
        for bar in bars:
            remaining = usable - bar.used_mm
            if remaining >= need:
                bar.pieces.append(piece)
                bar.used_mm += need
                break
        else:
            bar = StockBar(index=len(bars) + 1, stock_mm=stock_mm)
            bar.pieces.append(piece)
            bar.used_mm = need
            bars.append(bar)
    for bar in bars:
        bar.used_mm = sum(piece.length_mm for piece in bar.pieces)
        bar.waste_mm = max(stock_mm - bar.used_mm, 0.0)
    return bars


def optimize(
    pieces: list[PieceRef],
    stock_lengths: list[float] | None = None,
    kerf_mm: float = 5,
    end_trim_mm: float = 30,
    profile_names: dict[str, str] | None = None,
) -> list[BarGroup]:
    """Trả về kế hoạch cắt theo từng mã thanh nhôm."""
    stock_lengths = stock_lengths or [6500]
    profile_names = profile_names or {}
    groups: dict[str, list[PieceRef]] = {}
    for piece in pieces:
        groups.setdefault(piece.profile_code, []).append(piece)

    result: list[BarGroup] = []
    for code, group_pieces in sorted(groups.items()):
        best: BarGroup | None = None
        for stock in stock_lengths:
            bars = _pack(group_pieces, stock, kerf_mm, end_trim_mm)
            candidate = BarGroup(
                profile_code=code,
                profile_name=profile_names.get(code, ""),
                stock_mm=stock,
                bars=bars,
                total_pieces=len(group_pieces),
            )
            if best is None or candidate.total_waste_mm < best.total_waste_mm:
                best = candidate
        if best is not None:
            result.append(best)
    return result


def pieces_from_results(results: list) -> list[PieceRef]:
    """Chuyển danh sách ItemResult -> danh sách thanh cần cắt (đã nhân số lượng cửa)."""
    refs: list[PieceRef] = []
    for result in results:
        for piece in result.pieces:
            total = piece.qty * result.item.qty
            for _ in range(total):
                refs.append(
                    PieceRef(
                        tag=result.item.tag,
                        profile_code=piece.profile_code,
                        profile_name=piece.profile_name,
                        length_mm=piece.length_mm,
                        note=piece.note,
                    )
                )
    return refs
