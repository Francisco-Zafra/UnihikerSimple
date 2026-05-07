"""Base class for pygame views."""


class View:
    name = "view"

    def __init__(self):
        self.app = None

    def on_mount(self, app):
        self.app = app

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def on_config_updated(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        raise NotImplementedError
