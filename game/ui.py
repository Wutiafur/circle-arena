# -*- coding: utf-8 -*-
"""界面绘制层：主菜单 / 图鉴 / 效果 / 胜率 / 结算 / 侧边栏等纯绘制函数。"""
import math
import random

import pygame

from game.data import *
from game.engine import *
from game import runtime

def draw_menu(screen, title_font, subtitle_font, button_font, player_count, hover_name, disable_timed_weapon_drops, disabled_count=0):
    screen.fill(BACKGROUND_COLOR)

    # 背景装饰：竞技场网格 + 中央圆环光环
    for gx in range(0, SCREEN_WIDTH, 40):
        pygame.draw.line(screen, (22, 28, 36), (gx, 0), (gx, SCREEN_HEIGHT), 1)
    for gy in range(0, SCREEN_HEIGHT, 40):
        pygame.draw.line(screen, (22, 28, 36), (0, gy), (SCREEN_WIDTH, gy), 1)
    for rx in range(0, SCREEN_WIDTH, 160):
        pygame.draw.line(screen, GRID_COLOR, (rx, 0), (rx, SCREEN_HEIGHT), 1)
    for ry in range(0, SCREEN_HEIGHT, 160):
        pygame.draw.line(screen, GRID_COLOR, (0, ry), (SCREEN_WIDTH, ry), 1)
    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow, (58, 92, 168, 30), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), 150, 3)
    pygame.draw.circle(glow, (58, 92, 168, 20), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), 192, 2)
    pygame.draw.circle(glow, (96, 84, 176, 14), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), 234, 2)
    screen.blit(glow, (0, 0))

    # 标题面板（两侧同心圆装饰）
    title_rect = pygame.Rect(144, 58, 512, 92)
    draw_panel(screen, title_rect, (16, 22, 30), accent_color=MENU_ACCENT, radius=18, shadow_offset=(4, 5))
    for tx in (162, 638):
        pygame.draw.circle(screen, (110, 170, 255), (tx, 104), 12, 2)
        pygame.draw.circle(screen, (110, 170, 255), (tx, 104), 6, 2)
    title = title_font.render("圆环斗场", True, TEXT_COLOR)
    subtitle = subtitle_font.render("自动对战竞技场 · 百余名角色混战", True, (180, 192, 208))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 92)))
    screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 128)))

    panel_rect = pygame.Rect(174, 176, 452, 290)
    decrement_rect = pygame.Rect(232, 258, 60, 60)
    increment_rect = pygame.Rect(508, 258, 60, 60)
    start_rect = pygame.Rect(244, 476, 312, 68)
    pokedex_rect = pygame.Rect(244, 556, 150, 50)
    duel_rect = pygame.Rect(402, 556, 150, 50)
    effects_rect = pygame.Rect(244, 614, 150, 50)
    ban_rect = pygame.Rect(402, 614, 150, 50)
    win_rate_rect = pygame.Rect(244, 672, 312, 46)
    settings_rect = pygame.Rect(558, 352, 118, 34)
    weapon_drops_rect = pygame.Rect(244, 356, 300, 28)
    weapon_checkbox_rect = pygame.Rect(244, 356, 20, 20)

    draw_panel(screen, panel_rect, MENU_PANEL, accent_color=(90, 122, 176), radius=18)

    label = button_font.render(f"参赛人数: {player_count}", True, TEXT_COLOR)
    label_rect = label.get_rect(center=(SCREEN_WIDTH // 2, 238))
    screen.blit(label, label_rect)

    minus_color = MENU_BUTTON_HOVER if hover_name == "minus" else MENU_BUTTON
    plus_color = MENU_BUTTON_HOVER if hover_name == "plus" else MENU_BUTTON
    start_color = MENU_BUTTON_HOVER if hover_name == "start" else MENU_ACCENT
    pokedex_color = MENU_BUTTON_HOVER if hover_name == "pokedex" else MENU_BUTTON
    duel_color = MENU_BUTTON_HOVER if hover_name == "duel" else MENU_BUTTON
    effects_color = MENU_BUTTON_HOVER if hover_name == "effects" else MENU_BUTTON
    ban_color = MENU_BUTTON_HOVER if hover_name == "ban" else MENU_BUTTON
    win_rate_color = MENU_BUTTON_HOVER if hover_name == "win_rate" else MENU_BUTTON
    settings_color = MENU_BUTTON_HOVER if hover_name == "settings" else MENU_BUTTON

    if player_count <= MIN_CHARACTERS:
        minus_color = MENU_BUTTON_DISABLED
    if player_count >= MAX_CHARACTERS:
        plus_color = MENU_BUTTON_DISABLED

    draw_panel(screen, decrement_rect, minus_color, radius=12, shadow_offset=(2, 2))
    draw_panel(screen, increment_rect, plus_color, radius=12, shadow_offset=(2, 2))
    draw_panel(screen, start_rect, start_color, radius=14, shadow_offset=(3, 4), accent_color=(255, 214, 120))
    draw_panel(screen, pokedex_rect, pokedex_color, radius=12, shadow_offset=(2, 3))
    draw_panel(screen, duel_rect, duel_color, radius=12, shadow_offset=(2, 3))
    draw_panel(screen, settings_rect, settings_color, radius=8, shadow_offset=(1, 1))
    draw_panel(screen, effects_rect, effects_color, radius=12, shadow_offset=(2, 3))
    draw_panel(screen, ban_rect, ban_color, radius=12, shadow_offset=(2, 3))
    draw_panel(screen, win_rate_rect, win_rate_color, radius=12, shadow_offset=(2, 3))

    # 开始按钮 ▶ 图标 + 文案
    start_text = button_font.render("死斗战", True, TEXT_COLOR)
    tri = [(start_rect.left + 24, start_rect.centery - 9), (start_rect.left + 24, start_rect.centery + 9), (start_rect.left + 36, start_rect.centery)]
    pygame.draw.polygon(screen, (255, 214, 120), tri)
    screen.blit(start_text, start_text.get_rect(center=(start_rect.centerx + 6, start_rect.centery)))

    # 图鉴 / 效果 / 胜率 按钮：左侧彩色圆点
    icon_dots = (
        (pokedex_rect, (110, 170, 255)),
        (duel_rect, (255, 158, 96)),
        (effects_rect, (142, 226, 188)),
        (ban_rect, (232, 96, 96)),
        (win_rate_rect, (255, 214, 120)),
    )
    for rect, dot_color in icon_dots:
        pygame.draw.circle(screen, dot_color, (rect.left + 18, rect.centery), 6)
        pygame.draw.circle(screen, BORDER_COLOR, (rect.left + 18, rect.centery), 6, 1)

    minus_text = title_font.render("-", True, TEXT_COLOR)
    plus_text = title_font.render("+", True, TEXT_COLOR)
    pokedex_text = button_font.render(POKEDEX_UI_TEXT["menu_button"], True, TEXT_COLOR)
    duel_text = subtitle_font.render("擂台模式", True, TEXT_COLOR)
    effects_text = subtitle_font.render(EFFECT_UI_TEXT["menu_button"], True, TEXT_COLOR)
    ban_text = subtitle_font.render(f"禁用角色 ({disabled_count}/3)", True, TEXT_COLOR)
    win_rate_text = subtitle_font.render("胜率", True, TEXT_COLOR)
    screen.blit(minus_text, minus_text.get_rect(center=decrement_rect.center))
    screen.blit(plus_text, plus_text.get_rect(center=increment_rect.center))
    screen.blit(pokedex_text, pokedex_text.get_rect(center=(pokedex_rect.centerx + 8, pokedex_rect.centery)))
    screen.blit(duel_text, duel_text.get_rect(center=(duel_rect.centerx + 8, duel_rect.centery)))
    screen.blit(effects_text, effects_text.get_rect(center=(effects_rect.centerx + 8, effects_rect.centery)))
    screen.blit(ban_text, ban_text.get_rect(center=(ban_rect.centerx + 8, ban_rect.centery)))
    screen.blit(win_rate_text, win_rate_text.get_rect(center=(win_rate_rect.centerx + 8, win_rate_rect.centery)))

    hint = subtitle_font.render(f"最少 {MIN_CHARACTERS} 人，最多 {MAX_CHARACTERS} 人", True, (150, 164, 180))
    screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 430)))

    row_color = TEXT_COLOR if hover_name == "weapon_drops" else (180, 192, 208)
    row_text = subtitle_font.render("关闭定时武器掉落", True, row_color)
    screen.blit(row_text, (weapon_drops_rect.left + 30, weapon_drops_rect.top - 1))

    checkbox_fill = MENU_BUTTON_HOVER if hover_name == "weapon_drops" else MENU_BUTTON
    if disable_timed_weapon_drops:
        checkbox_fill = MENU_ACCENT
    pygame.draw.rect(screen, checkbox_fill, weapon_checkbox_rect, border_radius=4)
    pygame.draw.rect(screen, BORDER_COLOR, weapon_checkbox_rect, 2, border_radius=4)
    if disable_timed_weapon_drops:
        pygame.draw.line(screen, TEXT_COLOR, (weapon_checkbox_rect.left + 4, weapon_checkbox_rect.centery), (weapon_checkbox_rect.centerx - 1, weapon_checkbox_rect.bottom - 5), 2)
        pygame.draw.line(screen, TEXT_COLOR, (weapon_checkbox_rect.centerx - 1, weapon_checkbox_rect.bottom - 5), (weapon_checkbox_rect.right - 4, weapon_checkbox_rect.top + 4), 2)

    # 设置按钮（齿轮图标 + 文字）
    settings_color_on = MENU_ACCENT if GAME_SETTINGS.get("fullscreen") else settings_color
    pygame.draw.circle(screen, (120, 160, 210), (settings_rect.left + 20, settings_rect.centery), 6, 2)
    pygame.draw.circle(screen, (120, 160, 210), (settings_rect.left + 20, settings_rect.centery), 2, 1)
    settings_text = subtitle_font.render("设置", True, TEXT_COLOR)
    screen.blit(settings_text, (settings_rect.left + 34, settings_rect.centery - settings_text.get_height() // 2))

    # 底部信息条
    version_text = subtitle_font.render(f"已收录 {len(JOB_DEFS)} 名角色 · 圆环斗场 v0.9 · Enter 进入死斗战", True, (150, 164, 180))
    screen.blit(version_text, version_text.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10)))

    return {
        "minus": decrement_rect,
        "plus": increment_rect,
        "start": start_rect,
        "pokedex": pokedex_rect,
        "duel": duel_rect,
        "effects": effects_rect,
        "ban": ban_rect,
        "win_rate": win_rate_rect,
        "settings": settings_rect,
        "weapon_drops": weapon_drops_rect,
    }


def get_menu_button_rects():
    return {
        "minus": pygame.Rect(232, 258, 60, 60),
        "plus": pygame.Rect(508, 258, 60, 60),
        "start": pygame.Rect(244, 476, 312, 68),
        "pokedex": pygame.Rect(244, 556, 150, 50),
        "duel": pygame.Rect(402, 556, 150, 50),
        "effects": pygame.Rect(244, 614, 150, 50),
        "ban": pygame.Rect(402, 614, 150, 50),
        "win_rate": pygame.Rect(244, 672, 312, 46),
        "settings": pygame.Rect(558, 352, 118, 34),
        "weapon_drops": pygame.Rect(244, 356, 300, 28),
    }


def draw_battle_end_button(surface, button_font, hover_active):
    button_rect = pygame.Rect(250, 610, 300, 74)
    button_color = MENU_BUTTON_HOVER if hover_active else MENU_BUTTON
    draw_panel(surface, button_rect, button_color, radius=14, shadow_offset=(3, 4))
    button_text = button_font.render("Back To Menu", True, TEXT_COLOR)
    surface.blit(button_text, button_text.get_rect(center=button_rect.center))
    return button_rect


def draw_result_summary(surface, title_font, body_font, game_state, panel_rect, close_rect):
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((6, 10, 16, 150))
    surface.blit(overlay, (0, 0))

    draw_panel(surface, panel_rect, MENU_PANEL, accent_color=(255, 214, 120), radius=18, shadow_offset=(4, 6))

    winner = game_state.get("winner_character")
    title = title_font.render("本局结算", True, TEXT_COLOR)
    surface.blit(title, title.get_rect(center=(panel_rect.centerx, panel_rect.top + 28)))

    participants = list(game_state.get("battle_participants", game_state.get("characters", [])))
    alive_winner = winner if winner is not None and winner.alive else (next((c for c in participants if c.alive), None))

    # 冠军卡
    if alive_winner is not None:
        champ_rect = pygame.Rect(panel_rect.left + 24, panel_rect.top + 52, panel_rect.width - 48, 58)
        draw_panel(surface, champ_rect, (30, 38, 50), accent_color=(255, 214, 120), radius=10, shadow_offset=(2, 2))
        draw_shape_icon(surface, alive_winner.shape, alive_winner.color, (champ_rect.left + 32, champ_rect.centery), 20)
        name = body_font.render(f"冠军：{get_character_display_name(alive_winner)}", True, TEXT_COLOR)
        surface.blit(name, (champ_rect.left + 66, champ_rect.top + 6))
        stats_line = body_font.render(
            f"伤害 {int(alive_winner.damageDealt)}    承伤 {int(alive_winner.damageTaken)}    击杀 {int(getattr(alive_winner, 'kill_count', 0))}",
            True,
            (150, 214, 170),
        )
        surface.blit(stats_line, (champ_rect.left + 66, champ_rect.top + 32))

    # Top 3 排行
    cols = [
        ("伤害榜", "damageDealt", (220, 72, 72)),
        ("承伤榜", "damageTaken", (84, 150, 255)),
        ("击杀榜", "kill_count", (255, 214, 120)),
    ]
    for col_index, (label, attr, color) in enumerate(cols):
        col_rect = pygame.Rect(panel_rect.left + 18 + col_index * 178, panel_rect.top + 122, 166, 158)
        draw_panel(surface, col_rect, (24, 30, 40), border_color=(60, 70, 84), radius=10, shadow_offset=(1, 2))
        header = body_font.render(label, True, color)
        surface.blit(header, header.get_rect(center=(col_rect.centerx, col_rect.top + 18)))
        ranked = sorted(participants, key=lambda character: -float(getattr(character, attr, 0.0) or 0.0))
        for rank, character in enumerate(ranked[:3]):
            if character is None:
                continue
            item_y = col_rect.top + 42 + rank * 38
            rank_color = (255, 214, 120) if rank == 0 else (200, 208, 220)
            rank_text = body_font.render(f"{rank + 1}.", True, rank_color)
            surface.blit(rank_text, (col_rect.left + 10, item_y))
            name_text = body_font.render(truncate_text(get_character_display_name(character), body_font, 74), True, TEXT_COLOR)
            surface.blit(name_text, (col_rect.left + 40, item_y))
            value_text = body_font.render(str(int(round(float(getattr(character, attr, 0.0))))), True, color)
            surface.blit(value_text, value_text.get_rect(right=col_rect.right - 10, centery=item_y + 10))
            draw_shape_icon(surface, character.shape, character.color, (col_rect.left + 26, item_y + 10), 8)

    # MVP
    best = max(participants, key=lambda character: float(getattr(character, "damageDealt", 0.0) or 0.0), default=None)
    if best is not None:
        mvp_rect = pygame.Rect(panel_rect.left + 24, panel_rect.top + 292, panel_rect.width - 48, 40)
        draw_panel(surface, mvp_rect, (30, 36, 44), border_color=(74, 82, 92), radius=8, shadow_offset=(1, 1))
        mvp_text = body_font.render(f"MVP：{get_character_display_name(best)}（最高输出 {int(best.damageDealt)}）", True, (150, 214, 170))
        surface.blit(mvp_text, mvp_text.get_rect(center=(panel_rect.centerx, panel_rect.centery - 18)))

    # 押注结果
    bet_job = game_state.get("bet_job")
    if bet_job:
        bet_rect = pygame.Rect(panel_rect.left + 24, panel_rect.top + 340, panel_rect.width - 48, 38)
        bet_winner = alive_winner is not None and alive_winner.job_name == bet_job
        fill = (36, 52, 44) if bet_winner else (46, 40, 34)
        border = (120, 210, 160) if bet_winner else (190, 150, 90)
        draw_panel(surface, bet_rect, fill, border_color=border, radius=8, shadow_offset=(1, 1))
        if bet_winner:
            bet_text = body_font.render(f"🏆 押注命中！{get_character_display_name(alive_winner)} 如你所料", True, (255, 214, 120))
        else:
            bet_name = get_pokedex_data(bet_job).get("display_name", bet_job)
            bet_text = body_font.render(f"押注落空：你押的是 {bet_name}", True, (200, 208, 220))
        surface.blit(bet_text, bet_text.get_rect(center=bet_rect.center))

    draw_panel(surface, close_rect, MENU_BUTTON_HOVER, radius=10, shadow_offset=(2, 2))
    close_text = body_font.render("关闭", True, TEXT_COLOR)
    surface.blit(close_text, close_text.get_rect(center=close_rect.center))


def draw_pause_menu(surface, title_font, subtitle_font, button_font, hover_name):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 10, 16, 180))
    surface.blit(overlay, (0, 0))

    panel_rect = pygame.Rect(200, 220, 400, 280)
    resume_rect = pygame.Rect(250, 320, 300, 68)
    menu_rect = pygame.Rect(250, 404, 300, 68)
    draw_panel(surface, panel_rect, MENU_PANEL, accent_color=(100, 130, 178), radius=18)

    title = title_font.render("Game Paused", True, TEXT_COLOR)
    subtitle = subtitle_font.render("Press Esc to resume or choose an option", True, (180, 192, 208))
    surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 266)))
    surface.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 294)))

    resume_color = MENU_BUTTON_HOVER if hover_name == "resume" else MENU_ACCENT
    menu_color = MENU_BUTTON_HOVER if hover_name == "menu" else MENU_BUTTON
    draw_panel(surface, resume_rect, resume_color, radius=14, shadow_offset=(2, 3))
    draw_panel(surface, menu_rect, menu_color, radius=14, shadow_offset=(2, 3))

    resume_text = button_font.render("Resume Game", True, TEXT_COLOR)
    menu_text = button_font.render("Back To Menu", True, TEXT_COLOR)
    surface.blit(resume_text, resume_text.get_rect(center=resume_rect.center))
    surface.blit(menu_text, menu_text.get_rect(center=menu_rect.center))
    return {"resume": resume_rect, "menu": menu_rect}




def draw_pokedex(screen, title_font, subtitle_font, body_font, button_font, selected_name, list_scroll_offset, detail_scroll_offset, hover_name, search_query="", stats=None, ordered_names=None, cached_detail=None):
    screen.fill(BACKGROUND_COLOR)

    title = title_font.render(POKEDEX_UI_TEXT["title"], True, TEXT_COLOR)
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 48)))

    progress_text = subtitle_font.render(f"已收录 {len(CHARACTER_DATA)} / {len(JOB_DEFS)}", True, (150, 164, 180))
    screen.blit(progress_text, progress_text.get_rect(midtop=(SCREEN_WIDTH // 2, 86)))

    ordered = ordered_names if ordered_names is not None else get_pokedex_ordered_names()
    filtered = filter_pokedex_names(ordered, search_query)
    entries = pokedex_layout_entries(filtered)

    search_rect = pygame.Rect(36, 112, 240, 34)
    list_panel = pygame.Rect(36, 154, 240, 556)
    detail_panel = pygame.Rect(300, 104, 464, 668)
    return_rect = pygame.Rect(36, 722, 220, 40)
    draw_panel(screen, search_rect, MENU_PANEL, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
    draw_panel(screen, list_panel, MENU_PANEL, radius=16)
    draw_panel(screen, detail_panel, (18, 24, 32), accent_color=(84, 128, 184), radius=16)
    draw_panel(screen, return_rect, MENU_BUTTON_HOVER if hover_name == "return" else MENU_BUTTON, radius=12, shadow_offset=(2, 2))

    search_text = search_query if search_query else "搜索角色名…"
    search_color = TEXT_COLOR if search_query else (110, 124, 140)
    search_surface = body_font.render(search_text, True, search_color)
    screen.blit(search_surface, (search_rect.left + 12, search_rect.centery - search_surface.get_height() // 2))

    return_text = body_font.render(POKEDEX_UI_TEXT["return"], True, TEXT_COLOR)
    screen.blit(return_text, return_text.get_rect(center=return_rect.center))

    row_h = 44
    header_h = 22
    list_top = list_panel.top + 12
    item_rects = {}
    previous_clip = screen.get_clip()
    screen.set_clip(list_panel)
    y = list_top - list_scroll_offset
    for entry_type, value in entries:
        if entry_type == "header":
            if y < list_panel.top - 10 or y + header_h > list_panel.bottom - 8:
                y += header_h
                continue
            header_surface = body_font.render(value, True, (130, 142, 158))
            screen.blit(header_surface, (list_panel.left + 14, y))
            y += header_h
            continue
        name = value
        item_rect = pygame.Rect(list_panel.left + 10, y, list_panel.width - 20, row_h - 6)
        if item_rect.bottom < list_panel.top + 6 or item_rect.top > list_panel.bottom - 6:
            y += row_h
            continue
        item_rects[name] = item_rect
        if name == selected_name:
            color = MENU_ACCENT
        elif hover_name == name:
            color = MENU_BUTTON_HOVER
        else:
            color = MENU_BUTTON
        draw_panel(screen, item_rect, color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
        localized = get_pokedex_data(name)
        num = get_role_display_number(name)
        color_dot = (item_rect.left + 16, item_rect.centery)
        pygame.draw.circle(screen, localized["color"], color_dot, 6)
        pygame.draw.circle(screen, BORDER_COLOR, color_dot, 6, 1)
        draw_shape_icon(screen, localized["shape"], localized["color"], (item_rect.left + 34, item_rect.centery), 8, True)
        if num is not None:
            num_surface = body_font.render(f"#{num:02d}", True, (140, 152, 168))
            screen.blit(num_surface, (item_rect.left + 48, item_rect.centery - num_surface.get_height() // 2 + 1))
        name_text = body_font.render(localized["display_name"], True, TEXT_COLOR)
        screen.blit(name_text, (item_rect.left + 90, item_rect.centery - name_text.get_height() // 2))
        tag = get_role_attack_tag(name, localized)
        tag_color = (196, 208, 224)
        if tag.endswith("混"):
            tag_color = (255, 214, 120)
        elif tag.endswith("法"):
            tag_color = (255, 150, 220)
        elif tag.endswith("物"):
            tag_color = (255, 130, 130)
        elif tag.endswith("真"):
            tag_color = (240, 240, 240)
        tag_surface = body_font.render(tag, True, tag_color)
        screen.blit(tag_surface, tag_surface.get_rect(right=item_rect.right - 10, centery=item_rect.centery))
        y += row_h

    screen.set_clip(previous_clip)
    content_h = sum(header_h if t == "header" else row_h for t, _ in entries)
    visible_h = list_panel.height - 24
    list_max_scroll = max(0, content_h - visible_h)
    if list_max_scroll > 0:
        track = pygame.Rect(list_panel.right - 8, list_panel.top + 8, 4, list_panel.height - 16)
        thumb_h = max(16, int(visible_h * visible_h / content_h))
        thumb_y = track.top + int((track.height - thumb_h) * list_scroll_offset / list_max_scroll)
        pygame.draw.rect(screen, (60, 72, 88), track, border_radius=2)
        pygame.draw.rect(screen, (130, 148, 172), pygame.Rect(track.left, thumb_y, 4, thumb_h), border_radius=2)

    if cached_detail is not None:
        detail_surface, detail_viewport, detail_max_scroll = cached_detail
    else:
        data = get_pokedex_data(selected_name)
        detail_surface, detail_viewport, detail_max_scroll = build_pokedex_detail_surface(detail_panel, data, subtitle_font, body_font, stats=stats)
    clamped_detail_scroll = int(clamp(detail_scroll_offset, 0, detail_max_scroll))
    screen.blit(
        detail_surface,
        detail_viewport,
        area=pygame.Rect(0, clamped_detail_scroll, detail_viewport.width, detail_viewport.height),
    )
    if detail_max_scroll > 0:
        track = pygame.Rect(detail_panel.right - 8, detail_panel.top + 8, 4, detail_panel.height - 16)
        thumb_h = max(16, int(detail_viewport.height * detail_viewport.height / (detail_viewport.height + detail_max_scroll)))
        thumb_y = track.top + int((track.height - thumb_h) * clamped_detail_scroll / max(1, detail_max_scroll))
        pygame.draw.rect(screen, (60, 72, 88), track, border_radius=2)
        pygame.draw.rect(screen, (130, 148, 172), pygame.Rect(track.left, thumb_y, 4, thumb_h), border_radius=2)

    if search_query:
        count_text = body_font.render(f"{len(filtered)} 条结果", True, (140, 152, 168))
        screen.blit(count_text, count_text.get_rect(bottomright=(list_panel.right - 12, list_panel.bottom - 10)))

    return return_rect, item_rects, list_panel, detail_panel, row_h, detail_max_scroll


def draw_effectdex(screen, title_font, subtitle_font, body_font, button_font, selected_name, list_scroll_offset, detail_scroll_offset, hover_name):
    screen.fill(BACKGROUND_COLOR)

    title = title_font.render(EFFECT_UI_TEXT["title"], True, TEXT_COLOR)
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 54)))

    list_panel = pygame.Rect(36, 104, 240, 620)
    detail_panel = pygame.Rect(300, 104, 464, 620)
    return_rect = pygame.Rect(36, 734, 220, 40)
    draw_panel(screen, list_panel, MENU_PANEL, radius=16)
    draw_panel(screen, detail_panel, (18, 24, 32), accent_color=(84, 128, 184), radius=16)
    draw_panel(screen, return_rect, MENU_BUTTON_HOVER if hover_name == "return" else MENU_BUTTON, radius=12, shadow_offset=(2, 2))

    return_text = body_font.render(EFFECT_UI_TEXT["return"], True, TEXT_COLOR)
    screen.blit(return_text, return_text.get_rect(center=return_rect.center))

    item_height = 52
    list_top = list_panel.top + 18
    visible_width = list_panel.width - 24
    item_rects = {}
    keys = list(EFFECT_DATA.keys())
    for index, key in enumerate(keys):
        y = list_top + index * item_height - list_scroll_offset
        item_rect = pygame.Rect(list_panel.left + 12, y, visible_width, item_height - 6)
        item_rects[key] = item_rect
        if item_rect.bottom < list_panel.top + 10 or item_rect.top > list_panel.bottom - 10:
            continue
        effect = get_effect_data(key)
        if key == selected_name:
            color = MENU_ACCENT
        elif hover_name == key:
            color = MENU_BUTTON_HOVER
        else:
            color = MENU_BUTTON
        draw_panel(screen, item_rect, color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
        dot_center = (item_rect.left + 16, item_rect.centery)
        pygame.draw.circle(screen, effect["category_color"], dot_center, 6)
        pygame.draw.circle(screen, BORDER_COLOR, dot_center, 6, 1)
        name_text = body_font.render(effect["display_name"], True, TEXT_COLOR)
        screen.blit(name_text, (item_rect.left + 30, item_rect.centery - name_text.get_height() // 2))

    data = get_effect_data(selected_name)
    detail_surface, detail_viewport, detail_max_scroll = build_effect_detail_surface(detail_panel, data, subtitle_font, body_font)
    clamped_detail_scroll = int(clamp(detail_scroll_offset, 0, detail_max_scroll))
    screen.blit(
        detail_surface,
        detail_viewport,
        area=pygame.Rect(0, clamped_detail_scroll, detail_viewport.width, detail_viewport.height),
    )

    return return_rect, item_rects, list_panel, detail_panel, item_height, detail_max_scroll


def draw_win_rate_screen(screen, title_font, subtitle_font, body_font, button_font, hover_name, scroll_offset, stats):
    screen.fill(BACKGROUND_COLOR)

    title = title_font.render("胜率", True, TEXT_COLOR)
    subtitle = subtitle_font.render("统计每个角色的场次、获胜次数与胜率", True, (180, 192, 208))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 52)))
    screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 84)))

    top_three_jobs = set(get_top_three_jobs(stats, min_matches=3))

    panel_rect = pygame.Rect(36, 116, 728, 608)
    return_rect = pygame.Rect(36, 734, 220, 40)
    draw_panel(screen, panel_rect, MENU_PANEL, accent_color=(84, 128, 184), radius=16)
    draw_panel(screen, return_rect, MENU_BUTTON_HOVER if hover_name == "return" else MENU_BUTTON, radius=12, shadow_offset=(2, 2))

    return_text = body_font.render("返回开始界面", True, TEXT_COLOR)
    screen.blit(return_text, return_text.get_rect(center=return_rect.center))

    header_y = panel_rect.top + 18
    columns = {
        "name": panel_rect.left + 26,
        "matches": panel_rect.left + 390,
        "wins": panel_rect.left + 505,
        "rate": panel_rect.left + 620,
    }
    header_color = (168, 184, 206)
    screen.blit(subtitle_font.render("角色", True, header_color), (columns["name"], header_y))
    screen.blit(subtitle_font.render("场次", True, header_color), (columns["matches"], header_y))
    screen.blit(subtitle_font.render("获胜", True, header_color), (columns["wins"], header_y))
    screen.blit(subtitle_font.render("胜率", True, header_color), (columns["rate"], header_y))
    pygame.draw.line(screen, BORDER_COLOR, (panel_rect.left + 16, header_y + 28), (panel_rect.right - 16, header_y + 28), 1)

    row_height = 40
    list_top = header_y + 40
    visible_rows = max(1, (panel_rect.height - 72) // row_height)
    rows = build_win_rate_rows(body_font, stats)
    max_scroll = max(0, len(rows) - visible_rows)
    scroll_offset = int(clamp(scroll_offset, 0, max_scroll))

    for index, row in enumerate(rows[scroll_offset : scroll_offset + visible_rows]):
        row_y = list_top + index * row_height
        row_rect = pygame.Rect(panel_rect.left + 14, row_y, panel_rect.width - 28, row_height - 4)
        fill = (26, 32, 42) if index % 2 == 0 else (22, 28, 36)
        draw_panel(screen, row_rect, fill, border_color=(46, 52, 64), radius=10, shadow_offset=(1, 1))

        is_top_three = row["job_name"] in top_three_jobs
        icon_center = (row_rect.left + 22, row_rect.centery)
        draw_shape_icon(screen, row["shape"], row["color"], icon_center, 9)
        if is_top_three:
            crown_points = [
                (row_rect.left + 6, row_rect.top + 8),
                (row_rect.left + 9, row_rect.top + 15),
                (row_rect.left + 12, row_rect.top + 9),
                (row_rect.left + 15, row_rect.top + 16),
                (row_rect.left + 18, row_rect.top + 9),
                (row_rect.left + 20, row_rect.top + 14),
            ]
            pygame.draw.polygon(screen, (255, 208, 54), crown_points)
        name_text = truncate_text(row["display_name"], body_font, 290)
        name_color = (255, 214, 120) if is_top_three else TEXT_COLOR
        screen.blit(body_font.render(name_text, True, name_color), (row_rect.left + 34, row_rect.top + 8))
        screen.blit(body_font.render(str(row["matches"]), True, TEXT_COLOR), (columns["matches"], row_rect.top + 8))
        screen.blit(body_font.render(str(row["wins"]), True, TEXT_COLOR), (columns["wins"], row_rect.top + 8))
        rate_text = f"{row['win_rate']:.1f}%"
        rate_color = (255, 208, 54) if is_top_three else (MENU_ACCENT if row["matches"] > 0 else (132, 144, 160))
        screen.blit(body_font.render(rate_text, True, rate_color), (columns["rate"], row_rect.top + 8))

    return return_rect, max_scroll


def get_character_display_name(character):
    return get_pokedex_data(character.job_name)["display_name"]


def truncate_text(text, font, max_width):
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    while text and font.size(text + ellipsis)[0] > max_width:
        text = text[:-1]
    return text + ellipsis if text else ellipsis


def describe_design_state(character):
    parts = []
    if getattr(character, "design_banished", False):
        parts.append(f"放逐{character.design_banish_points}/{BANISH_POINTS_THRESHOLD}")
    meta = getattr(character, "design_meta", None) or {}
    role_num = meta.get("role_num")
    if character.is_phoenix():
        parts.append(f"凤羽{character.design_phoenix_feather}")
        if character.design_phoenix_fall:
            parts.append(f"凤陨{character.design_phoenix_fall}")
        if character.design_phoenix_egg_timer > 0:
            parts.append("不灭蛋")
    elif character.is_xuanwu():
        parts.append(f"玄甲{character.design_shell_stacks}")
        if character.design_xuan_bulwark_timer > 0:
            parts.append("壁垒")
    elif character.is_tiger():
        if character.design_tiger_prey_id is not None:
            parts.append("猎")
        parts.append(f"虎魄{character.design_tiger_power}")
        if character.design_tiger_hunt_value >= 100:
            parts.append("猎杀满")
        elif character.design_tiger_hunt_value > 0:
            parts.append(f"猎杀{int(character.design_tiger_hunt_value)}")
    elif character.is_dragon():
        parts.append("雷" if character.design_dragon_form == "thunder" else "木")
        breath = character.get_dragon_breath()
        if breath:
            parts.append(f"息{breath}")
        if character.design_dragon_awe:
            parts.append(f"龙威{character.design_dragon_awe}")
        if character.design_dragon_sweep_cooldown > 0:
            parts.append("冷却")
    elif role_num == 98:
        parts.append(f"Lv.{character.design_level}")
    elif character.is_twin_mirror():
        parts.append("白" if character.twin_mirror_form == "white" else "黑")
    elif character.job_name == SOUL_ARBITER_JOB_NAME:
        if character.soul_arbiter_hunt_timer > 0:
            parts.append("巡狩")
        if character.soul_arbiter_chains:
            parts.append(f"链{len(character.soul_arbiter_chains)}")
    elif character.is_sunfire_blademaster():
        parts.append(f"连击{character.sunfire_combo_step}")
        if character.sunfire_fire_timer > 0:
            parts.append("炎")
    elif character.is_windstorm_fox():
        if character.windstorm_qi_stacks:
            parts.append(f"气{character.windstorm_qi_stacks}")
    elif character.job_name == SEA_SAGE_JOB_NAME:
        if character.sea_tide_shield_hp > 0:
            parts.append("水盾")
    elif character.job_name == "DesignRole77_shadow_dancer":
        if character.design_shadow_idle >= 5.0:
            parts.append("影·蓄势")
    elif character.design_meta.get("role_num") == 59:
        if character.design_ranger_lock_timer > 0:
            parts.append(f"猎魂{character.design_ranger_lock_timer:.0f}s")
    elif character.design_meta.get("role_num") == 117:
        if character.design_raikiri_mark:
            parts.append(f"雷痕{character.design_raikiri_mark}")
        parts.append(f"段{character.design_raikiri_stage + 1}")
    elif character.design_meta.get("role_num") == 119:
        if character.design_blood_feast_timer > 0:
            parts.append("盛宴")
        if character.design_blood_curse:
            parts.append(f"血咒{character.design_blood_curse}")
    elif character.design_meta.get("role_num") == 120:
        if character.design_kenshi_mark:
            parts.append(f"狐印{character.design_kenshi_mark}")
    elif character.job_name == "DesignRole90_collector":
        if character.design_collect_fervor:
            parts.append(f"狂热{character.design_collect_fervor}")
    elif character.job_name == "DesignRole53_sentinel":
        if character.design_sentinel_lock:
            parts.append("瞄准")
    return " ".join(parts)


SIDEBAR_VISIBLE_ROWS = max(1, (BATTLE_WINDOW_HEIGHT - 16 - 8 - 102) // 58)


def draw_follow_panel(surface, title_font, body_font, character):
    panel = pygame.Rect(SCREEN_WIDTH - 288, 64, 274, 144)
    draw_panel(surface, panel, (20, 26, 36), accent_color=(150, 214, 170), radius=12, shadow_offset=(2, 2))
    name = title_font.render(f"跟随 · {get_character_display_name(character)}", True, (150, 214, 170))
    surface.blit(name, (panel.left + 12, panel.top + 8))
    hp_ratio = clamp(character.hp / max(1.0, character.max_hp), 0.0, 1.0)
    bar = pygame.Rect(panel.left + 12, panel.top + 34, panel.width - 24, 10)
    pygame.draw.rect(surface, (34, 40, 52), bar, border_radius=5)
    pygame.draw.rect(surface, (110, 190, 140), pygame.Rect(bar.left + 1, bar.top + 1, max(1, int((bar.width - 2) * hp_ratio)), bar.height - 2), border_radius=4)
    hp_text = body_font.render(f"{int(character.hp)}/{int(character.max_hp)}", True, (196, 208, 224))
    surface.blit(hp_text, (panel.right - hp_text.get_width() - 14, panel.top + 28))
    y = panel.top + 52
    lines = [
        f"伤害 {int(character.damageDealt)} · 承伤 {int(character.damageTaken)}",
        f"击杀 {int(getattr(character, 'kill_count', 0))} · 连杀 {getattr(character, 'kill_streak', 0)}",
    ]
    if getattr(character, "killstreak_buff_level", 0) > 0:
        lines.append(f"连杀增益 Lv.{character.killstreak_buff_level} ({character.killstreak_buff_timer:.1f}s)")
    state = describe_design_state(character)
    if state:
        lines.append(state)
    for line in lines:
        line_surface = body_font.render(truncate_text(line, body_font, panel.width - 24), True, (196, 208, 224))
        surface.blit(line_surface, (panel.left + 12, y))
        y += 20


def draw_battle_sidebar(surface, title_font, subtitle_font, body_font, game_state, active_tab, hover_tab, follow_character_id=None, scroll_offset=0, speed_text=""):
    sidebar_rect = pygame.Rect(0, 0, BATTLE_SIDEBAR_WIDTH, BATTLE_WINDOW_HEIGHT)
    panel_rect = sidebar_rect.inflate(-16, -16)
    surface.fill((10, 14, 20), sidebar_rect)
    draw_panel(surface, panel_rect, (18, 24, 32), accent_color=(84, 128, 184), radius=14)
    pygame.draw.line(surface, BORDER_COLOR, (sidebar_rect.left, 0), (sidebar_rect.left, BATTLE_WINDOW_HEIGHT), 2)

    header = title_font.render("本局数据", True, TEXT_COLOR)
    surface.blit(header, header.get_rect(center=(sidebar_rect.width // 2, 20)))

    # 顶部信息条：存活 / 武器球 / 倍速（C1+C2 统一收纳）
    alive = len(get_living_main_characters(game_state))
    total = len(game_state.get("battle_participants", []))
    orbs = len(game_state["weapon_orbs"])
    speed_part = f" · 速度 x{speed_text}" if speed_text else ""
    info_line = f"存活 {alive}/{total} · 球 {orbs}{speed_part}"
    info_surface = subtitle_font.render(info_line, True, (150, 214, 170))
    surface.blit(info_surface, info_surface.get_rect(center=(sidebar_rect.width // 2, 46)))

    tab_y = 62
    tab_w = 84
    tab_h = 30
    tab_gap = 6
    tab_rects = {}
    tab_labels = {"output": "输出", "taken": "承伤", "kills": "击杀"}
    for index, key in enumerate(tab_labels):
        tab_rects[key] = pygame.Rect(panel_rect.left + 6 + index * (tab_w + tab_gap), tab_y, tab_w, tab_h)
    for key, rect in tab_rects.items():
        is_active = active_tab == key
        is_hover = hover_tab == key
        color = MENU_ACCENT if is_active else (MENU_BUTTON_HOVER if is_hover else MENU_BUTTON)
        draw_panel(surface, rect, color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
        label = subtitle_font.render(tab_labels[key], True, TEXT_COLOR)
        surface.blit(label, label.get_rect(center=rect.center))

    participants = list(game_state.get("battle_participants", game_state.get("characters", [])))
    metric = {"output": "damageDealt", "taken": "damageTaken", "kills": "kill_count"}[active_tab]
    accent = {"output": (220, 72, 72), "taken": (84, 150, 255), "kills": (255, 214, 120)}[active_tab]
    bar_bg = (34, 40, 52)
    bar_inner = (72, 78, 92)
    rows = sorted(participants, key=lambda character: (-float(getattr(character, metric, 0.0) or 0.0), character.id))
    max_value = max((float(getattr(character, metric, 0.0) or 0.0) for character in rows), default=0.0)

    row_top = 102
    row_height = 58
    bar_width = 150
    visible_rows = max(1, (panel_rect.bottom - 8 - row_top) // row_height)
    visible = rows[scroll_offset : scroll_offset + visible_rows]
    clickable_rows = []
    for index, character in enumerate(visible):
        row_y = row_top + index * row_height
        row_rect = pygame.Rect(panel_rect.left + 6, row_y, panel_rect.width - 12, row_height - 10)
        clickable_rows.append({"character": character, "rect": row_rect})
        row_bg = (26, 30, 38) if character.alive else (22, 24, 30)
        is_follow = follow_character_id is not None and character.id == follow_character_id
        if is_follow:
            row_bg = (42, 52, 66)
        pygame.draw.rect(surface, row_bg, row_rect, border_radius=10)
        pygame.draw.rect(surface, (46, 52, 64), row_rect, 1, border_radius=10)

        icon_color = character.color if character.alive else tuple(max(0, int(channel * 0.55)) for channel in character.color)
        draw_shape_icon(surface, character.shape, icon_color, (row_rect.left + 16, row_rect.top + 16), 9)

        name_color = TEXT_COLOR if character.alive else (160, 168, 176)
        if is_follow:
            name_color = (150, 214, 170)
        name = truncate_text(get_character_display_name(character), body_font, 100)
        name_surface = body_font.render(name, True, name_color)
        surface.blit(name_surface, (row_rect.left + 34, row_rect.top + 5))
        kills = int(getattr(character, "kill_count", 0))
        kill_surface = subtitle_font.render(f"×{kills}", True, (255, 214, 120))
        surface.blit(kill_surface, (row_rect.left + 34 + name_surface.get_width() + 4, row_rect.top + 7))

        value = float(getattr(character, metric, 0.0) or 0.0)
        value_surface = subtitle_font.render(str(int(round(value))), True, accent)
        surface.blit(value_surface, (row_rect.right - value_surface.get_width() - 8, row_rect.top + 5))

        state_text = describe_design_state(character)
        if state_text and character.alive:
            if is_follow:
                state_surface = body_font.render(truncate_text(state_text, body_font, 220), True, (150, 180, 205))
                surface.blit(state_surface, (row_rect.left + 34, row_rect.top + 26))
            else:
                state_surface = subtitle_font.render(truncate_text(state_text, subtitle_font, 200), True, (150, 180, 205))
                surface.blit(state_surface, (row_rect.left + 34, row_rect.top + 27))

        fill_width = int(bar_width * (value / max_value)) if max_value > 0 else 0
        bar_rect = pygame.Rect(row_rect.left + 34, row_rect.bottom - 14, bar_width, 8)
        pygame.draw.rect(surface, bar_bg, bar_rect, border_radius=4)
        if fill_width > 0:
            pygame.draw.rect(surface, bar_inner, bar_rect.inflate(-2, -2), border_radius=4)
            pygame.draw.rect(surface, accent, pygame.Rect(bar_rect.left + 1, bar_rect.top + 1, max(1, fill_width - 2), bar_rect.height - 2), border_radius=4)

    if scroll_offset > 0 or scroll_offset + visible_rows < len(rows):
        scroll_hint = subtitle_font.render(f"滚轮滚动 {scroll_offset + 1}-{min(len(rows), scroll_offset + visible_rows)}/{len(rows)}", True, (120, 140, 160))
        surface.blit(scroll_hint, scroll_hint.get_rect(center=(sidebar_rect.width // 2, BATTLE_WINDOW_HEIGHT - 18)))
    return clickable_rows


def create_ui_font(size, bold=False):
    preferred_fonts = [
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    return pygame.font.SysFont(preferred_fonts, size, bold=bold)