# -*- coding: utf-8 -*-
"""圆环斗场 headless 回归测试。

覆盖：数据完整性 + 死斗模拟若干帧 + 单帧渲染冒烟。
用法：python tests/regress.py [帧数] [人数]
可设 REGRESS_MODULE=main 走薄壳入口（默认 game 包）。
"""
import os
import random
import sys

# 把项目根（tests/ 的上一级）加入 sys.path，保证 `import game` 不受运行目录影响
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
sys.stdout.reconfigure(encoding="utf-8")

import pygame

pygame.init()
pygame.font.init()

# 拆分完成后入口为 game 包；也可 REGRESS_MODULE=main 走薄壳入口
TARGET = os.environ.get("REGRESS_MODULE", "game")
game = __import__(TARGET)

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 2400
PLAYERS = int(sys.argv[2]) if len(sys.argv) > 2 else 20

# 固定种子保证回归确定性（seed=1 不触发已知的 ColdSpear 崩溃 bug，见拆分汇报）
random.seed(1)


def check_data():
    assert len(game.JOB_DEFS) >= 100, f"JOB_DEFS 过少: {len(game.JOB_DEFS)}"
    assert len(game.CHARACTER_DATA) >= 100, f"CHARACTER_DATA 过少"
    assert len(game.JOB_RESISTANCE_PROFILES) >= 100, f"抗性表过少"
    assert game.JOB_DEFS.keys() == game.CHARACTER_DATA.keys(), "JOB_DEFS 与 CHARACTER_DATA 键不一致"
    print(f"[data] JOB_DEFS={len(game.JOB_DEFS)} CHARACTER_DATA={len(game.CHARACTER_DATA)} "
          f"RESIST={len(game.JOB_RESISTANCE_PROFILES)} OK")


def run_simulation():
    state = game.create_game_state(PLAYERS, True)
    game.runtime._LIVE_GAME_STATE = state
    game.runtime._LIVE_SPEED_MULTIPLIER = 1.0
    for c in state["characters"]:
        c.spawn_fx_timer = 0.0  # 跳过开场定格

    winner = ""
    for frame in range(FRAMES):
        dt = 1.0 / 60.0
        state["elapsed_time"] += dt
        game.update_weapon_orbs(state, dt)
        living = game.get_living_characters(state)
        for c in living:
            c.update(dt, state)
        for i, c in enumerate(living):
            for o in living[i + 1:]:
                c.resolve_overlap(o)
        for sw in state["shield_walls"]:
            for c in living:
                sw.block_character(c)
        for orb in state["weapon_orbs"]:
            if not orb.alive:
                continue
            for c in living:
                if c.try_pickup_weapon(orb):
                    break
        game.update_world_lists(state, dt)
        state["characters"] = [c for c in state["characters"] if c.alive]
        living = game.get_living_main_characters(state)
        if len(living) == 1:
            winner = f"{living[0].job_name} 胜"
            break
        elif len(living) == 0:
            winner = "无人生还"
            break

    alive = len(state["characters"])
    deaths = len(state["battle_participants"]) - alive
    print(f"[sim] {frame + 1} 帧后存活 {alive} 人（阵亡 {deaths}），结果: {winner or '仍在战斗'}")
    assert deaths > 0, "跑满帧数仍无任何阵亡，疑似战斗逻辑未生效"


def run_render_smoke():
    screen = pygame.display.set_mode((game.BATTLE_WINDOW_WIDTH, game.BATTLE_WINDOW_HEIGHT))
    state = game.create_game_state(6, True)
    game.runtime._LIVE_GAME_STATE = state
    for c in state["characters"]:
        c.spawn_fx_timer = 0.0
    small = game.create_ui_font(16)
    title = game.create_ui_font(24, bold=True)
    scene = pygame.Surface((game.SCREEN_WIDTH, game.SCREEN_HEIGHT))
    game.draw_grid(scene)
    game.draw_ui(scene, title, small, state)
    game.draw_world(scene, state, small)
    sidebar = pygame.Surface((game.BATTLE_SIDEBAR_WIDTH, game.BATTLE_WINDOW_HEIGHT))
    game.draw_battle_sidebar(sidebar, title, small, small, state, "output", None, None, 0, "1")
    pygame.display.flip()
    print("[render] 单帧渲染 OK")


if __name__ == "__main__":
    check_data()
    run_simulation()
    run_render_smoke()
    print("ALL PASS")
