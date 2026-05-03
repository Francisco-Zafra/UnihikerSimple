"""Investment evolution view."""

import pygame

from investments import InvestmentClient
from .base import View


BG = (7, 10, 15)
CARD = (14, 19, 28)
TEXT = (235, 244, 246)
MUTED = (118, 138, 146)
GRID = (42, 55, 66)
GREEN = (61, 255, 143)
RED = (255, 110, 110)
ACCENT = (0, 229, 200)
W, H = 240, 320


def fmt_pct(value):
    return f"{value:+.2f}%"


class InvestmentView(View):
    name = "investment"

    def __init__(self):
        super().__init__()
        self.client = None
        self.font_title = None
        self.font_value = None
        self.font_mid = None
        self.font_small = None

    def on_mount(self, app):
        super().on_mount(app)
        self.client = InvestmentClient(app.config)
        self.font_title = pygame.font.SysFont("monospace", 10, bold=True)
        self.font_value = pygame.font.SysFont("monospace", 28, bold=True)
        self.font_mid = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 9)
        self.client.fetch_async()

    def update(self, dt):
        self.client.update(dt)

    def draw(self, screen):
        state = self.client.snapshot()

        screen.fill(BG)
        pygame.draw.rect(screen, CARD, (8, 8, W - 16, H - 16), border_radius=10)
        pygame.draw.line(screen, ACCENT, (34, 24), (W - 34, 24), 1)

        title = self.font_title.render(self.app.config["investment_label"].upper(), True, MUTED)
        screen.blit(title, ((W - title.get_width()) // 2, 38))

        if not state.points:
            message = "CARGANDO..." if state.loading else "SIN DATOS"
            text = self.font_mid.render(message, True, MUTED)
            screen.blit(text, ((W - text.get_width()) // 2, 148))
            return

        first = state.first
        last = state.last
        pct = state.percent_change or 0.0
        week_pct = state.percent_change_since_days(7) or 0.0
        month_pct = state.percent_change_since_days(30) or 0.0
        positive = pct >= 0
        change_color = GREEN if positive else RED

        total_label = self.font_small.render("DESDE INICIO", True, MUTED)
        total = self.font_value.render(fmt_pct(pct), True, change_color)
        week_label = self.font_mid.render("7D", True, ACCENT)
        week_value = self.font_mid.render(fmt_pct(week_pct), True, GREEN if week_pct >= 0 else RED)
        month_label = self.font_mid.render("30D", True, ACCENT)
        month_value = self.font_mid.render(fmt_pct(month_pct), True, GREEN if month_pct >= 0 else RED)
        period = self.font_small.render(
            f"{first.day.strftime('%d/%m/%y')} - {last.day.strftime('%d/%m/%y')}",
            True,
            MUTED,
        )

        screen.blit(total_label, ((W - total_label.get_width()) // 2, 62))
        screen.blit(total, ((W - total.get_width()) // 2, 78))
        self._draw_metric(screen, 34, 118, week_label, week_value)
        self._draw_metric(screen, W - 34, 118, month_label, month_value, align="right")
        screen.blit(period, ((W - period.get_width()) // 2, 139))

        self._draw_chart(screen, state.points, change_color)

        if state.error:
            status = self.font_small.render("CACHE", True, MUTED)
            screen.blit(status, ((W - status.get_width()) // 2, H - 24))

    def _draw_chart(self, screen, points, line_color):
        rect = pygame.Rect(10, 154, W - 20, 128)
        pygame.draw.rect(screen, (9, 13, 20), rect, border_radius=6)

        for i in range(1, 4):
            y = rect.top + int(rect.height * i / 4)
            pygame.draw.line(screen, GRID, (rect.left, y), (rect.right, y), 1)

        values = [point.close for point in points]
        min_v = min(values)
        max_v = max(values)
        span = max(max_v - min_v, 0.01)

        coords = []
        max_index = max(len(points) - 1, 1)
        for index, point in enumerate(points):
            x = rect.left + int(index * rect.width / max_index)
            y = rect.bottom - int((point.close - min_v) * rect.height / span)
            coords.append((x, y))

        if len(coords) > 1:
            pygame.draw.lines(screen, line_color, False, coords, 2)

        pygame.draw.circle(screen, ACCENT, coords[-1], 3)

    def _draw_metric(self, screen, x, y, label, value, align="left"):
        gap = 6
        width = label.get_width() + value.get_width() + gap
        if align == "right":
            x -= width

        screen.blit(label, (x, y))
        screen.blit(value, (x + label.get_width() + gap, y))
