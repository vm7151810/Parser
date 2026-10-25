"""
Synthetic PDF Generator using PyMuPDF (fitz) with native NotoSansCJK font.
Generates 3 smoke test PDFs to test parser generalization:
1. stress_3col.pdf: 3-period comparison columns
2. stress_neg_marker.pdf: ▲ (black triangle) markers and detached marker merge
3. stress_flatindent.pdf: Flat indentation where all items share identical x0
"""
from pathlib import Path
import fitz

FONT_PATH = "/usr/share/fonts/google-noto-sans-cjk-vf-fonts/NotoSansCJK-VF.ttc"


def create_stress_3col_pdf(output_path: str):
    """
    Creates a 3-column financial table (3 periods comparative).
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_font(fontname="cjk", fontfile=FONT_PATH)

    # Header
    page.insert_text(fitz.Point(60, 70), "連結貸借対照表 (単位：千円)", fontname="cjk", fontsize=10)

    # 3 periods: columns at x=340, 420, 500
    page.insert_text(fitz.Point(340, 100), "前々連結会計年度", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(420, 100), "前連結会計年度", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(500, 100), "当連結会計年度", fontname="cjk", fontsize=9)

    page.insert_text(fitz.Point(340, 115), "(2024年3月31日)", fontname="cjk", fontsize=8)
    page.insert_text(fitz.Point(420, 115), "(2025年3月31日)", fontname="cjk", fontsize=8)
    page.insert_text(fitz.Point(500, 115), "(2026年3月31日)", fontname="cjk", fontsize=8)

    # Data
    page.insert_text(fitz.Point(60, 145), "資産の部", fontname="cjk", fontsize=10)
    page.insert_text(fitz.Point(75, 165), "流動資産", fontname="cjk", fontsize=9)

    items = [
        ("現金及び預金", "1,500,000", "2,000,000", "2,500,000"),
        ("受取手形", "100,000", "120,000", "150,000"),
        ("売掛金", "800,000", "900,000", "1,000,000"),
        ("貸倒引当金", "△5,000", "△6,000", "△7,000"),
        ("流動資産合計", "2,395,000", "3,014,000", "3,643,000"),
    ]

    y = 185
    for label, v1, v2, v3 in items:
        indent = 75 if "合計" in label else 90
        page.insert_text(fitz.Point(indent, y), label, fontname="cjk", fontsize=9)
        page.insert_text(fitz.Point(340, y), v1, fontname="cjk", fontsize=9)
        page.insert_text(fitz.Point(420, y), v2, fontname="cjk", fontsize=9)
        page.insert_text(fitz.Point(500, y), v3, fontname="cjk", fontsize=9)
        y += 20

    doc.save(output_path)
    doc.close()


def create_stress_neg_marker_pdf(output_path: str):
    """
    Creates a table with alternative ▲ negative markers and detached marker tokens.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="cjk", fontfile=FONT_PATH)

    page.insert_text(fitz.Point(60, 70), "連結貸借対照表 (単位：千円)", fontname="cjk", fontsize=10)
    page.insert_text(fitz.Point(400, 100), "前連結会計年度", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(490, 100), "当連結会計年度", fontname="cjk", fontsize=9)

    y = 145
    page.insert_text(fitz.Point(60, y), "資産の部", fontname="cjk", fontsize=10)
    y += 20
    page.insert_text(fitz.Point(75, y), "固定資産", fontname="cjk", fontsize=9)
    y += 20
    page.insert_text(fitz.Point(88, y), "有形固定資産", fontname="cjk", fontsize=9)

    # Gross
    y += 20
    page.insert_text(fitz.Point(101, y), "建物及び構築物", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(400, y), "1,000,000", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(490, y), "1,200,000", fontname="cjk", fontsize=9)

    # Contra: col 1 has detached ▲ token (▲ drawn at x=388, digits at x=400)
    # col 2 has united ▲700,000
    y += 20
    page.insert_text(fitz.Point(114, y), "減価償却累計額", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(388, y), "▲", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(400, y), "600,000", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(490, y), "▲700,000", fontname="cjk", fontsize=9)

    # Net
    y += 20
    page.insert_text(fitz.Point(114, y), "建物及び構築物（純額）", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(400, y), "400,000", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(490, y), "500,000", fontname="cjk", fontsize=9)

    # Subtotal
    y += 20
    page.insert_text(fitz.Point(88, y), "有形固定資産合計", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(400, y), "400,000", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(490, y), "500,000", fontname="cjk", fontsize=9)

    doc.save(output_path)
    doc.close()


def create_stress_flatindent_pdf(output_path: str):
    """
    Creates a table with zero physical indentation (all labels start at x=60).
    Forces parser to use heuristic structural hierarchy fallback.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="cjk", fontfile=FONT_PATH)

    page.insert_text(fitz.Point(60, 70), "連結貸借対照表 (単位：千円)", fontname="cjk", fontsize=10)
    page.insert_text(fitz.Point(400, 100), "前連結会計年度", fontname="cjk", fontsize=9)
    page.insert_text(fitz.Point(490, 100), "当連結会計年度", fontname="cjk", fontsize=9)

    rows = [
        ("資産の部", "", ""),
        ("流動資産", "", ""),
        ("現金及び預金", "500,000", "600,000"),
        ("売掛金", "300,000", "400,000"),
        ("貸倒引当金", "△1,000", "△2,000"),
        ("流動資産合計", "799,000", "998,000"),
    ]

    y = 145
    for label, v1, v2 in rows:
        # Strictly identical x=60.0 for every single row
        page.insert_text(fitz.Point(60, y), label, fontname="cjk", fontsize=9)
        if v1:
            page.insert_text(fitz.Point(400, y), v1, fontname="cjk", fontsize=9)
        if v2:
            page.insert_text(fitz.Point(490, y), v2, fontname="cjk", fontsize=9)
        y += 20

    doc.save(output_path)
    doc.close()


def generate_all_fixtures(output_dir: str = "tests/fixtures"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    create_stress_3col_pdf(str(out / "stress_3col.pdf"))
    create_stress_neg_marker_pdf(str(out / "stress_neg_marker.pdf"))
    create_stress_flatindent_pdf(str(out / "stress_flatindent.pdf"))


if __name__ == "__main__":
    generate_all_fixtures()
