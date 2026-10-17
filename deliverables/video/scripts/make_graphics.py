from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "frames"
FONTS = ROOT / "fonts"
FINAL = ROOT / "final"

PAPER = "#FBF7F2"
INK = "#1F1B16"
CORAL = "#E4572E"
SAGE = "#5B8C6B"
AMBER = "#F2A541"
BLUE = "#3D6A8F"
MUTED = "#6B635A"


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    name = {
        "regular": "Poppins-Regular.ttf",
        "medium": "Poppins-Medium.ttf",
        "semibold": "Poppins-SemiBold.ttf",
    }[weight]
    return ImageFont.truetype(str(FONTS / name), size)


def paper(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGB", size, PAPER)
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 1.1, (size[1], size[0], 1))
    base = np.asarray(image).astype(np.float32)
    base = np.clip(base + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(base, "RGB")


def draw_brand(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, dark: bool = False) -> None:
    r = int(34 * scale)
    fill = PAPER if dark else CORAL
    stroke = INK if dark else "white"
    draw.ellipse((x, y, x + r * 2, y + r * 2), fill=fill)
    width = max(3, int(5 * scale))
    cx = x + r
    draw.arc((cx - int(16 * scale), y + int(18 * scale), cx + int(16 * scale), y + int(50 * scale)), 190, 350, fill=stroke, width=width)
    draw.rounded_rectangle((x + int(13 * scale), y + int(34 * scale), x + int(21 * scale), y + int(52 * scale)), radius=3, fill=stroke)
    draw.rounded_rectangle((x + int(47 * scale), y + int(34 * scale), x + int(55 * scale), y + int(52 * scale)), radius=3, fill=stroke)


def hook_card() -> Image.Image:
    image = Image.new("RGB", (1920, 1080), "#15120F")
    draw = ImageDraw.Draw(image)
    draw_brand(draw, 120, 100, 0.72, dark=True)
    draw.text((190, 105), "EK AWAAZ", font=font("semibold", 26), fill=PAPER)
    draw.text((120, 388), "ONE VOICE.", font=font("semibold", 106), fill=PAPER)
    draw.text((120, 520), "IN AN EMERGENCY,", font=font("medium", 34), fill="#D7CBC0")
    draw.text((120, 572), "EVERY SECOND MATTERS.", font=font("medium", 34), fill="#D7CBC0")
    base_x, base_y = 1170, 527
    heights = [44, 90, 62, 132, 76, 118, 56, 104, 68, 126, 50, 84]
    for index, height in enumerate(heights):
        x = base_x + index * 46
        draw.rounded_rectangle((x, base_y - height // 2, x + 14, base_y + height // 2), radius=7, fill=CORAL)
    draw.rounded_rectangle((120, 770, 570, 842), radius=36, fill="#2B241F")
    draw.ellipse((152, 796, 170, 814), fill=SAGE)
    draw.text((190, 788), "LISTENING NOW", font=font("medium", 23), fill="#EFE5DC")
    return image


def problem_card() -> Image.Image:
    image = paper((1920, 1080))
    draw = ImageDraw.Draw(image)
    draw.text((120, 104), "THE PROBLEM", font=font("semibold", 22), fill=CORAL)
    draw.text((120, 225), "Panic.", font=font("semibold", 116), fill=INK)
    draw.text((120, 360), "One phone.", font=font("semibold", 116), fill=INK)
    draw.text((120, 495), "Many calls", font=font("semibold", 116), fill=CORAL)
    draw.text((120, 630), "to make.", font=font("semibold", 116), fill=CORAL)
    draw.text((127, 815), "The caller should not have to coordinate the crisis.", font=font("regular", 29), fill=MUTED)
    center = (1515, 485)
    for radius, color, width in ((310, "#F3E7DD", 4), (225, "#E9D5C7", 5), (140, "#D8C0B0", 6)):
        draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), outline=color, width=width)
    draw.ellipse((center[0] - 86, center[1] - 86, center[0] + 86, center[1] + 86), fill="#352B22")
    draw_brand(draw, center[0] - 34, center[1] - 34, 1.0, dark=True)
    chips = (("AMBULANCE", CORAL, 228), ("FAMILY", SAGE, 495), ("LOCATION", BLUE, 762))
    for label, color, y in chips:
        draw.rounded_rectangle((1280, y, 1750, y + 76), radius=38, fill="white", outline="#EADFD3", width=2)
        draw.ellipse((1310, y + 24, 1338, y + 52), fill=color)
        draw.text((1362, y + 20), label, font=font("medium", 24), fill=INK)
    return image


def close_card() -> Image.Image:
    image = paper((1920, 1080))
    draw = ImageDraw.Draw(image)
    draw_brand(draw, 760, 135, 1.25)
    draw.text((870, 178), "EK AWAAZ", anchor="lm", font=font("semibold", 32), fill=CORAL)
    draw.text((960, 405), "One voice.", anchor="mm", font=font("semibold", 96), fill=INK)
    draw.text((960, 525), "Many calls.", anchor="mm", font=font("semibold", 96), fill=CORAL)
    draw.rounded_rectangle((635, 665, 1285, 733), radius=34, fill="#352B22")
    draw.text((960, 699), "CALM IN. COORDINATION OUT.", anchor="mm", font=font("medium", 23), fill="#FFF7EE")
    draw.text((960, 870), "Built with Bolna  •  Symphony Buildathon", anchor="mm", font=font("medium", 25), fill=MUTED)
    return image


def thumbnail() -> Image.Image:
    source = Image.open(FRAMES / "console-complete.png").convert("RGB")
    source = source.crop((0, 80, source.width, min(source.height, 2004))).resize((1280, 720), Image.Resampling.LANCZOS)
    background = ImageEnhance.Contrast(source).enhance(0.78).filter(ImageFilter.GaussianBlur(2.0))
    shade = Image.new("RGBA", background.size, (20, 16, 13, 80))
    image = Image.alpha_composite(background.convert("RGBA"), shade)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((55, 72, 710, 648), radius=36, fill=(251, 247, 242, 245), outline=(255, 255, 255, 160), width=2)
    draw_brand(draw, 100, 112, 0.65)
    draw.text((170, 120), "EK AWAAZ", font=font("semibold", 23), fill=INK)
    draw.text((98, 230), "ONE VOICE.", font=font("semibold", 61), fill=INK)
    draw.text((98, 310), "MANY CALLS.", font=font("semibold", 61), fill=CORAL)
    draw.text((101, 423), "Voice-first emergency", font=font("medium", 24), fill=MUTED)
    draw.text((101, 460), "coordination, live.", font=font("medium", 24), fill=MUTED)
    draw.rounded_rectangle((100, 540, 480, 592), radius=26, fill="#352B22")
    draw.ellipse((125, 559, 141, 575), fill=SAGE)
    draw.text((160, 553), "LIVE DEMO", font=font("medium", 19), fill="#FFF7EE")
    return Image.alpha_composite(image, overlay).convert("RGB")


def portrait_hook() -> Image.Image:
    image = Image.new("RGB", (1080, 1920), "#15120F")
    draw = ImageDraw.Draw(image)
    draw_brand(draw, 90, 110, 0.85, dark=True)
    draw.text((180, 130), "EK AWAAZ", font=font("semibold", 30), fill=PAPER)
    draw.text((90, 510), "ONE", font=font("semibold", 118), fill=PAPER)
    draw.text((90, 645), "VOICE.", font=font("semibold", 118), fill=PAPER)
    draw.text((90, 815), "MANY", font=font("semibold", 118), fill=CORAL)
    draw.text((90, 950), "CALLS.", font=font("semibold", 118), fill=CORAL)
    draw.text((94, 1160), "One calm conversation.", font=font("medium", 30), fill="#D7CBC0")
    draw.text((94, 1210), "Every action visible.", font=font("medium", 30), fill="#D7CBC0")
    base_x, base_y = 100, 1510
    heights = [42, 88, 58, 126, 72, 112, 54, 100, 66, 120, 48, 80]
    for index, height in enumerate(heights):
        x = base_x + index * 68
        draw.rounded_rectangle((x, base_y - height // 2, x + 20, base_y + height // 2), radius=10, fill=CORAL)
    draw.rounded_rectangle((90, 1690, 570, 1766), radius=38, fill="#2B241F")
    draw.ellipse((125, 1718, 145, 1738), fill=SAGE)
    draw.text((172, 1710), "LIVE DEMO", font=font("medium", 25), fill="#FFF7EE")
    return image


def portrait_close() -> Image.Image:
    image = paper((1080, 1920))
    draw = ImageDraw.Draw(image)
    draw_brand(draw, 90, 110, 0.85)
    draw.text((180, 130), "EK AWAAZ", font=font("semibold", 30), fill=CORAL)
    draw.text((540, 610), "One voice.", anchor="mm", font=font("semibold", 94), fill=INK)
    draw.text((540, 735), "Many calls.", anchor="mm", font=font("semibold", 94), fill=CORAL)
    draw.rounded_rectangle((115, 920, 965, 1010), radius=45, fill="#352B22")
    draw.text((540, 965), "CALM IN. COORDINATION OUT.", anchor="mm", font=font("medium", 25), fill="#FFF7EE")
    draw.text((540, 1380), "Built with Bolna", anchor="mm", font=font("medium", 30), fill=MUTED)
    draw.text((540, 1430), "for Symphony Buildathon", anchor="mm", font=font("medium", 30), fill=MUTED)
    return image


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)
    hook_card().save(FRAMES / "hook-card.png", quality=95)
    problem_card().save(FRAMES / "problem-card.png", quality=95)
    close_card().save(FRAMES / "close-card.png", quality=95)
    portrait_hook().save(FRAMES / "portrait-hook.png", quality=95)
    portrait_close().save(FRAMES / "portrait-close.png", quality=95)
    thumbnail().save(FINAL / "ek-awaaz-thumbnail.png", quality=95)


if __name__ == "__main__":
    main()
