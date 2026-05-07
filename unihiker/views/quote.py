"""Daily quote view."""

import textwrap

import pygame

from unihiker.services.quote import QuoteClient
from .base import View


BG = (8, 10, 15)
CARD = (16, 20, 28)
TEXT = (235, 244, 246)
MUTED = (118, 138, 146)
ACCENT = (0, 229, 200)
GREEN = (61, 255, 143)
W, H = 240, 320


class QuoteView(View):
    name = "quote"

    def __init__(self):
        super().__init__()
        self.client = None
        self.font_title = None
        self.font_phrase = None
        self.font_status = None
        self.font_small = None

    def on_mount(self, app):
        super().on_mount(app)
        self.client = QuoteClient(app.config)
        self.font_title = pygame.font.SysFont("monospace", 10, bold=True)
        self.font_phrase = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_status = pygame.font.SysFont("monospace", 11)
        self.font_small = pygame.font.SysFont("monospace", 9)
        self.client.fetch_async()

    def update(self, dt):
        self.client.update(dt)

    def on_config_updated(self):
        if self.client:
            self.client.config = self.app.config
            self.client.reset_schedule()

    def draw(self, screen):
        state = self.client.snapshot()

        screen.fill(BG)
        pygame.draw.rect(screen, CARD, (8, 8, W - 16, H - 16), border_radius=10)
        pygame.draw.line(screen, ACCENT, (40, 26), (W - 40, 26), 1)

        title = self.font_title.render("DAILY FACT", True, MUTED)
        screen.blit(title, ((W - title.get_width()) // 2, 48))

        if not state.phrase:
            message = "CARGANDO..." if state.loading else "SIN DATOS"
            text = self.font_status.render(message, True, MUTED)
            screen.blit(text, ((W - text.get_width()) // 2, 148))
            return

        self._draw_centered_wrapped(screen, state.phrase, self.font_phrase, TEXT, 22, 88, 27)

        if state.source:
            source_text = self._fit_text(state.source.upper(), self.font_small, W - 44)
            source = self.font_small.render(source_text, True, GREEN)
            screen.blit(source, ((W - source.get_width()) // 2, 252))

        if state.error:
            status = self.font_small.render("CACHE", True, MUTED)
            screen.blit(status, ((W - status.get_width()) // 2, H - 28))

    def _draw_centered_wrapped(self, screen, text, font, color, x, y, line_height):
        lines = []
        for paragraph in text.splitlines():
            lines.extend(textwrap.wrap(paragraph, width=24) or [""])

        lines = lines[:5]
        block_h = len(lines) * line_height
        y += max(0, (132 - block_h) // 2)

        for line in lines:
            rendered = font.render(line, True, color)
            screen.blit(rendered, ((W - rendered.get_width()) // 2, y))
            y += line_height

    def _fit_text(self, text, font, max_width):
        if font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."
        while text and font.size(text + ellipsis)[0] > max_width:
            text = text[:-1]
        return text + ellipsis if text else ellipsis
