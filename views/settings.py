"""Configuration view for app-wide options."""

import pygame

from .base import View


BG = (8, 10, 14)
PANEL = (16, 22, 30)
TEXT = (235, 244, 246)
MUTED = (118, 138, 146)
ACCENT = (0, 229, 200)
GREEN = (61, 255, 143)
W, H = 240, 320


def format_duration(seconds):
    minutes, secs = divmod(int(seconds), 60)
    if minutes and secs:
        return f"{minutes}m {secs:02d}s"
    if minutes:
        return f"{minutes} min"
    return f"{secs} s"


class SettingsView(View):
    name = "settings"

    def __init__(self):
        super().__init__()
        self.font_title = None
        self.font_value = None
        self.font_text = None
        self.font_small = None

    def on_mount(self, app):
        super().on_mount(app)
        self.font_title = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_value = pygame.font.SysFont("monospace", 30, bold=True)
        self.font_text = pygame.font.SysFont("monospace", 11, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 9)

    def draw(self, screen):
        screen.fill(BG)
        pygame.draw.rect(screen, PANEL, (8, 8, W - 16, H - 16), border_radius=10)
        pygame.draw.line(screen, ACCENT, (36, 30), (W - 36, 30), 1)

        title = self.font_title.render("CONFIGURACION", True, TEXT)
        label = self.font_text.render("CAMBIO AUTOMATICO", True, MUTED)
        value = self.font_value.render(format_duration(self.app.auto_switch_seconds), True, GREEN)
        minus = self.font_small.render("A  -30s", True, MUTED)
        plus = self.font_small.render("B  +30s", True, MUTED)
        exit_hint = self.font_small.render("A+B  salir", True, ACCENT)

        screen.blit(title, ((W - title.get_width()) // 2, 58))
        screen.blit(label, ((W - label.get_width()) // 2, 112))
        screen.blit(value, ((W - value.get_width()) // 2, 142))

        pygame.draw.line(screen, (*MUTED, 55), (30, 202), (W - 30, 202))
        screen.blit(minus, (34, 224))
        screen.blit(plus, (W - plus.get_width() - 34, 224))
        screen.blit(exit_hint, ((W - exit_hint.get_width()) // 2, H - 36))
