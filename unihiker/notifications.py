"""Small global notification overlay for the pygame app."""

from collections import deque
from dataclasses import dataclass

import pygame


W, H = 240, 320
HEIGHT = 64
MARGIN = 8
SLIDE_SECONDS = 0.22
VISIBLE_SECONDS = 3.6
PERSISTENT_LEVELS = {"notice", "warning", "critical"}

COLORS = {
    "info": {
        "bg": (16, 24, 32),
        "accent": (0, 229, 200),
        "title": (235, 244, 246),
        "body": (155, 176, 184),
    },
    "notice": {
        "bg": (15, 25, 22),
        "accent": (61, 255, 143),
        "title": (232, 255, 240),
        "body": (166, 218, 185),
    },
    "warning": {
        "bg": (32, 26, 14),
        "accent": (255, 190, 76),
        "title": (255, 241, 212),
        "body": (215, 190, 145),
    },
    "critical": {
        "bg": (35, 15, 20),
        "accent": (255, 110, 110),
        "title": (255, 232, 232),
        "body": (230, 165, 165),
    },
}


@dataclass
class Notification:
    title: str
    message: str = ""
    level: str = "info"


class NotificationCenter:
    def __init__(self, size=(W, H), buzzer=None):
        self.size = size
        self.buzzer = buzzer
        self.queue = deque()
        self.current = None
        self.elapsed = 0.0
        self.dismiss_elapsed = 0.0
        self.dismissing = False
        self.font_title = None
        self.font_body = None
        self.font_meta = None

    def push(self, title, message="", level="info"):
        level = level if level in COLORS else "info"
        self.queue.append(Notification(title=title, message=message, level=level))
        if not self.current:
            self._next()

    def update(self, dt):
        if not self.current:
            return

        if self.dismissing:
            self.dismiss_elapsed += dt
            if self.dismiss_elapsed >= SLIDE_SECONDS:
                self._next()
            return

        self.elapsed += dt
        if self.current.level in PERSISTENT_LEVELS:
            return

        if self.elapsed >= SLIDE_SECONDS + VISIBLE_SECONDS + SLIDE_SECONDS:
            self._next()

    def handle_event(self, event):
        if not self.current:
            return False
        if event.type not in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            return False
        if self.current.level not in PERSISTENT_LEVELS:
            return False

        self.dismiss()
        return True

    def draw(self, screen):
        if not self.current:
            return

        self._ensure_fonts()

        width, _ = self.size
        rect_width = width - MARGIN * 2
        y = self._current_y()
        rect = pygame.Rect(MARGIN, y, rect_width, HEIGHT)
        palette = COLORS[self.current.level]

        pygame.draw.rect(screen, palette["bg"], rect, border_radius=8)
        pygame.draw.rect(screen, palette["accent"], rect, width=1, border_radius=8)
        pygame.draw.rect(
            screen,
            palette["accent"],
            (rect.left, rect.top + 10, 3, rect.height - 20),
            border_radius=2,
        )

        title = self._fit_text(self.current.title.upper(), self.font_title, rect_width - 24)
        title_surface = self.font_title.render(title, True, palette["title"])
        screen.blit(title_surface, (rect.left + 12, rect.top + 11))

        if self.current.message:
            message = self._fit_text(self.current.message, self.font_body, rect_width - 24)
            body_surface = self.font_body.render(message, True, palette["body"])
            screen.blit(body_surface, (rect.left + 12, rect.top + 34))

    def _next(self):
        self.current = self.queue.popleft() if self.queue else None
        self.elapsed = 0.0
        self.dismiss_elapsed = 0.0
        self.dismissing = False
        if self.current:
            self._buzz(self.current.level)

    def dismiss(self):
        if not self.current or self.dismissing:
            return

        self.dismiss_elapsed = 0.0
        self.dismissing = True

    def _buzz(self, level):
        if not self.buzzer:
            return

        if level == "info":
            self.buzzer.beep(frequency=880, beats=1)
        elif level == "notice":
            self.buzzer.sequence((660, 880), beats=1)
        elif level == "warning":
            self.buzzer.sequence((880, 660, 440), beats=1)
        elif level == "critical":
            self.buzzer.sequence((880, 440, 880, 440), beats=1)

    def _current_y(self):
        if self.dismissing:
            t = min(1.0, self.dismiss_elapsed / SLIDE_SECONDS)
            return int(MARGIN - (HEIGHT + MARGIN) * self._ease_in(t))

        if self.elapsed < SLIDE_SECONDS:
            t = self.elapsed / SLIDE_SECONDS
            return int(-HEIGHT + (HEIGHT + MARGIN) * self._ease_out(t))

        if self.current.level in PERSISTENT_LEVELS:
            return MARGIN

        hide_at = SLIDE_SECONDS + VISIBLE_SECONDS
        if self.elapsed > hide_at:
            t = min(1.0, (self.elapsed - hide_at) / SLIDE_SECONDS)
            return int(MARGIN - (HEIGHT + MARGIN) * self._ease_in(t))

        return MARGIN

    def _ensure_fonts(self):
        if self.font_title:
            return

        self.font_title = pygame.font.SysFont("monospace", 12, bold=True)
        self.font_body = pygame.font.SysFont("monospace", 10)
        self.font_meta = pygame.font.SysFont("monospace", 8)

    def _fit_text(self, text, font, max_width):
        if font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."
        while text and font.size(text + ellipsis)[0] > max_width:
            text = text[:-1]
        return text + ellipsis if text else ellipsis

    def _ease_out(self, value):
        return 1 - (1 - value) * (1 - value)

    def _ease_in(self, value):
        return value * value
