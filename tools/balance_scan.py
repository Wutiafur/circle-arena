# -*- coding: utf-8 -*-
"""圆环斗场 · headless 平衡扫描器（方案 A1）。

批量跑死斗模拟，聚合每个角色的出场 / 胜场 / 击杀 / 输出 / 承伤，
产出 _balance_report.json 与 _balance_report.txt，用于数据驱动平衡。

用法：
    python tools/balance_scan.py [场数] [每场最大帧数]
默认 50 场 × 6000 帧（100 秒游戏时间）。

说明：
    - 死斗战 20 人混战，单场只有一个胜者，故「胜率」天然稀疏；
      本扫描器以 击杀/输出/承伤/出场 为主指标，比人工对战的 win_rate_stats.json 样本大得多。
    - 固定种子保证可复现；不渲染画面，只跑逻辑。
"""
import os
import sys
import json
import time
import random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
sys.stdout.reconfigure(encoding="utf-8")

import pygame

pygame.init()
pygame.font.init()

import game

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_battle(seed, max_frames):
    """跑一场 20 人死斗，返回 (角色引用表, 胜者 job_name 或 None)。"""
    random.seed(seed)
    state = game.create_game_state(20, True)
    game.runtime._LIVE_GAME_STATE = state
    for c in state["characters"]:
        c.spawn_fx_timer = 0.0  # 跳过登场定格

    all_chars = {c.id: c for c in state["characters"]}  # 保持引用，死后也能读统计
    winner = None
    for _ in range(max_frames):
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

        lm = game.get_living_main_characters(state)
        if len(lm) == 1:
            winner = lm[0].job_name
            break
        if len(lm) == 0:
            break
    return all_chars, winner


def main():
    battles = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    max_frames = int(sys.argv[2]) if len(sys.argv) > 2 else 6000

    agg = defaultdict(lambda: {"matches": 0, "wins": 0, "kills": 0, "damage": 0.0, "taken": 0.0})
    t0 = time.time()
    finished = 0

    for seed in range(battles):
        all_chars, winner = run_battle(seed, max_frames)
        if winner is not None:
            finished += 1
            agg[winner]["wins"] += 1
        for c in all_chars.values():
            d = agg[c.job_name]
            d["matches"] += 1
            d["kills"] += int(getattr(c, "kill_count", 0))
            d["damage"] += float(getattr(c, "damageDealt", 0.0))
            d["taken"] += float(getattr(c, "damageTaken", 0.0))
        if (seed + 1) % 10 == 0:
            print(f"  {seed + 1}/{battles} 场，已用 {time.time() - t0:.1f}s", flush=True)

    # 转成排序好的列表
    rows = []
    for job_name, d in agg.items():
        m = d["matches"]
        rows.append({
            "job": job_name,
            "matches": m,
            "wins": d["wins"],
            "kills": d["kills"],
            "avg_kills": round(d["kills"] / m, 2) if m else 0,
            "avg_damage": round(d["damage"] / m, 1) if m else 0,
            "avg_taken": round(d["taken"] / m, 1) if m else 0,
        })

    report = {
        "battles": battles,
        "finished": finished,
        "max_frames": max_frames,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rows": sorted(rows, key=lambda r: (-r["avg_kills"], -r["avg_damage"], -r["wins"])),
    }

    json_path = os.path.join(ROOT, "_balance_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 人类可读汇总
    txt_lines = [
        f"圆环斗场平衡扫描报告（{battles} 场 × 20 人死斗，完成 {finished} 场）",
        f"生成时间：{report['generated_at']}",
        "排序：场均击杀 ↓ 场均伤害 ↓ 胜场 ↓",
        "",
        f"{'角色':<32}{'出场':>5}{'胜场':>5}{'击杀':>6}{'场均杀':>8}{'场均伤':>9}{'场均承伤':>9}",
    ]
    for r in report["rows"]:
        txt_lines.append(
            f"{r['job']:<32}{r['matches']:>5}{r['wins']:>5}{r['kills']:>6}"
            f"{r['avg_kills']:>8}{r['avg_damage']:>9}{r['avg_taken']:>9}"
        )
    txt_path = os.path.join(ROOT, "_balance_report.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"\n完成：{battles} 场（分胜负 {finished}），总耗时 {time.time() - t0:.1f}s")
    print(f"报告已写入：{json_path} 与 {txt_path}")


if __name__ == "__main__":
    main()
