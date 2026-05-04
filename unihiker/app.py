"""Application orchestration and view navigation."""

import sys

import pygame

from .config import DEFAULT_CONFIG, load_config, save_config
from .notifications import NotificationCenter
from .services.buzzer import BuzzerClient
from .services.web_config import start_web_config_server


W, H = 240, 320
FPS = 30
DEFAULT_AUTO_SWITCH_SECONDS = DEFAULT_CONFIG["auto_switch_seconds"]
TRANSITION_SECONDS = 0.28


PREVIOUS_KEYS = {
    pygame.K_b,
    pygame.K_LEFT,
    pygame.K_PAGEUP,
}

NEXT_KEYS = {
    pygame.K_a,
    pygame.K_RIGHT,
    pygame.K_PAGEDOWN,
}

QUIT_KEYS = {
    pygame.K_ESCAPE,
    pygame.K_q,
}

TEST_NOTIFICATION_KEYS = {
    pygame.K_n,
}


class UnihikerApp:
    """Small pygame shell that owns the screen and switches between views."""

    def __init__(self, views, settings_view=None, size=(W, H), fps=FPS, auto_switch_seconds=None):
        if not views:
            raise ValueError("At least one view is required")

        self.config = load_config()
        if auto_switch_seconds is not None:
            self.config["auto_switch_seconds"] = auto_switch_seconds

        self.all_views = list(views)
        self.views = self._configured_views(self.config["view_order"])
        self.settings_view = settings_view
        self.size = size
        self.fps = fps
        self.auto_switch_seconds = self.config["auto_switch_seconds"]
        self.auto_switch_elapsed = 0.0
        self.current_index = 0
        self.settings_active = False
        self.pressed_keys = set()
        self.combo_consumed = False
        self.transition = None
        self.buzzer = BuzzerClient(enabled=self.config["buzzer_enabled"])
        self.notifications = NotificationCenter(size=size, buzzer=self.buzzer)
        self.test_notification_index = 0
        self.web_server = None
        self.screen = None
        self.clock = None
        self.running = False

    @property
    def current_view(self):
        if self.settings_active:
            return self.settings_view
        return self.views[self.current_index]

    @property
    def view_names(self):
        return [view.name for view in self.all_views]

    def run(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption("UnihikerSimple")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.running = True

        mounted_views = list(self.all_views)
        if self.settings_view:
            mounted_views.append(self.settings_view)

        for view in mounted_views:
            view.on_mount(self)

        self.web_server = start_web_config_server(self)
        self.current_view.on_enter()

        try:
            while self.running:
                dt = self.clock.tick(self.fps) / 1000.0
                self._handle_events()
                self._update_auto_switch(dt)
                self.current_view.update(dt)
                self.notifications.update(dt)
                self._update_transition(dt)
                self._draw_frame()
                self.notifications.draw(self.screen)
                pygame.display.flip()
        finally:
            if self.web_server:
                self.web_server.stop()
            pygame.quit()
        sys.exit()

    def stop(self):
        self.running = False

    def previous_view(self):
        self._set_view((self.current_index - 1) % len(self.views))

    def next_view(self):
        self._set_view((self.current_index + 1) % len(self.views))

    def change_auto_switch_seconds(self, delta):
        self.auto_switch_seconds = max(10, self.auto_switch_seconds + delta)
        self.config["auto_switch_seconds"] = self.auto_switch_seconds
        save_config(self.config)
        self.reset_auto_switch_timer()

    def reset_auto_switch_timer(self):
        self.auto_switch_elapsed = 0.0

    def apply_view_order(self, view_order):
        ordered_views = self._configured_views(view_order)
        current_name = self.current_view.name if not self.settings_active else None

        self.views = ordered_views
        if current_name:
            self.current_index = next(
                (index for index, view in enumerate(self.views) if view.name == current_name),
                0,
            )
        else:
            self.current_index = min(self.current_index, len(self.views) - 1)

        self.transition = None
        self.reset_auto_switch_timer()

    def toggle_settings(self):
        if not self.settings_view:
            return

        previous = self.current_view
        previous.on_exit()
        self.settings_active = not self.settings_active
        current = self.current_view
        current.on_enter()
        self._start_transition(previous, current, direction=0)
        self.reset_auto_switch_timer()

    def _set_view(self, index):
        if self.settings_active:
            self.toggle_settings()

        if index == self.current_index:
            return

        previous = self.current_view
        previous.on_exit()
        previous_index = self.current_index
        self.current_index = index
        current = self.current_view
        current.on_enter()
        direction = 1
        if (index - previous_index) % len(self.views) > len(self.views) / 2:
            direction = -1
        self._start_transition(previous, current, direction)
        self.reset_auto_switch_timer()

    def _configured_views(self, view_order):
        views_by_name = {view.name: view for view in self.all_views}
        names = [name for name in view_order if name in views_by_name]
        if not names:
            names = [view.name for view in self.all_views]
        return [views_by_name[name] for name in names]

    def _start_transition(self, from_view, to_view, direction):
        if from_view is to_view:
            self.transition = None
            return

        self.transition = {
            "from": from_view,
            "to": to_view,
            "direction": direction,
            "elapsed": 0.0,
            "duration": TRANSITION_SECONDS,
        }

    def _update_transition(self, dt):
        if not self.transition:
            return

        self.transition["elapsed"] += dt
        if self.transition["elapsed"] >= self.transition["duration"]:
            self.transition = None

    def _draw_frame(self):
        if not self.transition:
            self.current_view.draw(self.screen)
            return

        width, height = self.size
        duration = self.transition["duration"]
        t = min(1.0, self.transition["elapsed"] / duration)
        eased = 1 - (1 - t) * (1 - t)

        from_surface = pygame.Surface(self.size).convert()
        to_surface = pygame.Surface(self.size).convert()
        self.transition["from"].draw(from_surface)
        self.transition["to"].draw(to_surface)

        direction = self.transition["direction"]
        if direction == 0:
            self.screen.blit(from_surface, (0, 0))
            to_surface.set_alpha(int(255 * eased))
            self.screen.blit(to_surface, (0, 0))
            return

        offset = int(width * eased)
        self.screen.fill((0, 0, 0))
        self.screen.blit(from_surface, (-direction * offset, 0))
        self.screen.blit(to_surface, (direction * (width - offset), 0))

    def _update_auto_switch(self, dt):
        if self.settings_active or self.auto_switch_seconds <= 0:
            return

        self.auto_switch_elapsed += dt
        if self.auto_switch_elapsed >= self.auto_switch_seconds:
            self.next_view()

    def _has_previous_pressed(self):
        return bool(self.pressed_keys & PREVIOUS_KEYS)

    def _has_next_pressed(self):
        return bool(self.pressed_keys & NEXT_KEYS)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.stop()
                continue

            if self.notifications.handle_event(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key in QUIT_KEYS:
                    self.stop()
                    continue

                if event.key in TEST_NOTIFICATION_KEYS:
                    self._push_test_notification()
                    continue

                if event.key in PREVIOUS_KEYS or event.key in NEXT_KEYS:
                    if self.transition:
                        continue

                    self.pressed_keys.add(event.key)
                    if (
                        self._has_previous_pressed()
                        and self._has_next_pressed()
                        and not self.combo_consumed
                    ):
                        self.toggle_settings()
                        self.combo_consumed = True
                    continue

            if event.type == pygame.KEYUP:
                if event.key in PREVIOUS_KEYS or event.key in NEXT_KEYS:
                    if self.transition:
                        self.pressed_keys.discard(event.key)
                        if not self.pressed_keys:
                            self.combo_consumed = False
                        continue

                    was_combo = self.combo_consumed
                    is_previous = event.key in PREVIOUS_KEYS
                    is_next = event.key in NEXT_KEYS

                    self.pressed_keys.discard(event.key)
                    if not self.pressed_keys:
                        self.combo_consumed = False

                    if was_combo:
                        continue

                    if self.settings_active:
                        if is_previous:
                            self.change_auto_switch_seconds(-30)
                        elif is_next:
                            self.change_auto_switch_seconds(30)
                        continue

                    if is_previous:
                        self.previous_view()
                    elif is_next:
                        self.next_view()
                    continue

            if not self.transition:
                self.current_view.handle_event(event)

    def _push_test_notification(self):
        samples = (
            ("Info", "Se cierra sola", "info"),
            ("Notice", "Toca la pantalla para cerrar", "notice"),
            ("Warning", "Requiere confirmacion", "warning"),
            ("Critical", "No desaparece sola", "critical"),
        )
        title, message, level = samples[self.test_notification_index % len(samples)]
        self.test_notification_index += 1
        self.notifications.push(title, message, level=level)
