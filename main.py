#!/usr/bin/env python3
"""Entry point for the UniHiker multi-view pygame app."""

from app import UnihikerApp
from views.clock import ClockView
from views.homeload import HomeLoadView
from views.investment import InvestmentView
from views.quote import QuoteView
from views.settings import SettingsView


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
