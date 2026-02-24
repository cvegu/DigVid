"""
Image processing service: color extraction, vinyl disc creation, background generation.
"""
import math
import random
from pathlib import Path
from typing import List, Tuple
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def extract_dominant_colors(image_path: str, n: int = 5) -> List[Tuple[int, int, int]]:
    """
    Extract n dominant colors from an image using color quantization.
    Returns list of (R, G, B) tuples.
    """
    img = Image.open(image_path).convert("RGB")
    # Resize for speed
    img = img.resize((150, 150))
    # Quantize
    quantized = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()

    colors = []
    for i in range(n):
        r = palette[i * 3]
        g = palette[i * 3 + 1]
        b = palette[i * 3 + 2]
        colors.append((r, g, b))

    # Sort by luminance (darkest first for background)
    colors.sort(key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])
    return colors


def create_vinyl_image(cover_path: str, size: int = 800) -> Image.Image:
    """
    Create a vinyl record image with the album cover filling the entire disc.
    Returns a PIL Image with alpha channel.
    """
    vinyl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vinyl)
    center = size // 2
    radius = size // 2 - 4
    cover_diameter = radius * 2

    # Circular mask for the entire disc
    disc_mask = Image.new("L", (size, size), 0)
    disc_mask_draw = ImageDraw.Draw(disc_mask)
    disc_mask_draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        fill=255
    )

    if cover_path and Path(cover_path).exists():
        # Cover art fills the entire disc — resize to full canvas, apply circular mask
        cover = Image.open(cover_path).convert("RGBA")
        cover = cover.resize((size, size), Image.LANCZOS)
        # Apply disc mask to cover's alpha
        cover_with_mask = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        cover_with_mask.paste(cover, (0, 0), disc_mask)
        vinyl = Image.alpha_composite(vinyl, cover_with_mask)
    else:
        # Fallback: dark disc
        draw.ellipse(
            [center - radius, center - radius, center + radius, center + radius],
            fill=(35, 35, 40, 255)
        )

    # Overlay semi-transparent vinyl grooves on top of the cover
    grooves = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grooves_draw = ImageDraw.Draw(grooves)
    for r in range(radius, 0, -6):
        groove_alpha = 35 if r % 12 < 6 else 20
        grooves_draw.ellipse(
            [center - r, center - r, center + r, center + r],
            outline=(0, 0, 0, groove_alpha),
            width=1
        )

    vinyl = Image.alpha_composite(vinyl, grooves)

    # Center hole
    hole_radius = int(radius * 0.03)
    draw = ImageDraw.Draw(vinyl)
    draw.ellipse(
        [center - hole_radius, center - hole_radius,
         center + hole_radius, center + hole_radius],
        fill=(0, 0, 0, 255)
    )

    # Subtle shine effect
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine)
    for i in range(50):
        alpha = max(0, 18 - i)
        offset = i * 2
        shine_draw.arc(
            [center - radius + offset, center - radius + offset,
             center + radius - offset, center + radius - offset],
            start=200, end=320,
            fill=(255, 255, 255, alpha),
            width=2
        )

    vinyl = Image.alpha_composite(vinyl, shine)
    return vinyl


def create_background_frame(
    colors: List[Tuple[int, int, int]],
    width: int,
    height: int,
    frame_index: int,
    total_frames: int
) -> Image.Image:
    """
    Create a single animated gradient background frame.
    Renders a tiny color grid and upscales with BICUBIC for perfectly smooth gradients,
    then adds subtle noise dithering to eliminate 8-bit banding.
    """
    if len(colors) < 3:
        colors = [(40, 25, 70), (60, 20, 80), (30, 50, 90), (70, 30, 60), (50, 40, 75)]

    # Animation phase
    phase = frame_index / max(total_frames, 1)
    angle = phase * 2 * math.pi

    # Smooth oscillators for color cycling
    t1 = (math.sin(angle) + 1) / 2
    t2 = (math.cos(angle * 0.7) + 1) / 2
    t3 = (math.sin(angle * 0.5 + 1.2) + 1) / 2

    def lerp_color(c_a, c_b, t_val):
        return tuple(int(a + (b - a) * t_val) for a, b in zip(c_a, c_b))

    # Create 4 corner colors that slowly shift
    c_tl = lerp_color(colors[0], colors[1], t1)
    c_tr = lerp_color(colors[1], colors[2 % len(colors)], t2)
    c_bl = lerp_color(colors[2 % len(colors)], colors[3 % len(colors)], t3)
    c_br = lerp_color(colors[3 % len(colors)], colors[4 % len(colors)], t1 * 0.7 + t2 * 0.3)

    # Darken for background but keep some vibrancy
    def darken(c, factor=0.55):
        return tuple(max(8, int(v * factor)) for v in c)

    c_tl = darken(c_tl)
    c_tr = darken(c_tr)
    c_bl = darken(c_bl)
    c_br = darken(c_br)

    # Create a tiny 2x2 image with the 4 corner colors
    tiny = Image.new("RGB", (2, 2))
    tiny.putpixel((0, 0), c_tl)
    tiny.putpixel((1, 0), c_tr)
    tiny.putpixel((0, 1), c_bl)
    tiny.putpixel((1, 1), c_br)

    # Upscale with BICUBIC → perfectly smooth gradient, zero banding
    img = tiny.resize((width, height), Image.BICUBIC)

    # Add subtle noise dithering to completely eliminate any 8-bit banding
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-2, 3, arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    return img

