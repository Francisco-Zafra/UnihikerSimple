"""Home load progress view for the UniHiker 240x320 display."""

from datetime import date, datetime

import pygame

from .base import View


MILESTONES = [
    ("2025-11-13", "Reserva"),
    ("2026-04-24", "Firma Contrato"),
    ("2026-08-01", "Pago 1"),
    ("2026-12-01", "Pago 2"),
    ("2027-04-01", "Pago 3"),
    ("2027-08-01", "Pago 4"),
    ("2028-10-01", "Entrega de llaves"),
]


BG = (6, 9, 15)
CARD = (12, 18, 32)
GREEN = (61, 255, 143)
GREEN2 = (22, 197, 100)
TEAL = (0, 229, 200)
AMBER = (255, 209, 102)
MUTED = (120, 180, 150)
DIM = (28, 46, 34)
WHITE = (255, 255, 255)

W, H = 240, 320


def parse(s):
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def fmt_date(d):
    return f"{d.day:02d}/{d.month:02d}/{str(d.year)[2:]}"


def fmt_time(dt):
    return dt.strftime("%H:%M")


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def txt(surf, text, font, color, x, y, align="left"):
    s = font.render(text, True, color)
    if align == "center":
        x -= s.get_width() // 2
    elif align == "right":
        x -= s.get_width()
    surf.blit(s, (x, y))
    return s.get_width()


def grad_surface(w, h, cl, cr, alpha=255):
    s = pygame.Surface((max(w, 1), max(h, 1)), pygame.SRCALPHA)
    for x in range(max(w, 1)):
        t = x / max(w - 1, 1)
        c = lerp_color(cl, cr, t)
        pygame.draw.line(s, (*c, alpha), (x, 0), (x, max(h, 1) - 1))
    return s


def draw_bar(surf, x, y, w, h, pct, m_pcts):
    pygame.draw.rect(surf, DIM, (x, y, w, h), border_radius=h)
    fw = int(w * pct)

    if fw > 2:
        surf.blit(grad_surface(fw, h, GREEN2, TEAL), (x, y))

    if fw > 4:
        cx, cy = x + fw, y + h // 2
        for r, a in [(9, 25), (6, 60), (3, 130)]:
            gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*TEAL, a), (r, r), r)
            surf.blit(gs, (cx - r, cy - r))
        pygame.draw.circle(surf, WHITE, (cx, cy), 3)

    for mp, done in m_pcts:
        tx, ty = x + int(w * mp), y + h // 2
        pygame.draw.circle(surf, BG, (tx, ty), 5)
        pygame.draw.circle(surf, GREEN if done else MUTED, (tx, ty), 5, 2)
        if done:
            pygame.draw.circle(surf, GREEN, (tx, ty), 2)


def compute(dt_now):
    start = datetime(2025, 11, 1, 0, 0, 0)
    end = datetime(2028, 10, 1, 1, 0, 0)

    total_seconds = (end - start).total_seconds()
    elapsed_seconds = max(0, min((dt_now - start).total_seconds(), total_seconds))

    pct = elapsed_seconds / total_seconds
    days_left = max(0, (end.date() - dt_now.date()).days)

    m_dates = [datetime.strptime(m[0], "%Y-%m-%d") for m in MILESTONES]
    m_pcts = [((d - start).total_seconds() / total_seconds, d <= dt_now) for d in m_dates]

    next_idx = next((i for i, d in enumerate(m_dates) if d > dt_now), None)
    next_m = MILESTONES[next_idx] if next_idx is not None else None
    prev_d = m_dates[next_idx - 1].date() if next_idx else None

    return pct, days_left, m_pcts, next_m, next_idx, prev_d


class HomeLoadView(View):
    name = "homeload"

    def __init__(self):
        super().__init__()
        self.f_huge = None
        self.f_dec = None
        self.f_med = None
        self.f_sm = None
        self.f_xs = None
        self.scanlines = None
        self.frame = 0
        self.last_day = None
        self.anim_pct = 0.0
        self.anim_num = 0.0
        self.pct = 0.0
        self.pct_pct = 0.0
        self.days_left = 0
        self.m_pcts = []
        self.next_m = None
        self.next_idx = None
        self.prev_d = None
        self.dt_now = None
        self.today = None

    def on_mount(self, app):
        super().on_mount(app)
        self.f_huge = pygame.font.SysFont("monospace", 72, bold=True)
        self.f_dec = pygame.font.SysFont("monospace", 30, bold=True)
        self.f_med = pygame.font.SysFont("monospace", 13, bold=True)
        self.f_sm = pygame.font.SysFont("monospace", 11)
        self.f_xs = pygame.font.SysFont("monospace", 9)

        self.scanlines = pygame.Surface((W, H), pygame.SRCALPHA)
        for sy in range(0, H, 4):
            pygame.draw.line(self.scanlines, (0, 0, 0, 20), (0, sy), (W, sy))

    def on_enter(self):
        self.last_day = None
        self.anim_pct = 0.0
        self.anim_num = 0.0

    def update(self, dt):
        self.frame += 1
        self.dt_now = datetime.now()
        self.today = self.dt_now.date()

        if self.today != self.last_day:
            (
                self.pct,
                self.days_left,
                self.m_pcts,
                self.next_m,
                self.next_idx,
                self.prev_d,
            ) = compute(self.dt_now)
            self.pct_pct = self.pct * 100
            self.last_day = self.today
            self.anim_pct = 0.0
            self.anim_num = 0.0

        if self.anim_pct < self.pct:
            self.anim_pct = min(self.pct, self.anim_pct + self.pct * 0.04)
            self.anim_num = min(self.pct_pct, self.anim_num + self.pct_pct * 0.04)

    def draw(self, screen):
        screen.fill(BG)
        pygame.draw.rect(screen, CARD, (6, 6, W - 12, H - 12), border_radius=10)
        screen.blit(grad_surface(W - 80, 1, GREEN, TEAL, 140), (40, 6))

        txt(screen, "PROGRESO  *  PISO", self.f_xs, MUTED, W // 2, 15, "center")

        dot_col = GREEN
        if (self.frame // 15) % 2 == 0:
            pygame.draw.circle(screen, dot_col, (W - 20, 18), 3)
            gs = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*dot_col, 50), (6, 6), 6)
            screen.blit(gs, (W - 26, 12))

        pct_str = f"{self.anim_num:.2f}"
        int_str, dec_str = pct_str.split(".")
        dec_str = "." + dec_str + "%"

        int_surf = self.f_huge.render(int_str, True, WHITE)
        dec_surf = self.f_dec.render(dec_str, True, TEAL)

        gm = grad_surface(int_surf.get_width(), int_surf.get_height(), WHITE, GREEN)
        int_surf.blit(gm, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        total_w = int_surf.get_width() + dec_surf.get_width() + 2
        base_x = (W - total_w) // 2

        screen.blit(int_surf, (base_x, 28))
        dec_y = 28 + int_surf.get_height() - dec_surf.get_height() - 5
        screen.blit(dec_surf, (base_x + int_surf.get_width() + 2, dec_y))

        dl = f"FALTAN  {self.days_left:,}  DIAS".replace(",", ".")
        txt(screen, dl, self.f_xs, MUTED, W // 2, 114, "center")

        draw_bar(screen, 16, 132, W - 32, 6, self.anim_pct, self.m_pcts)
        pygame.draw.line(screen, (*MUTED, 40), (14, 152), (W - 14, 152))

        if self.next_m:
            self._draw_next_milestone(screen)

        fy = H - 20
        pygame.draw.line(screen, (*MUTED, 40), (14, fy - 4), (W - 14, fy - 4))

        txt(screen, "HOY", self.f_xs, MUTED, 16, fy)
        txt(screen, fmt_date(self.today), self.f_xs, TEAL, 38, fy)

        txt(screen, "HORA", self.f_xs, MUTED, W // 2 + 8, fy)
        txt(screen, fmt_time(self.dt_now), self.f_sm, GREEN, W - 16, fy, "right")

        screen.blit(self.scanlines, (0, 0))

    def _draw_next_milestone(self, screen):
        ds, name = self.next_m
        cy0 = 160

        cs = pygame.Surface((W - 28, 100), pygame.SRCALPHA)
        cs.fill((255, 209, 102, 10))
        screen.blit(cs, (14, cy0))

        pygame.draw.rect(screen, (*AMBER, 45), (14, cy0, W - 28, 100), 1, border_radius=8)

        txt(screen, "PROXIMO HITO", self.f_xs, MUTED, W // 2, cy0 + 8, "center")
        pygame.draw.line(screen, (*AMBER, 40), (30, cy0 + 20), (W - 30, cy0 + 20))

        txt(screen, name, self.f_med, AMBER, W // 2, cy0 + 30, "center")
        txt(screen, fmt_date(parse(ds)), self.f_sm, WHITE, W // 2, cy0 + 52, "center")

        days_to = max(0, (parse(ds) - self.today).days)
        txt(screen, f"en {days_to:,} dias".replace(",", "."), self.f_xs, MUTED, W // 2, cy0 + 70, "center")

        if self.next_idx and self.prev_d:
            seg_total = (parse(ds) - self.prev_d).days
            seg_elapsed = max(0, (self.today - self.prev_d).days)
            seg_pct = min(1.0, seg_elapsed / seg_total)

            bx, by, bw, bh = 26, cy0 + 85, W - 52, 3
            pygame.draw.rect(screen, DIM, (bx, by, bw, bh), border_radius=bh)

            if seg_pct > 0:
                fw2 = max(1, int(bw * seg_pct))
                screen.blit(grad_surface(fw2, bh, GREEN2, AMBER), (bx, by))
