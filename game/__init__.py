# -*- coding: utf-8 -*-
"""圆环斗场 · game 包：模块化拆分后的公共 API 聚合。

依赖顺序：data → utils → drawing → character(→engine) → world → ui → loops。
"""
from game import runtime, paths  # noqa: F401
from game.data import *          # noqa: F401,F403
from game.utils import *         # noqa: F401,F403
from game.drawing import *       # noqa: F401,F403
from game.character import *     # noqa: F401,F403  内部底部导入 engine
from game.world import *         # noqa: F401,F403
from game.ui import *            # noqa: F401,F403
from game.loops import *         # noqa: F401,F403
