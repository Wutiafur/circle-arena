# -*- coding: utf-8 -*-
"""流程控制层：主菜单与各游戏循环 + 入口 main()。"""
import math
import os
import random
import sys

import pygame

from game.data import *
from game.engine import *
from game.ui import *
from game.world import *
from game import runtime



def main_menu(screen, clock, title_font, subtitle_font, button_font):
    player_count = MAX_CHARACTERS
    disable_timed_weapon_drops = False

    while True:
        button_rects = get_menu_button_rects()
        canvas_rect, device_pixel_ratio = get_window_transform(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if button_rects["minus"].collidepoint(mapped_pos):
                    player_count = max(MIN_CHARACTERS, player_count - 1)
                elif button_rects["plus"].collidepoint(mapped_pos):
                    player_count = min(MAX_CHARACTERS, player_count + 1)
                elif button_rects["weapon_drops"].collidepoint(mapped_pos):
                    disable_timed_weapon_drops = not disable_timed_weapon_drops
                elif button_rects["start"].collidepoint(mapped_pos):
                    return ("battle", player_count, disable_timed_weapon_drops)
                elif button_rects["pokedex"].collidepoint(mapped_pos):
                    return ("pokedex", None)
                elif button_rects["duel"].collidepoint(mapped_pos):
                    return ("duel", None)
                elif button_rects["ban"].collidepoint(mapped_pos):
                    return ("ban", None)
                elif button_rects["effects"].collidepoint(mapped_pos):
                    return ("effects", None)
                elif button_rects["win_rate"].collidepoint(mapped_pos):
                    return ("win_rate", None)
                elif button_rects["settings"].collidepoint(mapped_pos):
                    return ("settings", None)

        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        hover_name = next((name for name, rect in button_rects.items() if mouse_pos is not None and rect.collidepoint(mouse_pos)), None)
        canvas_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        draw_menu(canvas_surface, title_font, subtitle_font, button_font, player_count, hover_name, disable_timed_weapon_drops, disabled_count=len(runtime._DISABLED_ROLE_KEYS))
        present_canvas(screen, canvas_surface, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


_POKEDEX_LAST_SELECTED = None

_DISABLED_ROLE_MAX = 3


def pokedex_loop(screen, clock, title_font, subtitle_font, body_font, button_font):
    global _POKEDEX_LAST_SELECTED
    ordered_names = get_pokedex_ordered_names()
    stats = load_win_rate_stats()
    search_query = ""
    filtered = filter_pokedex_names(ordered_names, search_query)
    if _POKEDEX_LAST_SELECTED in filtered:
        selected_name = _POKEDEX_LAST_SELECTED
    else:
        selected_name = filtered[0] if filtered else ordered_names[0]
    list_scroll_offset = 0
    detail_scroll_offset = 0
    list_dragging = False
    list_drag_offset = 0.0
    list_track_rect = None
    list_thumb_rect = None
    list_panel = pygame.Rect(36, 154, 240, 556)
    detail_panel = pygame.Rect(300, 104, 464, 668)
    row_h = 44
    header_h = 22
    detail_cache = {}

    def build_detail(name):
        item = detail_cache.get(name)
        if item is None:
            item = build_pokedex_detail_surface(detail_panel, get_pokedex_data(name), subtitle_font, body_font, stats=stats)
            detail_cache[name] = item
        return item

    def compute_list_max_scroll(names):
        entries = pokedex_layout_entries(names)
        content_h = sum(header_h if entry_type == "header" else row_h for entry_type, _ in entries)
        return max(0, content_h - (list_panel.height - 24))

    max_scroll = compute_list_max_scroll(filtered)
    _, _, detail_max_scroll = build_detail(selected_name)
    item_rects = {}

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if pygame.Rect(36, 722, 220, 40).collidepoint(mapped_pos):
                    return "menu"
                # 列表滑动条交互：拖动滑块 / 点击轨道按比例跳转（与擂台选人同款）
                if list_track_rect is not None and list_track_rect.collidepoint(mapped_pos):
                    if list_thumb_rect is not None and list_thumb_rect.collidepoint(mapped_pos):
                        list_dragging = True
                        list_drag_offset = mapped_pos[1] - list_thumb_rect.top
                    elif max_scroll > 0:
                        ratio = (mapped_pos[1] - list_track_rect.top - list_thumb_rect.height / 2) / max(1, list_track_rect.height - list_thumb_rect.height)
                        list_scroll_offset = int(clamp(round(ratio * max_scroll), 0, max_scroll))
                for name, rect in item_rects.items():
                    if rect.collidepoint(mapped_pos):
                        if selected_name != name:
                            selected_name = name
                            _POKEDEX_LAST_SELECTED = name
                            detail_scroll_offset = 0
                            _, _, detail_max_scroll = build_detail(selected_name)
                        break
            if event.type == pygame.MOUSEMOTION and list_dragging:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is not None and list_track_rect is not None and max_scroll > 0:
                    ratio = (mapped_pos[1] - list_track_rect.top - list_drag_offset) / max(1, list_track_rect.height - list_thumb_rect.height)
                    list_scroll_offset = int(clamp(round(ratio * max_scroll), 0, max_scroll))
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                list_dragging = False
            if event.type == pygame.MOUSEWHEEL:
                hover_mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
                if hover_mouse_pos is not None and list_panel.collidepoint(hover_mouse_pos):
                    list_scroll_offset = int(clamp(list_scroll_offset - event.y * 26, 0, max_scroll))
                elif hover_mouse_pos is not None and detail_panel.collidepoint(hover_mouse_pos):
                    detail_scroll_offset = int(clamp(detail_scroll_offset - event.y * 26, 0, detail_max_scroll))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    list_scroll_offset = int(clamp(list_scroll_offset - 32, 0, max_scroll))
                elif event.key == pygame.K_DOWN:
                    list_scroll_offset = int(clamp(list_scroll_offset + 32, 0, max_scroll))
                elif event.key == pygame.K_ESCAPE:
                    return "menu"
                elif event.key == pygame.K_BACKSPACE:
                    search_query = search_query[:-1]
                    filtered = filter_pokedex_names(ordered_names, search_query)
                    max_scroll = compute_list_max_scroll(filtered)
                    list_scroll_offset = 0
                    if selected_name not in filtered:
                        selected_name = filtered[0] if filtered else ordered_names[0]
                        _POKEDEX_LAST_SELECTED = selected_name
                        detail_scroll_offset = 0
                        _, _, detail_max_scroll = build_pokedex_detail_surface(
                            detail_panel,
                            get_pokedex_data(selected_name),
                            subtitle_font,
                            body_font,
                            stats=stats,
                        )
                elif event.unicode and event.unicode.isprintable() and len(search_query) < 12:
                    search_query += event.unicode
                    filtered = filter_pokedex_names(ordered_names, search_query)
                    max_scroll = compute_list_max_scroll(filtered)
                    list_scroll_offset = 0
                    if selected_name not in filtered:
                        selected_name = filtered[0] if filtered else ordered_names[0]
                        _POKEDEX_LAST_SELECTED = selected_name
                        detail_scroll_offset = 0
                        _, _, detail_max_scroll = build_pokedex_detail_surface(
                            detail_panel,
                            get_pokedex_data(selected_name),
                            subtitle_font,
                            body_font,
                            stats=stats,
                        )

        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        hover_name = None
        if mouse_pos is not None:
            for name, rect in item_rects.items():
                if rect.collidepoint(mouse_pos):
                    hover_name = name
                    break
        if hover_name is None and mouse_pos is not None and pygame.Rect(36, 722, 220, 40).collidepoint(mouse_pos):
            hover_name = "return"
        canvas_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        (
            _return_rect,
            item_rects,
            list_panel,
            detail_panel,
            row_h,
            detail_max_scroll,
            list_track_rect,
            list_thumb_rect,
        ) = draw_pokedex(
            canvas_surface,
            title_font,
            subtitle_font,
            body_font,
            button_font,
            selected_name,
            list_scroll_offset,
            detail_scroll_offset,
            hover_name,
            search_query,
            stats,
            ordered_names,
            build_detail(selected_name),
            list_thumb_dragging=list_dragging,
        )
        present_canvas(screen, canvas_surface, canvas_rect)
        detail_scroll_offset = int(clamp(detail_scroll_offset, 0, detail_max_scroll))
        pygame.display.flip()
        clock.tick(FPS)


MAX_DISABLED_ROLES = 3


def toggle_disabled_role(job_name):
    if job_name in runtime._DISABLED_ROLE_KEYS:
        runtime._DISABLED_ROLE_KEYS.discard(job_name)
        return True
    if len(runtime._DISABLED_ROLE_KEYS) >= MAX_DISABLED_ROLES:
        return False
    runtime._DISABLED_ROLE_KEYS.add(job_name)
    return True




def ban_loop(screen, clock, title_font, subtitle_font, body_font, button_font):
    ordered_names = get_pokedex_ordered_names()
    grid_left, grid_top = 28, 138
    cols = 6
    cell_w, cell_h = 122, 56
    grid_panel = pygame.Rect(16, 120, SCREEN_WIDTH - 32, 620)
    rows_visible = (grid_panel.height - 20) // cell_h
    scroll_row = 0

    def visible_names():
        start = scroll_row * cols
        return ordered_names[start : start + rows_visible * cols]

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)
        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        cell_rects = {}
        visible = visible_names()
        for index, name in enumerate(visible):
            col = index % cols
            row = index // cols
            rect = pygame.Rect(grid_left + col * (cell_w + 8), grid_top + row * (cell_h + 8), cell_w, cell_h)
            cell_rects[name] = rect

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if pygame.Rect(244, 754, 312, 36).collidepoint(mapped_pos):
                    return "menu"
                for name, rect in cell_rects.items():
                    if rect.collidepoint(mapped_pos):
                        toggle_disabled_role(name)
                        break
            if event.type == pygame.MOUSEWHEEL:
                hover_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
                if hover_pos is not None and grid_panel.collidepoint(hover_pos):
                    scroll_row = int(clamp(scroll_row - event.y, 0, max(0, (len(ordered_names) + cols - 1) // cols - rows_visible)))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "menu"

        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        canvas.fill(BACKGROUND_COLOR)
        for gx in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(canvas, (22, 28, 36), (gx, 0), (gx, SCREEN_HEIGHT), 1)
        for gy in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(canvas, (22, 28, 36), (0, gy), (SCREEN_WIDTH, gy), 1)
        title = title_font.render(f"禁用角色（{len(runtime._DISABLED_ROLE_KEYS)}/{MAX_DISABLED_ROLES}）：被禁角色不会出现在自动对战中", True, TEXT_COLOR)
        canvas.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 66)))
        hint = subtitle_font.render("点击切换禁用，最多 3 个 · 滚轮滚动 · Esc 返回", True, (150, 164, 180))
        canvas.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 96)))
        draw_panel(canvas, grid_panel, (16, 22, 30), radius=14)

        for name, rect in cell_rects.items():
            data = CHARACTER_DATA.get(name, {})
            disabled = name in runtime._DISABLED_ROLE_KEYS
            fill = (52, 30, 34) if disabled else (24, 30, 40)
            border = (232, 96, 96) if disabled else (60, 70, 84)
            draw_panel(canvas, rect, fill, border_color=border, radius=8, shadow_offset=(1, 1))
            draw_shape_icon(canvas, data.get("shape", "circle"), data.get("color", (180, 180, 180)), (rect.left + 20, rect.centery), 9)
            label = body_font.render(truncate_text(get_pokedex_data(name).get("display_name", name), body_font, rect.width - 40), True, TEXT_COLOR)
            canvas.blit(label, (rect.left + 34, rect.top + 6))
            detail = subtitle_font.render(f"#{get_role_display_number(name)}", True, (150, 164, 180))
            canvas.blit(detail, (rect.left + 34, rect.top + 26))
            if disabled:
                cross = button_font.render("✕", True, (255, 120, 110))
                canvas.blit(cross, cross.get_rect(topright=(rect.right - 10, rect.top + 4)))

        back_rect = pygame.Rect(244, 754, 312, 36)
        draw_panel(canvas, back_rect, MENU_BUTTON_HOVER if mouse_pos is not None and back_rect.collidepoint(mouse_pos) else MENU_BUTTON, radius=10, shadow_offset=(2, 2))
        back_text = subtitle_font.render("返回主菜单", True, TEXT_COLOR)
        canvas.blit(back_text, back_text.get_rect(center=back_rect.center))
        present_canvas(screen, canvas, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


def bet_loop(screen, clock, title_font, subtitle_font, body_font, button_font, game_state):
    characters = [c for c in game_state.get("battle_participants", game_state.get("characters", [])) if c.alive]
    if not characters:
        return "skip"
    stats = load_win_rate_stats()
    grid_left, grid_top = 28, 150
    cols = 5
    cell_w, cell_h = 142, 62
    grid_panel = pygame.Rect(16, 132, SCREEN_WIDTH - 32, 590)
    rows_visible = (grid_panel.height - 20) // cell_h
    scroll_row = 0

    def visible_chars():
        start = scroll_row * cols
        return characters[start : start + rows_visible * cols]

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)
        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        cell_rects = {}
        visible = visible_chars()
        for index, char in enumerate(visible):
            col = index % cols
            row = index // cols
            rect = pygame.Rect(grid_left + col * (cell_w + 10), grid_top + row * (cell_h + 10), cell_w, cell_h)
            cell_rects[id(char)] = rect

        skip_rect = pygame.Rect(180, 744, 200, 36)
        cancel_rect = pygame.Rect(420, 744, 200, 36)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if skip_rect.collidepoint(mapped_pos):
                    return "skip"
                if cancel_rect.collidepoint(mapped_pos):
                    return "cancel"
                for cid, rect in cell_rects.items():
                    if rect.collidepoint(mapped_pos):
                        return next(c.job_name for c in visible if id(c) == cid)
            if event.type == pygame.MOUSEWHEEL:
                hover_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
                if hover_pos is not None and grid_panel.collidepoint(hover_pos):
                    scroll_row = int(clamp(scroll_row - event.y, 0, max(0, (len(characters) + cols - 1) // cols - rows_visible)))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "cancel"

        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        canvas.fill(BACKGROUND_COLOR)
        for gx in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(canvas, (22, 28, 36), (gx, 0), (gx, SCREEN_HEIGHT), 1)
        for gy in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(canvas, (22, 28, 36), (0, gy), (SCREEN_WIDTH, gy), 1)
        title = title_font.render("入场押注：猜本局冠军！猜中结算送上冠军称号", True, TEXT_COLOR)
        canvas.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 66)))
        hint = subtitle_font.render("点击角色头像押注 · 参考下方历史胜率 · 滚轮滚动 · 也可跳过或返回", True, (150, 164, 180))
        canvas.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 100)))
        draw_panel(canvas, grid_panel, (16, 22, 30), radius=14)

        for char in visible:
            rect = cell_rects[id(char)]
            data = get_pokedex_data(char.job_name)
            draw_panel(canvas, rect, (24, 30, 40), border_color=(60, 70, 84), radius=8, shadow_offset=(1, 1))
            draw_shape_icon(canvas, data.get("shape", "circle"), data.get("color", (180, 180, 180)), (rect.left + 24, rect.top + 24), 12)
            name = body_font.render(truncate_text(data.get("display_name", char.job_name), body_font, rect.width - 56), True, TEXT_COLOR)
            canvas.blit(name, (rect.left + 50, rect.top + 8))
            num = subtitle_font.render(f"#{get_role_display_number(char.job_name)}", True, (150, 164, 180))
            canvas.blit(num, (rect.left + 50, rect.top + 30))
            entry = stats.get(char.job_name, {})
            matches = max(0, int(entry.get("matches", 0)))
            if matches >= 1:
                wr = max(0.0, int(entry.get("wins", 0))) / matches * 100.0
                win_text = f"{wr:.0f}% · {matches}场"
                win_color = (120, 210, 160) if wr >= 50.0 else (220, 120, 110)
            else:
                win_text = "暂无战绩"
                win_color = (110, 124, 142)
            win_surface = subtitle_font.render(win_text, True, win_color)
            canvas.blit(win_surface, (rect.left + 50, rect.top + 44))

        for rect, text in ((skip_rect, "不押注，直接战斗"), (cancel_rect, "返回主菜单")):
            hover = mouse_pos is not None and rect.collidepoint(mouse_pos)
            draw_panel(canvas, rect, MENU_BUTTON_HOVER if hover else MENU_BUTTON, radius=10, shadow_offset=(2, 2))
            label = subtitle_font.render(text, True, TEXT_COLOR)
            canvas.blit(label, label.get_rect(center=rect.center))

        present_canvas(screen, canvas, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


def duel_placement_valid(unit, new_pos, units, mid_x):
    if unit["team"] == 1 and new_pos.x > mid_x + 2.0:
        return False
    if unit["team"] == 2 and new_pos.x < mid_x - 2.0:
        return False
    for other in units:
        if other is unit:
            continue
        if (other["pos"] - new_pos).length() < 26.0:
            return False
    return True


def setup_loop(screen, clock, title_font, subtitle_font, body_font, button_font, red_jobs, blue_jobs):
    mid_x = (ARENA_RECT.left + ARENA_RECT.right) / 2.0
    units = []

    def apply_default_positions():
        units.clear()
        for index, job in enumerate(red_jobs):
            pos = pygame.Vector2(ARENA_RECT.left + 110 + index * 54, ARENA_RECT.bottom - 110 - index * 54)
            units.append({"job": job, "team": 1, "pos": pos, "radius": 12})
        for index, job in enumerate(blue_jobs):
            pos = pygame.Vector2(ARENA_RECT.right - 110 - index * 54, ARENA_RECT.top + 110 + index * 54)
            units.append({"job": job, "team": 2, "pos": pos, "radius": 12})

    apply_default_positions()
    dragging = None

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)
        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        start_rect = pygame.Rect(180, 726, 180, 44)
        reset_rect = pygame.Rect(380, 726, 160, 44)
        back_rect = pygame.Rect(560, 734, 150, 40)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if start_rect.collidepoint(mapped_pos):
                    return {"red": [u["pos"] for u in units if u["team"] == 1], "blue": [u["pos"] for u in units if u["team"] == 2]}
                if reset_rect.collidepoint(mapped_pos):
                    apply_default_positions()
                    continue
                if back_rect.collidepoint(mapped_pos):
                    return "back"
                if mapped_pos.x < ARENA_RECT.right and mapped_pos.y < ARENA_RECT.bottom:
                    for unit in units:
                        if (unit["pos"] - pygame.Vector2(mapped_pos)).length() < 22:
                            dragging = unit
                            break
            if event.type == pygame.MOUSEMOTION and dragging is not None:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is not None:
                    dragging["pos"] = pygame.Vector2(mapped_pos)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and dragging is not None:
                if not duel_placement_valid(dragging, dragging["pos"], units, mid_x):
                    for team_jobs, team_id in ((red_jobs, 1), (blue_jobs, 2)):
                        for index, job in enumerate(team_jobs):
                            unit = next((u for u in units if u["job"] == job and u["team"] == team_id), None)
                            if unit is dragging:
                                if team_id == 1:
                                    unit["pos"] = pygame.Vector2(ARENA_RECT.left + 110 + index * 54, ARENA_RECT.bottom - 110 - index * 54)
                                else:
                                    unit["pos"] = pygame.Vector2(ARENA_RECT.right - 110 - index * 54, ARENA_RECT.top + 110 + index * 54)
                dragging = None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "back"

        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        canvas.fill(BACKGROUND_COLOR)
        draw_grid(canvas)
        # 半场领地底色
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (224, 84, 76, 10), pygame.Rect(ARENA_RECT.left, ARENA_RECT.top, round(mid_x - ARENA_RECT.left), ARENA_RECT.height))
        pygame.draw.rect(overlay, (96, 160, 255, 10), pygame.Rect(round(mid_x), ARENA_RECT.top, ARENA_RECT.right - round(mid_x), ARENA_RECT.height))
        canvas.blit(overlay, (0, 0))
        pygame.draw.rect(canvas, BORDER_COLOR, ARENA_RECT, 3)
        pygame.draw.line(canvas, (255, 214, 120), (round(mid_x), ARENA_RECT.top), (round(mid_x), ARENA_RECT.bottom), 2)
        title = title_font.render("战前布阵：拖拽角色到自己半场任意位置", True, TEXT_COLOR)
        canvas.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 40)))
        hint = subtitle_font.render("红方只能放左半场 · 蓝方只能放右半场 · 不可重叠 · Esc 返回选人", True, (150, 164, 180))
        canvas.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 72)))
        red_hint = subtitle_font.render("红方领地（左）", True, (255, 170, 160))
        canvas.blit(red_hint, (ARENA_RECT.left + 14, ARENA_RECT.top + 10))
        blue_hint = subtitle_font.render("蓝方领地（右）", True, (150, 200, 255))
        canvas.blit(blue_hint, blue_hint.get_rect(topright=(ARENA_RECT.right - 14, ARENA_RECT.top + 10)))

        for unit in units:
            data = get_pokedex_data(unit["job"])
            draw_shape_icon(canvas, data.get("shape", "circle"), data.get("color", (180, 180, 180)), (round(unit["pos"].x), round(unit["pos"].y)), unit["radius"])
            ring = (224, 84, 76) if unit["team"] == 1 else (96, 160, 255)
            pygame.draw.circle(canvas, ring, (round(unit["pos"].x), round(unit["pos"].y)), unit["radius"] + 4, 2)
            name_s = subtitle_font.render(truncate_text(data.get("display_name", unit["job"]), subtitle_font, 70), True, TEXT_COLOR)
            canvas.blit(name_s, name_s.get_rect(center=(round(unit["pos"].x), round(unit["pos"].y - unit["radius"] - 18))))

        for rect, label in ((start_rect, "开始对战"), (reset_rect, "恢复默认"), (back_rect, "返回选人")):
            hover = mouse_pos is not None and rect.collidepoint(mouse_pos)
            color = MENU_ACCENT if label == "开始对战" and hover else MENU_BUTTON_HOVER if hover else (MENU_BUTTON if label != "开始对战" else MENU_ACCENT)
            draw_panel(canvas, rect, color, radius=10, shadow_offset=(2, 2))
            label_s = subtitle_font.render(label, True, TEXT_COLOR)
            canvas.blit(label_s, label_s.get_rect(center=rect.center))

        present_canvas(screen, canvas, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


def duel_loop(screen, clock, title_font, subtitle_font, body_font, button_font):
    ordered_names = get_pokedex_ordered_names()
    selection = {"red": set(), "blue": set()}
    scroll = {"red": 0, "blue": 0}
    list_top, list_h, row_h = 158, 550, 56
    TEAM_MAX = 8
    RED_COLOR = (224, 84, 76)
    BLUE_COLOR = (96, 160, 255)
    # 滑动条几何：红/蓝列表右侧各一条
    visible_rows = list_h // row_h
    total_rows = len(ordered_names)
    max_scroll = max(0, total_rows - visible_rows)
    bar_left = {"red": 36 + 352, "blue": 424 + 352}
    bar_width = 8
    thumb_h = max(26, round(list_h * visible_rows / max(1, total_rows)))
    dragging_side = None
    dragging_thumb_offset = 0.0

    def visible_names(key):
        start = scroll[key]
        return ordered_names[start : start + list_h // row_h]

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)
        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        row_rects = {"red": {}, "blue": {}}
        for side, left in (("red", 36), ("blue", 424)):
            for index, name in enumerate(visible_names(side)):
                row_rects[side][name] = pygame.Rect(left, list_top + index * row_h, 340, row_h - 6)
        start_rect = pygame.Rect(244, 736, 312, 44)
        back_rect = pygame.Rect(244, 790, 312, 40)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if back_rect.collidepoint(mapped_pos):
                    return "menu"
                if start_rect.collidepoint(mapped_pos) and selection["red"] and selection["blue"]:
                    prep = setup_loop(
                        screen, clock, title_font, subtitle_font, body_font, button_font,
                        sorted(selection["red"]),
                        sorted(selection["blue"]),
                    )
                    if prep == "back":
                        continue
                    return _run_duel(
                        screen, clock, title_font, subtitle_font, body_font, button_font,
                        sorted(selection["red"]),
                        sorted(selection["blue"]),
                        prep["red"],
                        prep["blue"],
                    )
                # 滑动条交互：拖动滑块 / 点击轨道跳转
                if max_scroll > 0:
                    thumb_y_now = {
                        s: list_top + round((scroll[s] / max_scroll) * (list_h - thumb_h))
                        for s in ("red", "blue")
                    }
                    for side in ("red", "blue"):
                        track_rect = pygame.Rect(bar_left[side], list_top, bar_width, list_h)
                        if track_rect.collidepoint(mapped_pos):
                            thumb_rect = pygame.Rect(bar_left[side], thumb_y_now[side], bar_width, thumb_h)
                            if thumb_rect.collidepoint(mapped_pos):
                                dragging_side = side
                                dragging_thumb_offset = mapped_pos[1] - thumb_rect.top
                            else:
                                ratio = (mapped_pos[1] - list_top - thumb_h / 2) / max(1, list_h - thumb_h)
                                scroll[side] = int(clamp(round(ratio * max_scroll), 0, max_scroll))
                            break
                for side in ("red", "blue"):
                    for name, rect in row_rects[side].items():
                        if rect.collidepoint(mapped_pos):
                            if name in selection[side]:
                                selection[side].discard(name)
                            elif len(selection[side]) < TEAM_MAX:
                                selection[side].add(name)
                            break
            if event.type == pygame.MOUSEMOTION and dragging_side is not None:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is not None and max_scroll > 0:
                    ratio = (mapped_pos[1] - list_top - dragging_thumb_offset) / max(1, list_h - thumb_h)
                    scroll[dragging_side] = int(clamp(round(ratio * max_scroll), 0, max_scroll))
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_side = None
            if event.type == pygame.MOUSEWHEEL:
                hover_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
                for side, left in (("red", 36), ("blue", 424)):
                    panel_rect = pygame.Rect(left - 4, list_top - 30, 348, list_h + 34)
                    if hover_pos is not None and panel_rect.collidepoint(hover_pos):
                        scroll[side] = int(clamp(scroll[side] - event.y, 0, max(0, len(ordered_names) - list_h // row_h)))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "menu"

        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        canvas.fill(BACKGROUND_COLOR)
        for gx in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(canvas, (22, 28, 36), (gx, 0), (gx, SCREEN_HEIGHT), 1)
        for gy in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(canvas, (22, 28, 36), (0, gy), (SCREEN_WIDTH, gy), 1)
        title = title_font.render("红蓝擂台赛：红队 vs 蓝队（每队 1~8 人）", True, TEXT_COLOR)
        canvas.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 62)))
        hint = subtitle_font.render("点击角色加入/移出队伍 · 滚轮或拖动滑动条滚动 · Esc 返回", True, (150, 164, 180))
        canvas.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 98)))

        for side, left, team_color, side_title in (
            ("red", 36, RED_COLOR, f"红队（{len(selection['red'])}/{TEAM_MAX}）"),
            ("blue", 424, BLUE_COLOR, f"蓝队（{len(selection['blue'])}/{TEAM_MAX}）"),
        ):
            panel_rect = pygame.Rect(left - 4, list_top - 30, 348, list_h + 34)
            draw_panel(canvas, panel_rect, (16, 22, 30), radius=12)
            side_label = subtitle_font.render(side_title, True, team_color)
            canvas.blit(side_label, side_label.get_rect(center=(left + 170, list_top - 16)))
            for name, rect in row_rects[side].items():
                data = get_pokedex_data(name)
                selected = name in selection[side]
                fill = (58, 26, 24) if selected and side == "red" else (24, 34, 56) if selected else (24, 30, 40)
                border = team_color if selected else (60, 70, 84)
                draw_panel(canvas, rect, fill, border_color=border, radius=8, shadow_offset=(1, 1))
                draw_shape_icon(canvas, data.get("shape", "circle"), data.get("color", (180, 180, 180)), (rect.left + 20, rect.centery), 10)
                label = body_font.render(truncate_text(data.get("display_name", name), body_font, rect.width - 90), True, TEXT_COLOR)
                canvas.blit(label, (rect.left + 40, rect.top + 6))
                num = subtitle_font.render(f"#{get_role_display_number(name)} · {data.get('display_attack_tag', '')}", True, (150, 164, 180))
                canvas.blit(num, (rect.left + 40, rect.top + 28))
                if selected:
                    mark = button_font.render("✔", True, team_color)
                    canvas.blit(mark, mark.get_rect(center=(rect.right - 20, rect.centery)))
            # 滑动条：轨道 + 滑块
            bar_track = pygame.Rect(bar_left[side], list_top, bar_width, list_h)
            pygame.draw.rect(canvas, (30, 38, 48), bar_track, border_radius=4)
            thumb_y = list_top + round((scroll[side] / max_scroll) * (list_h - thumb_h)) if max_scroll > 0 else list_top
            thumb_rect = pygame.Rect(bar_left[side], thumb_y, bar_width, thumb_h)
            thumb_color = team_color if dragging_side == side else (110, 130, 150)
            pygame.draw.rect(canvas, thumb_color, thumb_rect, border_radius=4)

        red_count, blue_count = len(selection["red"]), len(selection["blue"])
        ready = red_count >= 1 and blue_count >= 1
        draw_panel(canvas, start_rect, (255, 214, 120) if ready else MENU_BUTTON_DISABLED, radius=10, shadow_offset=(2, 2))
        if ready:
            start_text = button_font.render(f"开始对战 · 红队 {red_count} vs 蓝队 {blue_count}", True, TEXT_COLOR)
        else:
            start_text = subtitle_font.render("请先为双方各选至少 1 名角色", True, (150, 164, 180))
        canvas.blit(start_text, start_text.get_rect(center=start_rect.center))
        draw_panel(canvas, back_rect, MENU_BUTTON_HOVER if mouse_pos is not None and back_rect.collidepoint(mouse_pos) else MENU_BUTTON, radius=10, shadow_offset=(2, 2))
        back_text = subtitle_font.render("返回主菜单", True, TEXT_COLOR)
        canvas.blit(back_text, back_text.get_rect(center=back_rect.center))

        present_canvas(screen, canvas, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


def _run_duel(screen, clock, title_font, subtitle_font, body_font, button_font, red_jobs, blue_jobs, red_positions=None, blue_positions=None):
    gs = create_game_state(2, timed_weapon_orb_drops_enabled=False)
    gs["timed_weapon_orb_drops_enabled"] = False
    characters = []
    for index, job in enumerate(red_jobs):
        pos = red_positions[index] if red_positions else pygame.Vector2(ARENA_RECT.left + 110 + index * 54, ARENA_RECT.bottom - 110 - index * 54)
        characters.append(Character(job, index + 1, pos, owner_id=1))
    for index, job in enumerate(blue_jobs):
        pos = blue_positions[index] if blue_positions else pygame.Vector2(ARENA_RECT.right - 110 - index * 54, ARENA_RECT.top + 110 + index * 54)
        characters.append(Character(job, 100 + index + 1, pos, owner_id=2))
    gs["characters"] = characters
    gs["battle_participants"] = list(characters)
    for char in characters:
        char.spawn_fx_timer = 0.0
        if char.is_soul_casket():
            char.design_immobile = True
            char.spawn_soul_blade(gs)
    scene_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    result_text = ""
    result_color = (255, 214, 120)
    battle_font = create_ui_font(22, bold=True)
    RED_COLOR = (224, 84, 76)
    BLUE_COLOR = (96, 160, 255)

    def team_alive(owner_id):
        return [c for c in gs["characters"] if c.alive and c.owner_id == owner_id]

    while True:
        dt = clock.tick(FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        rematch_rect = pygame.Rect(180, 684, 200, 44)
        back_rect = pygame.Rect(420, 684, 200, 44)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "menu"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and result_text:
                return _run_duel(screen, clock, title_font, subtitle_font, body_font, button_font, red_jobs, blue_jobs)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if result_text and rematch_rect.collidepoint(event.pos):
                    return _run_duel(screen, clock, title_font, subtitle_font, body_font, button_font, red_jobs, blue_jobs)
                if result_text and back_rect.collidepoint(event.pos):
                    return "menu"

        if not result_text:
            red_alive = team_alive(1)
            blue_alive = team_alive(2)
            if not red_alive and not blue_alive:
                result_text = "红蓝同归于尽！"
                result_color = (200, 208, 220)
            elif not red_alive:
                result_text = f"蓝队获胜！（剩 {len(blue_alive)} 人）"
                result_color = BLUE_COLOR
            elif not blue_alive:
                result_text = f"红队获胜！（剩 {len(red_alive)} 人）"
                result_color = RED_COLOR
            else:
                gs["elapsed_time"] += dt
                for character in gs["characters"]:
                    character.update(dt, gs)
                for index, character in enumerate(gs["characters"]):
                    for other in gs["characters"][index + 1 :]:
                        character.resolve_overlap(other)
                update_world_lists(gs, dt)
                gs["characters"] = [c for c in gs["characters"] if c.alive]

        draw_grid(scene_surface)
        draw_ui(scene_surface, title_font, body_font, gs)
        pygame.draw.rect(scene_surface, BORDER_COLOR, ARENA_RECT, 3)
        draw_world(scene_surface, gs, body_font)

        # 队伍光环（红圈/蓝圈）+ 顶部队牌
        for char in gs["characters"]:
            ring = RED_COLOR if char.owner_id == 1 else BLUE_COLOR
            pygame.draw.circle(scene_surface, ring, (round(char.pos.x), round(char.pos.y)), char.radius + 5, 2)
        red_badge = pygame.Rect(ARENA_RECT.left + 8, 72, 110, 26)
        blue_badge = pygame.Rect(ARENA_RECT.right - 118, 72, 110, 26)
        draw_panel(scene_surface, red_badge, (58, 26, 24), border_color=RED_COLOR, radius=8, shadow_offset=(1, 1))
        draw_panel(scene_surface, blue_badge, (24, 34, 56), border_color=BLUE_COLOR, radius=8, shadow_offset=(1, 1))
        red_label = body_font.render(f"红队 {len(team_alive(1))}", True, (255, 190, 186))
        blue_label = body_font.render(f"蓝队 {len(team_alive(2))}", True, (168, 200, 255))
        scene_surface.blit(red_label, red_label.get_rect(center=red_badge.center))
        scene_surface.blit(blue_label, blue_label.get_rect(center=blue_badge.center))

        if result_text:
            end_panel = pygame.Rect(110, 150, 580, 520)
            draw_panel(scene_surface, end_panel, MENU_PANEL, accent_color=(255, 214, 120), radius=16, shadow_offset=(3, 4))
            result_surface = battle_font.render(result_text, True, result_color)
            scene_surface.blit(result_surface, result_surface.get_rect(center=(end_panel.centerx, end_panel.top + 26)))
            y = end_panel.top + 56
            for owner, team_color, team_label in ((1, RED_COLOR, "红队"), (2, BLUE_COLOR, "蓝队")):
                team_chars = [c for c in characters if c.owner_id == owner]
                head = subtitle_font.render(f"— {team_label} —", True, team_color)
                scene_surface.blit(head, (end_panel.left + 40, y))
                y += 22
                for char in team_chars:
                    if y >= end_panel.bottom - 8:
                        break
                    stat_line = body_font.render(
                        f"{get_character_display_name(char)}：{int(char.damageDealt)} 伤 / {int(char.damageTaken)} 承" + (" 存活" if char.alive else " 战败"),
                        True,
                        (196, 208, 224),
                    )
                    scene_surface.blit(stat_line, (end_panel.left + 56, y))
                    y += 20
            rematch_hover = rematch_rect.collidepoint(mouse_pos)
            back_hover = back_rect.collidepoint(mouse_pos)
            draw_panel(scene_surface, rematch_rect, MENU_BUTTON_HOVER if rematch_hover else MENU_ACCENT, radius=10, shadow_offset=(2, 2))
            draw_panel(scene_surface, back_rect, MENU_BUTTON_HOVER if back_hover else MENU_BUTTON, radius=10, shadow_offset=(2, 2))
            rematch_label = body_font.render("再来一局", True, TEXT_COLOR)
            back_label = body_font.render("返回", True, TEXT_COLOR)
            scene_surface.blit(rematch_label, rematch_label.get_rect(center=rematch_rect.center))
            scene_surface.blit(back_label, back_label.get_rect(center=back_rect.center))
        screen.blit(scene_surface, (0, 0))
        pygame.display.flip()


def effectdex_loop(screen, clock, title_font, subtitle_font, body_font, button_font):
    effect_keys = list(EFFECT_DATA.keys())
    selected_name = effect_keys[0]
    list_scroll_offset = 0
    detail_scroll_offset = 0
    item_height = 52
    list_panel = pygame.Rect(36, 104, 240, 620)
    detail_panel = pygame.Rect(300, 104, 464, 620)
    max_scroll = max(0, len(effect_keys) * item_height - (list_panel.height - 24))
    _, _, detail_max_scroll = build_effect_detail_surface(detail_panel, get_effect_data(selected_name), subtitle_font, body_font)

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if pygame.Rect(36, 734, 220, 40).collidepoint(mapped_pos):
                    return "menu"
                for key in effect_keys:
                    index = effect_keys.index(key)
                    y = list_panel.top + 18 + index * item_height - list_scroll_offset
                    rect = pygame.Rect(list_panel.left + 12, y, list_panel.width - 24, item_height - 6)
                    if rect.collidepoint(mapped_pos):
                        if selected_name != key:
                            selected_name = key
                            detail_scroll_offset = 0
                            _, _, detail_max_scroll = build_effect_detail_surface(
                                detail_panel,
                                get_effect_data(selected_name),
                                subtitle_font,
                                body_font,
                            )
                        break
            if event.type == pygame.MOUSEWHEEL:
                hover_mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
                if hover_mouse_pos is not None and list_panel.collidepoint(hover_mouse_pos):
                    list_scroll_offset = int(clamp(list_scroll_offset - event.y * 26, 0, max_scroll))
                elif hover_mouse_pos is not None and detail_panel.collidepoint(hover_mouse_pos):
                    detail_scroll_offset = int(clamp(detail_scroll_offset - event.y * 26, 0, detail_max_scroll))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    list_scroll_offset = int(clamp(list_scroll_offset - 32, 0, max_scroll))
                elif event.key == pygame.K_DOWN:
                    list_scroll_offset = int(clamp(list_scroll_offset + 32, 0, max_scroll))

        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        hover_name = None
        if mouse_pos is not None:
            for key in effect_keys:
                index = effect_keys.index(key)
                y = list_panel.top + 18 + index * item_height - list_scroll_offset
                rect = pygame.Rect(list_panel.left + 12, y, list_panel.width - 24, item_height - 6)
                if rect.collidepoint(mouse_pos):
                    hover_name = key
                    break
        if hover_name is None and mouse_pos is not None and pygame.Rect(36, 734, 220, 40).collidepoint(mouse_pos):
            hover_name = "return"
        canvas_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        (
            _return_rect,
            _item_rects,
            list_panel,
            detail_panel,
            item_height,
            detail_max_scroll,
        ) = draw_effectdex(
            canvas_surface,
            title_font,
            subtitle_font,
            body_font,
            button_font,
            selected_name,
            list_scroll_offset,
            detail_scroll_offset,
            hover_name,
        )
        present_canvas(screen, canvas_surface, canvas_rect)
        detail_scroll_offset = int(clamp(detail_scroll_offset, 0, detail_max_scroll))
        pygame.display.flip()
        clock.tick(FPS)


def win_rate_loop(screen, clock, title_font, subtitle_font, body_font, button_font):
    scroll_offset = 0
    stats = load_win_rate_stats()

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)
        return_rect = pygame.Rect(36, 734, 220, 40)
        rows = build_win_rate_rows(body_font, stats)
        visible_rows = max(1, (608 - 72) // 40)
        max_scroll = max(0, len(rows) - visible_rows)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is not None and return_rect.collidepoint(mapped_pos):
                    return "menu"
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset = int(clamp(scroll_offset - event.y * 26, 0, max_scroll))

        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        hover_name = "return" if mouse_pos is not None and return_rect.collidepoint(mouse_pos) else None
        canvas_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        _, max_scroll = draw_win_rate_screen(
            canvas_surface,
            title_font,
            subtitle_font,
            body_font,
            button_font,
            hover_name,
            scroll_offset,
            stats,
        )
        scroll_offset = int(clamp(scroll_offset, 0, max_scroll))
        present_canvas(screen, canvas_surface, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


def settings_loop(screen, clock, title_font, subtitle_font, body_font, button_font):
    settings = dict(GAME_SETTINGS)

    volume_rect = pygame.Rect(244, 260, 300, 34)
    volume_slider = pygame.Rect(320, 268, 190, 18)
    quality_high_rect = pygame.Rect(290, 330, 110, 40)
    quality_low_rect = pygame.Rect(420, 330, 110, 40)
    entrance_rect = pygame.Rect(244, 400, 312, 40)
    fullscreen_rect = pygame.Rect(244, 460, 312, 40)
    damage_rect = pygame.Rect(244, 520, 312, 40)
    return_rect = pygame.Rect(300, 576, 200, 44)

    dragging_volume = False

    while True:
        canvas_rect, device_pixel_ratio = get_window_transform(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(1, event.w), max(1, event.h)), WINDOW_FLAGS)
                canvas_rect, device_pixel_ratio = get_window_transform(screen)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is None:
                    continue
                if return_rect.collidepoint(mapped_pos):
                    GAME_SETTINGS.update(settings)
                    save_settings(GAME_SETTINGS)
                    return "menu"
                if quality_high_rect.collidepoint(mapped_pos):
                    settings["effects_quality"] = "high"
                elif quality_low_rect.collidepoint(mapped_pos):
                    settings["effects_quality"] = "low"
                elif entrance_rect.collidepoint(mapped_pos):
                    settings["skip_entrance"] = not settings.get("skip_entrance", False)
                elif fullscreen_rect.collidepoint(mapped_pos):
                    settings["fullscreen"] = not settings.get("fullscreen", False)
                    flags = pygame.FULLSCREEN if settings["fullscreen"] else pygame.DOUBLEBUF
                    screen = pygame.display.set_mode((WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT), flags | pygame.DOUBLEBUF)
                    canvas_rect, device_pixel_ratio = get_window_transform(screen)
                elif damage_rect.collidepoint(mapped_pos):
                    settings["show_damage_numbers"] = not settings.get("show_damage_numbers", True)
                elif volume_slider.collidepoint(mapped_pos):
                    dragged_x = clamp(mapped_pos.x - volume_slider.left, 0, volume_slider.width)
                    settings["volume"] = int(round(dragged_x / volume_slider.width * 100))
                    dragging_volume = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_volume = False
            if event.type == pygame.MOUSEMOTION and dragging_volume:
                mapped_pos = map_window_pos_to_canvas(event.pos, canvas_rect, device_pixel_ratio)
                if mapped_pos is not None:
                    dragged_x = clamp(mapped_pos.x - volume_slider.left, 0, volume_slider.width)
                    settings["volume"] = int(round(dragged_x / volume_slider.width * 100))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                GAME_SETTINGS.update(settings)
                save_settings(GAME_SETTINGS)
                return "menu"

        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        hover_name = None
        if mouse_pos is not None:
            for name, rect in (
                ("return", return_rect),
                ("quality_high", quality_high_rect),
                ("quality_low", quality_low_rect),
                ("entrance", entrance_rect),
                ("fullscreen", fullscreen_rect),
                ("damage", damage_rect),
            ):
                if rect.collidepoint(mouse_pos):
                    hover_name = name
                    break

        canvas_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        canvas_surface.fill(BACKGROUND_COLOR)

        title = title_font.render("设置", True, TEXT_COLOR)
        canvas_surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        panel = pygame.Rect(174, 150, 452, 480)
        draw_panel(canvas_surface, panel, MENU_PANEL, accent_color=(110, 170, 255), radius=18)

        # 音量
        volume_label = subtitle_font.render(f"音量：{settings['volume']}", True, TEXT_COLOR)
        canvas_surface.blit(volume_label, volume_rect.topleft)
        draw_panel(canvas_surface, volume_slider, (30, 38, 50), border_color=(74, 82, 92), radius=8)
        fill_w = int(volume_slider.width * settings["volume"] / 100)
        if fill_w > 0:
            pygame.draw.rect(canvas_surface, MENU_ACCENT, pygame.Rect(volume_slider.left, volume_slider.top, max(2, fill_w), volume_slider.height), border_radius=8)
        knob_x = volume_slider.left + fill_w
        pygame.draw.circle(canvas_surface, TEXT_COLOR, (knob_x, volume_slider.centery), 7)

        # 特效品质
        quality_label = subtitle_font.render("特效品质", True, TEXT_COLOR)
        canvas_surface.blit(quality_label, (panel.left + 30, quality_high_rect.top - 30))
        for name, rect in (("高", quality_high_rect), ("低", quality_low_rect)):
            active = settings["effects_quality"] == ("high" if name == "高" else "low")
            color = MENU_ACCENT if active else (MENU_BUTTON_HOVER if hover_name == ("quality_high" if name == "高" else "quality_low") else MENU_BUTTON)
            draw_panel(canvas_surface, rect, color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
            label = body_font.render(name, True, TEXT_COLOR)
            canvas_surface.blit(label, label.get_rect(center=rect.center))

        # 跳过登场演出
        entrance_color = MENU_BUTTON_HOVER if hover_name == "entrance" else MENU_BUTTON
        draw_panel(canvas_surface, entrance_rect, entrance_color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
        entrance_text = body_font.render("跳过登场演出（开场直接开打）", True, TEXT_COLOR)
        canvas_surface.blit(entrance_text, entrance_text.get_rect(center=(entrance_rect.centerx + 20, entrance_rect.centery)))
        if settings.get("skip_entrance", False):
            pygame.draw.circle(canvas_surface, (142, 226, 188), (entrance_rect.left + 22, entrance_rect.centery), 8)

        # 全屏
        fullscreen_color = MENU_BUTTON_HOVER if hover_name == "fullscreen" else MENU_BUTTON
        draw_panel(canvas_surface, fullscreen_rect, fullscreen_color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
        fullscreen_text = body_font.render("全屏显示", True, TEXT_COLOR)
        canvas_surface.blit(fullscreen_text, fullscreen_text.get_rect(center=(fullscreen_rect.centerx + 20, fullscreen_rect.centery)))
        if settings.get("fullscreen", False):
            pygame.draw.circle(canvas_surface, (142, 226, 188), (fullscreen_rect.left + 22, fullscreen_rect.centery), 8)

        # 伤害数字显示
        damage_color = MENU_BUTTON_HOVER if hover_name == "damage" else MENU_BUTTON
        draw_panel(canvas_surface, damage_rect, damage_color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
        damage_text = body_font.render("显示伤害数字（关闭更清爽）", True, TEXT_COLOR)
        canvas_surface.blit(damage_text, damage_text.get_rect(center=(damage_rect.centerx + 20, damage_rect.centery)))
        if settings.get("show_damage_numbers", True):
            pygame.draw.circle(canvas_surface, (142, 226, 188), (damage_rect.left + 22, damage_rect.centery), 8)

        return_color = MENU_BUTTON_HOVER if hover_name == "return" else MENU_BUTTON
        draw_panel(canvas_surface, return_rect, return_color, radius=12, shadow_offset=(2, 2))
        return_text = button_font.render("返回", True, TEXT_COLOR)
        canvas_surface.blit(return_text, return_text.get_rect(center=return_rect.center))

        present_canvas(screen, canvas_surface, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


def battle_loop(screen, clock, title_font, small_font, button_font, player_count, timed_weapon_orb_drops_enabled=True, skip_entrance=False, low_effects=False, game_state=None, bet_job=None):
    if game_state is None:
        game_state = create_game_state(player_count, timed_weapon_orb_drops_enabled)
    if bet_job is not None:
        game_state["bet_job"] = bet_job
    scene_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    frame_surface = pygame.Surface((BATTLE_WINDOW_WIDTH, BATTLE_WINDOW_HEIGHT))
    sidebar_surface = pygame.Surface((BATTLE_SIDEBAR_WIDTH, BATTLE_WINDOW_HEIGHT))
    paused = False
    active_tab = "output"
    speed_multiplier = 1.0
    follow_character_id = None
    follow_timer = 0.0
    sidebar_rows = []
    sidebar_scroll = 0
    show_result_summary = False

    if skip_entrance:
        for character in game_state["characters"]:
            character.spawn_fx_timer = 0.0
    elif low_effects:
        for character in game_state["characters"]:
            character.spawn_fx_timer = min(character.spawn_fx_timer, 0.6)

    top_three_jobs = set(get_top_three_jobs())
    for character in game_state["characters"]:
        character.gold_spawn_fx = character.job_name in top_three_jobs

    for character in game_state["characters"]:
        if character.is_soul_casket():
            character.design_immobile = True
            character.spawn_soul_blade(game_state)

        runtime._LIVE_GAME_STATE = game_state
    runtime._LIVE_SPEED_MULTIPLIER = 1.0

    battle_font = create_ui_font(20, bold=True)
    result_title_font = create_ui_font(30, bold=True)

    while True:
        runtime._LIVE_GAME_STATE = game_state
        runtime._LIVE_SPEED_MULTIPLIER = speed_multiplier
        game_state["_pause_flag"] = paused
        dt = clock.tick(FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        end_button_rect = pygame.Rect(250, 610, 300, 74)
        pause_button_rects = {
            "resume": pygame.Rect(250, 320, 300, 68),
            "menu": pygame.Rect(250, 404, 300, 68),
        }
        sidebar_tab_rects = {
            "output": pygame.Rect(SCREEN_WIDTH + 22, 62, 84, 30),
            "taken": pygame.Rect(SCREEN_WIDTH + 112, 62, 84, 30),
            "kills": pygame.Rect(SCREEN_WIDTH + 202, 62, 84, 30),
        }

        result_summary_rect = pygame.Rect(120, 300, 560, 420)
        result_summary_close_rect = pygame.Rect(310, 664, 180, 40)
        result_summary_toggle_rect = pygame.Rect(580, 640, 180, 36)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not game_state["winner_text"]:
                paused = not paused
            if event.type == pygame.KEYDOWN and not game_state["winner_text"]:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    speed_multiplier = 1.0
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    speed_multiplier = 2.0
                elif event.key in (pygame.K_3, pygame.K_4, pygame.K_KP3, pygame.K_KP4):
                    speed_multiplier = 4.0
            if event.type == pygame.MOUSEWHEEL and not game_state["winner_text"]:
                wheel_mouse_x, wheel_mouse_y = pygame.mouse.get_pos()
                if wheel_mouse_x >= SCREEN_WIDTH:
                    participant_count = len(game_state.get("battle_participants", []))
                    max_scroll = max(0, participant_count - SIDEBAR_VISIBLE_ROWS)
                    sidebar_scroll = int(clamp(sidebar_scroll - event.y, 0, max_scroll))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if result_summary_close_rect.collidepoint(event.pos) and game_state["winner_text"] and show_result_summary:
                    show_result_summary = False
                elif result_summary_toggle_rect.collidepoint(event.pos) and game_state["winner_text"]:
                    show_result_summary = not show_result_summary
                elif sidebar_tab_rects["output"].collidepoint(event.pos):
                    active_tab = "output"
                elif sidebar_tab_rects["taken"].collidepoint(event.pos):
                    active_tab = "taken"
                elif sidebar_tab_rects["kills"].collidepoint(event.pos):
                    active_tab = "kills"
                elif game_state["winner_text"] and end_button_rect.collidepoint(event.pos):
                    return "menu"
                elif paused and pause_button_rects["resume"].collidepoint(event.pos):
                    paused = False
                elif paused and pause_button_rects["menu"].collidepoint(event.pos):
                    return "menu"
                else:
                    for row in sidebar_rows:
                        if row["rect"].collidepoint(event.pos):
                            follow_character_id = row["character"].id
                            follow_timer = 2.5
                            break

        if not paused and not game_state["winner_text"]:
            steps = max(1, int(speed_multiplier))
            sim_dt = dt * speed_multiplier / steps
            for _ in range(steps):
                game_state["elapsed_time"] += sim_dt
                apply_faction_bonuses(game_state)
                update_weapon_orbs(game_state, sim_dt)
                living_characters = get_living_characters(game_state)
                for character in living_characters:
                    character.update(sim_dt, game_state)

                for index, character in enumerate(living_characters):
                    for other in living_characters[index + 1 :]:
                        character.resolve_overlap(other)
                for shield_wall in game_state["shield_walls"]:
                    for character in living_characters:
                        shield_wall.block_character(character)

                for orb in game_state["weapon_orbs"]:
                    if not orb.alive:
                        continue
                    for character in living_characters:
                        if character.try_pickup_weapon(orb):
                            break

                update_world_lists(game_state, sim_dt)
                game_state["characters"] = [character for character in game_state["characters"] if character.alive]
                living_characters = get_living_main_characters(game_state)
                if len(living_characters) == 1:
                    winner = living_characters[0]
                    game_state["winner_text"] = f"Player {winner.id} ({winner.job_name}) Wins!"
                    game_state["winner_character"] = winner
                elif len(living_characters) == 0:
                    game_state["winner_text"] = "No Winner"
                    game_state["winner_character"] = None
                if game_state["winner_text"]:
                    break

        if game_state["winner_text"] and not game_state["result_recorded"]:
            record_win_rate_result(game_state)
            game_state["result_recorded"] = True

        if follow_timer > 0:
            follow_timer = max(0.0, follow_timer - dt)

        draw_grid(scene_surface)
        draw_ui(scene_surface, title_font, small_font, game_state)
        pygame.draw.rect(scene_surface, BORDER_COLOR, ARENA_RECT, 3)
        draw_world(scene_surface, game_state, small_font)
        frame_surface.fill(BACKGROUND_COLOR)
        if not paused and game_state["shake_timer"] > 0:
            shake_strength = game_state["shake_magnitude"] * (game_state["shake_timer"] / SCREEN_SHAKE_DURATION)
            offset = (
                round(random.uniform(-shake_strength, shake_strength)),
                round(random.uniform(-shake_strength, shake_strength)),
            )
        else:
            offset = (0, 0)
        if follow_character_id is not None and follow_timer > 0 and not game_state["winner_text"]:
            follow_target = next((c for c in game_state["characters"] if c.id == follow_character_id and c.alive), None)
            if follow_target is not None:
                arena_center_x = ARENA_RECT.centerx
                arena_center_y = ARENA_RECT.centery
                dx = clamp((follow_target.pos.x - arena_center_x) * 0.55, -90.0, 90.0)
                dy = clamp((follow_target.pos.y - arena_center_y) * 0.55, -70.0, 70.0)
                offset = (offset[0] - round(dx), offset[1] - round(dy))
        frame_surface.blit(scene_surface, offset)
        if game_state["winner_text"]:
            draw_battle_end_button(frame_surface, button_font, end_button_rect.collidepoint(mouse_pos))
            if show_result_summary:
                draw_result_summary(
                    frame_surface,
                    result_title_font,
                    battle_font,
                    game_state,
                    result_summary_rect,
                    result_summary_close_rect,
                )
            summary_hover = result_summary_toggle_rect.collidepoint(mouse_pos)
            toggle_color = MENU_BUTTON_HOVER if summary_hover else MENU_BUTTON
            draw_panel(frame_surface, result_summary_toggle_rect, toggle_color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
            label = battle_font.render("查看结算" if not show_result_summary else "隐藏结算", True, TEXT_COLOR)
            frame_surface.blit(label, label.get_rect(center=result_summary_toggle_rect.center))
        elif paused:
            pause_hover = next((name for name, rect in pause_button_rects.items() if rect.collidepoint(mouse_pos)), None)
            draw_pause_menu(frame_surface, title_font, small_font, button_font, pause_hover)

        if follow_character_id is not None and follow_timer > 0 and not game_state["winner_text"]:
            follow_target = next((c for c in game_state["characters"] if c.id == follow_character_id and c.alive), None)
            if follow_target is not None:
                draw_follow_panel(frame_surface, battle_font, small_font, follow_target)

        sidebar_surface.fill((10, 14, 20))
        sidebar_rows = draw_battle_sidebar(
            sidebar_surface,
            title_font,
            small_font,
            small_font,
            game_state,
            active_tab,
            next((key for key, rect in sidebar_tab_rects.items() if rect.collidepoint(mouse_pos)), None),
            follow_character_id,
            scroll_offset=sidebar_scroll,
            speed_text=f"{speed_multiplier:g}",
        )
        frame_surface.blit(sidebar_surface, (SCREEN_WIDTH, 0))
        screen.blit(frame_surface, (0, 0))
        pygame.display.flip()


def main():
    pygame.init()
    menu_flags = WINDOW_FLAGS | (pygame.FULLSCREEN if GAME_SETTINGS.get("fullscreen") else 0)
    screen = pygame.display.set_mode((WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT), menu_flags)
    pygame.display.set_caption("Pygame Auto Battler")
    clock = pygame.time.Clock()
    title_font = create_ui_font(24, bold=True)
    subtitle_font = create_ui_font(18)
    button_font = create_ui_font(28, bold=True)
    small_font = create_ui_font(16)

    while True:
        menu_result = main_menu(screen, clock, title_font, subtitle_font, button_font)
        if menu_result is None:
            break
        action = menu_result[0]
        if action == "pokedex":
            result = pokedex_loop(screen, clock, title_font, subtitle_font, small_font, button_font)
            if result is None:
                break
            continue
        if action == "effects":
            result = effectdex_loop(screen, clock, title_font, subtitle_font, small_font, button_font)
            if result is None:
                break
            continue
        if action == "win_rate":
            result = win_rate_loop(screen, clock, title_font, subtitle_font, small_font, button_font)
            if result is None:
                break
            continue
        if action == "settings":
            result = settings_loop(screen, clock, title_font, subtitle_font, small_font, button_font)
            if result is None:
                break
            continue
        if action == "ban":
            result = ban_loop(screen, clock, title_font, subtitle_font, small_font, button_font)
            if result is None:
                break
            continue
        if action == "duel":
            result = duel_loop(screen, clock, title_font, subtitle_font, small_font, button_font)
            if result is None:
                break
            continue
        player_count = menu_result[1]
        timed_weapon_orb_drops_enabled = not menu_result[2] if len(menu_result) > 2 else True
        if GAME_SETTINGS.get("skip_entrance"):
            apply_skip_entrance = True
        else:
            apply_skip_entrance = False
        screen = pygame.display.set_mode((BATTLE_WINDOW_WIDTH, BATTLE_WINDOW_HEIGHT), BATTLE_WINDOW_FLAGS)
        prep_state = create_game_state(player_count, timed_weapon_orb_drops_enabled)
        bet_job = bet_loop(screen, clock, title_font, subtitle_font, small_font, button_font, prep_state)
        if bet_job is None:
            break
        if bet_job == "cancel":
            screen = pygame.display.set_mode((WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT), menu_flags)
            continue
        if bet_job == "skip":
            bet_job = None
        result = battle_loop(
            screen,
            clock,
            title_font,
            small_font,
            button_font,
            player_count,
            timed_weapon_orb_drops_enabled,
            skip_entrance=apply_skip_entrance,
            low_effects=GAME_SETTINGS.get("effects_quality") == "low",
            game_state=prep_state,
            bet_job=bet_job,
        )
        screen = pygame.display.set_mode((WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT), menu_flags)
        if result is None:
            break

    pygame.quit()


if __name__ == "__main__":
    sys.excepthook = handle_unhandled_exception
    try:
        main()
    finally:
        pygame.quit()
