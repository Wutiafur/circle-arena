# -*- coding: utf-8 -*-
"""项目根路径锚点。

main.py 里多处用 Path(__file__).resolve().parent 定位项目根；
拆到 game/ 子包后 __file__ 指向 game/，会指错。统一用 PROJECT_ROOT 修正。
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
