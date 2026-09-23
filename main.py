# -*- coding: utf-8 -*-
"""圆环斗场 · 入口薄壳。

全部逻辑已拆分到 game/ 包（data/engine/ui/loops + runtime/paths）。
此文件仅聚合导入并提供 main() 入口，保持 `python main.py` 与 `import main` 兼容。
"""
import os
import sys

os.environ.setdefault("SDL_VIDEO_HIGHDPI", "1")

import pygame

from game import *  # noqa: F401,F403

if __name__ == "__main__":
    sys.excepthook = handle_unhandled_exception
    try:
        main()
    finally:
        pygame.quit()
