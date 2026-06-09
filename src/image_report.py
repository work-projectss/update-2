"""
Report PNG — spreadsheet layout for WhatsApp (Campaign / Vicidial ID / Main Code).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.report import GrandTotals, PerformanceReport, RowMetrics

COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (255, 0, 0)

TABLE_TOP = 55
ROW_HEIGHT = 24
HEADER_HEIGHT = 48
GAP_TABLES = 48
FONT_SIZE = 13
RENDER_SCALE = 3
HEADER_PAD = 10

# Campaign columns: 0 Campaign, 1 Vicidial ID, 2 Main Code, 3 Lead Vol, ...
C_VICIDIAL = 1
C_HEADCOUNT = 7

_MIN_CAMPAIGN_W = 200
_MIN_VICIDIAL_W = 95
_MIN_MAIN_CODE_W = 200
_MIN_TEAM_W = 130
_MIN_HRS_W = 58
_MIN_WAIT_W = 72

FONT_DIR = Path("C:/Windows/Fonts")


@dataclass
class CellStyle:
    fill: tuple[int, int, int] = COLOR_WHITE
    text: tuple[int, int, int] = COLOR_BLACK
    font_key: str = "regular"


def _font_path(*, bold: bool = False, italic: bool = False) -> str:
    if bold and italic:
        return str(FONT_DIR / "calibriz.ttf")
    if bold:
        return str(FONT_DIR / "calibrib.ttf")
    if italic:
        return str(FONT_DIR / "calibrii.ttf")
    return str(FONT_DIR / "calibri.ttf")


def _load_font(size: int, *, bold: bool = False, italic: bool = False):
    for path in [_font_path(bold=bold, italic=italic), str(FONT_DIR / "arial.ttf")]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _fmt_decimal(value: float | None) -> str:
    if value is None:
        return "#DIV/0!"
    return f"{value:.1f}".replace(".", ",")


def _fmt_pct(value: int | None) -> str:
    return "" if value is None else f"{value}%"


def _fmt_int(value: int) -> str:
    return str(value)


def _header_col_widths(
    headers: list[str],
    font,
    pad_output: int,
    scale: int,
    min_overrides: dict[int, int] | None = None,
) -> list[int]:
    side = pad_output * scale
    result = []
    for i, h in enumerate(headers):
        try:
            bb = font.getbbox(h or " ")
            h_w = bb[2] - bb[0]
        except AttributeError:
            h_w = len(h) * 7 if h else 7
        w = max(60, h_w + 2 * side)
        if min_overrides and i in min_overrides:
            w = max(w, min_overrides[i] * scale)
        result.append(w)
    return result


def _word_wrap(text: str, font, max_w: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        try:
            bb = font.getbbox(test)
            w = bb[2] - bb[0]
        except AttributeError:
            w = len(test) * 6
        if w <= max_w:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _cell(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    text: str,
    style: CellStyle,
    fonts: dict,
    *,
    wrap: bool = False,
) -> None:
    draw.rectangle(xy, fill=style.fill, outline=COLOR_BLACK, width=1)
    if not text:
        return
    font = fonts[style.font_key]
    x0, y0, x1, y1 = xy
    cell_w = x1 - x0
    cell_h = y1 - y0
    pad = 6
    lines = _word_wrap(text, font, cell_w - 2 * pad) if wrap else [text]

    def _sz(ln: str) -> tuple[int, int]:
        bb = draw.textbbox((0, 0), ln, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]

    sizes = [_sz(ln) for ln in lines]
    line_gap = 3
    total_h = sum(h for _, h in sizes) + line_gap * (len(lines) - 1)
    y_cur = y0 + max(pad, (cell_h - total_h) // 2)

    for ln, (lw, lh) in zip(lines, sizes):
        x = x0 + max(pad, (cell_w - lw) // 2)
        draw.text((x, y_cur), ln, fill=style.text, font=font)
        y_cur += lh + line_gap


def _campaign_styles(values: list[str], *, is_total: bool = False) -> list[CellStyle]:
    styles: list[CellStyle] = []
    for col in range(len(values)):
        text_c = COLOR_RED if col == C_VICIDIAL and not is_total else COLOR_BLACK
        font_key = "total" if is_total else "regular"
        if col == C_HEADCOUNT and not is_total:
            font_key = "italic"
        styles.append(CellStyle(text=text_c, font_key=font_key))
    return styles


def _team_styles(*, is_total: bool = False) -> list[CellStyle]:
    font_key = "total" if is_total else "regular"
    return [CellStyle(font_key=font_key) for _ in range(9)]


def _draw_table(
    draw: ImageDraw.ImageDraw,
    *,
    top: int,
    left: int,
    col_widths: list[int],
    headers: list[str],
    rows: list[list[str]],
    row_styles: list[list[CellStyle]],
    fonts: dict,
    row_height: int,
    header_height: int,
    gap_after: int = 0,
) -> int:
    y = top
    x = left
    for idx, header in enumerate(headers):
        w = col_widths[idx]
        _cell(
            draw,
            (x, y, x + w, y + header_height),
            header,
            CellStyle(font_key="header"),
            fonts,
            wrap=True,
        )
        x += w
    y += header_height

    for values, styles in zip(rows, row_styles):
        x = left
        for col, (value, style) in enumerate(zip(values, styles)):
            w = col_widths[col]
            _cell(draw, (x, y, x + w, y + row_height), value, style, fonts, wrap=col <= 2)
            x += w
        y += row_height
    return y + gap_after


def _campaign_row_values(row: RowMetrics) -> list[str]:
    return [
        row.label,
        row.sub_label,
        row.main_code,
        str(row.target),
        _fmt_int(row.sales),
        _fmt_int(row.b_sales),
        str(row.hrs),
        str(row.headcount),
        _fmt_decimal(row.avg_per_hour),
        _fmt_decimal(row.ave_per_agent),
        _fmt_pct(row.pct_to_target),
        _fmt_int(row.wait_time or 0),
    ]


def _team_row_values(row: RowMetrics) -> list[str]:
    return [
        row.label,
        str(row.target),
        _fmt_int(row.sales),
        _fmt_int(row.b_sales),
        str(row.hrs),
        str(row.headcount),
        _fmt_decimal(row.avg_per_hour),
        _fmt_decimal(row.ave_per_agent),
        _fmt_pct(row.pct_to_target),
    ]


def _grand_campaign(grand: GrandTotals, target_total: int) -> list[str]:
    return [
        "TOTAL",
        "",
        "",
        str(target_total),
        _fmt_int(grand.sales),
        _fmt_int(grand.b_sales),
        str(grand.hrs),
        str(grand.headcount),
        _fmt_decimal(grand.avg_per_hour),
        _fmt_decimal(grand.ave_per_agent),
        _fmt_pct(grand.pct_to_target),
        _fmt_int(grand.wait_time or 0),
    ]


def _grand_team(grand: GrandTotals, target_total: int) -> list[str]:
    return [
        "Total",
        str(target_total),
        _fmt_int(grand.sales),
        _fmt_int(grand.b_sales),
        str(grand.hrs),
        str(grand.headcount),
        _fmt_decimal(grand.avg_per_hour),
        _fmt_decimal(grand.ave_per_agent),
        _fmt_pct(grand.pct_to_target),
    ]


def generate_report_image(
    report: PerformanceReport,
    output_path: Path,
    *,
    generated_at: datetime | None = None,
) -> Path:
    _ = generated_at
    s = RENDER_SCALE
    rh = ROW_HEIGHT * s
    hh = HEADER_HEIGHT * s
    gap = GAP_TABLES * s

    fonts = {
        "regular": _load_font(FONT_SIZE * s),
        "header": _load_font(FONT_SIZE * s, bold=True),
        "italic": _load_font(FONT_SIZE * s, italic=True),
        "total": _load_font(FONT_SIZE * s, bold=True, italic=True),
    }

    campaign_headers = [
        "Campaign",
        "Vicidial Campaign ID",
        "Main Code",
        "Lead Volume",
        "Sales",
        "B-Sales",
        "Hrs",
        "Headcount",
        "Avg per hour",
        "Ave/Agent",
        "% to Target",
        "Wait(sec)",
    ]
    team_headers = [
        "Team",
        "Target",
        "Sales",
        "B-Sales",
        "Hrs",
        "Headcount",
        "Avg per hour",
        "Ave/Agent",
        "% to Target",
    ]

    hfont = fonts["header"]
    regular = fonts["regular"]

    def _text_width(text: str) -> int:
        try:
            bb = regular.getbbox(text or " ")
            return bb[2] - bb[0]
        except AttributeError:
            return len(text) * 7

    longest_campaign = max(
        (r.label for r in report.campaign_rows),
        key=len,
        default="",
    )
    longest_main = max(
        (r.main_code for r in report.campaign_rows),
        key=len,
        default="",
    )
    longest_vicidial = max(
        (r.sub_label for r in report.campaign_rows),
        key=len,
        default="",
    )
    min_campaign = max(
        _MIN_CAMPAIGN_W,
        int(_text_width(longest_campaign) / s) + 2 * HEADER_PAD + 8,
    )
    min_main = max(
        _MIN_MAIN_CODE_W,
        int(_text_width(longest_main) / s) + 2 * HEADER_PAD + 8,
    )
    min_vicidial = max(
        _MIN_VICIDIAL_W,
        int(_text_width(longest_vicidial) / s) + 2 * HEADER_PAD + 8,
    )

    campaign_w = _header_col_widths(
        campaign_headers,
        hfont,
        HEADER_PAD,
        s,
        min_overrides={
            0: min_campaign,
            1: min_vicidial,
            2: min_main,
            6: _MIN_HRS_W,
            11: _MIN_WAIT_W,
        },
    )
    canvas_w = sum(campaign_w)

    # Team table aligns under Main Code (cols 2–10 of campaign table).
    team_w = campaign_w[2:11]
    team_left = campaign_w[0] + campaign_w[1]

    n_camp = len(report.campaign_rows) + 1
    n_team = len(report.team_rows) + 1
    canvas_h = (
        TABLE_TOP * s
        + hh + n_camp * rh
        + gap
        + hh + n_team * rh
        + TABLE_TOP * s
    )

    campaign_rows = [_campaign_row_values(r) for r in report.campaign_rows]
    campaign_styles = [_campaign_styles(r) for r in campaign_rows]
    grand_c = _grand_campaign(report.campaign_grand, report.campaign_target_total)
    campaign_rows.append(grand_c)
    campaign_styles.append(_campaign_styles(grand_c, is_total=True))

    team_rows = [_team_row_values(r) for r in report.team_rows]
    team_styles = [_team_styles() for _ in team_rows]
    grand_t = _grand_team(report.team_grand, report.team_target_total)
    team_rows.append(grand_t)
    team_styles.append(_team_styles(is_total=True))

    image = Image.new("RGB", (canvas_w, canvas_h), COLOR_WHITE)
    draw = ImageDraw.Draw(image)

    y = TABLE_TOP * s
    y = _draw_table(
        draw,
        top=y,
        left=0,
        col_widths=campaign_w,
        headers=campaign_headers,
        rows=campaign_rows,
        row_styles=campaign_styles,
        fonts=fonts,
        row_height=rh,
        header_height=hh,
        gap_after=gap,
    )
    _draw_table(
        draw,
        top=y,
        left=team_left,
        col_widths=team_w,
        headers=team_headers,
        rows=team_rows,
        row_styles=team_styles,
        fonts=fonts,
        row_height=rh,
        header_height=hh,
    )

    output_w = canvas_w // s
    output_h = canvas_h // s
    final = image.resize((output_w, output_h), Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(output_path, format="PNG", compress_level=2)
    return output_path
