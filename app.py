"""Application orchestration and view navigation."""

import sys

import pygame

from config import DEFAULT_CONFIG, load_config, save_config


W, H = 240, 320
FPS = 30
DEFAULT_AUTO_SWITCH_SECONDS = DEFAULT_CONFIG["auto_switch_seconds"]


PREVIOUS_KEYS = {
    pygame.K_a,
    pygame.K_LEFT,
    pygame.K_PAGEUP,
}

NEXT_KEYS = {
    pygame.K_b,
    pygame.K_RIGHT,
    pygame.K_PAGEDOWN,
}

QUIT_KEYS = {
    pygame.K_ESCAPE,
    pygame.K_q,
}


class UnihikerApp:
    """Small pygame shell that owns the screen and switches between views."""

    def __init__(self, views, settings_view=None, size=(W, H), fps=FPS, auto_switch_seconds=None):
        if not views:
            raise ValueError("At least one view is required")

        self.config = load_config()
        if auto_switch_seconds is not None:
            self.config["auto_switch_seconds"] = auto_switch_seconds

        self.views = list(views)
        self.settings_view = settings_view
        self.size = size
        self.fps = fps
        self.auto_switch_seconds = self.config["auto_switch_seconds"]
        self.auto_switch_elapsed = 0.0
        self.current_index = 0
        self.settings_active = False
        self.pressed_keys = set()
        self.combo_consumed = False
        self.screen = None
        self.clock = None
        self.running = False

    @property
    def current_view(self):
        if self.settings_active:
            return self.settings_view
        return self.views[self.current_index]

    def run(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption("UnihikerSimple")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.running = True

        mounted_views = list(self.views)
        if self.settings_view:
            mounted_views.append(self.settings_view)

        for view in mounted_views:
            view.on_mount(self)

        self.current_view.on_enter()

        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            self._handle_events()
            self._update_auto_switch(dt)
            self.current_view.update(dt)
            self.current_view.draw(self.screen)
            pygame.display.flip()

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

    def toggle_settings(self):
        if not self.settings_view:
            return

        self.current_view.on_exit()
        self.settings_active = not self.settings_active
        self.current_view.on_enter()
        self.reset_auto_switch_timer()

    def _set_view(self, index):
        if self.settings_active:
            self.toggle_settings()

        if index == self.current_index:
            return

        self.current_view.on_exit()
        self.current_index = index
        self.current_view.on_enter()
        self.reset_auto_switch_timer()

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

            if event.type == pygame.KEYDOWN:
                if event.key in QUIT_KEYS:
                    self.stop()
                    continue

                if event.key in PREVIOUS_KEYS or event.key in NEXT_KEYS:
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

            self.current_view.handle_event(event)
