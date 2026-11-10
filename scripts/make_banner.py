#!/usr/bin/env python3
"""Social preview banner (1200x630) in the site's dealt palette.

Paper ground, ink type, teal accent, sharp corners — the same system as
the site. Regenerate with: python scripts/make_banner.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
PAPER = (247, 249, 250)
SURFACE = (236, 240, 242)
INK = (31, 48, 56)
MUTED = (93, 107, 114)
ACCENT = (13, 116, 128)
WHITE = (255, 255, 255)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def main() -> int:
    out = Path(__file__).resolve().parent.parent / "docs" / "social-preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # Top glow band + hairline, same as the site hero.
    d.rectangle([0, 0, W, 8], fill=ACCENT)
    d.rectangle([0, H - 1, W, H], fill=SURFACE)

    # Accent mark.
    d.rectangle([72, 108, 128, 164], fill=ACCENT)
    d.text((84, 118), "AI", font=font("DejaVuSans-Bold.ttf", 28), fill=WHITE)

    d.text((148, 112), "INVESTMENT INTELLIGENCE", font=font("DejaVuSansMono.ttf", 26), fill=MUTED)

    headline_font = font("DejaVuSans-Bold.ttf", 64)
    for line, y in (("Investment research,", 216), ("ahead of the market.", 296)):
        w = d.textlength(line, font=headline_font)
        assert w <= W - 144, f"headline too wide: {line} ({w:.0f}px)"
        d.text((72, y), line, font=headline_font, fill=INK)

    d.text((72, 420), "AI research for Indian stocks: news sentiment, live prices,",
           font=font("DejaVuSans.ttf", 30), fill=MUTED)
    d.text((72, 460), "opportunity scans and goal-based portfolios.",
           font=font("DejaVuSans.ttf", 30), fill=MUTED)

    # Ticker strip: live prices verified via yfinance, 10 Nov 2026 evening.
    # Prices only (no change %) — the strip is a static image.
    chips = [("RELIANCE", "₹1,324.40"), ("TCS", "₹2,475.40"), ("HDFCBANK", "₹798.15")]
    x = 72
    for ticker, price in chips:
        label = f"{ticker}  {price}"
        w = d.textlength(label, font=font("DejaVuSansMono.ttf", 24))
        d.rectangle([x, 530, x + w + 32, 574], outline=ACCENT, width=2)
        d.text((x + 16, 540), label, font=font("DejaVuSansMono.ttf", 24), fill=ACCENT)
        x += int(w) + 56

    img.save(out, "PNG")
    print(f"Wrote {out} ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
