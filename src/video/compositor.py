from __future__ import annotations

from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from .animations import (
    slide_from_angle,
    fade_in,
    stagger_progress,
    countdown_text,
)
from ..config.settings import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    FPS,
    TIMER_SECONDS,
    ENTRY_ANIMATION_DURATION,
    IMAGE_STAGGER_DELAY,
    FONT_PRIMARY,
    FONT_SECONDARY,
    ASSETS_DIR,
)

# =========================================================
# TYPES
# =========================================================

Frame = Image.Image
Point = Tuple[int, int]

# =========================================================
# LAYOUT CONSTANTS
# =========================================================

TOP_Y = 120
INSTRUCTION_Y = 260
GRID_TOP_Y = 380
GRID_GAP = 20

TIMER_POS = (VIDEO_WIDTH - 160, 60)
IMAGE_SIZE = (420, 420)

OUTRO_SECONDS = 3

# =========================================================
# FONT LOADING
# =========================================================

FONT_HOOK = ImageFont.truetype(str(FONT_PRIMARY), 78)
FONT_INSTRUCTION = ImageFont.truetype(str(FONT_SECONDARY), 52)
FONT_TIMER = ImageFont.truetype(str(FONT_PRIMARY), 54)

FONT_OUTRO_TITLE = ImageFont.truetype(str(FONT_PRIMARY), 72)
FONT_OUTRO_TEXT = ImageFont.truetype(str(FONT_PRIMARY), 46)  # BOLD for red text
FONT_ICON_LABEL = ImageFont.truetype(str(FONT_SECONDARY), 34)

# =========================================================
# CORE COMPOSITOR
# =========================================================


class QuizCompositor:
    def __init__(
        self,
        hook_text: str,
        instruction_text: str,
        images: List[Image.Image],
        duration_seconds: int,
        background: Image.Image,
    ) -> None:
        if len(images) != 4:
            raise ValueError("Exactly 4 images are required")

        self.hook_text = hook_text
        self.instruction_text = instruction_text
        self.images = images
        self.duration_seconds = duration_seconds
        self.background = background.resize((VIDEO_WIDTH, VIDEO_HEIGHT))

        self.total_frames = duration_seconds * FPS

        # animation timing
        self.hook_start = 0.0
        self.instruction_start = ENTRY_ANIMATION_DURATION
        self.grid_start = self.instruction_start + ENTRY_ANIMATION_DURATION
        self.timer_start = (
            self.grid_start + ENTRY_ANIMATION_DURATION + (3 * IMAGE_STAGGER_DELAY)
        )
        self.outro_start = duration_seconds - OUTRO_SECONDS

        # assets
        self.logo = None
        logo_path = ASSETS_DIR / "logo.png"
        if logo_path.exists():
            self.logo = Image.open(logo_path).convert("RGBA")

        self.icons = {}
        for name in ("like", "comment", "subscribe"):
            p = ASSETS_DIR / "icons" / f"{name}.png"
            if p.exists():
                self.icons[name] = Image.open(p).convert("RGBA")

    # =====================================================
    # FRAME LOOP
    # =====================================================

    def render_frames(self) -> List[Frame]:
        return [self._render_frame(i / FPS) for i in range(self.total_frames)]

    # =====================================================
    # FRAME RENDER
    # =====================================================

    def _render_frame(self, t: float) -> Frame:
        if t >= self.outro_start:
            return self._render_outro(t - self.outro_start)

        base = self.background.copy()
        draw = ImageDraw.Draw(base)

        # Hook
        hp = self._progress(t, self.hook_start, ENTRY_ANIMATION_DURATION)
        if hp > 0:
            pos = slide_from_angle((VIDEO_WIDTH // 2, TOP_Y), hp, 270)
            self._draw_centered_text(draw, pos, self.hook_text, FONT_HOOK, fade_in(hp))

        # Instruction
        ip = self._progress(t, self.instruction_start, ENTRY_ANIMATION_DURATION)
        if ip > 0:
            pos = slide_from_angle((VIDEO_WIDTH // 2, INSTRUCTION_Y), ip, 0)
            self._draw_centered_text(
                draw, pos, self.instruction_text, FONT_INSTRUCTION, fade_in(ip)
            )

        self._draw_image_grid(base, t)

        if t >= self.timer_start:
            timer = countdown_text(TIMER_SECONDS, t - self.timer_start)
            draw.text(TIMER_POS, timer, font=FONT_TIMER, fill=(220, 30, 30))

        return base

    # =====================================================
    # OUTRO
    # =====================================================

    def _render_outro(self, t: float) -> Frame:
        base = self.background.copy()
        draw = ImageDraw.Draw(base)

        alpha = min(255, int((t / 0.6) * 255))
        cx = VIDEO_WIDTH // 2

        # LOGO (TOP RIGHT)
        if self.logo:
            logo = self.logo.resize((120, 120))
            logo.putalpha(alpha)
            base.paste(logo, (VIDEO_WIDTH - 140, 30), logo)

        # TITLE
        self._draw_centered_text(
            draw,
            (cx, int(VIDEO_HEIGHT * 0.30)),
            "🎁 Monthly Rewards",
            FONT_OUTRO_TITLE,
            alpha,
        )

        # RED + BOLD SUBTEXT
        self._draw_centered_text(
            draw,
            (cx, int(VIDEO_HEIGHT * 0.42)),
            "Top commenters with correct answers\nget rewarded every month!",
            FONT_OUTRO_TEXT,
            alpha,
            color=(220, 30, 30),
        )

        # ICONS + LABELS
        icon_y = int(VIDEO_HEIGHT * 0.62)
        label_y = icon_y + 70
        spacing = 200

        items = [
            ("like", "Like"),
            ("comment", "Comment"),
            ("subscribe", "Subscribe"),
        ]

        for (name, label), x in zip(items, (cx - spacing, cx, cx + spacing)):
            if name in self.icons:
                icon = self.icons[name].resize((80, 80))
                icon.putalpha(alpha)
                base.paste(icon, (x - 40, icon_y - 40), icon)

                self._draw_centered_text(
                    draw,
                    (x, label_y),
                    label,
                    FONT_ICON_LABEL,
                    alpha,
                )

        return base

    # =====================================================
    # IMAGE GRID
    # =====================================================

    def _draw_image_grid(self, base: Image.Image, t: float) -> None:
        start_x = (VIDEO_WIDTH - (IMAGE_SIZE[0] * 2 + GRID_GAP)) // 2
        positions = [
            (start_x, GRID_TOP_Y),
            (start_x + IMAGE_SIZE[0] + GRID_GAP, GRID_TOP_Y),
            (start_x, GRID_TOP_Y + IMAGE_SIZE[1] + GRID_GAP),
            (start_x + IMAGE_SIZE[0] + GRID_GAP, GRID_TOP_Y + IMAGE_SIZE[1] + GRID_GAP),
        ]

        for i, (img, pos) in enumerate(zip(self.images, positions)):
            gp = max(0.0, t - self.grid_start)
            p = stagger_progress(gp, i, IMAGE_STAGGER_DELAY, ENTRY_ANIMATION_DURATION)
            if p <= 0:
                continue

            final = slide_from_angle(pos, p, 180)
            self._paste_image(base, img, final, p)

    # =====================================================
    # HELPERS
    # =====================================================

    def _paste_image(self, base: Image.Image, img: Image.Image, pos: Point, p: float):
        img = img.resize(IMAGE_SIZE).convert("RGBA")
        img.putalpha(fade_in(p))
        base.paste(img, pos, img)

    def _draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        center: Point,
        text: str,
        font: ImageFont.FreeTypeFont,
        alpha: int,
        color: tuple[int, int, int] = (255, 255, 255),
    ):
        bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = center[0] - w // 2
        y = center[1] - h // 2

        draw.multiline_text(
            (x, y),
            text,
            font=font,
            fill=(*color, alpha),
            align="center",
        )

    @staticmethod
    def _progress(t: float, start: float, duration: float) -> float:
        if t <= start:
            return 0.0
        if t >= start + duration:
            return 1.0
        return (t - start) / duration
