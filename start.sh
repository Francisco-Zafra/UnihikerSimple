#!/bin/bash
cd /root/UnihikerSimple || exit 1

export DISPLAY=:0
export SDL_VIDEODRIVER=x11
export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

sleep 20

uv sync
uv add pygame
uv run ./main.py >> /root/UnihikerSimple/app.log 2>&1
