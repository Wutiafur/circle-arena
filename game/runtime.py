# -*- coding: utf-8 -*-
"""跨模块共享的可变全局状态。

battle_loop 每帧重绑 _LIVE_GAME_STATE / _LIVE_SPEED_MULTIPLIER，
崩溃快照与治疗逻辑读取它们。统一放这里，避免各模块各自持有副本。
"""

_LIVE_GAME_STATE = None
_LIVE_SPEED_MULTIPLIER = 1.0

# 禁用角色表（主菜单"禁用角色"设置，最多 3 个），按 job_name 存放
_DISABLED_ROLE_KEYS = set()
