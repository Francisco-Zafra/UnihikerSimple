"""Simple clock view used to test navigation."""

from datetime import datetime

import pygame

from .base import View
from unihiker.services.weather import WeatherClient


BG = (8, 12, 18)
CARD = (15, 23, 32)
TEXT = (235, 245, 248)
MUTED = (115, 140, 150)
ACCENT = (0, 229, 200)
GREEN = (61, 255, 143)
W, H = 240, 320

WEEKDAYS_ES = [
    "LUNES",
    "MARTES",
    "MIERCOLES",
    "JUEVES",
    "VIERNES",
    "SABADO",
    "DOMINGO",
]


class ClockView(View):
    name = "clock"

    def __init__(self):
        super().__init__()
        self.now = datetime.now()
        self.font_time = None
        self.font_date = None
        self.font_label = None
        self.font_small = None
        self.weather = None

    def on_mount(self, app):
        super().on_mount(app)
        self.font_time = pygame.font.SysFont("monospace", 48, bold=True)
        self.font_date = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 10, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 10)
        self.weather = WeatherClient(app.config)
        self.weather.fetch_async()

    def update(self, dt):
        self.now = datetime.now()
        self.weather.update(dt)

    def draw(self, screen):
        screen.fill(BG)
        pygame.draw.rect(screen, CARD, (8, 8, W - 16, H - 16), border_radius=10)
        pygame.draw.line(screen, ACCENT, (42, 24), (W - 42, 24), 1)

        label = self.font_label.render("RELOJ", True, MUTED)
        time_text = self.font_time.render(self.now.strftime("%H:%M"), True, TEXT)
        seconds = self.font_date.render(self.now.strftime("%S"), True, GREEN)
        date_text = self.font_date.render(self.now.strftime("%d/%m/%Y"), True, ACCENT)
        weekday = self.font_small.render(WEEKDAYS_ES[self.now.weekday()], True, MUTED)

        total_time_w = time_text.get_width() + seconds.get_width() + 6
        time_x = (W - total_time_w) // 2

        screen.blit(label, ((W - label.get_width()) // 2, 54))
        screen.blit(time_text, (time_x, 112))
        screen.blit(seconds, (time_x + time_text.get_width() + 6, 137))
        screen.blit(date_text, ((W - date_text.get_width()) // 2, 190))
        screen.blit(weekday, ((W - weekday.get_width()) // 2, 218))
        self._draw_weather(screen)

    def _draw_weather(self, screen):
        state = self.weather.snapshot()

        pygame.draw.line(screen, (*MUTED, 55), (30, 248), (W - 30, 248))

        place = self.font_label.render(self.app.config["weather_label"].upper(), True, MUTED)
        screen.blit(place, ((W - place.get_width()) // 2, 258))

        if state.loading and state.temperature is None:
            status = self.font_small.render("CLIMA...", True, MUTED)
            screen.blit(status, ((W - status.get_width()) // 2, 278))
            return

        if state.error:
            status = self.font_small.render(state.error, True, MUTED)
            screen.blit(status, ((W - status.get_width()) // 2, 278))
            return

        temp = self.font_date.render(f"{state.temperature:.0f}C", True, TEXT)
        condition = self.font_small.render(state.condition, True, ACCENT)
        details = self.font_small.render(f"{state.humidity}%  {state.wind_speed:.0f}km/h", True, MUTED)

        row_gap = 8
        row_w = temp.get_width() + condition.get_width() + row_gap
        row_x = (W - row_w) // 2

        screen.blit(temp, (row_x, 274))
        screen.blit(condition, (row_x + temp.get_width() + row_gap, 278))
        screen.blit(details, ((W - details.get_width()) // 2, 294))
