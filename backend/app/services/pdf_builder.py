"""Pure-Python stdlib PDF 1.4 report builder using built-in Type1 Helvetica fonts."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any

PORTRAIT_SIZE = (595.28, 841.89)
LANDSCAPE_SIZE = (841.89, 595.28)
MARGIN_X = 36.0
MARGIN_TOP = 36.0
MARGIN_BOTTOM = 42.0

RGB_TEAL_DARK = "0.082 0.200 0.227"  # #15333A
RGB_TEAL_MUTED = "0.722 0.800 0.792"  # #B8CCCA
RGB_TERRACOTTA = "0.800 0.431 0.220"  # #CC6E38
RGB_CANVAS = "0.980 0.973 0.953"  # #FAF8F3
RGB_SUBTLE = "0.953 0.937 0.902"  # #F3EFE6
RGB_WHITE = "1.000 1.000 1.000"
RGB_BORDER = "0.894 0.875 0.831"  # #E4DFD4
RGB_INK_PRIMARY = "0.082 0.200 0.227"
RGB_INK_BODY = "0.200 0.294 0.318"
RGB_INK_MUTED = "0.478 0.549 0.565"

CHAR_MAP = {
    "\u2014": "-",  # fallback only if cp1252 fails; cp1252 supports \u2014 natively
    "\u2192": "->",
    "\u2265": ">=",
    "\u2264": "<=",
}


def pdf_escape(text: str) -> bytes:
    """Encode string as WinAnsi (cp1252) PDF literal content without raw control chars."""
    cleaned = " ".join(str(text).splitlines()).strip()
    for src, dst in CHAR_MAP.items():
        if src != "\u2014":
            cleaned = cleaned.replace(src, dst)
    out = bytearray()
    for ch in cleaned:
        try:
            encoded = ch.encode("cp1252")
        except UnicodeEncodeError:
            normalized = unicodedata.normalize("NFKD", ch)
            encoded = normalized.encode("cp1252", errors="replace")
        for b in encoded:
            if b in (0x5C, 0x28, 0x29):  # \, (, )
                out.append(0x5C)
            out.append(b)
    return bytes(out)


def _literal(text: str) -> str:
    return "(" + pdf_escape(text).decode("latin1") + ")"


def _wrap_text(text: str, max_width: float, font_size: float) -> list[str]:
    """Conservative word-wrapper for proportional Helvetica text inside fixed cells."""
    raw = " ".join(str(text).split())
    if not raw:
        return [""]
    # Average glyph width factor ~0.54 * font_size leaves clean cell breathing room.
    max_chars = max(4, int(max_width / max(font_size * 0.54, 1.0)))
    words = raw.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        while len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[: max_chars - 1] + "-")
            word = word[max_chars - 1 :]
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


@dataclass
class _Canvas:
    width: float
    height: float
    title: str
    subtitle: str
    pages: list[list[str]] = field(default_factory=list)
    cursor_y: float = 0.0

    @property
    def content_width(self) -> float:
        return self.width - 2 * MARGIN_X

    def _cmd(self, command: str) -> None:
        self.pages[-1].append(command)

    def _rect(
        self,
        x: float,
        y_top: float,
        w: float,
        h: float,
        *,
        fill: str | None = None,
        stroke: str | None = None,
        line_width: float = 0.6,
    ) -> None:
        y_bot = self.height - y_top - h
        parts: list[str] = ["q"]
        if fill:
            parts.append(f"{fill} rg")
        if stroke:
            parts.append(f"{line_width:.2f} w {stroke} RG")
        op = "B" if (fill and stroke) else ("f" if fill else "S")
        parts.append(f"{x:.2f} {y_bot:.2f} {w:.2f} {h:.2f} re {op}")
        parts.append("Q")
        self._cmd(" ".join(parts))

    def _text(
        self,
        x: float,
        y_baseline: float,
        text: str,
        *,
        font: str = "/F1",
        size: float = 8.5,
        color: str = RGB_INK_PRIMARY,
        align: str = "left",
        cell_width: float = 0.0,
    ) -> None:
        draw_x = x
        if align == "right" and cell_width > 0:
            est = len(text) * size * 0.50
            draw_x = max(x, x + cell_width - est)
        elif align == "center" and cell_width > 0:
            est = len(text) * size * 0.50
            draw_x = max(x, x + (cell_width - est) / 2.0)
        y_pdf = self.height - y_baseline
        self._cmd(
            f"BT {font} {size:.2f} Tf {color} rg 1 0 0 1 {draw_x:.2f} {y_pdf:.2f} Tm {_literal(text)} Tj ET"
        )

    def new_page(self, *, first: bool = False) -> None:
        self.pages.append([])
        if first:
            banner_h = 56.0
            self._rect(MARGIN_X, MARGIN_TOP, self.content_width, banner_h, fill=RGB_TEAL_DARK)
            self._rect(
                MARGIN_X, MARGIN_TOP + banner_h - 3.0, self.content_width, 3.0, fill=RGB_TERRACOTTA
            )
            self._text(
                MARGIN_X + 14.0,
                MARGIN_TOP + 22.0,
                self.title,
                font="/F2",
                size=13.0,
                color=RGB_WHITE,
            )
            self._text(
                MARGIN_X + 14.0,
                MARGIN_TOP + 39.0,
                self.subtitle,
                font="/F1",
                size=8.2,
                color=RGB_TEAL_MUTED,
            )
            self.cursor_y = MARGIN_TOP + banner_h + 14.0
        else:
            self._rect(
                MARGIN_X, MARGIN_TOP, self.content_width, 22.0, fill=RGB_SUBTLE, stroke=RGB_BORDER
            )
            self._text(
                MARGIN_X + 10.0,
                MARGIN_TOP + 14.5,
                f"{self.title} (lanjutan)",
                font="/F2",
                size=8.5,
                color=RGB_INK_PRIMARY,
            )
            self.cursor_y = MARGIN_TOP + 34.0

    def ensure_space(self, needed: float) -> bool:
        if self.cursor_y + needed > self.height - MARGIN_BOTTOM:
            self.new_page(first=False)
            return True
        return False

    def draw_meta(self, meta_rows: list[tuple[str, str]]) -> None:
        if not meta_rows:
            return
        cols = 2
        row_count = (len(meta_rows) + cols - 1) // cols
        row_h = 16.0
        box_h = 12.0 + row_count * row_h
        self.ensure_space(box_h + 10.0)
        self._rect(
            MARGIN_X, self.cursor_y, self.content_width, box_h, fill=RGB_CANVAS, stroke=RGB_BORDER
        )
        col_w = (self.content_width - 24.0) / cols
        for idx, (label, val) in enumerate(meta_rows):
            r = idx // cols
            c = idx % cols
            x = MARGIN_X + 12.0 + c * col_w
            y = self.cursor_y + 16.0 + r * row_h
            max_chars = max(16, int((col_w - 8.0) / 4.4))
            line = f"{label}: {val}"
            if len(line) > max_chars:
                line = line[: max_chars - 3] + "..."
            self._text(x, y, line, font="/F1", size=8.0, color=RGB_INK_BODY)
        self.cursor_y += box_h + 14.0

    def draw_section(self, section: dict[str, Any]) -> None:
        title = str(section.get("title", ""))
        subtitle = section.get("subtitle")
        headers: list[str] = [str(h) for h in section.get("headers", [])]
        rows: list[list[str]] = [[str(cell) for cell in row] for row in section.get("rows", [])]
        empty_note = str(section.get("empty_note", "Tidak ada data."))
        aligns: list[str] = list(section.get("aligns") or ["left"] * len(headers))

        if headers:
            raw_weights = section.get("widths") or [1.0] * len(headers)
            total_w = float(sum(raw_weights)) or 1.0
            col_widths = [self.content_width * (float(w) / total_w) for w in raw_weights]
        else:
            col_widths = [self.content_width]

        def draw_section_head(*, continuation: bool = False) -> None:
            head_text = f"{title} (lanjutan)" if continuation else title
            self._text(
                MARGIN_X,
                self.cursor_y + 11.0,
                head_text,
                font="/F2",
                size=10.0,
                color=RGB_INK_PRIMARY,
            )
            self.cursor_y += 15.0
            if subtitle and not continuation:
                self._text(
                    MARGIN_X,
                    self.cursor_y + 9.0,
                    str(subtitle),
                    font="/F1",
                    size=7.8,
                    color=RGB_INK_MUTED,
                )
                self.cursor_y += 12.0

        def draw_table_header() -> None:
            if not headers:
                return
            wrapped_hdrs = [
                _wrap_text(h, max(w - 10.0, 14.0), 7.6)
                for h, w in zip(headers, col_widths, strict=True)
            ]
            max_lines = max(len(lines) for lines in wrapped_hdrs)
            hdr_h = max(20.0, max_lines * 9.5 + 8.0)
            self._rect(
                MARGIN_X,
                self.cursor_y,
                self.content_width,
                hdr_h,
                fill=RGB_SUBTLE,
                stroke=RGB_BORDER,
            )
            x = MARGIN_X
            for w, lines, align in zip(col_widths, wrapped_hdrs, aligns, strict=True):
                self._rect(x, self.cursor_y, w, hdr_h, stroke=RGB_BORDER, line_width=0.4)
                for li, line in enumerate(lines):
                    self._text(
                        x + 5.0,
                        self.cursor_y + 11.5 + li * 9.5,
                        line,
                        font="/F2",
                        size=7.6,
                        color=RGB_INK_PRIMARY,
                        align=align,
                        cell_width=max(w - 10.0, 10.0),
                    )
                x += w
            self.cursor_y += hdr_h

        min_needed = 46.0 if headers else 28.0
        self.ensure_space(min_needed)
        draw_section_head(continuation=False)
        if not rows:
            box_h = 24.0
            self.ensure_space(box_h)
            self._rect(
                MARGIN_X,
                self.cursor_y,
                self.content_width,
                box_h,
                fill=RGB_CANVAS,
                stroke=RGB_BORDER,
            )
            self._text(
                MARGIN_X + 10.0,
                self.cursor_y + 15.0,
                empty_note,
                font="/F1",
                size=8.0,
                color=RGB_INK_MUTED,
            )
            self.cursor_y += box_h + 14.0
            return

        draw_table_header()
        for row_idx, row in enumerate(rows):
            padded_row = (row + [""] * len(col_widths))[: len(col_widths)]
            wrapped_cells = [
                _wrap_text(cell, max(w - 10.0, 12.0), 7.6)
                for cell, w in zip(padded_row, col_widths, strict=True)
            ]
            max_lines = max(len(lines) for lines in wrapped_cells)
            row_h = max(18.0, max_lines * 9.5 + 7.0)
            if self.ensure_space(row_h):
                draw_section_head(continuation=True)
                draw_table_header()
            bg = RGB_WHITE if row_idx % 2 == 0 else RGB_CANVAS
            self._rect(
                MARGIN_X,
                self.cursor_y,
                self.content_width,
                row_h,
                fill=bg,
                stroke=RGB_BORDER,
                line_width=0.4,
            )
            x = MARGIN_X
            for w, lines, align in zip(col_widths, wrapped_cells, aligns, strict=True):
                self._rect(x, self.cursor_y, w, row_h, stroke=RGB_BORDER, line_width=0.35)
                for li, line in enumerate(lines):
                    self._text(
                        x + 5.0,
                        self.cursor_y + 11.0 + li * 9.5,
                        line,
                        font="/F1",
                        size=7.6,
                        color=RGB_INK_BODY,
                        align=align,
                        cell_width=max(w - 10.0, 10.0),
                    )
                x += w
            self.cursor_y += row_h
        self.cursor_y += 14.0

    def finalize(self, footer_right: str) -> bytes:
        total_pages = len(self.pages)
        for idx, _ in enumerate(self.pages, start=1):
            # Temporarily target page `idx - 1` by calling helper directly on active list slice
            y_rule = self.height - 28.0
            self.pages[idx - 1].append(
                f"q 0.50 w {RGB_BORDER} RG {MARGIN_X:.2f} {self.height - y_rule:.2f} m "
                f"{self.width - MARGIN_X:.2f} {self.height - y_rule:.2f} l S Q"
            )
            y_txt = self.height - 17.0
            left = _literal(f"Halaman {idx} / {total_pages} · Sistem Pengukuran Capaian OBE PNL")
            right = _literal(footer_right)
            self.pages[idx - 1].append(
                f"BT /F1 7.40 Tf {RGB_INK_MUTED} rg 1 0 0 1 {MARGIN_X:.2f} {self.height - y_txt:.2f} Tm {left} Tj ET"
            )
            est_w = len(footer_right) * 7.4 * 0.50
            rx = max(MARGIN_X + 200.0, self.width - MARGIN_X - est_w)
            self.pages[idx - 1].append(
                f"BT /F1 7.40 Tf {RGB_INK_MUTED} rg 1 0 0 1 {rx:.2f} {self.height - y_txt:.2f} Tm {right} Tj ET"
            )

        objects: list[bytes] = []
        page_obj_nums: list[int] = []
        first_page_obj = 5
        for idx in range(total_pages):
            page_obj_nums.append(first_page_obj + idx * 2)

        kids_ref = " ".join(f"{num} 0 R" for num in page_obj_nums)
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(
            f"<< /Type /Pages /Kids [{kids_ref}] /Count {total_pages} >>".encode("latin1")
        )
        objects.append(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
        )
        objects.append(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
        )

        for idx, cmds in enumerate(self.pages):
            p_num = first_page_obj + idx * 2
            c_num = p_num + 1
            stream_data = ("\n".join(cmds) + "\n").encode("latin1")
            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {c_num} 0 R >>"
            ).encode("latin1")
            content_obj = (
                f"<< /Length {len(stream_data)} >>\nstream\n".encode("latin1")
                + stream_data
                + b"endstream"
            )
            objects.append(page_dict)
            objects.append(content_obj)

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = [0]
        for obj_id, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{obj_id} 0 obj\n".encode("latin1"))
            out.extend(body)
            out.extend(b"\nendobj\n")

        xref_offset = len(out)
        total_objs = len(objects) + 1
        out.extend(f"xref\n0 {total_objs}\n".encode("latin1"))
        out.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            out.extend(f"{offset:010d} 00000 n \n".encode("latin1"))
        out.extend(
            f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
                "latin1"
            )
        )
        return bytes(out)


def build_report_pdf(
    *,
    title: str,
    subtitle: str,
    meta_rows: list[tuple[str, str]],
    sections: list[dict[str, Any]],
    landscape: bool = False,
    footer_right: str = "",
) -> bytes:
    """Build a multi-page A4 PDF report with PNL OBE branding and structured tables."""
    width, height = LANDSCAPE_SIZE if landscape else PORTRAIT_SIZE
    canvas = _Canvas(width=width, height=height, title=title, subtitle=subtitle)
    canvas.new_page(first=True)
    canvas.draw_meta(meta_rows)
    for section in sections:
        canvas.draw_section(section)
    return canvas.finalize(footer_right)
