#!/usr/bin/env python3
"""Entry point for the UniHiker multi-view pygame app."""

from unihiker.app import UnihikerApp
from unihiker.views.clock import ClockView
from unihiker.views.homeload import HomeLoadView
from unihiker.views.investment import InvestmentView
from unihiker.views.quote import QuoteView
from unihiker.views.settings import SettingsView


def main():
    app = UnihikerApp(
        views=[
            HomeLoadView(),
            ClockView(),
            InvestmentView(),
            QuoteView(),
        ],
        settings_view=SettingsView(),
    )
    app.run()


if __name__ == "__main__":
    main()
