# -*- coding: utf-8 -*-
"""圆环斗场 · game 包：模块化拆分后的公共 API 聚合。

依赖顺序：data → engine → ui → loops（后者依赖前者，无环）。
"""
from game import runtime, paths  # noqa: F401
from game.data import *          # noqa: F401,F403
from game.engine import *        # noqa: F401,F403
from game.ui import *            # noqa: F401,F403
from game.loops import *         # noqa: F401,F403
