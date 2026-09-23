# -*- coding: utf-8 -*-
"""引擎层：图形工具 / 目标选择 / 特效实体 / 角色 / 技能 / 世界模拟与绘制。

依赖 game.data（数据）与 game.runtime（共享全局）。
"""
import math
import random

import pygame

from game.data import *
from game import runtime

def clamp(value, low, high):
    return max(low, min(high, value))


def fit_rect_to_canvas(canvas_size, target_size):
    canvas_width, canvas_height = canvas_size
    target_width, target_height = target_size
    if canvas_width <= 0 or canvas_height <= 0 or target_width <= 0 or target_height <= 0:
        return pygame.Rect(0, 0, 0, 0)
    scale = min(target_width / canvas_width, target_height / canvas_height)
    width = max(1, int(round(canvas_width * scale)))
    height = max(1, int(round(canvas_height * scale)))
    left = (target_width - width) // 2
    top = (target_height - height) // 2
    return pygame.Rect(left, top, width, height)


def get_window_transform(window_surface):
    window_size = window_surface.get_size()
    reported_window_size = pygame.display.get_window_size()
    if reported_window_size[0] <= 0 or reported_window_size[1] <= 0:
        reported_window_size = window_size
    device_pixel_ratio = (
        window_size[0] / reported_window_size[0] if reported_window_size[0] > 0 else 1.0,
        window_size[1] / reported_window_size[1] if reported_window_size[1] > 0 else 1.0,
    )
    canvas_rect = fit_rect_to_canvas((SCREEN_WIDTH, SCREEN_HEIGHT), window_size)
    return canvas_rect, device_pixel_ratio


def map_window_pos_to_canvas(window_pos, canvas_rect, device_pixel_ratio):
    if window_pos is None or canvas_rect.width <= 0 or canvas_rect.height <= 0:
        return None
    pixel_x = window_pos[0] * device_pixel_ratio[0]
    pixel_y = window_pos[1] * device_pixel_ratio[1]
    if not canvas_rect.collidepoint(pixel_x, pixel_y):
        return None
    return pygame.Vector2(
        (pixel_x - canvas_rect.left) * SCREEN_WIDTH / canvas_rect.width,
        (pixel_y - canvas_rect.top) * SCREEN_HEIGHT / canvas_rect.height,
    )


def present_canvas(window_surface, canvas_surface, canvas_rect):
    window_surface.fill(LETTERBOX_COLOR)
    if canvas_rect.width <= 0 or canvas_rect.height <= 0:
        return
    try:
        scaled_canvas = pygame.transform.smoothscale(canvas_surface, canvas_rect.size)
    except pygame.error:
        scaled_canvas = pygame.transform.scale(canvas_surface, canvas_rect.size)
    window_surface.blit(scaled_canvas, canvas_rect)


def get_damage_kind(damage_type, source_character=None):
    damage_type = str(damage_type)
    if damage_type.startswith("true_"):
        return None
    if damage_type == "basic_melee":
        if source_character is not None and source_character.job_name in TRUE_BASIC_JOBS:
            return None
        return DAMAGE_KIND_PHYSICAL
    if damage_type == "basic":
        if source_character is not None and source_character.job_name in TRUE_BASIC_JOBS:
            return None
        if source_character is not None and source_character.job_name in SPELL_BASIC_JOBS:
            return DAMAGE_KIND_SPELL
        return DAMAGE_KIND_PHYSICAL
    if damage_type.startswith("design_physical_"):
        return DAMAGE_KIND_PHYSICAL
    if damage_type.startswith("design_spell_"):
        return DAMAGE_KIND_SPELL
    if damage_type in PHYSICAL_DAMAGE_TYPES:
        return DAMAGE_KIND_PHYSICAL
    if damage_type in SPELL_DAMAGE_TYPES:
        return DAMAGE_KIND_SPELL
    if damage_type.startswith("weapon_"):
        return DAMAGE_KIND_SPELL if damage_type == "weapon_staff" else DAMAGE_KIND_PHYSICAL
    return DAMAGE_KIND_SPELL


def get_damage_text_color(damage_kind, is_true_damage):
    if is_true_damage:
        return DAMAGE_TEXT_TRUE
    if damage_kind == DAMAGE_KIND_PHYSICAL:
        return DAMAGE_TEXT_PHYSICAL
    return DAMAGE_TEXT_SPELL


def random_unit_vector():
    angle = random.uniform(0, math.tau)
    return pygame.Vector2(math.cos(angle), math.sin(angle))


def regular_polygon_points(center, radius, sides, rotation=0.0):
    points = []
    for index in range(sides):
        angle = rotation + math.tau * index / sides
        points.append(
            (
                center[0] + math.cos(angle) * radius,
                center[1] + math.sin(angle) * radius,
            )
        )
    return points


def star_points(center, outer_radius, inner_radius, points, rotation=-math.pi / 2):
    coords = []
    for index in range(points * 2):
        angle = rotation + math.pi * index / points
        radius = outer_radius if index % 2 == 0 else inner_radius
        coords.append((center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius))
    return coords


def point_inside_arena(point, padding=0.0):
    return (
        ARENA_RECT.left + padding <= point.x <= ARENA_RECT.right - padding
        and ARENA_RECT.top + padding <= point.y <= ARENA_RECT.bottom - padding
    )


def segment_intersects_rect(start, end, rect):
    if rect.collidepoint(start) or rect.collidepoint(end):
        return True
    edges = [
        (pygame.Vector2(rect.topleft), pygame.Vector2(rect.topright)),
        (pygame.Vector2(rect.topright), pygame.Vector2(rect.bottomright)),
        (pygame.Vector2(rect.bottomright), pygame.Vector2(rect.bottomleft)),
        (pygame.Vector2(rect.bottomleft), pygame.Vector2(rect.topleft)),
    ]
    return any(segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in edges)


def segments_intersect(a1, a2, b1, b2):
    def ccw(p1, p2, p3):
        return (p3.y - p1.y) * (p2.x - p1.x) > (p2.y - p1.y) * (p3.x - p1.x)

    return ccw(a1, b1, b2) != ccw(a2, b1, b2) and ccw(a1, a2, b1) != ccw(a1, a2, b2)


def random_spawn_point(arena_rect, padding):
    return pygame.Vector2(
        random.uniform(arena_rect.left + padding, arena_rect.right - padding),
        random.uniform(arena_rect.top + padding, arena_rect.bottom - padding),
    )


def distance_point_to_segment(point, segment_start, segment_end):
    segment = segment_end - segment_start
    segment_length_sq = segment.length_squared()
    if segment_length_sq == 0:
        return (point - segment_start).length()
    t = clamp((point - segment_start).dot(segment) / segment_length_sq, 0.0, 1.0)
    projection = segment_start + segment * t
    return (point - projection).length()


def segment_intersects_oriented_rect(point, start_pos, end_pos, half_width, length, padding=0.0):
    direction = end_pos - start_pos
    if direction.length_squared() == 0:
        direction = pygame.Vector2(1, 0)
    else:
        direction = direction.normalize()
    side = pygame.Vector2(-direction.y, direction.x)
    half_length = length * 0.5
    for wave_pos in (start_pos, end_pos):
        rect_center = wave_pos + direction * half_length
        offset = point - rect_center
        if abs(offset.dot(direction)) <= half_length + padding and abs(offset.dot(side)) <= half_width + padding:
            return True
    return False


def draw_shape_icon(surface, shape, color, center, radius, outline=True):
    radius = max(4, radius)
    if outline:
        shadow_offset = max(1, int(round(radius * 0.14)))
        highlight_offset = max(1, int(round(radius * 0.11)))
        shadow_center = (center[0] + shadow_offset, center[1] + shadow_offset)
        highlight_center = (center[0] - highlight_offset, center[1] - highlight_offset)
        draw_shape_icon(surface, shape, shade_color(color, 0.42), shadow_center, radius, outline=False)
        draw_shape_icon(surface, shape, mix_color(color, (255, 255, 255), 0.28), highlight_center, max(3, int(radius * 0.72)), outline=False)
    if shape == "circle":
        pygame.draw.circle(surface, color, center, round(radius))
    elif shape == "square":
        rect = pygame.Rect(0, 0, radius * 1.8, radius * 1.8)
        rect.center = center
        pygame.draw.rect(surface, color, rect, border_radius=3)
    elif shape == "triangle":
        points = [
            (center[0], center[1] - radius),
            (center[0] - radius, center[1] + radius),
            (center[0] + radius, center[1] + radius),
        ]
        pygame.draw.polygon(surface, color, points)
    elif shape == "diamond":
        points = [
            (center[0], center[1] - radius),
            (center[0] + radius, center[1]),
            (center[0], center[1] + radius),
            (center[0] - radius, center[1]),
        ]
        pygame.draw.polygon(surface, color, points)
    elif shape == "pentagon":
        pygame.draw.polygon(surface, color, regular_polygon_points(center, radius, 5, -math.pi / 2))
    elif shape == "hexagon":
        pygame.draw.polygon(surface, color, regular_polygon_points(center, radius, 6, math.pi / 6))
    elif shape == "cross":
        horizontal = pygame.Rect(0, 0, radius * 1.8, radius * 0.7)
        vertical = pygame.Rect(0, 0, radius * 0.7, radius * 1.8)
        horizontal.center = center
        vertical.center = center
        pygame.draw.rect(surface, color, horizontal, border_radius=2)
        pygame.draw.rect(surface, color, vertical, border_radius=2)
    elif shape == "star5":
        pygame.draw.polygon(surface, color, star_points(center, radius, radius * 0.45, 5))
    elif shape == "star6":
        pygame.draw.polygon(surface, color, star_points(center, radius, radius * 0.52, 6))
    elif shape == "hourglass":
        points = [
            (center[0] - radius, center[1] - radius),
            (center[0] + radius, center[1] - radius),
            (center[0] + radius * 0.32, center[1]),
            (center[0] + radius, center[1] + radius),
            (center[0] - radius, center[1] + radius),
            (center[0] - radius * 0.32, center[1]),
        ]
        pygame.draw.polygon(surface, color, points)
    elif shape == "oval":
        rect = pygame.Rect(0, 0, radius * 2.25, radius * 1.5)
        rect.center = center
        pygame.draw.ellipse(surface, color, rect)
    elif shape == "wide":
        rect = pygame.Rect(0, 0, radius * 2.45, radius * 1.3)
        rect.center = center
        pygame.draw.rect(surface, color, rect, border_radius=max(3, int(radius * 0.35)))
    elif shape == "fan":
        blade = [
            (center[0], center[1] - radius),
            (center[0] + radius * 0.96, center[1] - radius * 0.12),
            (center[0] + radius * 0.68, center[1] + radius * 0.82),
            (center[0] + radius * 0.02, center[1] + radius * 0.98),
            (center[0] - radius * 0.68, center[1] + radius * 0.36),
            (center[0] - radius * 0.88, center[1] - radius * 0.22),
        ]
        pygame.draw.polygon(surface, color, blade)
        handle = pygame.Rect(0, 0, radius * 0.38, radius * 1.18)
        handle.center = (center[0] - radius * 0.22, center[1] + radius * 0.82)
        pygame.draw.rect(surface, tuple(max(0, int(channel * 0.72)) for channel in color), handle, border_radius=3)
    elif shape == "truck":
        body = pygame.Rect(0, 0, radius * 2.3, radius * 1.15)
        cab = pygame.Rect(0, 0, radius * 0.95, radius * 0.92)
        body.center = (center[0] - radius * 0.12, center[1])
        cab.center = (center[0] + radius * 0.72, center[1])
        pygame.draw.rect(surface, color, body, border_radius=4)
        pygame.draw.rect(surface, color, cab, border_radius=4)
    elif shape == "heart_down":
        left = pygame.Vector2(center[0] - radius * 0.5, center[1] - radius * 0.15)
        right = pygame.Vector2(center[0] + radius * 0.5, center[1] - radius * 0.15)
        bottom = pygame.Vector2(center[0], center[1] + radius)
        pygame.draw.circle(surface, color, (round(left.x), round(left.y)), round(radius * 0.55))
        pygame.draw.circle(surface, color, (round(right.x), round(right.y)), round(radius * 0.55))
        pygame.draw.polygon(surface, color, [(center[0] - radius, center[1]), (center[0] + radius, center[1]), bottom])
    elif shape == "cross_x":
        points_a = [
            (center[0] - radius, center[1] - radius * 0.45),
            (center[0] - radius * 0.45, center[1] - radius),
            (center[0] + radius, center[1] + radius * 0.45),
            (center[0] + radius * 0.45, center[1] + radius),
        ]
        points_b = [
            (center[0] + radius, center[1] - radius * 0.45),
            (center[0] + radius * 0.45, center[1] - radius),
            (center[0] - radius, center[1] + radius * 0.45),
            (center[0] - radius * 0.45, center[1] + radius),
        ]
        pygame.draw.polygon(surface, color, points_a)
        pygame.draw.polygon(surface, color, points_b)
    elif shape == "slim_diamond":
        points = [
            (center[0], center[1] - radius * 1.2),
            (center[0] + radius * 0.72, center[1]),
            (center[0], center[1] + radius * 1.2),
            (center[0] - radius * 0.72, center[1]),
        ]
        pygame.draw.polygon(surface, color, points)
    elif shape == "shards":
        shard_points = [
            [(center[0] - radius * 0.95, center[1] - radius * 0.25), (center[0] - radius * 0.25, center[1] - radius), (center[0], center[1] - radius * 0.1)],
            [(center[0] + radius * 0.2, center[1] - radius * 0.9), (center[0] + radius, center[1] - radius * 0.25), (center[0] + radius * 0.2, center[1])],
            [(center[0] - radius * 0.15, center[1] + radius * 0.1), (center[0] + radius * 0.85, center[1] + radius * 0.25), (center[0] + radius * 0.15, center[1] + radius)],
            [(center[0] - radius, center[1] + radius * 0.2), (center[0] - radius * 0.1, center[1] + radius * 0.05), (center[0] - radius * 0.45, center[1] + radius)],
        ]
        for shard in shard_points:
            pygame.draw.polygon(surface, color, shard)
    elif shape == "trapezoid":
        points = [
            (center[0] - radius * 0.75, center[1] - radius),
            (center[0] + radius * 0.75, center[1] - radius),
            (center[0] + radius, center[1] + radius),
            (center[0] - radius, center[1] + radius),
        ]
        pygame.draw.polygon(surface, color, points)
    elif shape == "music_note":
        note_head = (round(center[0] - radius * 0.25), round(center[1] + radius * 0.35))
        pygame.draw.circle(surface, color, note_head, round(radius * 0.45))
        stem_start = (round(center[0] + radius * 0.05), round(center[1] + radius * 0.25))
        stem_end = (round(center[0] + radius * 0.05), round(center[1] - radius))
        pygame.draw.line(surface, color, stem_start, stem_end, max(4, int(radius * 0.28)))
        flag = [
            (center[0] + radius * 0.05, center[1] - radius),
            (center[0] + radius * 0.85, center[1] - radius * 0.55),
            (center[0] + radius * 0.2, center[1] - radius * 0.12),
        ]
        pygame.draw.polygon(surface, color, flag)
    elif shape == "half_circle":
        rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        rect.center = center
        pygame.draw.circle(surface, color, center, round(radius))
        pygame.draw.rect(surface, BACKGROUND_COLOR, (rect.left - 2, center[1], rect.width + 4, radius + 4))
        pygame.draw.line(surface, color, (center[0] - radius, center[1]), (center[0] + radius, center[1]), max(3, int(radius * 0.2)))
    elif shape == "butterfly":
        wing_r = max(3, int(radius * 0.42))
        left_wing = (center[0] - int(radius * 0.5), center[1])
        right_wing = (center[0] + int(radius * 0.5), center[1])
        pygame.draw.circle(surface, color, left_wing, wing_r)
        pygame.draw.circle(surface, color, right_wing, wing_r)
        pygame.draw.line(surface, color, (center[0], center[1] - int(radius * 0.6)), (center[0], center[1] + int(radius * 0.6)), max(2, int(radius * 0.3)))
        pygame.draw.circle(surface, BORDER_COLOR, left_wing, wing_r, 1)
        pygame.draw.circle(surface, BORDER_COLOR, right_wing, wing_r, 1)
    elif shape == "crescent":
        pygame.draw.circle(surface, color, center, round(radius))
        cutout_center = (round(center[0] + radius * 0.34), round(center[1] - radius * 0.08))
        cutout_color = BACKGROUND_COLOR
        if isinstance(surface, pygame.Surface) and surface.get_flags() & pygame.SRCALPHA:
            cutout_color = (0, 0, 0, 0)
        pygame.draw.circle(surface, cutout_color, cutout_center, round(radius * 0.82))
    elif shape == "star5_down":
        pygame.draw.polygon(surface, color, star_points(center, radius, radius * 0.45, 5, math.pi / 2))
    elif shape == "gear":
        pygame.draw.circle(surface, color, center, round(radius * 0.78))
        for index in range(8):
            angle = math.tau * index / 8
            tooth_center = (center[0] + math.cos(angle) * radius * 0.95, center[1] + math.sin(angle) * radius * 0.95)
            tooth = pygame.Rect(0, 0, radius * 0.34, radius * 0.42)
            tooth.center = tooth_center
            pygame.draw.rect(surface, color, tooth, border_radius=2)
        pygame.draw.circle(surface, BACKGROUND_COLOR, center, round(radius * 0.28))
    elif shape == "triangle_down":
        points = [
            (center[0], center[1] + radius * 1.15),
            (center[0] - radius * 0.72, center[1] - radius),
            (center[0] + radius * 0.72, center[1] - radius),
        ]
        pygame.draw.polygon(surface, color, points)
    elif shape == "ring":
        pygame.draw.circle(surface, color, center, round(radius))
        pygame.draw.circle(surface, BACKGROUND_COLOR, center, round(radius * 0.56))
    else:
        pygame.draw.polygon(surface, color, regular_polygon_points(center, radius, 8, math.pi / 8))
    if outline:
        pygame.draw.circle(surface, BORDER_COLOR, center, round(radius + 2), 2)


def wrap_text(text, font, max_width):
    lines = []
    current = ""
    for paragraph in str(text).splitlines() or [""]:
        for word in paragraph.split(" "):
            if not word:
                continue
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            for character in word:
                candidate = f"{current}{character}"
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = character
        if current:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines


def build_pokedex_detail_surface(detail_panel, data, subtitle_font, body_font, stats=None):
    detail_viewport = pygame.Rect(detail_panel.left + 12, detail_panel.top + 12, detail_panel.width - 24, detail_panel.height - 24)
    content_width = detail_viewport.width
    text_x = 16
    value_x = text_x + 122
    stat_spacing = 42
    desc_spacing = 28
    desc_width = content_width - 32
    passive_name = data.get("display_passive_name", "")
    passive_desc = data.get("display_passive_description", "")
    passive_lines = wrap_text(passive_desc, body_font, desc_width) if passive_desc else []
    skill_lines = wrap_text(data["display_skill_description"], body_font, desc_width)

    job_name = data.get("job_name", "")
    form_block = []
    if job_name == DRAGON_JOB_NAME:
        form_block = [
            ("雷形态", "物理近战 · 攻速+30% · 受伤-20% · 每3秒电击最近敌人35真实伤害"),
            ("木形态", "法术中远程 · 射程+50% · 每4秒回复2%最大生命值"),
        ]
    elif job_name == TWIN_MIRROR_JOB_NAME:
        form_block = [("双形态", "白镜(白莲护盾) / 黑镜(黑曜穿透) · 独立血条 · 致命时切换并锁定")]
    form_wrapped = []
    form_lines_total = 0
    if form_block:
        for form_label, form_desc in form_block:
            lines = wrap_text(form_desc, body_font, desc_width - 20)
            form_wrapped.append((form_label, lines))
            form_lines_total += 1 + len(lines)
    stats_start_y = 246 + (28 + form_lines_total * desc_spacing if form_block else 0)

    details = [
        (POKEDEX_UI_TEXT["labels"]["max_hp"], str(data["max_hp"])),
        (POKEDEX_UI_TEXT["labels"]["move_speed"], str(int(data["move_speed"]))),
        (POKEDEX_UI_TEXT["labels"]["attack_type"], data["display_attack_type"]),
        (POKEDEX_UI_TEXT["labels"]["attack_damage"], f"{data['attack_damage']:g}"),
        (POKEDEX_UI_TEXT["labels"]["attack_interval"], f"{data['attack_interval']:.2f} 秒/次"),
        (POKEDEX_UI_TEXT["labels"]["attack_tag"], data["display_attack_tag"]),
        (POKEDEX_UI_TEXT["labels"]["attack_repeat"], f"x{data['attack_repeat']}" if data["attack_repeat"] > 1 else "单次"),
        (POKEDEX_UI_TEXT["labels"]["attack_range"], str(int(data["attack_range"]))),
        (POKEDEX_UI_TEXT["labels"]["physical_resistance"], f"{data['physical_resistance'] * 100:.0f}%"),
        (POKEDEX_UI_TEXT["labels"]["spell_resistance"], f"{data['spell_resistance'] * 100:.0f}%"),
        (POKEDEX_UI_TEXT["labels"]["mp_charge"], data["display_mp_charge_style"]),
        (POKEDEX_UI_TEXT["labels"]["skill"], data["display_skill_name"]),
    ]
    if passive_name:
        details.append((POKEDEX_UI_TEXT["labels"]["passive"], passive_name))
    win_rows = []
    if stats is not None:
        entry = stats.get(job_name, {})
        matches = max(0, int(entry.get("matches", 0)))
        wins = max(0, int(entry.get("wins", 0)))
        if matches > 0:
            win_rows = [
                ("出场", f"{matches} 场"),
                ("胜场", f"{wins} 场"),
                ("胜率", f"{wins / matches * 100.0:.1f}%"),
            ]
        else:
            win_rows = [("战绩", "暂无对战记录")]
    section_y = stats_start_y + len(details) * stat_spacing + 14
    section_height = 0
    if passive_lines:
        section_height += 28 + len(passive_lines) * desc_spacing + 10
    section_height += 28 + len(skill_lines) * desc_spacing
    if win_rows:
        section_height += 28 + len(win_rows) * desc_spacing
    helper_surface = subtitle_font.render(POKEDEX_UI_TEXT["helper"], True, (150, 164, 180))
    helper_y = max(section_y + section_height + 12, detail_viewport.height - helper_surface.get_height() - 8)
    content_height = max(detail_viewport.height, helper_y + helper_surface.get_height() + 8)

    content_surface = pygame.Surface((content_width, int(math.ceil(content_height))), pygame.SRCALPHA)
    preview_center = (content_width // 2, 108)
    draw_shape_icon(content_surface, data["shape"], data["color"], preview_center, 58)
    shape_label = subtitle_font.render(data["display_name"], True, TEXT_COLOR)
    content_surface.blit(shape_label, shape_label.get_rect(center=(content_width // 2, 200)))

    if form_block:
        form_title = subtitle_font.render("形态", True, (255, 214, 120))
        content_surface.blit(form_title, (text_x, 220))
        fy = 248
        for form_label, lines in form_wrapped:
            form_label_s = body_font.render(form_label + ":", True, (240, 200, 100))
            content_surface.blit(form_label_s, (text_x, fy))
            fy += desc_spacing
            for line in lines:
                line_surface = body_font.render(line, True, (196, 208, 224))
                content_surface.blit(line_surface, (text_x + 22, fy))
                fy += desc_spacing

    y = stats_start_y
    for label, value in details:
        label_surface = subtitle_font.render(f"{label}:", True, TEXT_COLOR)
        value_surface = body_font.render(value, True, (196, 208, 224))
        content_surface.blit(label_surface, (text_x, y))
        content_surface.blit(value_surface, (value_x, y + 2))
        y += stat_spacing

    if passive_lines:
        passive_title = subtitle_font.render(POKEDEX_UI_TEXT["labels"]["passive_desc"], True, TEXT_COLOR)
        content_surface.blit(passive_title, (text_x, y))
        y += 28
        for line in passive_lines:
            line_surface = body_font.render(line, True, (196, 208, 224))
            content_surface.blit(line_surface, (text_x, y))
            y += desc_spacing
        y += 10

    desc_title = subtitle_font.render(POKEDEX_UI_TEXT["labels"]["skill_desc"], True, TEXT_COLOR)
    content_surface.blit(desc_title, (text_x, y))
    y += 28
    for line in skill_lines:
        line_surface = body_font.render(line, True, (196, 208, 224))
        content_surface.blit(line_surface, (text_x, y))
        y += desc_spacing

    if win_rows:
        win_title = subtitle_font.render("战绩", True, (120, 210, 160))
        content_surface.blit(win_title, (text_x, y))
        if stats is not None and job_name in set(get_top_three_jobs(stats, min_matches=3)):
            badge = subtitle_font.render("🏆 当前前三", True, (255, 208, 54))
            content_surface.blit(badge, (text_x + 78, y))
        y += 28
        for label, value in win_rows:
            label_surface = subtitle_font.render(f"{label}:", True, TEXT_COLOR)
            value_surface = body_font.render(value, True, (196, 208, 224))
            content_surface.blit(label_surface, (text_x, y))
            content_surface.blit(value_surface, (value_x, y + 2))
            y += desc_spacing

    content_surface.blit(helper_surface, helper_surface.get_rect(midbottom=(content_width // 2, content_height - 8)))
    max_scroll = max(0, int(math.ceil(content_height - detail_viewport.height)))
    return content_surface, detail_viewport, max_scroll


def build_effect_detail_surface(detail_panel, data, subtitle_font, body_font):
    detail_viewport = pygame.Rect(detail_panel.left + 12, detail_panel.top + 12, detail_panel.width - 24, detail_panel.height - 24)
    content_width = detail_viewport.width
    text_x = 16
    section_gap = 18
    line_gap = 28
    content_surface = pygame.Surface((content_width, detail_viewport.height), pygame.SRCALPHA)

    title_surface = subtitle_font.render(data["display_name"], True, TEXT_COLOR)
    title_rect = title_surface.get_rect(center=(content_width // 2, 52))
    content_surface.blit(title_surface, title_rect)

    category_text = body_font.render(data["display_category"], True, TEXT_COLOR)
    pill_width = max(116, category_text.get_width() + 28)
    pill_rect = pygame.Rect((content_width - pill_width) // 2, 88, pill_width, 34)
    pygame.draw.rect(content_surface, data["category_color"], pill_rect, border_radius=16)
    pygame.draw.rect(content_surface, BORDER_COLOR, pill_rect, 1, border_radius=16)
    content_surface.blit(category_text, category_text.get_rect(center=pill_rect.center))

    sections = [
        (EFFECT_UI_TEXT["labels"]["category"], data["display_category"]),
        (EFFECT_UI_TEXT["labels"]["tags"], data["display_tags"]),
        (EFFECT_UI_TEXT["labels"]["sources"], data["display_sources"]),
        (EFFECT_UI_TEXT["labels"]["description"], data["description"]),
    ]

    y = 148
    for label, value in sections:
        label_surface = subtitle_font.render(f"{label}:", True, TEXT_COLOR)
        content_surface.blit(label_surface, (text_x, y))
        y += 32
        for line in wrap_text(value, body_font, content_width - 32):
            line_surface = body_font.render(line, True, (196, 208, 224))
            content_surface.blit(line_surface, (text_x, y))
            y += line_gap
        y += section_gap

    helper_surface = subtitle_font.render(EFFECT_UI_TEXT["helper"], True, (150, 164, 180))
    content_height = max(detail_viewport.height, y + helper_surface.get_height() + 12)
    if content_height > content_surface.get_height():
        expanded_surface = pygame.Surface((content_width, int(math.ceil(content_height))), pygame.SRCALPHA)
        expanded_surface.blit(content_surface, (0, 0))
        content_surface = expanded_surface
    content_surface.blit(helper_surface, helper_surface.get_rect(midbottom=(content_width // 2, content_height - 8)))
    max_scroll = max(0, int(math.ceil(content_height - detail_viewport.height)))
    return content_surface, detail_viewport, max_scroll


def get_living_characters(game_state):
    return [character for character in game_state["characters"] if character.alive]


def get_living_main_characters(game_state):
    return [character for character in game_state["characters"] if character.alive and getattr(character, "is_main_character", True)]


def get_targetables(game_state):
    targetables = []
    for character in game_state["characters"]:
        if character.alive and getattr(character, "design_untargetable_timer", 0.0) <= 0 and not getattr(character, "design_banished", False) and getattr(character, "design_sparrow_host_id", None) is None:
            targetables.append(character)
    for decoy in game_state["decoys"]:
        if decoy.alive:
            targetables.append(decoy)
    for summon in game_state["summons"]:
        if summon.alive:
            targetables.append(summon)
    for summon in game_state.get("design_summons", []):
        if summon.alive:
            targetables.append(summon)
    for totem in game_state.get("totems", []):
        if totem.alive:
            targetables.append(totem)
    for banner in game_state.get("banners", []):
        if banner.alive:
            targetables.append(banner)
    return targetables


def select_nearest_enemy(character, characters):
    nearest = None
    nearest_distance_sq = float("inf")
    for other in characters:
        if not other.alive or other.owner_id == character.owner_id or getattr(other, "design_banished", False):
            continue
        distance_sq = (other.pos - character.pos).length_squared()
        if distance_sq < nearest_distance_sq:
            nearest_distance_sq = distance_sq
            nearest = other
    return nearest


def select_lowest_hp_enemy(character, characters):
    enemies = [other for other in characters if other.alive and other.owner_id != character.owner_id and not getattr(other, "design_banished", False)]
    if not enemies:
        return None
    return min(enemies, key=lambda other: (other.hp, (other.pos - character.pos).length_squared()))


def select_farthest_enemy(character, characters):
    enemies = [other for other in characters if other.alive and other.owner_id != character.owner_id and not getattr(other, "design_banished", False)]
    if not enemies:
        return None
    return max(enemies, key=lambda other: (other.pos - character.pos).length_squared())


def select_highest_hp_enemy(character, characters):
    enemies = [other for other in characters if other.alive and other.owner_id != character.owner_id and not getattr(other, "design_banished", False)]
    if not enemies:
        return None
    return max(enemies, key=lambda other: (other.hp, -(other.pos - character.pos).length_squared()))


def select_nearest_targetable(unit, game_state):
    nearest = None
    nearest_score = float("inf")
    for target in get_targetables(game_state):
        if target.owner_id == unit.owner_id or target is unit:
            continue
        base_distance_sq = (target.pos - unit.pos).length_squared()
        score = base_distance_sq * (0.72 if getattr(target, "is_decoy", False) else 1.0)
        if score < nearest_score:
            nearest_score = score
            nearest = target
    return nearest


def select_random_targetable(unit, game_state):
    targets = [target for target in get_targetables(game_state) if target.owner_id != unit.owner_id and target is not unit]
    if not targets:
        return None
    return random.choice(targets)


def apply_aoe_damage(center, radius, amount, owner_id, game_state, source=None, damage_type="skill", count_on_damage_dealt=True):
    hits = 0
    for target in get_targetables(game_state):
        if not target.alive or target.owner_id == owner_id:
            continue
        if (target.pos - center).length() <= radius + getattr(target, "radius", 0):
            if isinstance(target, Character):
                dealt = target.take_damage(
                    amount,
                    source=source,
                    damage_type=damage_type,
                    game_state=game_state,
                    count_on_damage_dealt=count_on_damage_dealt,
                )
            else:
                dealt = target.take_damage(amount, source=source, damage_type=damage_type, game_state=game_state)
            if dealt > 0:
                hits += 1
    return hits


def apply_cone_damage(
    origin,
    direction,
    max_distance,
    half_angle_degrees,
    amount,
    owner_id,
    game_state,
    source=None,
    damage_type="skill",
    count_on_damage_dealt=True,
):
    hits = 0
    if direction.length_squared() == 0:
        return 0
    forward = direction.normalize()
    angle_limit = math.cos(math.radians(half_angle_degrees))
    for target in get_targetables(game_state):
        if not target.alive or target.owner_id == owner_id:
            continue
        offset = target.pos - origin
        distance = offset.length()
        if distance > max_distance + getattr(target, "radius", 0):
            continue
        if distance == 0:
            if isinstance(target, Character):
                dealt = target.take_damage(
                    amount,
                    source=source,
                    damage_type=damage_type,
                    game_state=game_state,
                    count_on_damage_dealt=count_on_damage_dealt,
                )
            else:
                dealt = target.take_damage(amount, source=source, damage_type=damage_type, game_state=game_state)
        else:
            facing = offset.normalize().dot(forward)
            if facing < angle_limit:
                continue
            if isinstance(target, Character):
                dealt = target.take_damage(
                    amount,
                    source=source,
                    damage_type=damage_type,
                    game_state=game_state,
                    count_on_damage_dealt=count_on_damage_dealt,
                )
            else:
                dealt = target.take_damage(amount, source=source, damage_type=damage_type, game_state=game_state)
        if dealt > 0:
            hits += 1
    return hits


def apply_segment_damage(
    start,
    end,
    width,
    amount,
    owner_id,
    game_state,
    source=None,
    damage_type="skill",
    count_on_damage_dealt=True,
):
    hits = 0
    for target in get_targetables(game_state):
        if not target.alive or target.owner_id == owner_id:
            continue
        if distance_point_to_segment(target.pos, start, end) <= width + getattr(target, "radius", 0):
            if isinstance(target, Character):
                dealt = target.take_damage(
                    amount,
                    source=source,
                    damage_type=damage_type,
                    game_state=game_state,
                    count_on_damage_dealt=count_on_damage_dealt,
                )
            else:
                dealt = target.take_damage(amount, source=source, damage_type=damage_type, game_state=game_state)
            if dealt > 0:
                hits += 1
    return hits


def collect_targets_in_cone(origin, direction, max_distance, half_angle_degrees, owner_id, game_state):
    targets = []
    if direction.length_squared() == 0:
        return targets
    forward = direction.normalize()
    angle_limit = math.cos(math.radians(half_angle_degrees))
    for target in get_targetables(game_state):
        if not target.alive or target.owner_id == owner_id:
            continue
        offset = target.pos - origin
        distance = offset.length()
        if distance > max_distance + getattr(target, "radius", 0):
            continue
        if distance == 0 or offset.normalize().dot(forward) >= angle_limit:
            targets.append(target)
    return targets


def has_living_design_summon(game_state, owner_id, summon_type):
    return any(
        summon.alive and summon.owner_id == owner_id and getattr(summon, "summon_type", None) == summon_type
        for summon in game_state.get("design_summons", [])
    )


def trigger_screen_shake(game_state, magnitude, duration=SCREEN_SHAKE_DURATION):
    game_state["shake_timer"] = max(game_state["shake_timer"], duration)
    game_state["shake_magnitude"] = max(game_state["shake_magnitude"], magnitude)


def get_active_equilibrium_arbiter(game_state, exclude_owner_id=None):
    if game_state is None:
        return None
    for character in game_state.get("characters", []):
        if (
            character.alive
            and character.job_name == EQUILIBRIUM_JOB_NAME
            and character.owner_id != exclude_owner_id
        ):
            return character
    return None


def spawn_damage_text(game_state, target, amount, damage_kind=None, is_true_damage=False, text=None, color=None, crit=False):
    if game_state is None or target is None:
        return
    offset = pygame.Vector2(0, -getattr(target, "radius", CHARACTER_RADIUS) - 10)
    new_pos = target.pos + offset
    merge_window = 0.15
    for existing in reversed(game_state["damage_texts"][-6:]):
        if existing.alive and (DAMAGE_TEXT_DURATION - existing.lifetime) < merge_window:
            if (existing.pos - new_pos).length() < 16.0:
                existing.add_amount(amount, text=text, crit=crit)
                return
    game_state["damage_texts"].append(
        DamageText(
            new_pos,
            amount,
            damage_kind=damage_kind,
            is_true_damage=is_true_damage,
            text=text,
            color=color,
            crit=crit,
        )
    )


def apply_equilibrium_field_damage(game_state, source_character, exclude_target=None):
    if game_state is None:
        return
    for target in get_targetables(game_state):
        if not target.alive or target is exclude_target:
            continue
        target.take_damage(
            EQUILIBRIUM_THRESHOLD_FIELD_DAMAGE,
            source=source_character,
            damage_type="design_spell_equilibrium_field",
            game_state=game_state,
            ignore_equilibrium_thresholds=True,
        )


def handle_equilibrium_thresholds(target, pre_damage_hp, source_character, game_state, ignore_equilibrium_thresholds=False):
    if ignore_equilibrium_thresholds or game_state is None or not hasattr(target, "hp") or not hasattr(target, "max_hp"):
        return
    arbiter = get_active_equilibrium_arbiter(game_state, exclude_owner_id=target.owner_id)
    if arbiter is None:
        return
    if target.owner_id == arbiter.owner_id:
        return
    threshold_flags = getattr(target, "equilibrium_thresholds_triggered", None)
    if threshold_flags is None:
        threshold_flags = set()
        setattr(target, "equilibrium_thresholds_triggered", threshold_flags)
    marked = getattr(target, "equilibrium_mark_timer", 0.0) > 0
    for threshold_ratio, threshold_damage in ((0.75, EQUILIBRIUM_THRESHOLD_DICE_DAMAGE), (0.5, EQUILIBRIUM_THRESHOLD_DICE_DAMAGE), (0.25, EQUILIBRIUM_THRESHOLD_EXECUTE_DAMAGE)):
        if threshold_ratio in threshold_flags:
            continue
        threshold_hp = target.max_hp * threshold_ratio
        if pre_damage_hp > threshold_hp and target.hp <= threshold_hp:
            threshold_flags.add(threshold_ratio)
            should_trigger = marked
            if not should_trigger:
                rolled = random.randint(1, 6)
                should_trigger = rolled < 4
                if not should_trigger:
                    if hasattr(target, "apply_equilibrium_mark"):
                        target.apply_equilibrium_mark(EQUILIBRIUM_MARK_DURATION)
                    break
            if marked:
                target.equilibrium_mark_timer = 0.0
            target.take_damage(
                threshold_damage,
                source=arbiter,
                damage_type="true_equilibrium_judgment",
                game_state=game_state,
                ignore_equilibrium_thresholds=True,
            )
            if target.hp <= 0:
                apply_equilibrium_field_damage(game_state, arbiter, exclude_target=target)
            break


DAMAGE_TEXT_CRIT_THRESHOLD = 40.0
SKILL_PRECAST_DURATION = 0.4
HEAL_TEXT_COLOR = (110, 230, 150)


class DamageText:
    def __init__(self, pos, amount, damage_kind=None, is_true_damage=False, text=None, color=None, crit=False):
        self.pos = pygame.Vector2(pos)
        self.amount = max(1, int(round(amount)))
        self.text = text if text is not None else f"-{self.amount}"
        self.color = color if color is not None else get_damage_text_color(damage_kind, is_true_damage)
        self.crit = crit
        self.lifetime = DAMAGE_TEXT_DURATION
        self.alive = True

    def add_amount(self, amount, text=None, crit=False):
        self.amount += max(1, int(round(amount)))
        self.text = text if text is not None else f"-{self.amount}"
        if crit:
            self.crit = True
        self.lifetime = DAMAGE_TEXT_DURATION

    def update(self, dt):
        self.pos.y -= 32 * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface, font):
        alpha = int(255 * clamp(self.lifetime / DAMAGE_TEXT_DURATION, 0.0, 1.0))
        if self.crit:
            age = DAMAGE_TEXT_DURATION - self.lifetime
            scale = 1.7 - 0.7 * clamp(age / 0.10, 0.0, 1.0)
            text_surface = font.render(self.text, True, (255, 224, 120))
            text_surface.set_alpha(alpha)
            w, h = text_surface.get_size()
            scaled_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            glow_surface = pygame.transform.smoothscale(font.render(self.text, True, (255, 170, 40)), scaled_size)
            glow_surface.set_alpha(max(0, alpha // 2))
            text_surface = pygame.transform.smoothscale(text_surface, scaled_size)
            center = (round(self.pos.x), round(self.pos.y))
            surface.blit(glow_surface, glow_surface.get_rect(center=(center[0] + 1, center[1] + 2)))
            surface.blit(text_surface, text_surface.get_rect(center=center))
            return
        text = font.render(self.text, True, self.color)
        text.set_alpha(alpha)
        surface.blit(text, text.get_rect(center=(round(self.pos.x), round(self.pos.y))))


class AttackImpactEffect:
    def __init__(self, pos, color, radius=14, thickness=3, lifetime=0.16, burst_count=6):
        self.pos = pygame.Vector2(pos)
        self.color = color
        self.radius = radius
        self.thickness = thickness
        self.lifetime = lifetime
        self.total_lifetime = lifetime
        self.burst_count = burst_count
        self.alive = True

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface):
        progress = 1.0 - clamp(self.lifetime / self.total_lifetime, 0.0, 1.0)
        alpha = int(255 * clamp(self.lifetime / self.total_lifetime, 0.0, 1.0))
        center = (round(self.pos.x), round(self.pos.y))
        overlay = pygame.Surface((self.radius * 5, self.radius * 5), pygame.SRCALPHA)
        overlay_center = (overlay.get_width() // 2, overlay.get_height() // 2)
        pulse_radius = self.radius + int(progress * self.radius * 1.35)
        ring_color = (*mix_color(self.color, (255, 255, 255), 0.24), alpha)
        core_color = (*self.color, max(48, alpha))
        pygame.draw.circle(overlay, ring_color, overlay_center, max(2, pulse_radius), self.thickness)
        pygame.draw.circle(overlay, core_color, overlay_center, max(2, int(self.radius * 0.45)))
        for index in range(self.burst_count):
            angle = math.tau * index / self.burst_count + progress * 0.8
            inner = pygame.Vector2(math.cos(angle), math.sin(angle)) * (self.radius * 0.22)
            outer = pygame.Vector2(math.cos(angle), math.sin(angle)) * (self.radius + self.radius * progress * 0.85)
            pygame.draw.line(
                overlay,
                (*mix_color(self.color, (255, 255, 255), 0.35), max(28, alpha // 2)),
                (round(overlay_center[0] + inner.x), round(overlay_center[1] + inner.y)),
                (round(overlay_center[0] + outer.x), round(overlay_center[1] + outer.y)),
                2,
            )
        surface.blit(overlay, (center[0] - overlay_center[0], center[1] - overlay_center[1]))


class DeathParticle:
    def __init__(self, pos, color, dust=False):
        self.pos = pygame.Vector2(pos)
        self.vel = random_unit_vector() * random.uniform(55.0, 155.0)
        self.color = color
        self.dust = dust
        self.size = random.randint(2, 4) if dust else random.randint(3, 6)
        self.lifetime = DEATH_PARTICLE_DURATION
        self.alive = True

    def update(self, dt):
        self.pos += self.vel * dt
        self.vel *= max(0.0, 1.0 - 2.2 * dt)
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface):
        alpha = int(255 * clamp(self.lifetime / DEATH_PARTICLE_DURATION, 0.0, 1.0))
        overlay = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        if self.dust:
            pygame.draw.rect(overlay, (*self.color, alpha), (1, 1, self.size * 2, self.size * 2))
        else:
            pygame.draw.circle(overlay, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(overlay, (round(self.pos.x - self.size), round(self.pos.y - self.size)))


class KillBanner:
    def __init__(self, character, text, color=None):
        self.character = character
        self.text = text
        self.color = color if color is not None else (255, 214, 120)
        self.lifetime = 2.2
        self.total_lifetime = 2.2
        self.alive = True
        self.pos = pygame.Vector2(character.pos)

    def update(self, dt):
        self.pos.y -= 22 * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface, font):
        progress = 1.0 - clamp(self.lifetime / self.total_lifetime, 0.0, 1.0)
        alpha = int(255 * (1.0 - progress)) if progress < 0.15 else int(255 * clamp(self.lifetime / (self.total_lifetime * 0.5), 0.0, 1.0))
        alpha = max(0, min(255, alpha))
        text = font.render(self.text, True, self.color)
        text.set_alpha(alpha)
        rect = text.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        panel = rect.inflate(24, 10)
        overlay = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (16, 20, 28, int(alpha * 0.66)), overlay.get_rect(), border_radius=9)
        pygame.draw.rect(overlay, (*self.color, min(255, alpha)), overlay.get_rect(), 2, border_radius=9)
        surface.blit(overlay, panel.topleft)
        surface.blit(text, rect)


KILLSTREAK_BANNERS = {
    3: "三连击破！",
    5: "五连绝杀！",
    8: "八连屠戮！",
    12: "十二连神罚！",
}


class SpellTrailParticle:
    def __init__(self, pos, color, velocity=None, size=3, lifetime=0.24):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(velocity) if velocity is not None else random_unit_vector() * random.uniform(12.0, 32.0)
        self.color = color
        self.size = max(1, int(size))
        self.lifetime = lifetime
        self.total_lifetime = lifetime
        self.alive = True

    def update(self, dt):
        self.pos += self.vel * dt
        self.vel *= max(0.0, 1.0 - 4.8 * dt)
        self.size = max(1, self.size - int(dt * 4))
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface):
        alpha = int(220 * clamp(self.lifetime / self.total_lifetime, 0.0, 1.0))
        overlay = pygame.Surface((self.size * 6, self.size * 6), pygame.SRCALPHA)
        center = (overlay.get_width() // 2, overlay.get_height() // 2)
        glow_color = (*mix_color(self.color, (255, 255, 255), 0.55), max(70, alpha))
        core_color = (*self.color, max(40, alpha))
        pygame.draw.circle(overlay, glow_color, center, self.size * 2)
        pygame.draw.circle(overlay, core_color, center, self.size)
        surface.blit(overlay, (round(self.pos.x - center[0]), round(self.pos.y - center[1])))


class MeleeSwingEffect:
    def __init__(self, start_pos, end_pos, color=TEXT_COLOR):
        self.start_pos = pygame.Vector2(start_pos)
        self.end_pos = pygame.Vector2(end_pos)
        self.color = color
        self.timer = 0.18
        self.total_timer = self.timer
        self.alive = True

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface):
        alpha = int(255 * clamp(self.timer / self.total_timer, 0.0, 1.0))
        direction = self.end_pos - self.start_pos
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        length = direction.length()
        direction = direction.normalize()
        angle = math.degrees(math.atan2(direction.y, direction.x))
        center = (self.start_pos + self.end_pos) * 0.5
        arc_radius = max(20, int(length * 0.58))
        overlay = pygame.Surface((arc_radius * 6, arc_radius * 6), pygame.SRCALPHA)
        overlay_center = (overlay.get_width() // 2, overlay.get_height() // 2)
        arc_rect = pygame.Rect(0, 0, arc_radius * 2, arc_radius * 2)
        arc_rect.center = overlay_center
        sweep_start = math.radians(198)
        sweep_end = math.radians(342)
        # 残影层：三层同心弧（外宽内窄），形成挥动残影
        for layer_index, (scale_f, alpha_mul, width) in enumerate(((0.94, 0.30, 5), (1.0, 0.62, 6), (1.07, 1.0, 7))):
            layer_rect = pygame.Rect(0, 0, int(arc_radius * 2 * scale_f), int(arc_radius * 2 * scale_f))
            layer_rect.center = overlay_center
            layer_alpha = int(alpha * alpha_mul)
            pygame.draw.arc(
                overlay,
                (*mix_color(self.color, (255, 255, 255), 0.22), max(18, layer_alpha)),
                layer_rect,
                sweep_start,
                sweep_end,
                width,
            )
        # 亮核月牙（实心带：外弧-内弧多边形）
        core_radius = arc_radius * 1.0
        inner_radius = arc_radius * 0.78
        mid_angle = (sweep_start + sweep_end) / 2.0
        half_sweep = (sweep_end - sweep_start) / 2.0
        steps = 10
        outer_points = [
            pygame.Vector2(overlay_center) + pygame.Vector2(math.cos(a), math.sin(a)) * core_radius
            for a in [mid_angle - half_sweep + (sweep_end - sweep_start) * i / steps for i in range(steps + 1)]
        ]
        inner_points = [
            pygame.Vector2(overlay_center) + pygame.Vector2(math.cos(a), math.sin(a)) * inner_radius
            for a in [mid_angle + half_sweep - (sweep_end - sweep_start) * i / steps for i in range(steps + 1)]
        ]
        crescent_poly = [(round(p.x), round(p.y)) for p in outer_points + inner_points]
        pygame.draw.polygon(overlay, (*mix_color(self.color, (255, 255, 255), 0.45), int(alpha * 0.8)), crescent_poly)
        # 高光尾尖
        tip_start = pygame.Vector2(overlay_center) + pygame.Vector2(arc_radius * 0.15, -arc_radius * 0.18)
        tip_end = pygame.Vector2(overlay_center) + pygame.Vector2(arc_radius * 0.78, arc_radius * 0.12)
        pygame.draw.line(overlay, (*mix_color(self.color, (255, 255, 255), 0.7), max(60, alpha)), tip_start, tip_end, 3)
        sparkle = [
            (overlay_center[0] + arc_radius * 0.42, overlay_center[1] - arc_radius * 0.08),
            (overlay_center[0] + arc_radius * 0.58, overlay_center[1] - arc_radius * 0.26),
            (overlay_center[0] + arc_radius * 0.76, overlay_center[1] - arc_radius * 0.02),
            (overlay_center[0] + arc_radius * 0.60, overlay_center[1] + arc_radius * 0.20),
        ]
        pygame.draw.polygon(overlay, (*mix_color(self.color, (255, 255, 255), 0.55), max(48, alpha)), sparkle)
        rotated = pygame.transform.rotozoom(overlay, angle, 1.0)
        surface.blit(rotated, rotated.get_rect(center=(round(center.x), round(center.y))))


class WeaponOrb:
    def __init__(self, weapon_id, pos, lifetime=None):
        self.weapon_id = weapon_id
        self.weapon_def = WEAPON_DEFS[weapon_id]
        self.pos = pygame.Vector2(pos)
        self.radius = WEAPON_ORB_RADIUS
        self.color = self.weapon_def["projectile_color"]
        self.alive = True
        self.lifetime = lifetime

    def draw(self, surface, font):
        center = (round(self.pos.x), round(self.pos.y))
        if self.weapon_id == "ColdSpear":
            # 冷锋枪：发光枪尖 + 长矛杆，带青色光晕
            pygame.draw.circle(surface, mix_color(self.color, (255, 255, 255), 0.5), center, int(self.radius * 1.6), 2)
            pygame.draw.circle(surface, self.color, center, self.radius + 2)
            pygame.draw.line(surface, (240, 248, 255), (center[0] - 3, center[1] - 2), (center[0] + 1, center[1] + 9), 3)
            pygame.draw.polygon(surface, (120, 232, 246), [(center[0] - 4, center[1] - 3), (center[0] + 3, center[1] - 2), (center[0] - 1, center[1] - 11)])
            pygame.draw.line(surface, (200, 240, 255), (center[0] - 8, center[1] + 8), (center[0] + 6, center[1] - 4), 1)
            return
        pygame.draw.circle(surface, self.color, center, self.radius)
        pygame.draw.circle(surface, BORDER_COLOR, center, self.radius, 2)
        label = font.render(self.weapon_def["label"], True, (18, 22, 28))
        surface.blit(label, label.get_rect(center=center))


def spawn_weapon_orb(arena_rect, characters, weapon_orbs):
    for _ in range(200):
        position = random_spawn_point(arena_rect, WEAPON_ORB_RADIUS + 12)
        too_close_to_character = any(
            character.alive and (character.pos - position).length() < CHARACTER_RADIUS + 42
            for character in characters
        )
        too_close_to_orb = any(orb.alive and (orb.pos - position).length() < WEAPON_ORB_RADIUS * 3 for orb in weapon_orbs)
        if not too_close_to_character and not too_close_to_orb:
            return WeaponOrb(random.choice(WEAPON_ORB_POOL), position)
    return WeaponOrb(random.choice(WEAPON_ORB_POOL), random_spawn_point(arena_rect, WEAPON_ORB_RADIUS + 12))


class Projectile:
    def __init__(
        self,
        pos,
        vel,
        owner,
        damage,
        color,
        source_kind="basic",
        pierce=False,
        slow_amount=0.0,
        slow_duration=0.0,
        radius=PROJECTILE_RADIUS,
        stun_duration=0.0,
        homing_strength=0.0,
        homing_target_id=None,
        max_range=None,
        explosion_radius=0.0,
        explosion_damage=None,
        explosion_damage_type=None,
        explosion_mp_per_hit=0.0,
        charm_duration=0.0,
        visual_shape="circle",
        on_hit=None,
        spell_trail=False,
    ):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.owner = owner
        self.owner_id = owner.owner_id
        self.damage = damage
        self.color = color
        self.source_kind = source_kind
        self.pierce = pierce
        self.slow_amount = slow_amount
        self.slow_duration = slow_duration
        self.radius = radius
        self.stun_duration = stun_duration
        self.homing_strength = homing_strength
        self.homing_target_id = homing_target_id
        self.max_range = max_range
        self.explosion_radius = explosion_radius
        self.explosion_damage = damage if explosion_damage is None else explosion_damage
        self.explosion_damage_type = explosion_damage_type or source_kind
        self.explosion_mp_per_hit = explosion_mp_per_hit
        self.charm_duration = charm_duration
        self.visual_shape = visual_shape
        self.on_hit = on_hit
        self.spell_trail = bool(
            spell_trail
            or str(source_kind).startswith("design_spell_")
            or source_kind in SPELL_DAMAGE_TYPES
            or (source_kind == "basic" and getattr(owner, "job_name", None) in SPELL_BASIC_JOBS)
        )
        self.distance_traveled = 0.0
        self.prev_pos = pygame.Vector2(pos)
        self.lifetime = PROJECTILE_LIFETIME
        self.alive = True
        self.hit_ids = set()
        source_kind_str = str(source_kind)
        if source_kind_str.startswith("true_"):
            self.trail_style = "white"
        elif any(t in source_kind_str for t in ("mortar", "shell", "cannon", "broadside", "powder", "rock", "comet", "flare", "bomb")):
            self.trail_style = "flame"
        elif self.spell_trail:
            self.trail_style = "glow"
        else:
            self.trail_style = "thin"

    def explode(self, game_state):
        if not self.alive:
            return
        self.alive = False
        if self.explosion_radius > 0:
            hits = apply_aoe_damage(
                self.pos,
                self.explosion_radius,
                self.explosion_damage,
                self.owner_id,
                game_state,
                source=self.owner,
                damage_type=self.explosion_damage_type,
            )
            if self.explosion_mp_per_hit > 0 and hits > 0 and isinstance(self.owner, Character) and self.owner.alive:
                self.owner.gain_mp(hits * self.explosion_mp_per_hit, "mortar_blast")

    def find_homing_target(self, game_state):
        if self.homing_target_id is None:
            return None
        for target in get_targetables(game_state):
            if target.alive and id(target) == self.homing_target_id:
                return target
        return None

    def emit_spell_trail(self, game_state, previous_pos):
        if not self.spell_trail:
            return
        if previous_pos.distance_squared_to(self.pos) <= 0:
            return
        trail_particles = game_state.setdefault("spell_trail_particles", [])
        travel = self.pos - previous_pos
        distance = travel.length()
        if distance <= 0:
            return
        steps = max(1, min(5, int(distance / 8.0) + 1))
        for index in range(steps):
            t = (index + random.random()) / steps
            particle_pos = previous_pos.lerp(self.pos, t)
            particle_pos += random_unit_vector() * random.uniform(0.0, 2.0)
            particle_velocity = -self.vel * random.uniform(0.04, 0.16) + random_unit_vector() * random.uniform(8.0, 20.0)
            particle_size = max(1, int(round(self.radius * random.uniform(0.45, 0.9))))
            trail_particles.append(
                SpellTrailParticle(
                    particle_pos,
                    mix_color(self.color, (255, 255, 255), 0.45),
                    velocity=particle_velocity,
                    size=particle_size,
                    lifetime=random.uniform(0.16, 0.28),
                )
            )

    def update(self, dt, game_state):
        if not self.alive:
            return

        previous_pos = pygame.Vector2(self.pos)
        self.prev_pos = pygame.Vector2(previous_pos)
        target = self.find_homing_target(game_state)
        if self.homing_strength > 0 and target is not None and self.vel.length_squared() > 0:
            speed = self.vel.length()
            desired = (target.pos - self.pos)
            if desired.length_squared() > 0:
                desired = desired.normalize() * speed
                blend = clamp(self.homing_strength * dt, 0.0, 1.0)
                self.vel = self.vel.lerp(desired, blend)
                if self.vel.length_squared() > 0:
                    self.vel.scale_to_length(speed)

        step = self.vel * dt
        self.pos += step
        self.distance_traveled += step.length()
        self.emit_spell_trail(game_state, previous_pos)
        self.lifetime -= dt
        if self.lifetime <= 0 or not point_inside_arena(self.pos, self.radius + 2):
            self.alive = False
            return
        if self.max_range is not None and self.distance_traveled >= self.max_range:
            self.alive = False
            return

        for shield_wall in game_state.get("shield_walls", []):
            if not shield_wall.alive or shield_wall.owner_id == self.owner_id:
                continue
            if segment_intersects_rect(previous_pos, self.pos, shield_wall.rect):
                self.alive = False
                return

        for character in game_state["characters"]:
            if (
                character.alive
                and character.owner_id != self.owner_id
                and getattr(character, "windrunner_storm_timer", 0.0) > 0
                and (character.pos - self.pos).length() <= WINDRUNNER_REPEL_RADIUS + self.radius
            ):
                self.alive = False
                return

        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            object_id = id(target)
            if object_id in self.hit_ids:
                continue
            if (target.pos - self.pos).length_squared() <= (self.radius + target.radius) ** 2:
                if self.explosion_radius > 0:
                    self.explode(game_state)
                    return
                dealt = target.take_damage(self.damage, source=self.owner, damage_type=self.source_kind, game_state=game_state)
                if dealt > 0 and self.slow_amount > 0 and hasattr(target, "apply_slow"):
                    target.apply_slow(self.slow_amount, self.slow_duration)
                if dealt > 0 and self.stun_duration > 0 and hasattr(target, "apply_stun"):
                    target.apply_stun(self.stun_duration)
                if dealt > 0 and self.charm_duration > 0 and hasattr(target, "apply_charm"):
                    target.apply_charm(self.owner_id, self.charm_duration)
                if dealt > 0 and self.source_kind == "design_physical_twin_white" and hasattr(self.owner, "add_true_shield"):
                    self.owner.add_true_shield(TWIN_MIRROR_WHITE_SHIELD)
                if dealt > 0 and callable(self.on_hit):
                    self.on_hit(self, target, dealt, game_state)
                if dealt > 0:
                    spawn_attack_impact(game_state, target.pos, self.color, radius=max(10, int(self.radius * 2.8)), damage=dealt)
                self.hit_ids.add(object_id)
                if not self.pierce:
                    self.alive = False
                    return

    def draw(self, surface):
        center = (round(self.pos.x), round(self.pos.y))
        trail_alpha = int(200 * clamp(self.lifetime / PROJECTILE_LIFETIME, 0.0, 1.0))
        trail_color = (*shade_color(self.color, 0.5), max(50, trail_alpha // 2))
        body_color = (*self.color, trail_alpha)
        pad = max(18, self.radius * 5)
        if self.prev_pos.distance_squared_to(self.pos) > 0:
            min_x = int(min(self.prev_pos.x, self.pos.x) - pad)
            min_y = int(min(self.prev_pos.y, self.pos.y) - pad)
            max_x = int(max(self.prev_pos.x, self.pos.x) + pad)
            max_y = int(max(self.prev_pos.y, self.pos.y) + pad)
        else:
            min_x = int(self.pos.x - pad)
            min_y = int(self.pos.y - pad)
            max_x = int(self.pos.x + pad)
            max_y = int(self.pos.y + pad)
        overlay = pygame.Surface((max(1, max_x - min_x), max(1, max_y - min_y)), pygame.SRCALPHA)
        center_local = (round(self.pos.x - min_x), round(self.pos.y - min_y))
        if self.prev_pos.distance_squared_to(self.pos) > 0:
            prev_local = (round(self.prev_pos.x - min_x), round(self.prev_pos.y - min_y))
            if self.trail_style == "flame":
                flame_layers = ((max(2, self.radius * 3), 0.45, 0.10), (max(1, self.radius * 2), 0.72, 0.24), (1, 1.0, 0.5))
                for width, alpha_mul, white_mix in flame_layers:
                    pygame.draw.line(
                        overlay,
                        (*mix_color(self.color, (255, 255, 255), white_mix), int(trail_alpha * alpha_mul)),
                        prev_local,
                        center_local,
                        width,
                    )
            elif self.trail_style == "white":
                pygame.draw.line(
                    overlay,
                    (*mix_color(self.color, (255, 255, 255), 0.85), int(trail_alpha * 0.55)),
                    prev_local,
                    center_local,
                    max(2, self.radius * 2),
                )
                pygame.draw.line(
                    overlay,
                    (*mix_color(self.color, (255, 255, 255), 0.95), trail_alpha),
                    prev_local,
                    center_local,
                    max(1, self.radius),
                )
            else:
                pygame.draw.line(
                    overlay,
                    trail_color,
                    prev_local,
                    center_local,
                    max(2, self.radius * 2),
                )
                pygame.draw.line(
                    overlay,
                    (*mix_color(self.color, (255, 255, 255), 0.3), max(72, trail_alpha)),
                    prev_local,
                    center_local,
                    max(1, self.radius),
                )
            pygame.draw.circle(overlay, (*mix_color(self.color, (255, 255, 255), 0.45), max(80, trail_alpha)), center_local, self.radius + 3)
        if self.visual_shape == "crescent":
            blade_radius = max(6, self.radius + 3)
            blade_size = blade_radius * 4
            blade_surface = pygame.Surface((blade_size, blade_size), pygame.SRCALPHA)
            blade_center = (blade_size // 2, blade_size // 2)
            pygame.draw.circle(blade_surface, (*self.color, trail_alpha), blade_center, blade_radius)
            cutout_center = (round(blade_center[0] + blade_radius * 0.36), round(blade_center[1] - blade_radius * 0.08))
            pygame.draw.circle(blade_surface, (0, 0, 0, 0), cutout_center, round(blade_radius * 0.82))
            angle = -math.degrees(math.atan2(self.vel.y, self.vel.x)) if self.vel.length_squared() > 0 else 0.0
            blade_surface = pygame.transform.rotozoom(blade_surface, angle, 1.0)
            blade_rect = blade_surface.get_rect(center=center_local)
            overlay.blit(blade_surface, blade_rect)
        else:
            body_shape = self.visual_shape
            if body_shape == "circle" and self.source_kind in {"basic", "weapon_staff"}:
                body_shape = "diamond"
            if body_shape == "circle":
                pygame.draw.circle(overlay, body_color, center_local, self.radius)
            else:
                draw_shape_icon(overlay, body_shape, self.color, center_local, max(4, self.radius + 1), outline=False)
        surface.blit(overlay, (min_x, min_y))


class BeamEvent:
    def __init__(self, start, end, color, style="line"):
        self.start = pygame.Vector2(start)
        self.end = pygame.Vector2(end)
        self.color = color
        self.style = style
        self.timer = 0.22
        self.alive = True

    def update(self, dt, game_state):
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface):
        alpha = int(255 * clamp(self.timer / 0.22, 0.0, 1.0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        start = (round(self.start.x), round(self.start.y))
        end = (round(self.end.x), round(self.end.y))
        if self.style == "crescent":
            pygame.draw.line(overlay, (*self.color, max(40, alpha // 2)), start, end, 3)
            direction = self.end - self.start
            if direction.length_squared() > 0:
                direction = direction.normalize()
                angle = -math.degrees(math.atan2(direction.y, direction.x))
                blade_radius = max(10, min(24, int(self.start.distance_to(self.end) * 0.12) + 8))
                blade_size = blade_radius * 4
                blade_surface = pygame.Surface((blade_size, blade_size), pygame.SRCALPHA)
                blade_center = (blade_size // 2, blade_size // 2)
                pygame.draw.circle(blade_surface, (*self.color, alpha), blade_center, blade_radius)
                cutout_center = (round(blade_center[0] + blade_radius * 0.38), round(blade_center[1] - blade_radius * 0.08))
                pygame.draw.circle(blade_surface, (0, 0, 0, 0), cutout_center, round(blade_radius * 0.82))
                blade_surface = pygame.transform.rotozoom(blade_surface, angle, 1.0)
                blade_rect = blade_surface.get_rect(center=(round((self.start.x + self.end.x) * 0.5), round((self.start.y + self.end.y) * 0.5)))
                overlay.blit(blade_surface, blade_rect)
        else:
            pygame.draw.line(overlay, (*self.color, alpha), start, end, 5)
        surface.blit(overlay, (0, 0))


class Summon:
    def __init__(self, owner, pos, summon_type="basic"):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.pos = pygame.Vector2(pos)
        self.vel = random_unit_vector() * 90.0
        self.radius = 8
        self.color = (248, 248, 248)
        self.hp = 6
        self.max_hp = 6
        self.speed = 145.0
        self.lifetime = 9.0
        self.alive = True
        self.is_decoy = False
        self.summon_type = summon_type
        self.burst_damage = 0.0
        self.burst_radius = 0.0
        if summon_type == "skeleton":
            self.shape = "diamond"
            self.color = (210, 214, 224)
            self.radius = 9
            self.hp = 42
            self.max_hp = 42
            self.speed = 154.0
            self.lifetime = 12.0
            self.damage = 9
            self.burst_damage = 8.0
            self.burst_radius = 36.0

    def take_damage(self, amount, source=None, damage_type="basic", game_state=None, ignore_shields=False, ignore_equilibrium_thresholds=False):
        if not self.alive:
            return 0.0
        pre_damage_hp = self.hp
        self.hp -= amount
        handle_equilibrium_thresholds(self, pre_damage_hp, source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None), game_state, ignore_equilibrium_thresholds=ignore_equilibrium_thresholds)
        if self.hp <= 0:
            if self.summon_type == "skeleton":
                self._explode_on_fall(game_state)
            self.alive = False
        source_character = source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None)
        if source_character is not None and getattr(source_character, "owner_id", None) != self.owner_id and hasattr(source_character, "on_damage_dealt"):
            source_character.on_damage_dealt(amount, damage_type)
        return amount

    def apply_slow(self, amount, duration):
        return None

    def apply_stun(self, duration):
        return None

    def apply_root(self, duration):
        return None

    def apply_knockback(self, direction, distance):
        return None

    def heal(self, amount):
        if not self.alive or amount <= 0:
            return 0.0
        previous_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - previous_hp

    def update(self, dt, game_state):
        if not self.alive:
            return

        self.lifetime -= dt
        if self.lifetime <= 0:
            if self.summon_type == "skeleton":
                self._explode_on_fall(game_state)
            self.alive = False
            return

        target = select_nearest_targetable(self, game_state)
        if target is not None:
            direction = target.pos - self.pos
            if direction.length_squared() > 0:
                move_speed = self.speed
                if self.summon_type == "skeleton" and hasattr(self.owner, "necromancer_bone_stacks"):
                    move_speed *= 1.0 + self.owner.necromancer_bone_stacks * 0.03
                self.vel = direction.normalize() * move_speed

        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)

        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            if (target.pos - self.pos).length() <= self.radius + target.radius:
                damage = 3
                if self.summon_type == "skeleton":
                    damage = self.damage
                    if hasattr(self.owner, "necromancer_bone_stacks"):
                        damage *= 1.0 + self.owner.necromancer_bone_stacks * 0.05
                target.take_damage(damage, source=self.owner, damage_type="summon", game_state=game_state)
                if self.summon_type == "skeleton":
                    self._explode_on_fall(game_state)
                self.alive = False
                return

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (round(self.pos.x), round(self.pos.y)), self.radius)
        pygame.draw.circle(surface, (30, 30, 30), (round(self.pos.x), round(self.pos.y)), self.radius, 1)

    def _explode_on_fall(self, game_state):
        if self.summon_type != "skeleton" or game_state is None:
            return
        apply_aoe_damage(self.pos, self.burst_radius, self.burst_damage, self.owner_id, game_state, source=self.owner, damage_type="necro_bone_burst")
        if self.owner is not None and hasattr(self.owner, "heal"):
            self.owner.heal(12.0)


class Mine:
    def __init__(self, owner, pos):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.pos = pygame.Vector2(pos)
        self.radius = 10
        self.color = (220, 50, 50)
        self.lifetime = 12.0
        self.alive = True
        self.is_decoy = False

    def take_damage(self, amount, source=None, damage_type="basic", game_state=None, ignore_shields=False, ignore_equilibrium_thresholds=False):
        if not self.alive:
            return 0.0
        pre_damage_hp = self.hp
        self.explode(None)
        handle_equilibrium_thresholds(self, pre_damage_hp, source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None), game_state, ignore_equilibrium_thresholds=ignore_equilibrium_thresholds)
        source_character = source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None)
        if source_character is not None and getattr(source_character, "owner_id", None) != self.owner_id and hasattr(source_character, "on_damage_dealt"):
            source_character.on_damage_dealt(amount, damage_type)
        return amount

    def explode(self, game_state):
        if not self.alive:
            return
        self.alive = False
        if game_state is not None:
            radius = 48.0
            damage = 11.0
            if getattr(self.owner, "job_name", None) == "Bomber":
                stacks = getattr(self.owner, "bomber_fuse_stacks", 0)
                if stacks > 0:
                    radius += stacks * 4.0
                    damage *= 1.0 + stacks * 0.12
            apply_aoe_damage(self.pos, radius, damage, self.owner_id, game_state, source=self.owner, damage_type="mine")

    def update(self, dt, game_state):
        if not self.alive:
            return

        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return

        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            if (target.pos - self.pos).length() <= self.radius + target.radius:
                self.explode(game_state)
                return

    def draw(self, surface):
        rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        rect.center = (round(self.pos.x), round(self.pos.y))
        pygame.draw.rect(surface, self.color, rect)
        pygame.draw.rect(surface, BORDER_COLOR, rect, 1)


class PoisonField:
    def __init__(self, owner, pos):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.pos = pygame.Vector2(pos)
        self.corrosion_stacks = getattr(owner, "toxicologist_corrosion_stacks", 0)
        self.radius = TOXIC_FIELD_RADIUS + self.corrosion_stacks * TOXICOLOGIST_CORROSION_FIELD_RADIUS_BONUS
        self.lifetime = TOXIC_FIELD_DURATION + self.corrosion_stacks * TOXICOLOGIST_CORROSION_FIELD_DURATION_BONUS
        self.alive = True
        self.is_decoy = False
        self.color = (110, 220, 86)
        self.poison_progress_rate = 2.0 + self.corrosion_stacks * TOXICOLOGIST_CORROSION_FIELD_PROGRESS_BONUS
        self.damage_per_second = TOXIC_FIELD_DPS + self.corrosion_stacks * TOXICOLOGIST_CORROSION_FIELD_DPS_BONUS

    def update(self, dt, game_state):
        if not self.alive:
            return
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return
        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            if (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0):
                target.take_damage(self.damage_per_second * dt, source=self.owner, damage_type="true_poison_field", game_state=game_state)
                if hasattr(target, "add_poison_progress"):
                    target.add_poison_progress(self.poison_progress_rate * dt)

    def draw(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = int(120 * clamp(self.lifetime / TOXIC_FIELD_DURATION, 0.35, 1.0))
        pygame.draw.circle(overlay, (*self.color, alpha), (round(self.pos.x), round(self.pos.y)), round(self.radius))
        pygame.draw.circle(overlay, (188, 255, 150, min(200, alpha + 40)), (round(self.pos.x), round(self.pos.y)), round(self.radius), 2)
        surface.blit(overlay, (0, 0))


class FrostComet:
    def __init__(self, owner, target):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.core_stacks = getattr(owner, "frost_mage_core_stacks", 0)
        self.pos = pygame.Vector2(owner.pos)
        self.target_pos = pygame.Vector2(target.pos)
        self.radius = 10
        direction = self.target_pos - self.pos
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        self.vel = direction.normalize() * 270.0
        self.color = (156, 232, 255)
        self.alive = True

    def explode(self, game_state):
        if not self.alive:
            return
        self.alive = False
        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            if (target.pos - self.pos).length() <= FROST_NOVA_RADIUS + getattr(target, "radius", 0):
                if hasattr(target, "apply_freeze"):
                    target.apply_freeze(FROST_NOVA_FREEZE * (1.0 + self.core_stacks * FROST_MAGE_CORE_FREEZE_BONUS))
                missing_hp = max(0.0, getattr(target, "max_hp", 0.0) - getattr(target, "hp", 0.0))
                per_tick = 1.0 + missing_hp * 0.01
                total_damage = (FROST_NOVA_TICKS + self.core_stacks * FROST_MAGE_CORE_TICKS_BONUS) * per_tick * (1.0 + self.core_stacks * FROST_MAGE_CORE_DAMAGE_BONUS)
                target.take_damage(total_damage, source=self.owner, damage_type="absolute_zero", game_state=game_state)
        game_state["beam_events"].append(BeamEvent(self.pos, self.pos + pygame.Vector2(1, 0), (150, 240, 255)))

    def update(self, dt, game_state):
        if not self.alive:
            return
        to_target = self.target_pos - self.pos
        step = self.vel * dt
        if step.length_squared() >= to_target.length_squared():
            self.pos = pygame.Vector2(self.target_pos)
            self.explode(game_state)
            return
        self.pos += step
        if not point_inside_arena(self.pos, self.radius + 4):
            self.explode(game_state)
            return
        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            if (target.pos - self.pos).length_squared() <= (self.radius + target.radius) ** 2:
                self.explode(game_state)
                return

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (round(self.pos.x), round(self.pos.y)), self.radius)
        pygame.draw.circle(surface, BORDER_COLOR, (round(self.pos.x), round(self.pos.y)), self.radius, 1)


class ShieldWall:
    def __init__(self, owner, direction):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.pos = pygame.Vector2(owner.pos)
        self.direction = pygame.Vector2(direction)
        if self.direction.length_squared() == 0:
            self.direction = pygame.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.lifetime = SHIELD_WALL_DURATION
        self.alive = True
        tangent = pygame.Vector2(-self.direction.y, self.direction.x)
        center = self.pos + self.direction * (owner.radius + SHIELD_WALL_THICKNESS)
        width = SHIELD_WALL_LENGTH if abs(tangent.x) > abs(tangent.y) else SHIELD_WALL_THICKNESS
        height = SHIELD_WALL_LENGTH if abs(tangent.y) > abs(tangent.x) else SHIELD_WALL_THICKNESS
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (round(center.x), round(center.y))

    def update(self, dt, game_state):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def block_character(self, character):
        if not self.alive or character.owner_id == self.owner_id or not self.rect.colliderect(character.rect):
            return
        overlap = character.rect.clip(self.rect)
        if overlap.width <= 0 or overlap.height <= 0:
            return
        if overlap.width < overlap.height:
            shift = overlap.width + 1
            if character.pos.x < self.rect.centerx:
                character.pos.x -= shift
            else:
                character.pos.x += shift
            character.vel.x *= -0.15
        else:
            shift = overlap.height + 1
            if character.pos.y < self.rect.centery:
                character.pos.y -= shift
            else:
                character.pos.y += shift
            character.vel.y *= -0.15
        character.pos.x = clamp(character.pos.x, ARENA_RECT.left + character.radius, ARENA_RECT.right - character.radius)
        character.pos.y = clamp(character.pos.y, ARENA_RECT.top + character.radius, ARENA_RECT.bottom - character.radius)
        character.update_rect()

    def draw(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = int(150 * clamp(self.lifetime / SHIELD_WALL_DURATION, 0.3, 1.0))
        pygame.draw.rect(overlay, (120, 190, 255, alpha), self.rect, border_radius=4)
        pygame.draw.rect(overlay, (235, 245, 255, min(220, alpha + 40)), self.rect, 2, border_radius=4)
        surface.blit(overlay, (0, 0))


class Totem:
    def __init__(self, owner, pos):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.pos = pygame.Vector2(pos)
        self.radius = 14
        self.hp = SHAMAN_TOTEM_HP
        self.max_hp = SHAMAN_TOTEM_HP
        self.cooldown = SHAMAN_TOTEM_INTERVAL
        self.alive = True
        self.is_decoy = False
        self.color = (220, 48, 48)
        self.shape = "square"
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def take_damage(self, amount, source=None, damage_type="basic", game_state=None, ignore_shields=False, ignore_equilibrium_thresholds=False):
        if not self.alive or amount <= 0:
            return 0.0
        pre_damage_hp = self.hp
        self.hp -= amount
        handle_equilibrium_thresholds(self, pre_damage_hp, source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None), game_state, ignore_equilibrium_thresholds=ignore_equilibrium_thresholds)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return amount

    def update(self, dt, game_state):
        if not self.alive:
            return
        self.cooldown -= dt
        if self.cooldown > 0:
            return
        self.cooldown += SHAMAN_TOTEM_INTERVAL
        candidates = [
            target
            for target in get_targetables(game_state)
            if target.alive
            and target.owner_id != self.owner_id
            and (target.pos - self.pos).length() <= SHAMAN_TOTEM_RANGE + getattr(target, "radius", 0)
        ]
        if not candidates:
            return
        target = max(candidates, key=lambda candidate: (candidate.pos - self.pos).length_squared())
        target.take_damage(SHAMAN_TOTEM_DAMAGE, source=self.owner, damage_type="lightning_totem", game_state=game_state)
        game_state["beam_events"].append(BeamEvent(self.pos, target.pos, (255, 92, 92)))

    def draw(self, surface):
        center = (round(self.pos.x), round(self.pos.y))
        draw_shape_icon(surface, self.shape, self.color, center, self.radius - 1)
        bar_width = 24
        hp_rect = pygame.Rect(round(self.pos.x - bar_width / 2), round(self.pos.y - self.radius - 10), bar_width, 4)
        pygame.draw.rect(surface, HEALTH_BG, hp_rect, border_radius=2)
        if self.hp > 0:
            fill = hp_rect.copy()
            fill.width = max(1, int(hp_rect.width * (self.hp / self.max_hp)))
            pygame.draw.rect(surface, self.color, fill, border_radius=2)
        pygame.draw.rect(surface, BORDER_COLOR, hp_rect, 1, border_radius=2)


class Banner:
    def __init__(self, owner, pos):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.pos = pygame.Vector2(pos)
        self.radius = 12
        self.hp = BANNER_HP
        self.max_hp = BANNER_HP
        self.lifesteal_timer = 0.0
        self.alive = True
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def take_damage(self, amount, source=None, damage_type="basic", game_state=None, ignore_shields=False, ignore_equilibrium_thresholds=False):
        if not self.alive or amount <= 0:
            return 0.0
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            if self.owner is not None and getattr(self.owner, "alive", False) and hasattr(self.owner, "design_banner_respawn_timer"):
                self.owner.design_banner_respawn_timer = BANNER_RESPAWN_DELAY
        return amount

    def update(self, dt, game_state):
        if not self.alive:
            return
        if self.lifesteal_timer > 0:
            self.lifesteal_timer = max(0.0, self.lifesteal_timer - dt)
        for ally in game_state.get("characters", []):
            if not ally.alive or ally.owner_id != self.owner_id:
                continue
            if (ally.pos - self.pos).length() <= BANNER_RADIUS + getattr(ally, "radius", 0):
                ally.design_banner_zone_timer = 0.6
                if self.lifesteal_timer > 0:
                    ally.design_banner_lifesteal_timer = 0.6

    def draw(self, surface, label_font=None):
        center = (round(self.pos.x), round(self.pos.y))
        pygame.draw.circle(surface, BANNER_COLOR, center, 14, 2)
        pygame.draw.line(surface, (200, 208, 216), (center[0], center[1] - 8), (center[0], center[1] - 34), 3)
        flag_points = [
            (center[0], center[1] - 34),
            (center[0] + 18, center[1] - 28),
            (center[0], center[1] - 22),
        ]
        pygame.draw.polygon(surface, (60, 92, 64), flag_points)
        pygame.draw.polygon(surface, (*BANNER_COLOR, 220), flag_points)
        hp_rect = pygame.Rect(center[0] - 12, center[1] - 46, 24, 4)
        pygame.draw.rect(surface, HEALTH_BG, hp_rect, border_radius=2)
        if self.hp > 0:
            fill = hp_rect.copy()
            fill.width = max(1, int(hp_rect.width * (self.hp / self.max_hp)))
            pygame.draw.rect(surface, (120, 220, 120), fill, border_radius=2)


class DesignEffect:
    def __init__(self, effect_type, owner, pos=None, **params):
        self.effect_type = effect_type
        self.owner = owner
        self.owner_id = owner.owner_id if owner is not None else params.get("owner_id")
        self.pos = pygame.Vector2(pos if pos is not None else owner.pos)
        self.params = dict(params)
        self.radius = float(params.get("radius", 24.0))
        self.lifetime = float(params.get("lifetime", 1.0))
        self.alive = True
        self.timer = 0.0
        self.hit_ids = set()
        self.hit_counts = {}
        self.direction = pygame.Vector2(params.get("direction", pygame.Vector2()))
        if self.direction.length_squared() > 0:
            self.direction = self.direction.normalize()
        self.velocity = pygame.Vector2(params.get("velocity", pygame.Vector2()))
        self.data = dict(params)
        self.rect = pygame.Rect(0, 0, 0, 0)

    def affect_targets(self, game_state, predicate, callback):
        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            if predicate(target):
                callback(target)

    def update(self, dt, game_state):
        if not self.alive:
            return
        self.timer += dt
        self.lifetime -= dt
        if self.effect_type == "trap":
            def on_touch(target):
                target.take_damage(self.data.get("damage", 40.0), source=self.owner, damage_type="design_physical_trap", game_state=game_state)
                if hasattr(target, "apply_disarm"):
                    target.apply_disarm(self.data.get("disarm_duration", 3.0))
                self.alive = False

            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                on_touch,
            )
        elif self.effect_type == "meteor":
            if self.lifetime <= 0:
                apply_aoe_damage(
                    self.pos,
                    self.radius,
                    self.data.get("damage", 150.0),
                    self.owner_id,
                    game_state,
                    source=self.owner,
                    damage_type=self.data.get("damage_type", "design_spell_meteor"),
                )
                self.alive = False
        elif self.effect_type == "windstorm_blades":
            interval = float(self.data.get("interval", 0.10))
            total = int(self.data.get("total", 8))
            fired = int(self.data.get("fired", 0))
            while fired < total and self.timer >= (fired + 1) * interval:
                fired += 1
                self.fire_windstorm_blade(game_state, fired)
            self.data["fired"] = fired
            if fired >= total:
                global_damage = float(self.data.get("global_damage", 0.0))
                if global_damage > 0:
                    for target in get_targetables(game_state):
                        if target.alive and target.owner_id != self.owner_id:
                            target.take_damage(global_damage, source=self.owner, damage_type="design_physical_windstorm_global", game_state=game_state)
                self.alive = False
        elif self.effect_type == "rail_train":
            delay = float(self.data.get("delay", 0.0))
            if delay > 0:
                self.data["delay"] = max(0.0, delay - dt)
                return
            speed = float(self.data.get("speed", RAIL_SPEED))
            traveled = float(self.data.get("traveled", 0.0)) + speed * dt
            self.data["traveled"] = traveled
            self.pos += self.direction * speed * dt
            half_len = float(self.data.get("length", RAIL_LENGTH)) * 0.5
            half_w = float(self.data.get("width", RAIL_WIDTH)) * 0.5
            for target in get_targetables(game_state):
                if not target.alive or target.owner_id == self.owner_id:
                    continue
                offset = target.pos - self.pos
                along = offset.dot(self.direction)
                if abs(along) > half_len + getattr(target, "radius", 0.0):
                    continue
                perp = offset - self.direction * along
                if perp.length() > half_w + getattr(target, "radius", 0.0):
                    continue
                target_id = id(target)
                if target_id not in self.hit_ids:
                    # 首撞（V1）：重撞伤害 + 垂直撞飞 + 眩晕
                    self.hit_ids.add(target_id)
                    target.take_damage(RAIL_DAMAGE, source=self.owner, damage_type="design_physical_rail_train", game_state=game_state)
                    call_target_method(target, "apply_stun", RAIL_STUN_DURATION)
                    knock_side = pygame.Vector2(-self.direction.y, self.direction.x) * random.choice((-1.0, 1.0))
                    call_target_method(target, "apply_knockback", knock_side, RAIL_KNOCKBACK)
                    spawn_attack_impact(game_state, target.pos, RAIL_LIGHT_COLOR, radius=12, thickness=2, burst_count=8)
                else:
                    # 碾压持续（V2）：被车体压住每 0.5s 受 6 伤（每秒 12）
                    grind_t = self.hit_counts.get(target_id, 0.0) + dt
                    self.hit_counts[target_id] = grind_t
                    while grind_t >= RAIL_GRIND_INTERVAL:
                        grind_t -= RAIL_GRIND_INTERVAL
                        target.take_damage(RAIL_GRIND_DAMAGE, source=self.owner, damage_type="design_physical_rail_grind", game_state=game_state)
                        spawn_attack_impact(game_state, target.pos, (232, 200, 120), radius=8, thickness=2, burst_count=4)
                    self.hit_counts[target_id] = grind_t
            if traveled >= float(self.data.get("total_travel", 0.0)):
                spawn_attack_impact(game_state, self.pos, RAIL_LIGHT_COLOR, radius=16, thickness=3, burst_count=12)
                game_state["shake_timer"] = max(game_state.get("shake_timer", 0.0), 0.1)
                game_state["shake_magnitude"] = max(game_state.get("shake_magnitude", 0.0), 4.0)
                self.alive = False
        elif self.effect_type == "soul_chain":
            target_id = self.data.get("target_id")
            target = next((candidate for candidate in get_targetables(game_state) if id(candidate) == target_id), None)
            chain = getattr(self.owner, "soul_arbiter_chains", {}).get(target_id) if self.owner is not None else None
            if self.owner is None or not getattr(self.owner, "alive", False) or chain is None or target is None or not target.alive:
                self.alive = False
            else:
                self.pos = pygame.Vector2(self.owner.pos)
        elif self.effect_type == "equilibrium_mark":
            target_id = self.data.get("target_id")
            target = next((candidate for candidate in get_targetables(game_state) if id(candidate) == target_id), None)
            if target is None or not target.alive:
                self.alive = False
            else:
                self.pos = pygame.Vector2(target.pos)
                self.radius = getattr(target, "radius", CHARACTER_RADIUS) + 10.0
        elif self.effect_type == "equilibrium_pulse":
            if self.lifetime <= 0:
                self.alive = False
        elif self.effect_type == "valkyrie_landing":
            if self.lifetime <= 0:
                self.alive = False
        elif self.effect_type == "abyss_charge":
            if self.lifetime <= 0:
                self._abyss_ray_resolve(game_state)
        elif self.effect_type == "flame_ring":
            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                lambda target: target.take_damage(
                    self.data.get("dps", FLAME_WHEEL_CIRCLE_DPS) * dt,
                    source=self.owner,
                    damage_type="design_spell_flame_ring",
                    game_state=game_state,
                ),
            )
        elif self.effect_type == "rift_line":
            self.affect_targets(
                game_state,
                lambda target: distance_point_to_segment(target.pos, self.pos - self.data.get("direction", pygame.Vector2(0, 0)) * self.data.get("length", 1.0) * 0.5, self.pos + self.data.get("direction", pygame.Vector2(0, 0)) * self.data.get("length", 1.0) * 0.5) <= getattr(target, "radius", 0) + self.radius,
                lambda target: target.take_damage(
                    self.data.get("dps", RIFT_LINE_DPS) * dt,
                    source=self.owner,
                    damage_type="design_spell_rift_line",
                    game_state=game_state,
                ),
            )
        elif self.effect_type == "rift_field":
            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                lambda target: target.apply_slow(RIFT_SLOW, 0.25) if hasattr(target, "apply_slow") else None,
            )
            if self.lifetime <= 0:
                apply_aoe_damage(
                    self.pos,
                    RIFT_DETONATION_RADIUS,
                    RIFT_DETONATION_DAMAGE,
                    self.owner_id,
                    game_state,
                    source=self.owner,
                    damage_type="design_spell_rift_detonate",
                )
                self.alive = False
        elif self.effect_type == "soul_slash":
            blade_id = self.data.get("blade_id")
            blade = None
            if blade_id is not None:
                for summoned in game_state.get("design_summons", []):
                    if summoned.summon_type == "soul_blade" and id(summoned) == blade_id and summoned.alive:
                        blade = summoned
                        break
            if blade is not None:
                self.pos = pygame.Vector2(blade.pos)
            else:
                # 剑灵死亡：斩击中断
                self.alive = False
                return
            if self.lifetime <= 0:
                strikes_left = int(self.data.get("strikes_left", 9))
                max_total = int(self.data.get("max_total", SOUL_NINE_SLASH_MAX_TOTAL))
                total_done = int(self.data.get("total_done", 0))
                target = None
                target_id = self.data.get("target_id")
                for candidate in get_targetables(game_state):
                    if id(candidate) == target_id and candidate.alive:
                        target = candidate
                        break
                if target is None or not target.alive:
                    target = select_nearest_enemy(self.owner, game_state["characters"]) if self.owner is not None else None
                    if target is not None:
                        self.data["target_id"] = id(target)
                if target is not None and target.alive and self.owner is not None:
                    crit = random.random() < SOUL_NINE_SLASH_CRIT_CHANCE
                    damage = SOUL_NINE_SLASH_DAMAGE * (SOUL_NINE_SLASH_CRIT_MULT if crit else 1.0)
                    dealt = target.take_damage(damage, source=self.owner, damage_type="design_physical_soul_slash", game_state=game_state)
                    slash_color = SOUL_SLASH_CRIT_COLOR if crit else SOUL_SLASH_COLOR
                    attack_origin = pygame.Vector2(self.pos)
                    game_state["beam_events"].append(BeamEvent(attack_origin, target.pos, slash_color))
                    spawn_attack_impact(game_state, target.pos, slash_color, radius=12 if not crit else 18, thickness=3, burst_count=10 if not crit else 14)
                    if dealt <= 0 or not target.alive:
                        target = select_nearest_enemy(self.owner, game_state["characters"]) if self.owner is not None else None
                        if target is not None:
                            self.data["target_id"] = id(target)
                            self.data["retargeted"] = True
                    extra_gain = SOUL_NINE_SLASH_CRIT_EXTRA if crit else 0
                else:
                    extra_gain = 0
                total_done += 1
                self.data["total_done"] = total_done
                strikes_left = strikes_left - 1 + extra_gain
                if total_done < max_total:
                    strikes_left = min(strikes_left, max_total - total_done)
                self.data["strikes_left"] = strikes_left
                if strikes_left <= 0 or total_done >= max_total:
                    self.alive = False
                else:
                    self.lifetime = SOUL_NINE_SLASH_DELAY
        elif self.effect_type == "swamp":
            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                lambda target: target.apply_slow(self.data.get("slow", 0.7), 0.25) if hasattr(target, "apply_slow") else None,
            )
        elif self.effect_type == "black_hole":
            self.affect_targets(
                game_state,
                lambda target: True,
                lambda target: self._pull_target(target, dt, self.data.get("pull", 55.0)),
            )
            if self.lifetime <= 0:
                apply_aoe_damage(
                    self.pos,
                    self.radius,
                    self.data.get("damage", 15.0),
                    self.owner_id,
                    game_state,
                    source=self.owner,
                    damage_type="true_design_black_hole",
                )
                self.alive = False
        elif self.effect_type == "mirror_void":
            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                lambda target: self._pull_target(target, dt, self.data.get("pull", 55.0)),
            )
            if self.lifetime <= 0:
                affected = [
                    target
                    for target in get_targetables(game_state)
                    if target.alive and target.owner_id != self.owner_id and (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0)
                ]
                apply_aoe_damage(
                    self.pos,
                    self.radius,
                    self.data.get("damage", 55.0),
                    self.owner_id,
                    game_state,
                    source=self.owner,
                    damage_type="design_spell_mirror_shatter",
                )
                slow_amount = self.data.get("slow", 0.5)
                slow_duration = self.data.get("slow_duration", 3.0)
                for target in affected:
                    if hasattr(target, "apply_slow"):
                        target.apply_slow(slow_amount, slow_duration)
                self.alive = False
        elif self.effect_type == "gravity":
            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                lambda target: self._pull_and_damage(target, dt, game_state, self.data.get("dps", 20.0), "design_spell_gravity"),
            )
        elif self.effect_type == "pillar":
            def pillar_hit(target):
                dealt = target.take_damage(self.data.get("dps", 25.0) * dt, source=self.owner, damage_type="design_spell_pillar", game_state=game_state)
                if dealt > 0 and self.owner is not None and (self.owner.pos - self.pos).length() <= self.radius + self.owner.radius:
                    self.owner.heal(self.data.get("heal", 10.0) * dt)

            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                pillar_hit,
            )
        elif self.effect_type == "fire_trail":
            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                lambda target: target.take_damage(self.data.get("dps", 5.0) * dt, source=self.owner, damage_type="design_spell_firetrail", game_state=game_state),
            )
        elif self.effect_type == "construct":
            pass
        elif self.effect_type == "arcane_field":
            if self.owner is None or not getattr(self.owner, "alive", False):
                self.alive = False
            else:
                tick = self.data.get("tick", MAGE_ARCANE_FIELD_TICK)
                self.data["tick_accumulator"] = self.data.get("tick_accumulator", 0.0) + dt
                while self.data["tick_accumulator"] >= tick:
                    self.data["tick_accumulator"] -= tick

                    def field_hit(target):
                        target.take_damage(
                            self.data.get("damage", MAGE_ARCANE_FIELD_DAMAGE),
                            source=self.owner,
                            damage_type="design_spell_arcane_field",
                            game_state=game_state,
                        )
                        if hasattr(target, "apply_slow"):
                            target.apply_slow(self.data.get("slow", MAGE_ARCANE_FIELD_SLOW), self.data.get("slow_duration", MAGE_ARCANE_FIELD_TICK))

                    self.affect_targets(
                        game_state,
                        lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                        field_hit,
                    )
            if self.lifetime <= 0:
                self.alive = False
        elif self.effect_type == "sound_ring":
            if self.timer < self.data.get("delay", 0.0):
                return
            active_time = self.timer - self.data.get("delay", 0.0)
            current_radius = self.data.get("start_radius", 10.0) + active_time * self.data.get("expand_speed", 120.0)
            self.radius = current_radius
            def ring_hit(target):
                target_id = id(target)
                if target_id in self.hit_ids:
                    return
                if abs((target.pos - self.pos).length() - current_radius) <= self.data.get("thickness", 14.0) + getattr(target, "radius", 0):
                    self.hit_ids.add(target_id)
                    target.take_damage(self.data.get("damage", 40.0), source=self.owner, damage_type="design_spell_sound", game_state=game_state)
                    if hasattr(target, "apply_stun"):
                        target.apply_stun(self.data.get("stun", ACOUSTIC_WAVE_STUN))

            self.affect_targets(game_state, lambda target: True, ring_hit)
        elif self.effect_type == "aurora":
            self.pos += self.velocity * dt
            in_radius = lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0)

            def first_hit(target):
                target_id = id(target)
                if target_id in self.hit_ids:
                    return
                self.hit_ids.add(target_id)
                target.take_damage(self.data.get("damage", 60.0), source=self.owner, damage_type="design_spell_aurora", game_state=game_state)
                if hasattr(target, "apply_blind"):
                    target.apply_blind(self.data.get("blind", 2.0))
                if isinstance(target, Character):
                    target.design_aurora_burn = AURORA_BURN_STACKS
                    target.design_aurora_burn_timer = 0.0
                    target.design_aurora_burn_source = self.owner

            self.affect_targets(game_state, in_radius, first_hit)
            if not point_inside_arena(self.pos, self.radius + 4):
                self.alive = False
        elif self.effect_type == "water_fish":
            if self.owner is None or not getattr(self.owner, "alive", False):
                self.alive = False
            elif self.data.get("follow_owner", True):
                self.data["orbit_angle"] = self.data.get("orbit_angle", 0.0) + self.data.get("orbit_speed", 1.8) * dt
                angle = self.data["orbit_angle"]
                orbit_radius = self.data.get("orbit_radius", 24.0)
                bob = math.sin(self.timer * 3.0) * 3.0
                self.pos = pygame.Vector2(self.owner.pos) + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit_radius + pygame.Vector2(0, bob)
        elif self.effect_type == "sea_wave":
            if self.owner is None or not getattr(self.owner, "alive", False):
                self.alive = False
            elif self.timer >= self.data.get("delay", 0.0):
                if not self.data.get("returning", False):
                    start_pos = pygame.Vector2(self.pos)
                    self.pos += self.direction * self.data.get("speed", SEA_SAGE_WAVE_SPEED) * dt
                    self.data["travel"] = self.data.get("travel", 0.0) + (self.pos - start_pos).length()
                    self._sea_wave_collide(game_state, start_pos, self.pos)
                    if self.data.get("stage", 1) == 3:
                        if self.data.get("returning", False) or self.data.get("travel", 0.0) >= self.data.get("range", SEA_SAGE_WAVE_RANGE):
                            self.data["returning"] = True
                    else:
                        if self.data.get("travel", 0.0) >= self.data.get("range", SEA_SAGE_WAVE_RANGE):
                            self.alive = False
                if self.data.get("returning", False) and self.alive:
                    to_owner = self.owner.pos - self.pos
                    if to_owner.length_squared() > 0:
                        self.direction = to_owner.normalize()
                    self.pos += self.direction * self.data.get("return_speed", SEA_SAGE_WAVE_RETURN_SPEED) * dt
                    if (self.owner.pos - self.pos).length() <= self.owner.radius + self.radius:
                        self.owner.heal(self.data.get("return_heal", SEA_SAGE_WAVE_RETURN_HEAL))
                        self.owner.consume_all_sea_fish(game_state)
                        self.alive = False
        elif self.effect_type == "grave_field":
            self.radius = self.data.get("grave_base_radius", GRAVEKEEPER_FIELD_RADIUS) + int(self.data.get("grave_stacks", 0)) * GRAVEKEEPER_FIELD_STACK_RADIUS
            marker_present = any(
                effect.alive
                and effect.effect_type == "grave_marker"
                and effect.owner is self.owner
                and (effect.pos - self.pos).length() <= self.radius + getattr(effect, "radius", 0)
                for effect in game_state.get("design_effects", [])
            )
            slow_amount = GRAVEKEEPER_FIELD_EMPOWERED_SLOW if marker_present else GRAVEKEEPER_FIELD_SLOW
            self.affect_targets(
                game_state,
                lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                lambda target: target.apply_slow(slow_amount, 0.25) if hasattr(target, "apply_slow") else None,
            )
            erosion_accum = self.data.get("erosion_accum", 0.0) + dt
            if erosion_accum >= GRAVEKEEPER_FIELD_TICK_INTERVAL:
                self.data["erosion_accum"] = 0.0
                stacks = int(self.data.get("grave_stacks", 0))
                tick_dps = GRAVEKEEPER_FIELD_BASE_DPS + stacks * GRAVEKEEPER_FIELD_STACK_DPS
                if marker_present:
                    tick_dps *= GRAVEKEEPER_FIELD_MARKER_DPS_MULTIPLIER
                self.affect_targets(
                    game_state,
                    lambda target: (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0),
                    lambda target: target.take_damage(
                        tick_dps * GRAVEKEEPER_FIELD_TICK_INTERVAL,
                        source=self.owner,
                        damage_type="design_spell_grave_erosion",
                        game_state=game_state,
                    ),
                )
            else:
                self.data["erosion_accum"] = erosion_accum
            if self.data.get("grave_detonate", False) or self.lifetime <= 0:
                if self.owner is not None and hasattr(self.owner, "resolve_gravekeeper_field"):
                    self.owner.resolve_gravekeeper_field(self, game_state)
                else:
                    self.alive = False
        elif self.effect_type == "grave_marker":
            drain_timer = self.data.get("drain_timer", 0.0) + dt
            if drain_timer >= GRAVEKEEPER_MARKER_DRAIN_INTERVAL:
                self.data["drain_timer"] = 0.0
                nearest = None
                nearest_distance = None
                for candidate in get_targetables(game_state):
                    if not candidate.alive or candidate.owner_id == self.owner_id:
                        continue
                    distance = (candidate.pos - self.pos).length()
                    if nearest is None or distance < nearest_distance:
                        nearest = candidate
                        nearest_distance = distance
                if nearest is not None:
                    nearest.take_damage(
                        GRAVEKEEPER_MARKER_DRAIN_DAMAGE,
                        source=self.owner,
                        damage_type="design_spell_grave_drain",
                        game_state=game_state,
                    )
            else:
                self.data["drain_timer"] = drain_timer
        elif self.effect_type == "grave_wraith":
            max_hits = int(self.data.get("max_hits", 1))
            target = None
            target_distance = None
            for candidate in get_targetables(game_state):
                if not candidate.alive or candidate.owner_id == self.owner_id:
                    continue
                distance = (candidate.pos - self.pos).length_squared()
                if target is None or distance < target_distance:
                    target = candidate
                    target_distance = distance
            if target is not None:
                to_target = target.pos - self.pos
                if to_target.length_squared() > 0:
                    self.direction = to_target.normalize()
            if self.direction.length_squared() <= 0:
                self.direction = random_unit_vector()
            self.pos += self.direction * self.data.get("speed", GRAVEKEEPER_WRAITH_SPEED) * dt
            if target is not None:
                if (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0):
                    hits_done = int(self.data.get("hits_done", 0))
                    target_id = id(target)
                    if self.hit_counts.get(target_id, 0.0) <= 0:
                        target.take_damage(
                            self.data.get("damage", GRAVEKEEPER_WRAITH_DAMAGE),
                            source=self.owner,
                            damage_type="design_spell_grave_wraith",
                            game_state=game_state,
                        )
                        if hasattr(target, "apply_slow"):
                            target.apply_slow(self.data.get("slow", GRAVEKEEPER_WRAITH_SLOW), self.data.get("slow_duration", GRAVEKEEPER_WRAITH_SLOW_DURATION))
                        field_px = self.data.get("field_px")
                        if field_px is not None:
                            field_center = pygame.Vector2(float(field_px), float(self.data.get("field_py", 0.0)))
                            if (target.pos - field_center).length() <= float(self.data.get("field_r", 0.0)) + getattr(target, "radius", 0):
                                target.take_damage(
                                    GRAVEKEEPER_WRAITH_FIELD_BONUS,
                                    source=self.owner,
                                    damage_type="true_grave_wraith",
                                    game_state=game_state,
                                )
                        hits_done += 1
                        self.data["hits_done"] = hits_done
                        self.hit_counts[target_id] = GRAVEKEEPER_GUARD_HIT_COOLDOWN if max_hits > 1 else 0.0
                        if hits_done >= max_hits:
                            self.alive = False
            if self.hit_counts:
                for hit_id in list(self.hit_counts):
                    self.hit_counts[hit_id] = max(0.0, self.hit_counts[hit_id] - dt)
            if not point_inside_arena(self.pos, self.radius + 4):
                self.alive = False

        if self.lifetime <= 0 and self.effect_type not in {"meteor", "black_hole"}:
            if self.effect_type == "gravity":
                self.collapse_gravity(game_state)
            self.alive = False

    def _abyss_ray_resolve(self, game_state):
        if self.owner is None:
            self.alive = False
            return
        target = None
        target_id = self.data.get("target_id")
        for candidate in get_targetables(game_state):
            if id(candidate) == target_id and candidate.alive:
                target = candidate
                break
        if target is not None:
            game_state["beam_events"].append(BeamEvent(self.pos + pygame.Vector2(0, -140), target.pos, ABYSS_EYE_COLOR))
            target.take_damage(self.data.get("damage", 80.0), source=self.owner, damage_type="true_design_abyss_ray", game_state=game_state)
            if hasattr(target, "apply_stun"):
                target.apply_stun(self.data.get("stun", 1.0))
            spawn_attack_impact(game_state, target.pos, ABYSS_EYE_COLOR, radius=22, thickness=4, burst_count=16)
        self.alive = False

    def _sea_wave_collide(self, game_state, start_pos, end_pos):
        stage = int(self.data.get("stage", 1))
        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            target_id = id(target)
            if target_id in self.hit_ids:
                continue
            if not segment_intersects_oriented_rect(
                target.pos,
                start_pos,
                end_pos,
                self.radius,
                self.data.get("length", SEA_SAGE_WAVE_LENGTH),
                getattr(target, "radius", 0),
            ):
                continue
            self.hit_ids.add(target_id)
            if stage == 1:
                target.take_damage(SEA_SAGE_WAVE_STAGE1_DAMAGE, source=self.owner, damage_type="design_spell_sea_wave_1", game_state=game_state)
                if hasattr(target, "apply_stun"):
                    target.apply_stun(SEA_SAGE_WAVE_STAGE1_STUN)
                if isinstance(self.owner, Character):
                    self.owner.spawn_sea_fish(game_state, target.pos)
            elif stage == 2:
                target.take_damage(SEA_SAGE_WAVE_STAGE2_DAMAGE, source=self.owner, damage_type="design_spell_sea_wave_2", game_state=game_state)
                if hasattr(target, "apply_stun"):
                    target.apply_stun(SEA_SAGE_WAVE_STAGE2_STUN)
                if hasattr(target, "apply_slow"):
                    target.apply_slow(SEA_SAGE_WAVE_STAGE2_SLOW, SEA_SAGE_WAVE_SLOW_DURATION)
            else:
                target.take_damage(SEA_SAGE_WAVE_STAGE3_DAMAGE, source=self.owner, damage_type="design_spell_sea_wave_3", game_state=game_state)
                if hasattr(target, "apply_stun"):
                    target.apply_stun(SEA_SAGE_WAVE_STAGE3_STUN)
                self.data["returning"] = True
                break

    def _pull_and_damage(self, target, dt, game_state, dps, damage_type):
        offset = self.pos - target.pos
        if offset.length_squared() > 0 and hasattr(target, "apply_knockback"):
            direction = offset.normalize()
            target.pos += direction * min(self.data.get("pull", 40.0) * dt, offset.length())
            if hasattr(target, "update_rect"):
                target.update_rect()
        target.take_damage(dps * dt, source=self.owner, damage_type=damage_type, game_state=game_state)

    def _pull_target(self, target, dt, strength):
        offset = self.pos - target.pos
        if offset.length_squared() <= 0:
            return
        direction = offset.normalize()
        target.pos += direction * min(strength * dt, offset.length())
        if hasattr(target, "update_rect"):
            target.update_rect()

    def fire_windstorm_blade(self, game_state, shot_index):
        living = [t for t in get_targetables(game_state) if t.alive and t.owner_id != self.owner_id]
        if living:
            chosen = random.choice(living)
            direction = chosen.pos - self.owner.pos
            if direction.length_squared() == 0:
                direction = random_unit_vector()
            direction = direction.normalize()
        else:
            direction = random_unit_vector()
        sway = float(self.data.get("sway_angle", 8.0))
        direction = direction.rotate((shot_index % 3 - 1) * sway)
        spawn_windstorm_blade_projectile(
            self.owner,
            game_state,
            direction,
            float(self.data.get("damage", WINDSTORM_FOX_SKILL_BLADE_DAMAGE)),
            self.data.get("damage_type", "design_physical_windstorm_blade"),
            speed=float(self.data.get("speed", 720.0)),
            max_range=float(self.data.get("max_range", 920.0)),
            apply_resist=bool(self.data.get("apply_resist", False)),
            lifesteal_ratio=float(self.data.get("lifesteal_ratio", 0.0)),
            ricochet=bool(self.data.get("ricochet", False)),
        )

    def collapse_gravity(self, game_state):
        for target in get_targetables(game_state):
            if not target.alive or target.owner_id == self.owner_id:
                continue
            if (target.pos - self.pos).length() <= self.radius + getattr(target, "radius", 0):
                offset = self.pos - target.pos
                if offset.length_squared() > 0:
                    direction = offset.normalize()
                    target.pos += direction * 60.0
                    if hasattr(target, "update_rect"):
                        target.update_rect()
                target.take_damage(60.0, source=self.owner, damage_type="design_spell_gravity_collapse", game_state=game_state)

    def draw(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        if self.effect_type == "trap":
            alpha = 60 if not self.data.get("hidden", True) else 28
            pygame.draw.circle(overlay, (140, 180, 220, alpha), (round(self.pos.x), round(self.pos.y)), round(self.radius))
        elif self.effect_type == "soul_chain":
            target_id = self.data.get("target_id")
            target = next((candidate for candidate in getattr(self.owner, "_design_cached_characters", []) if id(candidate) == target_id), None)
            chain = getattr(self.owner, "soul_arbiter_chains", {}).get(target_id) if self.owner is not None else None
            if chain is not None and target is not None and target.alive:
                start = (round(self.owner.pos.x), round(self.owner.pos.y))
                end = (round(target.pos.x), round(target.pos.y))
                pygame.draw.line(overlay, (*SOUL_ARBITER_EXECUTION_COLOR, 82), start, end, 7)
                pygame.draw.line(overlay, (*SOUL_ARBITER_EXECUTION_COLOR, 220), start, end, 2)
        elif self.effect_type == "equilibrium_mark":
            pulse = 0.55 + 0.45 * math.sin(self.timer * 8.0)
            outer_color = (*EQUILIBRIUM_MARK_COLOR, int(92 + 88 * pulse))
            inner_color = (*EQUILIBRIUM_MARK_GLOW, int(58 + 62 * pulse))
            center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, outer_color, center, round(self.radius), 2)
            pygame.draw.circle(overlay, inner_color, center, max(4, round(self.radius - 6)), 1)
        elif self.effect_type == "equilibrium_pulse":
            pulse_progress = clamp(self.timer / max(0.01, self.lifetime + self.timer), 0.0, 1.0)
            ring_radius = round(self.radius + pulse_progress * 28.0)
            alpha = int(180 * (1.0 - pulse_progress))
            center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, (*EQUILIBRIUM_PULSE_COLOR, max(36, alpha)), center, ring_radius, 3)
            pygame.draw.circle(overlay, (*EQUILIBRIUM_MARK_GLOW, max(24, alpha // 2)), center, max(2, ring_radius - 6), 1)
        elif self.effect_type == "skill_precast":
            progress = clamp(1.0 - self.lifetime / max(0.1, SKILL_PRECAST_DURATION), 0.0, 1.0)
            alpha = int(210 * (1.0 - progress))
            center = (round(self.pos.x), round(self.pos.y))
            outer_r = round(self.radius * (2.4 - 1.4 * progress))
            pygame.draw.circle(overlay, (255, 226, 130, max(24, alpha)), center, outer_r, 3)
            pygame.draw.circle(overlay, (255, 250, 220, max(16, alpha // 2)), center, max(2, outer_r - 5), 1)
            inner_r = round(self.radius * (0.4 + 0.8 * progress))
            pygame.draw.circle(overlay, (255, 240, 180, max(30, alpha)), center, inner_r, 2)
            for i in range(4):
                orbit_angle = self.timer * 5.0 + math.tau * i / 4
                orbit_r = max(2.0, self.radius * (2.6 - 2.2 * progress))
                dot = pygame.Vector2(center) + pygame.Vector2(math.cos(orbit_angle), math.sin(orbit_angle)) * orbit_r
                pygame.draw.circle(overlay, (255, 255, 220, max(40, alpha)), (round(dot.x), round(dot.y)), 2)
        elif self.effect_type == "rail_track":
            half_len = float(self.data.get("length", RAIL_LENGTH)) * 0.5
            width = float(self.data.get("width", RAIL_WIDTH))
            perp = pygame.Vector2(-self.direction.y, self.direction.x)
            for rail_side in (-1.0, 1.0):
                offset_vec = perp * (width * 0.5 - 5.0) * rail_side
                for segment_index in range(12):
                    t = -1.0 + 2.0 * segment_index / 11.0
                    p = self.pos + self.direction * (t * half_len) + offset_vec
                    pb = p - self.direction * (half_len / 14.0)
                    alpha_rail = int(200 * clamp(t, 0.0, 1.0)) + 20
                    pygame.draw.line(
                        overlay,
                        (*RAIL_TRACK_COLOR, max(40, alpha_rail)),
                        (round(pb.x), round(pb.y)),
                        (round(p.x), round(p.y)),
                        3,
                    )
        elif self.effect_type == "rail_train":
            length = float(self.data.get("length", RAIL_LENGTH))
            width = float(self.data.get("width", RAIL_WIDTH))
            angle = -math.degrees(math.atan2(self.direction.y, self.direction.x))
            car_surface = pygame.Surface((int(length) + 60, int(width) + 24), pygame.SRCALPHA)
            cy = car_surface.get_height() // 2
            body_rect = pygame.Rect(28, cy - int(width / 2), int(length), int(width))
            pygame.draw.rect(car_surface, (*RAIL_BODY_COLOR, 240), body_rect, border_radius=8)
            pygame.draw.rect(car_surface, (92, 100, 108, 240), body_rect, 2, border_radius=8)
            nose_rect = pygame.Rect(int(length) + 12, cy - int(width / 2) + 6, 30, int(width) - 12)
            pygame.draw.rect(car_surface, (*RAIL_LIGHT_COLOR, 255), nose_rect, border_radius=6)
            pygame.draw.circle(car_surface, (255, 255, 235, 255), (int(length) + 24, cy - 8), 5)
            for box_index in range(4):
                window_x = 48 + box_index * 96
                pygame.draw.rect(car_surface, (58, 64, 72, 235), (window_x, cy - int(width * 0.28), 46, int(width * 0.5)), border_radius=5)
            for wheel_x in (70, 170, 270, int(length) - 70):
                pygame.draw.circle(car_surface, (36, 40, 46, 255), (wheel_x, cy + int(width / 2) - 2), 6)
            rotated_car = pygame.transform.rotozoom(car_surface, angle, 1.0)
            overlay.blit(rotated_car, rotated_car.get_rect(center=(round(self.pos.x), round(self.pos.y))))
        elif self.effect_type == "valkyrie_landing":
            progress = clamp(1.0 - self.lifetime / max(0.1, VALKYRIE_LANDING_LIFETIME), 0.0, 1.0)
            alpha = int(230 * (1.0 - progress))
            center = (round(self.pos.x), round(self.pos.y))
            # 落地冲击环：向外扩散
            ring_radius = round(8.0 + progress * (self.radius * 1.25))
            pygame.draw.circle(overlay, (*VALKYRIE_LANDING_COLOR, max(30, alpha)), center, ring_radius, 4)
            pygame.draw.circle(overlay, (255, 250, 224, max(20, alpha // 3)), center, max(3, ring_radius - 6), 2)
            # 上升光柱：从地面冲向天空
            column_height = round(46.0 + (1.0 - progress) * 34.0)
            column_alpha = max(28, alpha)
            glow_rect = pygame.Rect(center[0] - 7, center[1] - column_height, 14, column_height)
            pygame.draw.rect(overlay, (*VALKYRIE_LANDING_COLOR, column_alpha), glow_rect, border_radius=5)
            pygame.draw.rect(overlay, (255, 252, 230, max(18, column_alpha - 40)), glow_rect.inflate(6, 8), border_radius=7)
            # 光柱顶部尖刺
            tip_y = center[1] - column_height
            pygame.draw.polygon(
                overlay,
                (*VALKYRIE_LANDING_COLOR, column_alpha),
                [(center[0] - 10, tip_y), (center[0] + 10, tip_y), (center[0], tip_y - 16)],
            )
            # 地面散落火花
            for index in range(8):
                angle = math.tau * index / 8 + progress * 0.6
                spark_radius = round(14.0 + progress * (self.radius * 1.15))
                spark_pos = (
                    round(center[0] + math.cos(angle) * spark_radius),
                    round(center[1] + math.sin(angle) * spark_radius * 0.35),
                )
                pygame.draw.circle(overlay, (*VALKYRIE_LANDING_COLOR, max(16, alpha // 2)), spark_pos, 2)
        elif self.effect_type == "abyss_charge":
            pulse = 0.5 + 0.5 * math.sin(self.timer * 9.0)
            alpha = int(90 + 90 * pulse)
            center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, (*ABYSS_EYE_COLOR, alpha), center, round(self.radius * (0.6 + 0.4 * pulse)))
            pygame.draw.circle(overlay, (*ABYSS_EYE_COLOR, min(255, alpha + 40)), center, max(4, round(self.radius * 0.9)), 3)
            pygame.draw.line(overlay, (*ABYSS_EYE_COLOR, alpha), (center[0] - 18, center[1]), (center[0] - self.radius - 8, center[1]), 2)
            pygame.draw.line(overlay, (*ABYSS_EYE_COLOR, alpha), (center[0] + 18, center[1]), (center[0] + self.radius + 8, center[1]), 2)
        elif self.effect_type == "flame_ring":
            alpha = int(110 * clamp(self.lifetime / max(0.1, self.data.get("lifetime", 1.0)), 0.0, 1.0))
            center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, (232, 86, 52, max(24, alpha)), center, round(self.radius), 5)
            pygame.draw.circle(overlay, (255, 180, 92, max(18, alpha // 2)), center, max(3, round(self.radius - 4)), 2)
        elif self.effect_type == "rift_line":
            alpha = int(130 * clamp(self.lifetime / max(0.1, self.data.get("lifetime", 1.0)), 0.0, 1.0))
            direction = self.data.get("direction", pygame.Vector2(0, 0))
            length = float(self.data.get("length", RIFT_DASH_DISTANCE))
            start_pos = self.pos - direction * length * 0.5
            end_pos = self.pos + direction * length * 0.5
            perp = pygame.Vector2(-direction.y, direction.x) * self.radius
            points = [
                (round(start_pos.x + perp.x), round(start_pos.y + perp.y)),
                (round(end_pos.x + perp.x), round(end_pos.y + perp.y)),
                (round(end_pos.x), round(end_pos.y)),
                (round(end_pos.x - perp.x), round(end_pos.y - perp.y)),
                (round(start_pos.x - perp.x), round(start_pos.y - perp.y)),
            ]
            pygame.draw.polygon(overlay, (*RIFT_BLUE, max(26, alpha)), points)
            pygame.draw.line(overlay, (*RIFT_BLUE, min(255, alpha + 30)), (round(start_pos.x), round(start_pos.y)), (round(end_pos.x), round(end_pos.y)), 4)
            pygame.draw.line(overlay, (224, 244, 255, max(30, alpha)), (round(start_pos.x), round(start_pos.y)), (round(end_pos.x), round(end_pos.y)), 2)
        elif self.effect_type == "rift_field":
            pulse = 0.5 + 0.5 * math.sin(self.timer * 6.0)
            alpha = int(70 + 60 * pulse)
            center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, (*RIFT_BLUE, alpha), center, round(self.radius))
            pygame.draw.circle(overlay, (*RIFT_BLUE, min(255, alpha + 30)), center, max(4, round(self.radius * 0.8)), 2)
        elif self.effect_type == "soul_slash":
            pulse = 0.5 + 0.5 * math.sin(self.timer * 24.0)
            center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, (*SOUL_SLASH_COLOR, int(90 + 90 * pulse)), center, round(6 + 6 * pulse))
        elif self.effect_type == "meteor":
            pygame.draw.circle(overlay, (255, 180, 110, 70), (round(self.pos.x), round(self.pos.y)), round(self.radius))
            pygame.draw.circle(overlay, (255, 220, 160, 180), (round(self.pos.x), round(self.pos.y)), round(self.radius), 2)
        elif self.effect_type in {"swamp", "gravity", "pillar", "fire_trail", "black_hole", "tiger_blood_trail"}:
            color_map = {
                "swamp": (112, 90, 64),
                "gravity": (156, 118, 220),
                "pillar": (250, 244, 176),
                "fire_trail": (220, 88, 42),
                "black_hole": (74, 64, 122),
                "tiger_blood_trail": (210, 70, 58),
            }
            color = self.data.get("color", color_map.get(self.effect_type, (180, 180, 180)))
            pygame.draw.circle(overlay, (*color, 72), (round(self.pos.x), round(self.pos.y)), round(self.radius))
            pygame.draw.circle(overlay, (*color, 180), (round(self.pos.x), round(self.pos.y)), round(self.radius), 2)
        elif self.effect_type == "grave_field":
            alpha = 72 + min(50, int(self.data.get("grave_stacks", 0)) * 12)
            center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, (*GRAVEKEEPER_FIELD_COLOR, alpha), center, round(self.radius))
            pygame.draw.circle(overlay, (*GRAVEKEEPER_FIELD_EDGE_COLOR, 200), center, round(self.radius), 2)
            if self.data.get("grave_stacks", 0) > 0:
                for index in range(int(self.data.get("grave_stacks", 0))):
                    ring_radius = max(8, round(self.radius - 8 - index * 5))
                    pygame.draw.circle(overlay, (108, 84, 66, 100), center, ring_radius, 1)
        elif self.effect_type == "grave_marker":
            alpha = max(40, int(220 * clamp(self.lifetime / max(0.1, GRAVEKEEPER_MARKER_DURATION), 0.0, 1.0)))
            center = (round(self.pos.x), round(self.pos.y))
            body = pygame.Rect(0, 0, max(10, round(self.radius * 0.95)), max(18, round(self.radius * 1.8)))
            body.center = center
            top = pygame.Rect(0, 0, max(8, round(body.width * 0.72)), max(8, round(body.height * 0.36)))
            top.center = (center[0], center[1] - round(body.height * 0.18))
            pygame.draw.rect(overlay, (*GRAVEKEEPER_MARKER_COLOR, alpha), body, border_radius=2)
            pygame.draw.rect(overlay, (*GRAVEKEEPER_MARKER_EDGE_COLOR, min(255, alpha + 35)), body, 2, border_radius=2)
            pygame.draw.rect(overlay, (*GRAVEKEEPER_MARKER_COLOR, alpha), top, border_radius=2)
            pygame.draw.line(overlay, (126, 126, 132, min(255, alpha + 20)), (body.left + 3, body.centery - 2), (body.right - 4, body.centery + 4), 1)
            pygame.draw.line(overlay, (74, 74, 78, min(255, alpha + 20)), (body.left + 4, body.top + 5), (body.right - 3, body.bottom - 6), 1)
            drain_progress = float(self.data.get("drain_timer", 0.0)) / GRAVEKEEPER_MARKER_DRAIN_INTERVAL
            if self.data.get("drain_timer", 0.0) > 0 or drain_progress > 0:
                pulse_alpha = int(30 + 26 * math.sin(self.timer * 7.0))
                pygame.draw.circle(overlay, (150, 214, 170, pulse_alpha), center, round(self.radius * (1.55 + 0.25 * drain_progress)), 2)
        elif self.effect_type == "grave_wraith":
            is_guard = int(self.data.get("max_hits", 1)) > 1
            alpha = 90 + max(0, int(90 * clamp(self.lifetime / max(0.1, self.data.get("lifetime", 1.0)), 0.0, 1.0)))
            center = (round(self.pos.x), round(self.pos.y))
            direction = self.direction if self.direction.length_squared() > 0 else pygame.Vector2(1, 0)
            trail_start = (round(self.pos.x - direction.x * self.radius * 1.6), round(self.pos.y - direction.y * self.radius * 1.6))
            pygame.draw.line(overlay, (*GRAVEKEEPER_WRAITH_TRAIL_COLOR, 120), trail_start, center, max(2, round(self.radius * 0.55)))
            body_color = GRAVEKEEPER_WRAITH_COLOR if not is_guard else (168, 226, 178)
            pygame.draw.circle(overlay, (*body_color, alpha), center, round(self.radius))
            pygame.draw.polygon(
                overlay,
                (*GRAVEKEEPER_WRAITH_TRAIL_COLOR, min(255, alpha + 25)),
                [
                    (center[0], center[1] - self.radius),
                    (center[0] + self.radius, center[1]),
                    (center[0], center[1] + self.radius),
                    (center[0] - self.radius, center[1]),
                ],
            )
            if is_guard:
                pygame.draw.circle(overlay, (150, 226, 166, min(255, alpha + 10)), center, round(self.radius + 3), 2)
        elif self.effect_type == "mirror_void":
            pygame.draw.circle(overlay, (92, 88, 104, 82), (round(self.pos.x), round(self.pos.y)), round(self.radius))
            pygame.draw.circle(overlay, (176, 168, 184, 180), (round(self.pos.x), round(self.pos.y)), round(self.radius), 2)
        elif self.effect_type == "construct":
            draw_shape_icon(overlay, "triangle", (245, 245, 245), (round(self.pos.x), round(self.pos.y)), max(6, int(self.radius)))
        elif self.effect_type == "arcane_field":
            pulse = 0.55 + 0.45 * math.sin(self.timer * 5.5)
            center = (round(self.pos.x), round(self.pos.y))
            outer = (176, 108, 236, int(78 + 44 * pulse))
            mid = (214, 180, 255, int(54 + 36 * pulse))
            inner = (248, 238, 255, int(34 + 22 * pulse))
            pygame.draw.circle(overlay, outer, center, round(self.radius))
            pygame.draw.circle(overlay, mid, center, max(4, round(self.radius - 9)), 2)
            pygame.draw.circle(overlay, inner, center, max(2, round(self.radius - 18)), 1)
        elif self.effect_type == "sound_ring":
            if self.timer >= self.data.get("delay", 0.0):
                pygame.draw.circle(overlay, (232, 238, 244, 140), (round(self.pos.x), round(self.pos.y)), round(self.radius), 3)
        elif self.effect_type == "aurora":
            pygame.draw.circle(overlay, (136, 222, 212, 140), (round(self.pos.x), round(self.pos.y)), round(self.radius))
        elif self.effect_type == "water_fish":
            fish_center = (round(self.pos.x), round(self.pos.y))
            pygame.draw.circle(overlay, (*SEA_SAGE_FISH_COLOR, 220), fish_center, max(4, round(self.radius)))
            pygame.draw.circle(overlay, (245, 255, 255, 180), fish_center, max(2, round(self.radius * 0.45)), 1)
        elif self.effect_type == "sea_wave":
            stage = int(self.data.get("stage", 1))
            outer = SEA_SAGE_WAVE_OUTER_COLOR if stage != 2 else (70, 132, 235)
            direction = self.direction if self.direction.length_squared() > 0 else pygame.Vector2(1, 0)
            center = self.pos + direction * (self.data.get("length", SEA_SAGE_WAVE_LENGTH) * 0.5)
            wave_rect = pygame.Rect(0, 0, round(self.data.get("length", SEA_SAGE_WAVE_LENGTH)), round(self.radius * 2))
            wave_rect.center = (round(center.x), round(center.y))
            wave_surface = pygame.Surface(wave_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(wave_surface, (*outer, 88), wave_surface.get_rect(), border_radius=8)
            pygame.draw.rect(wave_surface, (*SEA_SAGE_WAVE_INNER_COLOR, 180), wave_surface.get_rect().inflate(-8, -8), 2, border_radius=6)
            pygame.draw.rect(wave_surface, (*outer, 220), wave_surface.get_rect(), 2, border_radius=8)
            angle = -math.degrees(math.atan2(direction.y, direction.x))
            wave_surface = pygame.transform.rotate(wave_surface, angle)
            overlay.blit(wave_surface, wave_surface.get_rect(center=(round(center.x), round(center.y))))
        surface.blit(overlay, (0, 0))


class DesignSummon:
    def __init__(self, owner, summon_type, pos, source_character=None):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.job_name = None
        self.summon_type = summon_type
        self.source_character = source_character
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.alive = True
        self.is_decoy = False
        self.attack_cooldown = 0.0
        self.mage_burn_timer = 0.0
        if summon_type == "wolf":
            self.shape = "diamond"
            self.color = (168, 176, 186)
            self.radius = 10
            self.hp = 35
            self.max_hp = 35
            self.damage = 6
            self.speed = 140.0
            self.lifetime = DESIGN_WOLF_DURATION
            self.attack_type = "melee"
            self.attack_interval = 1.5
            self.projectile_speed = 0.0
            self.attack_range = 40.0
        elif summon_type == "drone":
            self.shape = "triangle"
            self.color = (210, 224, 240)
            self.radius = 9
            self.hp = 30
            self.max_hp = 30
            self.damage = 4
            self.speed = 120.0
            self.lifetime = DESIGN_DRONE_DURATION
            self.attack_type = "ranged"
            self.projectile_speed = 290.0
            self.attack_range = 240.0
            self.attack_interval = 3.0
            self.attack_cooldown = 3.0
        elif summon_type == "sailor":
            self.shape = "diamond"
            self.color = (116, 218, 142)
            self.radius = 9
            self.hp = 50
            self.max_hp = 50
            self.damage = 10
            self.speed = 136.0
            self.lifetime = DESIGN_GHOST_SAILOR_DURATION
            self.attack_type = "ranged"
            self.projectile_speed = 300.0
            self.attack_range = 220.0
            self.attack_interval = 0.9
            self.attack_cooldown = 0.9
        elif summon_type == "spirit":
            source = source_character or owner
            self.shape = getattr(source, "shape", "crescent")
            source_color = getattr(source, "color", owner.color)
            self.color = tuple(clamp(int(channel * 0.78 + 34), 0, 255) for channel in source_color)
            self.radius = max(8, int(round(getattr(source, "radius", 12) * 0.85)))
            self.hp = max(10.0, getattr(source, "max_hp", 100.0) * SOUL_ARBITER_SPIRIT_SCALE)
            self.max_hp = self.hp
            self.damage = max(1.0, getattr(source, "base_attack_damage", 10.0) * SOUL_ARBITER_SPIRIT_SCALE)
            self.speed = max(70.0, getattr(source, "move_speed", 100.0) * SOUL_ARBITER_SPIRIT_SCALE)
            self.lifetime = SOUL_ARBITER_SPIRIT_LIFETIME
            self.attack_type = getattr(source, "base_attack_type", "melee")
            self.projectile_speed = max(150.0, getattr(source, "base_projectile_speed", 260.0) * SOUL_ARBITER_SPIRIT_SCALE)
            self.attack_range = max(28.0, getattr(source, "base_attack_range", 40.0) * 0.75)
            self.attack_interval = max(0.22, getattr(source, "base_attack_interval", 0.8) * 0.75)
            self.attack_damage_kind = get_damage_kind("basic", source)
        elif summon_type == "soul_blade":
            self.shape = "slim_diamond"
            self.color = SOUL_BLADE_COLOR
            self.radius = 11
            self.hp = float(getattr(owner, "max_hp", 1000.0)) * SOUL_BLADE_MAX_HP_RATIO
            self.max_hp = self.hp
            self.damage = SOUL_BLADE_DAMAGE
            self.speed = SOUL_BLADE_SPEED
            self.lifetime = float("inf")
            self.attack_type = "melee"
            self.projectile_speed = 0.0
            self.attack_range = SOUL_BLADE_ATTACK_RANGE
            self.attack_interval = SOUL_BLADE_ATTACK_INTERVAL
            self.attack_damage_kind = DAMAGE_KIND_PHYSICAL
        else:
            self.shape = "square"
            self.color = (156, 162, 86)
            self.radius = 6
            self.hp = 5
            self.max_hp = 5
            self.damage = 5
            self.speed = 150.0
            self.lifetime = DESIGN_LARVA_DURATION
            self.attack_type = "melee"
            self.attack_interval = 1.0
            self.projectile_speed = 0.0
            self.attack_range = 24.0
            self.attack_damage_kind = DAMAGE_KIND_PHYSICAL
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.update_rect()

    def __getattr__(self, name):
        if not name.startswith("design_"):
            raise AttributeError(name)
        if name.endswith(("_owner_id", "_target_id", "_source", "_target")):
            return None
        if name.endswith(("_marked", "_flag", "_locked")):
            return False
        if name.endswith("_effects"):
            return []
        return 0.0

    def update_rect(self):
        self.rect.size = (self.radius * 2, self.radius * 2)
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def take_damage(
        self,
        amount,
        source=None,
        damage_type="basic",
        game_state=None,
        count_on_damage_dealt=True,
        ignore_shields=False,
        ignore_equilibrium_thresholds=False,
    ):
        if not self.alive or amount <= 0:
            return 0.0
        if self.summon_type == "soul_blade":
            blade_amount = amount
            damage_kind = get_damage_kind(damage_type, source if isinstance(source, Character) else None)
            if damage_kind is None:
                blade_amount *= 1.0 + SOUL_BLADE_TRUE_DAMAGE_INCREASE
            elif damage_kind == DAMAGE_KIND_PHYSICAL:
                blade_amount *= 1.0 - SOUL_BLADE_PHYSICAL_REDUCTION
            absorbed = blade_amount * 0.9
            transferred = blade_amount * SOUL_BLADE_TRANSFER_RATIO
            if transferred > 0 and self.owner is not None and getattr(self.owner, "alive", False):
                self.owner.take_damage(transferred, source=source, damage_type="true_soul_blade_link", game_state=game_state)
            pre_damage_hp = self.hp
            self.hp -= absorbed
            if self.hp <= 0:
                self.hp = 0
                self.alive = False
                if self.owner is not None and hasattr(self.owner, "design_soul_blade_timer"):
                    self.owner.design_soul_blade_timer = SOUL_BLADE_RESPAWN_DELAY
            return amount
        pre_damage_hp = self.hp
        self.hp -= amount
        handle_equilibrium_thresholds(self, pre_damage_hp, source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None), game_state, ignore_equilibrium_thresholds=ignore_equilibrium_thresholds)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            if self.summon_type == "wolf" and self.owner is not None and hasattr(self.owner, "design_wolf_cd_timer"):
                self.owner.design_wolf_cd_timer = max(self.owner.design_wolf_cd_timer, BEASTMASTER_WOLF_DEATH_CD)
        return amount

    def apply_slow(self, amount, duration):
        return None

    def apply_stun(self, duration):
        return None

    def apply_root(self, duration):
        return None

    def apply_knockback(self, direction, distance):
        return None

    def heal(self, amount):
        if not self.alive or amount <= 0:
            return 0.0
        previous_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - previous_hp

    def update(self, dt, game_state):
        if not self.alive:
            return
        if game_state.get("global_time_stop_timer", 0.0) > 0 and self.owner_id != game_state.get("global_time_stop_owner"):
            return
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            if self.summon_type == "wolf" and self.owner is not None and hasattr(self.owner, "design_wolf_cd_timer"):
                self.owner.design_wolf_cd_timer = max(self.owner.design_wolf_cd_timer, BEASTMASTER_WOLF_DEATH_CD)
            return
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        if self.summon_type == "spirit":
            target = select_nearest_targetable(self, game_state)
            if target is None:
                self.vel *= 0.92
                self.pos += self.vel * dt
                self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                self.update_rect()
                return
            offset = target.pos - self.pos
            distance = offset.length()
            direction = offset.normalize() if distance > 0 else random_unit_vector()
            if self.attack_type == "melee":
                if distance > self.attack_range + target.radius:
                    self.vel = direction * self.speed
                    self.pos += self.vel * dt
                else:
                    self.vel *= 0.2
                    if self.attack_cooldown <= 0:
                        target.take_damage(self.damage, source=self.owner, damage_type=self.attack_damage_kind or "design_physical_spirit", game_state=game_state)
                        self.attack_cooldown = self.attack_interval
            else:
                desired_distance = max(70.0, self.attack_range * 0.65)
                if distance > desired_distance:
                    self.vel = direction * self.speed
                    self.pos += self.vel * dt
                else:
                    self.vel *= 0.2
                if self.attack_cooldown <= 0 and distance <= self.attack_range + target.radius:
                    attack_kind = self.attack_damage_kind or DAMAGE_KIND_PHYSICAL
                    if attack_kind == DAMAGE_KIND_SPELL:
                        damage_type = "design_spell_spirit"
                    elif attack_kind == "true":
                        damage_type = "true_soul_spirit"
                    else:
                        damage_type = "design_physical_spirit"
                    velocity = direction * self.projectile_speed
                    start = self.pos + direction * (self.radius + 4)
                    game_state["projectiles"].append(
                        Projectile(
                            start,
                            velocity,
                            self.owner,
                            self.damage,
                            self.color,
                            source_kind=damage_type,
                            max_range=self.attack_range,
                        )
                    )
                    self.attack_cooldown = self.attack_interval
            self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
            self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
            self.update_rect()
            return
        if self.summon_type == "soul_blade":
            if self.owner is not None and not getattr(self.owner, "alive", False):
                self.alive = False
                return
            target = select_nearest_targetable(self, game_state)
            if target is None:
                return
            offset = target.pos - self.pos
            distance = offset.length()
            direction = offset.normalize() if distance > 0 else random_unit_vector()
            if distance > self.attack_range + target.radius:
                self.vel = direction * self.speed
                self.pos += self.vel * dt
            else:
                self.vel *= 0.2
                if self.attack_cooldown <= 0:
                    target.take_damage(self.damage, source=self.owner, damage_type="design_physical_soul_blade", game_state=game_state)
                    self.attack_cooldown = self.attack_interval
            self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
            self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
            self.update_rect()
            return
        target = select_nearest_targetable(self, game_state)
        if target is None:
            return
        offset = target.pos - self.pos
        distance = offset.length()
        direction = offset.normalize() if distance > 0 else random_unit_vector()
        if self.attack_type == "melee":
            self.vel = direction * self.speed
            self.pos += self.vel * dt
            if distance <= self.attack_range + target.radius and self.attack_cooldown <= 0:
                target.take_damage(self.damage, source=self.owner, damage_type="design_physical_summon", game_state=game_state)
                if self.summon_type == "wolf" and random.random() < 0.25 and hasattr(target, "apply_bleed"):
                    target.apply_bleed(1)
                self.attack_cooldown = max(0.1, float(getattr(self, "attack_interval", 1.0)))
                if self.summon_type == "larva":
                    self.alive = False
        else:
            desired_distance = max(70.0, self.attack_range * 0.6)
            if distance > desired_distance:
                self.vel = direction * self.speed
                self.pos += self.vel * dt
            else:
                self.vel *= 0.2
            if self.attack_cooldown <= 0 and distance <= self.attack_range + target.radius:
                shots = 2 if self.summon_type == "drone" else 1
                for shot_index in range(shots):
                    shot_dir = direction.rotate((-8 if shots == 2 else 0) + shot_index * 16)
                    velocity = shot_dir * self.projectile_speed
                    start = self.pos + shot_dir * (self.radius + 4)
                    game_state["projectiles"].append(
                        Projectile(
                            start,
                            velocity,
                            self.owner,
                            self.damage,
                            self.color,
                            source_kind="design_physical_summon",
                            max_range=self.attack_range,
                        )
                    )
                self.attack_cooldown = max(0.1, float(getattr(self, "attack_interval", 1.0)))
        self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
        self.update_rect()

    def draw(self, surface):
        center = (round(self.pos.x), round(self.pos.y))
        draw_shape_icon(surface, self.shape, self.color, center, self.radius - 1)
        hp_rect = pygame.Rect(round(self.pos.x - 12), round(self.pos.y - self.radius - 9), 24, 4)
        pygame.draw.rect(surface, HEALTH_BG, hp_rect, border_radius=2)
        if self.hp > 0:
            fill = hp_rect.copy()
            fill.width = max(1, int(hp_rect.width * (self.hp / self.max_hp)))
            pygame.draw.rect(surface, self.color, fill, border_radius=2)
        pygame.draw.rect(surface, BORDER_COLOR, hp_rect, 1, border_radius=2)


def add_design_effect(game_state, effect):
    game_state["design_effects"].append(effect)


def spawn_attack_impact(game_state, pos, color, radius=14, thickness=3, lifetime=0.16, burst_count=6, damage=None):
    if damage is not None and damage >= 35:
        radius = radius * 1.5
        thickness += 2
        lifetime = max(lifetime, 0.24)
        burst_count = 10
        game_state["shake_timer"] = max(game_state.get("shake_timer", 0.0), 0.12)
        game_state["shake_magnitude"] = max(game_state.get("shake_magnitude", 0.0), 5.0)
    elif damage is not None and damage >= 15:
        radius = radius * 1.22
        thickness += 1
        lifetime = max(lifetime, 0.2)
        burst_count = 8
        game_state["shake_timer"] = max(game_state.get("shake_timer", 0.0), 0.06)
        game_state["shake_magnitude"] = max(game_state.get("shake_magnitude", 0.0), 3.0)
    game_state["attack_fx"].append(
        AttackImpactEffect(
            pos,
            color,
            radius=radius,
            thickness=thickness,
            lifetime=lifetime,
            burst_count=burst_count,
        )
    )


def spawn_design_projectile(
    owner,
    game_state,
    direction,
    damage,
    damage_type,
    color=None,
    *,
    speed=None,
    max_range=None,
    pierce=False,
    slow_amount=0.0,
    slow_duration=0.0,
    visual_shape="circle",
    on_hit=None,
    explosion_radius=0.0,
    explosion_damage=None,
    explosion_damage_type=None,
    explosion_mp_per_hit=0.0,
):
    if direction.length_squared() == 0:
        direction = random_unit_vector()
    direction = direction.normalize()
    velocity = direction * (speed if speed is not None else owner.base_projectile_speed)
    start = owner.pos + direction * (owner.radius + 6)
    game_state["projectiles"].append(
        Projectile(
            start,
            velocity,
            owner,
            damage,
            color or owner.color,
            source_kind=damage_type,
            max_range=max_range if max_range is not None else owner.get_current_attack_range(),
            pierce=pierce,
            slow_amount=slow_amount,
            slow_duration=slow_duration,
            visual_shape=visual_shape,
            on_hit=on_hit,
            explosion_radius=explosion_radius,
            explosion_damage=explosion_damage,
            explosion_damage_type=explosion_damage_type or damage_type,
            explosion_mp_per_hit=explosion_mp_per_hit,
            spell_trail=damage_type.startswith("design_spell_"),
        )
    )


def call_target_method(target, method_name, *args, **kwargs):
    method = getattr(target, method_name, None)
    if callable(method):
        return method(*args, **kwargs)
    return None


def spawn_windstorm_blade_projectile(
    caster,
    game_state,
    direction,
    damage,
    damage_type,
    *,
    speed=620.0,
    max_range=None,
    pierce=False,
    apply_resist=False,
    lifesteal_ratio=0.0,
    ricochet=False,
):
    def on_hit(projectile, target, dealt, hit_game_state):
        if dealt <= 0:
            return
        if isinstance(target, Character):
            apply_design_hit_effects(caster, target, hit_game_state, True)
            if apply_resist:
                caster.apply_windstorm_physical_resistance()
            if lifesteal_ratio > 0:
                caster.heal(dealt * lifesteal_ratio)
        if ricochet and random.random() < WINDSTORM_FOX_RICOCHET_CHANCE:
            bounce = select_nearest_enemy(target, hit_game_state["characters"])
            if bounce is not None and bounce is not target and bounce.alive and bounce.owner_id != caster.owner_id:
                bounce_direction = bounce.pos - target.pos
                if bounce_direction.length_squared() == 0:
                    bounce_direction = random_unit_vector()
                spawn_windstorm_blade_projectile(
                    caster,
                    hit_game_state,
                    bounce_direction,
                    damage,
                    damage_type,
                    speed=speed,
                    max_range=max_range,
                    pierce=False,
                    apply_resist=False,
                    lifesteal_ratio=lifesteal_ratio,
                    ricochet=False,
                )

    spawn_design_projectile(
        caster,
        game_state,
        direction,
        damage,
        damage_type,
        WINDSTORM_FOX_BLADE_COLOR,
        speed=speed,
        max_range=max_range,
        pierce=pierce,
        visual_shape="crescent",
        on_hit=on_hit,
    )


def apply_raikiri_mark(attacker, target, amount, game_state):
    if not isinstance(target, Character):
        return
    previous = getattr(target, "design_raikiri_mark", 0)
    new_mark = min(RAIKIRI_MARK_MAX, previous + amount)
    target.design_raikiri_mark = new_mark
    if new_mark > 0 and hasattr(target, "apply_slow"):
        target.apply_slow(RAIKIRI_MARK_SLOW_PER * new_mark, 3.0)
    if game_state is not None:
        spawn_damage_text(game_state, target, 0.0, text=f"雷痕{new_mark}", color=RAIKIRI_COLOR)


def apply_kenshi_mark(attacker, target, amount, game_state):
    if not isinstance(target, Character):
        return
    new_mark = min(KENSHI_MARK_MAX, getattr(target, "design_kenshi_mark", 0) + amount)
    target.design_kenshi_mark = new_mark
    target.design_kenshi_mark_timer = KENSHI_MARK_DURATION
    if game_state is not None:
        spawn_damage_text(game_state, target, 0.0, text=f"狐印{new_mark}", color=KENSHI_COLOR)


def apply_design_hit_effects(attacker, target, game_state, is_melee):
    if not isinstance(target, Character):
        return
    role_num = attacker.design_meta.get("role_num")
    if role_num == 44 and random.random() < 0.6:
        call_target_method(target, "apply_bleed", 1)
    if role_num in {45, 68} and random.random() < 0.2:
        call_target_method(target, "add_poison_progress", 1.0)
    if role_num == 62 and random.random() < 0.1:
        call_target_method(target, "apply_cold", 1)
    if role_num == 52:
        current_rot = getattr(target, "gravekeeper_rot_stacks", 0)
        if current_rot >= GRAVEKEEPER_ROT_MAX:
            target.take_damage(
                GRAVEKEEPER_ROT_BONUS_DAMAGE,
                source=attacker,
                damage_type="true_gravekeeper_rot",
                game_state=game_state,
            )
            target.gravekeeper_rot_stacks = 0
            target.gravekeeper_rot_timer = 0.0
        else:
            target.gravekeeper_rot_stacks = current_rot + 1
            target.gravekeeper_rot_timer = GRAVEKEEPER_ROT_DURATION
    if role_num == 64 and random.random() < 0.01:
        call_target_method(target, "apply_sleep", 5.0)
    if role_num == 104:
        call_target_method(target, "apply_dread", 1)
    if role_num == 105:
        target.design_ember = min(FLAME_EMBER_MAX, target.design_ember + 1)
        target.design_ember_timer = FLAME_EMBER_DURATION
        if target.design_ember >= FLAME_EMBER_MAX:
            target.take_damage(FLAME_EMBER_BURST_DAMAGE, source=attacker, damage_type="design_spell_flame_ember_burst", game_state=game_state)
            target.design_ember = 0
            target.design_ember_timer = 0.0
            spawn_attack_impact(game_state, target.pos, (232, 86, 52), radius=18, thickness=3, burst_count=12)
    if role_num == 106:
        call_target_method(target, "apply_gaze", 1)
    if role_num == 107:
        target.design_stolen_marks = min(STOLEN_MARK_MAX, target.design_stolen_marks + 1)
        target.design_bonus_speed = max(-0.3, target.design_bonus_speed - STOLEN_STEAL_RATIO)
        attacker.design_bonus_speed = min(0.2, attacker.design_bonus_speed + STOLEN_STEAL_RATIO)
    if role_num == 108:
        add_design_effect(
            game_state,
            DesignEffect("rift_field", attacker, pygame.Vector2(target.pos), radius=12.0, lifetime=RIFT_FIELD_DURATION),
        )
    if role_num == 78 and random.random() < 0.2:
        call_target_method(target, "apply_hell_burn", 1, HELLBRINGER_BURN_DURATION, attacker)
    if role_num == 80:
        target.design_bonus_speed = max(-0.25, target.design_bonus_speed - 0.05)
        attacker.design_bonus_speed = min(0.25, attacker.design_bonus_speed + 0.05)
        attacker.design_time_theft_stacks = min(5, attacker.design_time_theft_stacks + 1)
    if role_num == 86:
        target.design_marked = True
        target.design_mark_duration = max(target.design_mark_duration, 8.0)
        target.design_mark_owner_id = attacker.owner_id
    if role_num == 99:
        if attacker.design_phoenix_same_target_id != id(target):
            attacker.design_phoenix_same_target_id = id(target)
            attacker.design_phoenix_same_hits = 1
        else:
            attacker.design_phoenix_same_hits += 1
        if attacker.design_phoenix_same_hits >= 12:
            attacker.design_phoenix_same_hits = 0
            target.apply_phoenix_fire(1, source=attacker, game_state=game_state)
    if role_num == 100:
        attacker.add_shell(1)
    if role_num == 101:
        target.apply_tiger_wound(1)
        if attacker.design_tiger_same_target_id != id(target):
            attacker.design_tiger_same_target_id = id(target)
            attacker.design_tiger_same_hits = 1
        else:
            attacker.design_tiger_same_hits += 1
        if attacker.design_tiger_same_hits % 3 == 0:
            lost_hp = max(0.0, target.max_hp - target.hp)
            wound_bonus = lost_hp * TIGER_WOUND_THIRD_DAMAGE_LOST_HP_RATIO
            if wound_bonus > 0:
                target.take_damage(wound_bonus, source=attacker, damage_type="design_physical_tiger_wound", game_state=game_state)
    if role_num == 102:
        attacker.design_dragon_hit_count += 1
        if attacker.design_dragon_hit_count % DRAGON_BREATH_HIT_INTERVAL == 0:
            attacker.add_dragon_breath(1)
    if role_num == 103:
        target.design_susanoo_prowl = min(SUSANOO_PROWL_MAX, target.design_susanoo_prowl + SUSANOO_PROWL_APPLY_ON_HIT)
    if role_num == 59:
        target.design_ranger_mark = min(RANGER_MARK_MAX, target.design_ranger_mark + 2)
    if role_num == 114:
        target.design_squad_mark_timer = SQUAD_MARK_DURATION
        target.design_squad_mark_owner_id = attacker.owner_id
    if role_num == 117 and getattr(target, "design_raikiri_mark", 0) > 0:
        chain_target = None
        for candidate in get_targetables(game_state):
            if candidate.alive and candidate.owner_id != attacker.owner_id and candidate is not target:
                if (candidate.pos - target.pos).length() <= RAIKIRI_CHAIN_RANGE:
                    chain_target = candidate
                    break
        if chain_target is not None:
            chain_damage = attacker.get_current_basic_damage() * RAIKIRI_CHAIN_RATIO
            chain_target.take_damage(chain_damage, source=attacker, damage_type="design_spell_raikiri_chain", game_state=game_state)
            game_state["beam_events"].append(BeamEvent(target.pos, chain_target.pos, (180, 230, 255)))
        target.design_raikiri_mark = max(0, getattr(target, "design_raikiri_mark", 0) - 1)
    if role_num == 77:
        attacker.design_shadow_stacks = min(SHADOW_VALUE_MAX, attacker.design_shadow_stacks + 1)
        call_target_method(target, "apply_slow", 0.2, 1.0)
    if role_num == 69 and random.random() < 0.2:
        call_target_method(target, "apply_stun", 0.3)
    if attacker.design_element_mode == "ice":
        call_target_method(target, "apply_slow", 0.5, 2.0)
    elif attacker.design_element_mode == "fire":
        target.mage_burn_timer = max(getattr(target, "mage_burn_timer", 0.0), 2.5)
    elif attacker.design_element_mode == "electric":
        call_target_method(target, "apply_knockback", target.pos - attacker.pos, 30.0)
    if role_num == 50 and attacker.design_element_mode:
        elem = attacker.design_element_mode
        prev = getattr(target, "design_last_element", None)
        if prev == elem:
            target.design_element_stacks = min(ELEMENTALIST_RESONANCE_MAX, getattr(target, "design_element_stacks", 0) + 1)
        else:
            target.design_element_stacks = 1
        target.design_last_element = elem
        if target.design_element_stacks >= ELEMENTALIST_RESONANCE_MAX:
            target.design_element_stacks = 0
            if elem == "ice":
                call_target_method(target, "apply_freeze", 1.0)
            elif elem == "fire":
                target.take_damage(22.0, source=attacker, damage_type="design_spell_elemental_ignite", game_state=game_state)
                target.mage_burn_timer = max(getattr(target, "mage_burn_timer", 0.0), 3.0)
            else:
                call_target_method(target, "apply_stun", 0.8)
    if role_num == 71 and is_melee:
        spawn_design_projectile(attacker, game_state, target.pos - attacker.pos, 3.0, "design_spell_spellblade_orb", (214, 168, 255), speed=280.0, max_range=160.0)


def fire_design_basic_attack(attacker, target, game_state):
    role_num = attacker.design_meta.get("role_num")
    if getattr(attacker, "design_confuse_timer", 0.0) > 0:
        return
    if getattr(attacker, "design_sparrow_host_id", None) is not None:
        return  # 雀影附着中不普攻
    if target is None or not target.alive:
        return
    if role_num == 91 and getattr(attacker, "phantom_lancer_spear_charges", 0) > 0:
        # 枪意突刺（冷锋枪化为 3 层枪意，普攻变为短距冲刺突刺）
        direction = target.pos - attacker.pos
        if direction.length_squared() == 0:
            return
        direction = direction.normalize()
        start_pos = pygame.Vector2(attacker.pos)
        dash_distance = min(42.0, max(18.0, (target.pos - attacker.pos).length() - (target.radius + attacker.radius + 2.0)))
        attacker.pos += direction * dash_distance
        attacker.pos.x = clamp(attacker.pos.x, ARENA_RECT.left + attacker.radius, ARENA_RECT.right - attacker.radius)
        attacker.pos.y = clamp(attacker.pos.y, ARENA_RECT.top + attacker.radius, ARENA_RECT.bottom - attacker.radius)
        attacker.update_rect()
        game_state["melee_effects"].append(MeleeSwingEffect(start_pos, attacker.pos + direction * (target.radius + 10), attacker.get_visual_color()))
        game_state["beam_events"].append(BeamEvent(start_pos, attacker.pos, (86, 224, 232)))
        thrust_damage = attacker.get_current_basic_damage() * 2.0 * attacker.get_target_attack_bonus(target)
        dealt = target.take_damage(thrust_damage, source=attacker, damage_type="basic_melee", game_state=game_state)
        if dealt > 0:
            spawn_attack_impact(game_state, target.pos, (86, 224, 232), radius=12, thickness=2, burst_count=6)
            attacker.heal(40.0)
        attacker.phantom_lancer_spear_charges -= 1
        attacker.phantom_lancer_throw_speed_timer = PHANTOM_LANCER_THROW_SPEED_DURATION
        attacker.phantom_lancer_spear_hunt_timer = max(getattr(attacker, "phantom_lancer_spear_hunt_timer", 0.0), PHANTOM_LANCER_SPEAR_HUNT_DURATION)
        if random.random() < 0.5:
            cast_design_skill(attacker, game_state, "phantom_lancer_throw")
        attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
        attacker.on_attack_committed()
        return
    repeats = max(1, int(attacker.config.get("attack_repeat", 1)))
    damage = attacker.get_current_basic_damage() * attacker.get_target_attack_bonus(target)
    if role_num == 63 and target.hp > 0 and target.hp <= target.max_hp * 0.5:
        damage *= 1.2
    if role_num == 59 and attacker.design_ranger_lock_timer > 0 and attacker.design_ranger_lock_target_id == target.id:
        damage *= RANGER_LOCK_DAMAGE_MULTIPLIER
    if role_num == 57:
        damage = random.choice(attacker.config.get("attack_random_values", [damage]))
    if role_num == 53 and attacker.design_sentinel_lock:
        damage *= 3.0
    if role_num == 92:
        direction = target.pos - attacker.pos
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        game_state["melee_effects"].append(MeleeSwingEffect(attacker.pos + direction * (attacker.radius + 2), attacker.pos + direction * (attacker.get_current_attack_range() + 10)))
        attacker.start_soul_chain(target, game_state)
        attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
        attacker.on_attack_committed()
        return
    if role_num == 94:
        direction = target.pos - attacker.pos
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        combo_step = max(1, min(5, int(getattr(attacker, "sunfire_combo_step", 1))))
        fire_form = attacker.sunfire_fire_timer > 0
        if combo_step == 1:
            half_angle = 34.0 * (1.5 if fire_form else 1.0)
            targets = collect_targets_in_cone(attacker.pos, direction, 82.0, half_angle, attacker.owner_id, game_state)
            for victim in targets:
                dealt = victim.take_damage(10.0, source=attacker, damage_type="design_physical_sunfire_1", game_state=game_state)
                if dealt > 0:
                    apply_design_hit_effects(attacker, victim, game_state, True)
            if fire_form:
                bonus_damage = attacker.max_hp * 0.02
                for victim in targets:
                    if victim.alive:
                        if isinstance(victim, Character):
                            victim.take_damage(
                                bonus_damage,
                                source=attacker,
                                damage_type="true_sunfire_1",
                                game_state=game_state,
                                count_on_damage_dealt=False,
                            )
                        else:
                            victim.take_damage(bonus_damage, source=attacker, damage_type="true_sunfire_1", game_state=game_state)
        elif combo_step == 2:
            start_pos = pygame.Vector2(attacker.pos)
            distance = (target.pos - attacker.pos).length()
            dash_distance = clamp(distance - (target.radius + attacker.radius + 4.0), 26.0, 84.0)
            end_pos = attacker.pos + direction * dash_distance
            end_pos.x = clamp(end_pos.x, ARENA_RECT.left + attacker.radius, ARENA_RECT.right - attacker.radius)
            end_pos.y = clamp(end_pos.y, ARENA_RECT.top + attacker.radius, ARENA_RECT.bottom - attacker.radius)
            dash_targets = []
            for victim in get_targetables(game_state):
                if not victim.alive or victim.owner_id == attacker.owner_id:
                    continue
                if distance_point_to_segment(victim.pos, start_pos, end_pos) <= victim.radius + attacker.radius + 12.0:
                    dash_targets.append(victim)
            game_state["melee_effects"].append(MeleeSwingEffect(start_pos, end_pos))
            for victim in dash_targets:
                dealt = victim.take_damage(12.0, source=attacker, damage_type="design_physical_sunfire_2", game_state=game_state)
                if dealt > 0:
                    apply_design_hit_effects(attacker, victim, game_state, True)
            if fire_form:
                bonus_damage = attacker.max_hp * 0.03
                for victim in dash_targets:
                    if victim.alive:
                        if isinstance(victim, Character):
                            victim.take_damage(
                                bonus_damage,
                                source=attacker,
                                damage_type="true_sunfire_2",
                                game_state=game_state,
                                count_on_damage_dealt=False,
                            )
                        else:
                            victim.take_damage(bonus_damage, source=attacker, damage_type="true_sunfire_2", game_state=game_state)
                attacker.sunfire_invuln_timer = SUNFIRE_INVULN_DURATION
            attacker.pos = end_pos
            attacker.update_rect()
            attacker.recent_move_dir = direction
        elif combo_step == 3:
            for _ in range(3):
                if not target.alive:
                    break
                dealt = target.take_damage(5.0, source=attacker, damage_type="design_physical_sunfire_3", game_state=game_state)
                if dealt > 0:
                    apply_design_hit_effects(attacker, target, game_state, True)
                    if fire_form:
                        bonus_damage = attacker.max_hp * 0.015
                        if isinstance(target, Character):
                            target.take_damage(
                                bonus_damage,
                                source=attacker,
                                damage_type="true_sunfire_3",
                                game_state=game_state,
                                count_on_damage_dealt=False,
                            )
                        else:
                            target.take_damage(bonus_damage, source=attacker, damage_type="true_sunfire_3", game_state=game_state)
            attacker.sunfire_evasion_timer = SUNFIRE_EVADE_DURATION
        elif combo_step == 4:
            targets = collect_targets_in_cone(attacker.pos, direction, 92.0, 38.0, attacker.owner_id, game_state)
            for victim in targets:
                dealt = victim.take_damage(23.0, source=attacker, damage_type="design_physical_sunfire_4", game_state=game_state)
                if dealt > 0:
                    apply_design_hit_effects(attacker, victim, game_state, True)
                    victim.apply_slow(0.2, 2.0)
            if fire_form:
                bonus_damage = attacker.max_hp * 0.04
                for victim in targets:
                    if victim.alive:
                        if isinstance(victim, Character):
                            victim.take_damage(
                                bonus_damage,
                                source=attacker,
                                damage_type="true_sunfire_4",
                                game_state=game_state,
                                count_on_damage_dealt=False,
                            )
                        else:
                            victim.take_damage(bonus_damage, source=attacker, damage_type="true_sunfire_4", game_state=game_state)
        elif combo_step == 5:
            targets = []
            for victim in get_targetables(game_state):
                if not victim.alive or victim.owner_id == attacker.owner_id:
                    continue
                if (victim.pos - attacker.pos).length() <= attacker.radius + 72.0 + getattr(victim, "radius", 0):
                    targets.append(victim)
            for victim in targets:
                dealt = victim.take_damage(15.0, source=attacker, damage_type="design_physical_sunfire_5", game_state=game_state)
                if dealt > 0:
                    apply_design_hit_effects(attacker, victim, game_state, True)
            if fire_form:
                for victim in targets:
                    if victim.alive:
                        bonus_damage = max(1.0, (getattr(victim, "max_hp", 0.0) - getattr(victim, "hp", 0.0)) * 0.08)
                        if isinstance(victim, Character):
                            victim.take_damage(
                                bonus_damage,
                                source=attacker,
                                damage_type="true_sunfire_5",
                                game_state=game_state,
                                count_on_damage_dealt=False,
                            )
                        else:
                            victim.take_damage(bonus_damage, source=attacker, damage_type="true_sunfire_5", game_state=game_state)
                attacker.heal(60.0)
            else:
                attacker.heal(30.0)
            primary_target = select_nearest_enemy(attacker, game_state["characters"])
            if fire_form and primary_target is not None:
                knockback_dir = primary_target.pos - attacker.pos
                if knockback_dir.length_squared() > 0:
                    primary_target.apply_knockback(knockback_dir, 160.0)
        attacker.sunfire_combo_step = 1 if combo_step >= 5 else combo_step + 1
        attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
        attacker.on_attack_committed()
        return
    if role_num == 95:
        full_qi = getattr(attacker, "windstorm_qi_stacks", 0) >= WINDSTORM_FOX_QI_MAX
        blade_damage = damage * (WINDSTORM_FOX_DOUBLE_BLADE_RATIO if full_qi else 1.0)
        attack_dir = target.pos - attacker.pos
        if attack_dir.length_squared() == 0:
            attack_dir = random_unit_vector()
        attack_dir = attack_dir.normalize()
        blade_dirs = [attack_dir]
        if full_qi:
            blade_dirs = [
                attack_dir.rotate(-WINDSTORM_FOX_DOUBLE_BLADE_ROTATION),
                attack_dir.rotate(WINDSTORM_FOX_DOUBLE_BLADE_ROTATION),
            ]
        for blade_dir in blade_dirs:
            spawn_windstorm_blade_projectile(
                attacker,
                game_state,
                blade_dir,
                blade_damage,
                attacker.get_design_damage_type("windstorm_blade"),
                speed=max(attacker.base_projectile_speed * 1.45, 620.0),
                max_range=max(attacker.get_current_attack_range() + 80.0, 520.0),
            )
        if full_qi and random.random() < WINDSTORM_FOX_DASH_CHANCE:
            retreat = -attack_dir
            if retreat.length_squared() > 0:
                retreat = retreat.normalize()
                attacker.pos += retreat * WINDSTORM_FOX_DASH_DISTANCE
                attacker.pos.x = clamp(attacker.pos.x, ARENA_RECT.left + attacker.radius, ARENA_RECT.right - attacker.radius)
                attacker.pos.y = clamp(attacker.pos.y, ARENA_RECT.top + attacker.radius, ARENA_RECT.bottom - attacker.radius)
                attacker.recent_move_dir = retreat
                attacker.update_rect()
        attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
        attacker.on_attack_committed()
        return
    if role_num == 97:
        direction = target.pos - attacker.pos
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        swing_start = attacker.pos + direction * (attacker.radius + 2)
        swing_end = attacker.pos + direction * (attacker.get_current_attack_range() + 10)
        game_state["melee_effects"].append(MeleeSwingEffect(swing_start, swing_end))
        packet_damage = damage * 0.5
        dealt_physical = target.take_damage(
            packet_damage,
            source=attacker,
            damage_type="design_physical_equilibrium",
            game_state=game_state,
        )
        dealt_spell = target.take_damage(
            packet_damage,
            source=attacker,
            damage_type="design_spell_equilibrium",
            game_state=game_state,
        )
        if dealt_physical > 0 or dealt_spell > 0:
            apply_design_hit_effects(attacker, target, game_state, True)
        attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
        attacker.on_attack_committed()
        return
    if attacker.get_current_basic_attack_type() == "melee":
        direction = target.pos - attacker.pos
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        game_state["melee_effects"].append(MeleeSwingEffect(attacker.pos + direction * (attacker.radius + 2), attacker.pos + direction * (attacker.get_current_attack_range() + 10)))
        for _ in range(repeats):
            dealt = target.take_damage(damage, source=attacker, damage_type=attacker.get_design_damage_type("basic_melee"), game_state=game_state)
            if dealt > 0:
                apply_design_hit_effects(attacker, target, game_state, True)
                if role_num == 63 and target.hp > 0 and target.hp <= target.max_hp * 0.15:
                    target.take_damage(target.hp + 1.0, source=attacker, damage_type="true_design_execute", game_state=game_state)
                    attacker.design_execute_buff_timer = 5.0
                if role_num == 119 and attacker.design_blood_feast_timer > 0:
                    target.design_blood_curse = min(BLOODSUCKER_CURSE_MAX, getattr(target, "design_blood_curse", 0) + 1)
                    target.design_blood_curse_timer = BLOODSUCKER_CURSE_DURATION
                    lost_hp = max(0.0, target.max_hp - target.hp)
                    target.take_damage(lost_hp * BLOODSUCKER_FEAST_TRUE_RATIO, source=attacker, damage_type="true_design_blood_feast", game_state=game_state)
        stun_duration = attacker.get_current_melee_stun_duration()
        if stun_duration > 0:
            call_target_method(target, "apply_stun", stun_duration)
    else:
        direction = target.pos - attacker.pos
        if role_num == 93:
            if getattr(attacker, "twin_mirror_form", "white") == "white":
                spawn_design_projectile(
                    attacker,
                    game_state,
                    direction,
                    damage,
                    "design_physical_twin_white",
                    TWIN_MIRROR_WHITE_COLOR,
                    speed=max(attacker.config.get("projectile_speed", 310.0), 380.0),
                    max_range=attacker.get_current_attack_range(),
                )
            else:
                spawn_design_projectile(
                    attacker,
                    game_state,
                    direction,
                    damage + TWIN_MIRROR_BLACK_ATTACK_BONUS,
                    "design_physical_twin_black",
                    TWIN_MIRROR_BLACK_COLOR,
                    speed=max(attacker.config.get("projectile_speed", 310.0) * 1.35, 420.0),
                    max_range=attacker.get_current_attack_range(),
                    pierce=True,
                )
            attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
            attacker.on_attack_committed()
            return
        if role_num == 48:
            for _ in range(attacker.config.get("shotgun_pellets", 12)):
                shot_dir = (direction.normalize() if direction.length_squared() > 0 else random_unit_vector()).rotate(random.uniform(-20.0, 20.0))
                spawn_design_projectile(attacker, game_state, shot_dir, attacker.config.get("shotgun_damage", 3.0), "design_physical_shotgun", max_range=attacker.config.get("shotgun_range", 180.0))
        elif role_num == 56:
            game_state["beam_events"].append(BeamEvent(attacker.pos, target.pos, (255, 222, 120)))
            dealt = target.take_damage(damage, source=attacker, damage_type="design_spell_oracle_beam", game_state=game_state)
            if dealt > 0:
                apply_design_hit_effects(attacker, target, game_state, False)
        elif role_num == 75:
            beam_dir = direction.normalize() if direction.length_squared() > 0 else pygame.Vector2(1, 0)
            beam_end = attacker.pos + beam_dir * 1200.0
            game_state["beam_events"].append(BeamEvent(attacker.pos, beam_end, attacker.color))
            for victim in get_targetables(game_state):
                if victim.alive and victim.owner_id != attacker.owner_id and distance_point_to_segment(victim.pos, attacker.pos, beam_end) <= victim.radius + 8:
                    dealt = victim.take_damage(damage, source=attacker, damage_type="design_spell_astral_beam", game_state=game_state)
                    if dealt > 0:
                        apply_design_hit_effects(attacker, victim, game_state, False)
        elif role_num == 55:
            blast_radius = attacker.config.get("attack_aoe_radius", 20.0)
            spawn_design_projectile(
                attacker,
                game_state,
                direction,
                damage,
                attacker.get_design_damage_type("mortar_blast"),
                speed=max(attacker.config.get("projectile_speed", 310.0), 360.0),
                max_range=attacker.get_current_attack_range(),
                explosion_radius=blast_radius,
                explosion_damage=damage,
                explosion_damage_type="design_physical_mortar_blast",
                explosion_mp_per_hit=2.0,
            )
        elif role_num == 78:  # 炼狱使者：远程法术火弹
            spawn_design_projectile(
                attacker,
                game_state,
                direction,
                damage,
                "design_spell_hellfire_orb",
                color=(232, 74, 58),
                speed=max(attacker.config.get("projectile_speed", 310.0), 360.0),
                max_range=attacker.get_current_attack_range(),
                on_hit=lambda proj, tgt, dealt, hgs: apply_design_hit_effects(attacker, tgt, hgs, False),
            )
        elif role_num == 110:  # 噬魂蝶母：常态蚀鳞粉 / 幻蝶形态双发幻蝶
            form_active = getattr(attacker, "design_soul_moth_form", False)
            if form_active:
                for shot_index in range(2):
                    shot_dir = direction.rotate(-14.0 if shot_index == 0 else 14.0)

                    def moth_form_hit(proj, tgt, dealt, hgs):
                        if dealt <= 0 or not isinstance(tgt, Character):
                            return
                        apply_design_hit_effects(attacker, tgt, hgs, False)
                        tgt.take_damage(
                            tgt.max_hp * SOUL_MOTH_TRUE_RATIO,
                            source=attacker,
                            damage_type="true_soul_moth_powder",
                            game_state=hgs,
                        )
                        if random.random() < SOUL_MOTH_POISON_CHANCE_FORM:
                            call_target_method(tgt, "add_poison_progress", 1.0)
                        attacker.heal(dealt * SOUL_MOTH_LIFESTEAL_RATIO)

                    spawn_design_projectile(
                        attacker,
                        game_state,
                        shot_dir,
                        SOUL_MOTH_FORM_ATTACK_DAMAGE,
                        "design_spell_soul_moth_form",
                        color=SOUL_MOTH_FORM_COLOR,
                        speed=max(attacker.config.get("projectile_speed", 310.0), 340.0),
                        max_range=attacker.get_current_attack_range(),
                        visual_shape="crescent",
                        on_hit=moth_form_hit,
                    )
            else:
                def moth_normal_hit(proj, tgt, dealt, hgs):
                    if dealt <= 0 or not isinstance(tgt, Character):
                        return
                    apply_design_hit_effects(attacker, tgt, hgs, False)
                    if random.random() < SOUL_MOTH_POISON_CHANCE_NORMAL:
                        call_target_method(tgt, "add_poison_progress", 1.0)

                spawn_design_projectile(
                    attacker,
                    game_state,
                    direction,
                    damage,
                    "design_spell_soul_moth_powder",
                    color=SOUL_MOTH_COLOR,
                    speed=max(attacker.config.get("projectile_speed", 310.0), 340.0),
                    max_range=attacker.get_current_attack_range(),
                    visual_shape="crescent",
                    on_hit=moth_normal_hit,
                )
        else:
            total_shots = repeats + (2 if role_num == 79 and random.random() < 0.2 else 0)
            for shot_index in range(total_shots):
                shot_dir = direction.normalize() if direction.length_squared() > 0 else random_unit_vector()
                if total_shots > 1:
                    shot_dir = shot_dir.rotate((shot_index - (total_shots - 1) / 2) * 6.0)
                spawn_design_projectile(
                    attacker,
                    game_state,
                    shot_dir,
                    damage,
                    attacker.get_design_damage_type("basic"),
                    max_range=1200.0 if role_num == 53 and attacker.design_sentinel_lock else attacker.get_current_attack_range(),
                    pierce=role_num == 59,
                    slow_amount=0.5 if attacker.design_element_mode == "ice" else 0.0,
                    slow_duration=2.0 if attacker.design_element_mode == "ice" else 0.0,
                    on_hit=(lambda proj, tgt, dealt, hgs: apply_design_hit_effects(attacker, tgt, hgs, False)) if role_num in {104, 106, 108} else None,
                )
        attacker.design_sentinel_lock = False
    attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
    attacker.on_attack_committed()


def cast_design_skill(caster, game_state, token=None):
    if getattr(caster, "design_banished", False):
        return False
    token = token or caster.design_meta.get("skill_token")
    role_num = caster.design_meta.get("role_num")
    enemies = [target for target in get_targetables(game_state) if target.alive and target.owner_id != caster.owner_id]
    if token != "mimic":
        game_state["last_design_skill_token"] = token
    if token == "trap":
        add_design_effect(game_state, DesignEffect("trap", caster, random_spawn_point(ARENA_RECT, 20.0), radius=18.0, lifetime=12.0, damage=40.0, disarm_duration=3.0, hidden=True))
    elif token == "hero_triple":
        choice = random.choice(("hero_slash", "hero_guard", "hero_dash"))
        if choice == "hero_slash":
            direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
            direction = direction.normalize()
            end_pos = caster.pos + direction * 120.0
            game_state["beam_events"].append(BeamEvent(caster.pos, end_pos, caster.color))
            for enemy in enemies:
                if distance_point_to_segment(enemy.pos, caster.pos, end_pos) <= enemy.radius + 18:
                    enemy.take_damage(35.0 + caster.max_hp * 0.15, source=caster, damage_type="design_physical_hero_slash", game_state=game_state)
        elif choice == "hero_guard":
            caster.add_true_shield(80.0)
            caster.design_damage_reduction = max(caster.design_damage_reduction, 0.30)
            caster.design_fortress_timer = max(caster.design_fortress_timer, 3.0)
        else:
            target = select_nearest_enemy(caster, game_state["characters"])
            if target is not None:
                direction = target.pos - caster.pos
                if direction.length_squared() == 0:
                    direction = random_unit_vector()
                direction = direction.normalize()
                landing = caster.pos + direction * 160.0
                landing.x = clamp(landing.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
                landing.y = clamp(landing.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
                game_state["beam_events"].append(BeamEvent(caster.pos, landing, caster.color))
                for enemy in enemies:
                    if distance_point_to_segment(enemy.pos, caster.pos, landing) <= enemy.radius + 14:
                        enemy.take_damage(28.0, source=caster, damage_type="design_physical_hero_dash", game_state=game_state)
                        enemy.apply_slow(0.3, 2.0)
                caster.pos = landing
                caster.update_rect()
    elif token == "sunfire_kagura":
        caster.clear_control_states()
        caster.sunfire_fire_timer = SUNFIRE_FIRE_DURATION
    elif role_num == 96 or token == "tide_flood":
        caster.spawn_sea_fish(game_state, caster.pos)
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            direction = target.pos - caster.pos
        else:
            direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        caster.spawn_sea_waves(game_state, direction)
    elif role_num == 97 or token == "absolute_equality":
        living_units = [unit for unit in game_state["characters"] if unit.alive]
        if not living_units:
            return True
        if len(living_units) == 1:
            chosen_units = [living_units[0], living_units[0]]
        elif len(living_units) == 2:
            chosen_units = living_units
        elif caster in living_units and len(living_units) == 2:
            chosen_units = living_units
        else:
            highest = max(living_units, key=lambda unit: (unit.hp, -((unit.pos - caster.pos).length_squared() if hasattr(unit, "pos") else 0.0)))
            lowest = min(living_units, key=lambda unit: (unit.hp, (unit.pos - caster.pos).length_squared() if hasattr(unit, "pos") else 0.0))
            chosen_units = [highest, lowest]
        average_hp = (chosen_units[0].hp + chosen_units[1].hp) / 2.0
        for unit in chosen_units:
            unit.hp = clamp(average_hp, 0.0, unit.max_hp)
            if hasattr(unit, "update_rect"):
                unit.update_rect()
            if hasattr(unit, "apply_equilibrium_resistance_penalty"):
                unit.apply_equilibrium_resistance_penalty(0.25, EQUILIBRIUM_THRESHOLD_RESIST_DURATION)
        midpoint = (pygame.Vector2(chosen_units[0].pos) + pygame.Vector2(chosen_units[1].pos)) * 0.5
        add_design_effect(
            game_state,
            DesignEffect(
                "equilibrium_pulse",
                caster,
                midpoint,
                radius=max(24.0, min(58.0, chosen_units[0].pos.distance_to(chosen_units[1].pos) * 0.35 + 22.0)),
                lifetime=EQUILIBRIUM_PULSE_DURATION,
            ),
        )
        caster.add_true_shield(60.0)
    elif role_num == 112 or role_num == 113 or role_num == 114:
        if role_num == 112:
            if token == "banner_valor":
                for flag in game_state.get("banners", []):
                    if flag.owner_id == caster.owner_id and flag.alive:
                        flag.lifesteal_timer = BANNER_LIFESTEAL_DURATION
                return True
            target = select_nearest_enemy(caster, game_state["characters"])
            my_banner = next((flag for flag in game_state.get("banners", []) if flag.owner_id == caster.owner_id and flag.alive), None)
            if my_banner is None:
                my_banner = Banner(caster, pygame.Vector2(caster.pos))
                game_state["banners"].append(my_banner)
            if target is None:
                return False
            my_banner.pos = pygame.Vector2(target.pos) + random_unit_vector() * 20.0
            my_banner.rect.center = (round(my_banner.pos.x), round(my_banner.pos.y))
            spawn_attack_impact(game_state, my_banner.pos, BANNER_COLOR, radius=14, thickness=3, burst_count=8)
            return True
        if role_num == 113:
            if token == "potion_wild":
                for ally in game_state.get("characters", []):
                    if ally.alive and ally.owner_id == caster.owner_id:
                        ally.design_wild_brew_timer = max(getattr(ally, "design_wild_brew_timer", 0.0), WILD_BREW_DURATION)
                return True
            allies = [c for c in game_state.get("characters", []) if c.alive and c.owner_id == caster.owner_id and c is not caster]
            if not allies:
                return False
            for ally in allies:
                caster.throw_potion(ally, game_state)
            return True
        if token == "squad_protect":
            allies = [c for c in game_state.get("characters", []) if c.alive and c.owner_id == caster.owner_id and c is not caster]
            if not allies:
                return False
            ally = min(allies, key=lambda c: (c.pos - caster.pos).length_squared())
            ally.design_protect_timer = max(getattr(ally, "design_protect_timer", 0.0), SQUAD_PROTECT_DURATION)
            spawn_attack_impact(game_state, ally.pos, COMMANDER_COLOR, radius=12, thickness=2, burst_count=8)
            return True
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return False
        target.design_squad_primary_timer = SQUAD_FOCUS_DURATION
        target.design_squad_primary_owner_id = caster.owner_id
        target.apply_slow(SQUAD_FOCUS_SLOW, 2.0)
        spawn_attack_impact(game_state, target.pos, (255, 90, 90), radius=12, thickness=3, burst_count=10)
        return True
    elif role_num == 120 or token == "kenshi_flash":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return False
        direction = target.pos - caster.pos
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        distance = (target.pos - caster.pos).length()
        step = min(KENSHI_FLASH_DASH, max(0.0, distance - target.radius - caster.radius - 4.0))
        caster.pos += direction * step
        caster.pos.x = clamp(caster.pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
        caster.pos.y = clamp(caster.pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
        caster.update_rect()
        dealt = target.take_damage(KENSHI_FLASH_DAMAGE, source=caster, damage_type="design_physical_kenshi_flash", game_state=game_state)
        mark_count = getattr(target, "design_kenshi_mark", 0)
        if dealt > 0 and mark_count >= KENSHI_FLASH_EXECUTE_MIN_MARK:
            lost_hp = max(0.0, target.max_hp - target.hp)
            target.take_damage(lost_hp * KENSHI_FLASH_EXECUTE_RATIO, source=caster, damage_type="true_design_kenshi_execute", game_state=game_state)
        spawn_attack_impact(game_state, target.pos, KENSHI_COLOR, radius=12, thickness=2, burst_count=8)
        return True
    elif role_num == 119 or token == "blood_feast":
        caster.design_blood_feast_timer = BLOODSUCKER_FEAST_DURATION
        spawn_attack_impact(game_state, caster.pos, BLOODSUCKER_COLOR, radius=20, thickness=3, burst_count=14)
        return True
    elif role_num == 118 or token == "tide_link":
        if caster.design_tide_link_active:
            for ally in game_state.get("characters", []):
                if getattr(ally, "design_tide_hub_id", None) == caster.id:
                    ally.design_tide_link_active = False
                    ally.design_tide_link_timer = 0.0
                    ally.design_tide_hub_id = None
            caster.design_tide_link_active = False
            caster.design_tide_link_timer = 0.0
            caster.design_tide_hub_id = None
            return True
        allies = [c for c in game_state.get("characters", []) if c.alive and c.owner_id == caster.owner_id]
        if len(allies) < 2:
            return False  # 团队战才有效（无同队无法链接）
        for ally in allies:
            ally.design_tide_link_active = True
            ally.design_tide_link_timer = TIDE_LINK_DURATION
            ally.design_tide_hub_id = caster.id
        spawn_attack_impact(game_state, caster.pos, TIDE_COLOR, radius=26, thickness=3, burst_count=14)
        return True
    elif role_num == 117 or token == "raikiri_first":
        stage = getattr(caster, "design_raikiri_stage", 0)
        if stage == 0:
            target = select_nearest_enemy(caster, game_state["characters"])
            if target is None:
                return False
            direction = target.pos - caster.pos
            if direction.length_squared() == 0:
                direction = random_unit_vector()
            direction = direction.normalize()
            distance = (target.pos - caster.pos).length()
            dash = min(RAIKIRI_STAGE1_DASH, max(0.0, distance - target.radius - caster.radius - 4.0))
            start_pos = pygame.Vector2(caster.pos)
            caster.pos += direction * dash
            caster.pos.x = clamp(caster.pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
            caster.pos.y = clamp(caster.pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
            caster.update_rect()
            game_state["beam_events"].append(BeamEvent(start_pos, caster.pos, RAIKIRI_COLOR))
            dealt = target.take_damage(RAIKIRI_STAGE1_DAMAGE, source=caster, damage_type="design_physical_raikiri_1", game_state=game_state)
            if dealt > 0:
                target.apply_slow(RAIKIRI_STAGE1_SLOW, 1.0)
                apply_raikiri_mark(caster, target, 1, game_state)
            spawn_attack_impact(game_state, target.pos, RAIKIRI_COLOR, radius=12, thickness=2, burst_count=8)
        elif stage == 1:
            target = select_nearest_enemy(caster, game_state["characters"])
            back = -caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
            back = back.normalize()
            pre_pos = pygame.Vector2(caster.pos)
            caster.pos += back * RAIKIRI_STAGE2_JUMP
            caster.pos.x = clamp(caster.pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
            caster.pos.y = clamp(caster.pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
            caster.update_rect()
            if target is not None and (target.pos - pre_pos).length() <= RAIKIRI_STAGE2_RANGE + getattr(target, "radius", 0):
                game_state["beam_events"].append(BeamEvent(pre_pos, target.pos, (180, 230, 255)))
                dealt = target.take_damage(RAIKIRI_STAGE2_DAMAGE, source=caster, damage_type="design_spell_raikiri_2", game_state=game_state)
                if dealt > 0:
                    target.apply_root(RAIKIRI_STAGE2_ROOT)
                    apply_raikiri_mark(caster, target, 1, game_state)
        else:
            hit_any = False
            for victim in enemies:
                if victim.alive and (victim.pos - caster.pos).length() <= RAIKIRI_STAGE3_RADIUS + getattr(victim, "radius", 0):
                    dealt = victim.take_damage(RAIKIRI_STAGE3_DAMAGE, source=caster, damage_type="design_spell_raikiri_3", game_state=game_state)
                    if dealt > 0:
                        call_target_method(victim, "apply_stun", RAIKIRI_STAGE3_STUN)
                        apply_raikiri_mark(caster, victim, 3, game_state)
                        spawn_attack_impact(game_state, victim.pos, RAIKIRI_COLOR, radius=14, thickness=3, burst_count=12)
                        hit_any = True
            if hit_any:
                game_state["shake_timer"] = max(game_state.get("shake_timer", 0.0), 0.08)
                game_state["shake_magnitude"] = max(game_state.get("shake_magnitude", 0.0), 3.0)
        caster.design_raikiri_stage = (stage + 1) % 3
        caster.gain_mp(RAIKIRI_SKILL_HIT_MP, "raikiri_hit")
        return True
    elif role_num == 116 or token == "sparrow_swap":
        current_host = caster.get_sparrow_host(game_state)
        for victim in enemies:
            if victim.alive and (victim.pos - caster.pos).length() <= 90.0 + getattr(victim, "radius", 0):
                victim.take_damage(SPARROW_SWAP_DAMAGE, source=caster, damage_type="design_spell_sparrow_swap", game_state=game_state)
                knock = victim.pos - caster.pos
                if knock.length_squared() > 0:
                    call_target_method(victim, "apply_knockback", knock.normalize(), 50.0)
        if current_host is not None:
            current_host.design_sparrow_fury_timer = max(getattr(current_host, "design_sparrow_fury_timer", 0.0), SPARROW_FURY_DURATION)
            caster.design_sparrow_host_id = None
        allies = [
            c for c in game_state.get("characters", [])
            if c.alive and c.owner_id == caster.owner_id and c is not caster and c is not current_host and getattr(c, "design_corrupted_blood", 0.0) <= 0
        ]
        if allies:
            new_host = min(allies, key=lambda c: (c.pos - caster.pos).length_squared())
            caster.attach_sparrow_host(new_host, game_state)
        return True
    elif role_num == 115 or token == "void_banish":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return False
        dealt = target.take_damage(BANISH_SKILL_DAMAGE, source=caster, damage_type="design_spell_void_banish", game_state=game_state)
        if dealt > 0:
            target.design_banish_mark += 1
            spawn_attack_impact(game_state, target.pos, BANISH_COLOR, radius=14, thickness=3, burst_count=10)
            if target.design_banish_mark >= BANISH_MARKS_REQUIRED:
                target.design_banish_mark = 0
                target.design_banished = True
                target.design_banish_points = 0
                target.design_banish_tick_timer = BANISH_TICK_INTERVAL
                target.design_banish_roll_timer = BANISH_ROLL_INTERVAL
                spawn_damage_text(game_state, target, 0.0, text="放逐！", color=BANISH_COLOR)
        return True
    elif role_num == 111 or token == "rail_train":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return False
        direction = target.pos - caster.pos
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        # 铁轨警示线（先铺轨）
        add_design_effect(
            game_state,
            DesignEffect(
                "rail_track",
                caster,
                pygame.Vector2(caster.pos),
                direction=direction,
                length=RAIL_LENGTH,
                width=RAIL_WIDTH,
                lifetime=RAIL_TRACK_DURATION,
            ),
        )
        # 列车：从屏幕外驶入，沿直线横穿
        diagonal_half = (ARENA_RECT.width + ARENA_RECT.height) * 0.5
        start_pos = caster.pos - direction * (diagonal_half + RAIL_LENGTH * 0.5)
        add_design_effect(
            game_state,
            DesignEffect(
                "rail_train",
                caster,
                start_pos,
                direction=direction,
                length=RAIL_LENGTH,
                width=RAIL_WIDTH,
                speed=RAIL_SPEED,
                delay=RAIL_ENTER_DELAY,
                total_travel=diagonal_half * 2.0 + RAIL_LENGTH,
                lifetime=8.0,
            ),
        )
        return True
    elif role_num == 110 or token == "soul_moth_silk":
        if caster.design_soul_moth_form:
            living = [enemy for enemy in enemies if enemy.alive]
            if not living:
                return False
            chosen_targets = random.sample(living, min(SOUL_MOTH_FLUTTER_TARGETS, len(living)))
            for chosen in chosen_targets:
                chosen.take_damage(SOUL_MOTH_FLUTTER_DAMAGE, source=caster, damage_type="design_spell_soul_moth_flutter", game_state=game_state)
                if isinstance(chosen, Character):
                    chosen.design_confuse_timer = max(getattr(chosen, "design_confuse_timer", 0.0), SOUL_MOTH_FLUTTER_CONFUSE_DURATION)
                spawn_attack_impact(game_state, chosen.pos, SOUL_MOTH_FORM_COLOR, radius=12, thickness=2, burst_count=8)
            return True
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return False
        target.take_damage(SOUL_MOTH_SILK_DAMAGE, source=caster, damage_type="design_spell_soul_moth_silk", game_state=game_state)
        drag = target.pos - caster.pos
        if drag.length_squared() > 0:
            pull_distance = min(SOUL_MOTH_SILK_DRAG, drag.length())
            target.pos -= drag.normalize() * pull_distance
            if hasattr(target, "update_rect"):
                target.update_rect()
        if hasattr(target, "apply_root"):
            target.apply_root(SOUL_MOTH_SILK_ROOT_DURATION)
        spawn_attack_impact(game_state, target.pos, SOUL_MOTH_COLOR, radius=14, thickness=3, burst_count=8)
        return True
    elif role_num == 95 or token == "windstorm_blade_roll":
        def add_windstorm_volley():
            living_enemies = [enemy for enemy in enemies if enemy.alive]
            if not living_enemies:
                return False
            roll = random.random()
            if roll < 0.50:
                tier = dict(total=8, speed=700.0, max_range=900.0, apply_resist=False, lifesteal_ratio=0.0, ricochet=False, global_damage=WINDSTORM_FOX_GLOBAL_BLADE_DAMAGE)
            elif roll < 0.85:
                tier = dict(total=12, speed=730.0, max_range=920.0, apply_resist=True, lifesteal_ratio=0.0, ricochet=False, global_damage=0.0)
            else:
                tier = dict(total=20, speed=760.0, max_range=940.0, apply_resist=False, lifesteal_ratio=WINDSTORM_FOX_LIFESTEAL_RATIO, ricochet=True, global_damage=0.0)
            add_design_effect(
                game_state,
                DesignEffect(
                    "windstorm_blades",
                    caster,
                    pygame.Vector2(caster.pos),
                    lifetime=tier["total"] * 0.10 + 1.0,
                    interval=0.10,
                    damage=WINDSTORM_FOX_SKILL_BLADE_DAMAGE,
                    damage_type="design_physical_windstorm_blade",
                    **tier,
                ),
            )
            return True

        if not add_windstorm_volley():
            return False  # 无活敌：不消耗
        if random.random() < 0.30:
            add_windstorm_volley()
    elif role_num == 93 or token == "twin_mirror_pulse":
        current_form = getattr(caster, "twin_mirror_form", "white")
        if current_form == "white":
            caster.heal(TWIN_MIRROR_WHITE_HEAL)
            for enemy in enemies:
                if (enemy.pos - caster.pos).length() <= 40.0 + getattr(enemy, "radius", 0):
                    enemy.apply_knockback(enemy.pos - caster.pos, TWIN_MIRROR_WHITE_KNOCKBACK)
        else:
            target = select_nearest_enemy(caster, game_state["characters"])
            anchor = pygame.Vector2(target.pos if target is not None else caster.pos)
            add_design_effect(
                game_state,
                DesignEffect(
                    "mirror_void",
                    caster,
                    anchor,
                    radius=TWIN_MIRROR_BLACK_PULL_RADIUS,
                    lifetime=TWIN_MIRROR_BLACK_DURATION,
                    pull=TWIN_MIRROR_BLACK_PULL_STRENGTH,
                    damage=TWIN_MIRROR_BLACK_AOE_DAMAGE,
                    slow=TWIN_MIRROR_BLACK_SLOW,
                    slow_duration=TWIN_MIRROR_BLACK_SLOW_DURATION,
                ),
            )
        if caster.switch_twin_mirror_form():
            caster.design_misc_timer = 0.0
    elif token == "charge_dash":
        target = select_farthest_enemy(caster, game_state["characters"])
        if target is not None:
            direction = (target.pos - caster.pos).normalize() if (target.pos - caster.pos).length_squared() > 0 else random_unit_vector()
            end_pos = caster.pos + direction * 300.0
            beam_end = pygame.Vector2(clamp(end_pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius), clamp(end_pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius))
            game_state["beam_events"].append(BeamEvent(caster.pos, beam_end, caster.color))
            for enemy in enemies:
                if distance_point_to_segment(enemy.pos, caster.pos, beam_end) <= enemy.radius + 16:
                    enemy.take_damage(30.0, source=caster, damage_type="design_physical_charge", game_state=game_state)
                    enemy.apply_knockback(enemy.pos - caster.pos, 55.0)
            caster.pos = beam_end
            caster.update_rect()
    elif token == "phase_shift":
        caster.pos = random_spawn_point(ARENA_RECT, caster.radius + 4)
        caster.design_untargetable_timer = 3.5
        caster.update_rect()
    elif token == "summon_wolf":
        if has_living_design_summon(game_state, caster.owner_id, "wolf"):
            return False
        if getattr(caster, "design_wolf_cd_timer", 0.0) > 0:
            return False
        game_state["design_summons"].append(DesignSummon(caster, "wolf", caster.pos + random_unit_vector() * 18))
    elif token == "plague_mark":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            target.take_damage(5.0, source=caster, damage_type="design_spell_plague", game_state=game_state)
            if target.design_marked and target.design_mark_owner_id == caster.owner_id:
                target.add_poison_progress(5.0)
                target.design_poison_erosion += 1
                target.design_marked = False
                target.design_mark_duration = 0.0
            else:
                target.design_marked = True
                target.design_mark_owner_id = caster.owner_id
                target.design_mark_duration = 8.0
    elif token == "meteor_storm":
        targets = enemies[:] if enemies else [None]
        for _ in range(4):
            anchor = random.choice(targets)
            pos = random_spawn_point(ARENA_RECT, 50.0) if anchor is None else pygame.Vector2(anchor.pos)
            add_design_effect(game_state, DesignEffect("meteor", caster, pos, radius=40.0, lifetime=1.0, damage=150.0))
    elif token == "fortress":
        caster.design_fortress_timer = 5.0
        caster.design_damage_reduction = DESIGN_FORTRESS_REDUCTION
        caster.design_taunt_timer = 5.0
        for enemy in enemies:
            if isinstance(enemy, Character) and (enemy.pos - caster.pos).length() <= DESIGN_FORTRESS_RADIUS + enemy.radius:
                enemy.design_taunt_timer = max(enemy.design_taunt_timer, 5.0)
                enemy.design_taunt_owner_id = caster.owner_id
    elif token == "cannon_support":
        for _ in range(6):
            if not enemies:
                break
            chosen = random.choice(enemies)
            spawn_design_projectile(caster, game_state, chosen.pos - caster.pos, 80.0, "design_physical_cannon", (214, 214, 214), speed=240.0, max_range=1200.0)
    elif token == "blood_ritual":
        for enemy in list(enemies):
            if enemy.hp > 0 and enemy.hp <= enemy.max_hp * 0.2:
                pos = pygame.Vector2(enemy.pos)
                enemy.take_damage(enemy.hp + 1.0, source=caster, damage_type="true_design_blood_ritual", game_state=game_state)
                apply_aoe_damage(pos, 48.0, 40.0, caster.owner_id, game_state, source=caster, damage_type="design_physical_blood_burst")
    elif token == "bloodwraith_blood_pool":
        caster.bloodwraith_shield_timer = BLOODWRAITH_SHIELD_DURATION
        caster.bloodwraith_shield_hp = max(caster.bloodwraith_shield_hp, caster.max_hp * BLOODWRAITH_SHIELD_RATIO)
    elif token == "phoenix_wrath":
        nearest = sorted(
            (enemy for enemy in enemies if enemy.alive and isinstance(enemy, Character)),
            key=lambda enemy: (enemy.pos - caster.pos).length_squared(),
        )[:PHOENIX_WRATH_TARGETS]
        for enemy in nearest:
            enemy.apply_phoenix_fire(1, source=caster, game_state=game_state)
            enemy.design_phoenix_wrath_timer = PHOENIX_WRATH_DOT_DURATION
            enemy.design_phoenix_wrath_accum = 0.0
            enemy.design_phoenix_wrath_source = caster
    elif token == "xuanwu_bulwark":
        caster.design_xuan_bulwark_shield = XUANWU_BULWARK_SHIELD_BASE + XUANWU_BULWARK_SHIELD_PER_SHELL * caster.design_shell_stacks
        caster.design_xuan_bulwark_timer = XUANWU_BULWARK_DURATION
        caster.design_xuan_bulwark_broken_triggered = False
        caster.design_damage_reduction = max(caster.design_damage_reduction, XUANWU_BULWARK_DAMAGE_REDUCTION)
        caster.design_fortress_timer = max(caster.design_fortress_timer, XUANWU_BULWARK_DURATION)
        for enemy in enemies:
            if isinstance(enemy, Character) and (enemy.pos - caster.pos).length() <= XUANWU_BULWARK_TAUNT_RADIUS + enemy.radius:
                enemy.design_taunt_timer = max(enemy.design_taunt_timer, XUANWU_BULWARK_TAUNT_DURATION)
                enemy.design_taunt_owner_id = caster.owner_id
    elif token == "tiger_roar":
        prey = caster.get_tiger_prey(game_state)
        if caster.design_tiger_hunt_value >= TIGER_HUNT_VALUE_MAX:
            caster.design_tiger_hunt_value = 0.0
            caster.gain_mp(TIGER_EXECUTE_CHARGE, "tiger_execute")
            if prey is not None and prey.alive:
                lost_hp = max(0.0, prey.max_hp - prey.hp)
                exec_damage = TIGER_EXECUTE_DAMAGE_BASE + lost_hp * TIGER_EXECUTE_DAMAGE_LOST_HP_RATIO
                prey.take_damage(exec_damage, source=caster, damage_type="design_physical_tiger_execute", game_state=game_state)
                if not prey.alive:
                    caster.tiger_execute_kill(game_state)
            else:
                caster.mark_tiger_prey(game_state)
        else:
            direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
            direction = direction.normalize()
            roar_targets = collect_targets_in_cone(caster.pos, direction, TIGER_ROAR_RANGE, TIGER_ROAR_HALF_ANGLE, caster.owner_id, game_state)
            total_dealt = 0.0
            for enemy in roar_targets:
                roar_damage = TIGER_ROAR_DAMAGE_BASE + TIGER_ROAR_DAMAGE_PER_POWER * caster.design_tiger_power
                dealt = enemy.take_damage(roar_damage, source=caster, damage_type="design_physical_tiger_roar", game_state=game_state)
                total_dealt += dealt
                enemy.apply_tiger_wound(1)
                enemy.apply_slow(TIGER_ROAR_SLOW, TIGER_ROAR_SLOW_DURATION)
            if prey is not None and prey.alive and prey in roar_targets:
                prey.apply_tiger_wound(1)
                caster.heal(total_dealt * TIGER_ROAR_HEAL_RATIO)
            if prey is not None and not prey.alive:
                caster.tiger_execute_kill(game_state)
    elif token == "dragon_sweep":
        if caster.design_dragon_sweep_cooldown <= 0:
            direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
            direction = direction.normalize()
            sweep_start = pygame.Vector2(caster.pos)
            sweep_end = sweep_start + direction * DRAGON_SWEEP_RANGE
            sweep_end.x = clamp(sweep_end.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
            sweep_end.y = clamp(sweep_end.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
            game_state["beam_events"].append(
                BeamEvent(sweep_start, sweep_end, DRAGON_THUNDER_COLOR if caster.design_dragon_form == "thunder" else DRAGON_WOOD_COLOR)
            )
            sweep_damage_type = caster.get_design_damage_type("dragon_sweep")
            for enemy in enemies:
                if enemy.alive and distance_point_to_segment(enemy.pos, sweep_start, sweep_end) <= DRAGON_SWEEP_PATH_WIDTH * 0.5 + getattr(enemy, "radius", 0):
                    enemy.take_damage(DRAGON_SWEEP_DAMAGE, source=caster, damage_type=sweep_damage_type, game_state=game_state)
            breath_before = caster.get_dragon_breath()
            caster.pos = sweep_end
            caster.update_rect()
            caster.design_dragon_sweep_cooldown = DRAGON_SWEEP_COOLDOWN
            caster.dragon_switch(game_state, breath_before)
    elif token == "susanoo_ominous_raijin":
        living = [enemy for enemy in enemies if enemy.alive and isinstance(enemy, Character)]
        if living:
            prey = max(living, key=lambda e: (int(getattr(e, "design_susanoo_prowl", 0)), -((e.pos - caster.pos).length_squared())))
            caster.design_untargetable_timer = max(caster.design_untargetable_timer, SUSANOO_CAST_INVULN)
            prowl_before = prey.design_susanoo_prowl
            for _ in range(SUSANOO_RAIJIN_BOLTS):
                if not prey.alive:
                    break
                game_state["beam_events"].append(BeamEvent(prey.pos + pygame.Vector2(0, -120), prey.pos, SUSANOO_THUNDER_COLOR))
                prey.take_damage(SUSANOO_BOLT_DAMAGE, source=caster, damage_type="design_spell_susanoo_bolt", game_state=game_state)
            for _ in range(prowl_before):
                if not prey.alive:
                    break
                game_state["beam_events"].append(BeamEvent(prey.pos + pygame.Vector2(0, -90), prey.pos, SUSANOO_ARC_COLOR))
                prey.take_damage(SUSANOO_PROWL_EXPLODE_DAMAGE, source=caster, damage_type="design_spell_susanoo_explode", game_state=game_state)
            prep_pos = pygame.Vector2(prey.pos)
            prey.design_susanoo_prowl = 0
            spawn_attack_impact(game_state, prep_pos, SUSANOO_THUNDER_COLOR, radius=18, thickness=3, burst_count=12)
    elif token == "ghost_fear":
        living = [enemy for enemy in enemies if enemy.alive and isinstance(enemy, Character)]
        for enemy in living:
            if (enemy.pos - caster.pos).length() <= GHOST_BARAGE_RADIUS + getattr(enemy, "radius", 0):
                dread = min(GHOST_DREAD_MAX, int(getattr(enemy, "design_dread", 0)))
                dealt = enemy.take_damage(
                    GHOST_BARAGE_BASE + GHOST_BARAGE_PER_STACK * dread,
                    source=caster,
                    damage_type="design_spell_ghost_fear",
                    game_state=game_state,
                )
                if dread >= GHOST_DREAD_MAX:
                    enemy.apply_fear(GHOST_BARAGE_FEAR, caster.owner_id)
                    enemy.design_dread = 0
                    enemy.design_dread_timer = 0.0
        spawn_attack_impact(game_state, caster.pos, GHOST_FEAR_TEAL, radius=30, thickness=3, burst_count=14)
    elif token == "flame_wheel":
        for enemy in enemies:
            ring_distance = (enemy.pos - caster.pos).length()
            if ring_distance <= FLAME_WHEEL_RADIUS + getattr(enemy, "radius", 0):
                enemy.take_damage(FLAME_WHEEL_DAMAGE, source=caster, damage_type="design_spell_flame_wheel", game_state=game_state)
                knock_dir = enemy.pos - caster.pos
                if knock_dir.length_squared() > 0:
                    enemy.apply_knockback(knock_dir, FLAME_WHEEL_KNOCKBACK)
        add_design_effect(
            game_state,
            DesignEffect("flame_ring", caster, pygame.Vector2(caster.pos), radius=FLAME_WHEEL_RADIUS, lifetime=FLAME_WHEEL_REMAIN, dps=FLAME_WHEEL_CIRCLE_DPS),
        )
        caster.design_spell_haste_timer = FLAME_DANCER_HASTE_DURATION
        spawn_attack_impact(game_state, caster.pos, (232, 86, 52), radius=26, thickness=3, burst_count=16)
    elif token == "abyss_eye":
        living = [enemy for enemy in enemies if enemy.alive]
        if living:
            prey = max(living, key=lambda e: (min(GAZE_MAX, int(getattr(e, "design_gaze", 0))), -((e.pos - caster.pos).length_squared())))
            target_pos = pygame.Vector2(prey.pos)
            add_design_effect(
                game_state,
                DesignEffect(
                    "abyss_charge",
                    caster,
                    target_pos,
                    radius=30.0,
                    lifetime=ABYSS_CHARGE_TIME,
                    damage=ABYSS_RAY_BASE + ABYSS_RAY_PER_STACK * min(GAZE_MAX, int(getattr(prey, "design_gaze", 0))),
                    stun=ABYSS_RAY_STUN,
                    target_id=id(prey),
                ),
            )
    elif token == "mind_steal":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None and target.alive:
            stolen = min(MIND_STEAL_MAX_STEAL, target.max_hp * MIND_STEAL_LIFESTEAL_RATIO)
            stolen = min(stolen, max(0.0, target.hp))
            if stolen > 0:
                target.take_damage(stolen, source=caster, damage_type="true_design_mind_steal", game_state=game_state)
                caster.heal(stolen)
            marks = min(STOLEN_MARK_MAX, int(getattr(target, "design_stolen_marks", 0)))
            for enemy in enemies:
                if enemy is not target and (enemy.pos - caster.pos).length() <= MIND_STEAL_AOE_RADIUS + getattr(enemy, "radius", 0):
                    enemy.take_damage(
                        MIND_STEAL_AOE_BASE + MIND_STEAL_AOE_PER_STACK * marks,
                        source=caster,
                        damage_type="design_spell_mind_steal_aoe",
                        game_state=game_state,
                    )
            target.design_stolen_marks = 0
        spawn_attack_impact(game_state, caster.pos, (176, 108, 236), radius=22, thickness=3, burst_count=12)
    elif token == "rift_slash":
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else pygame.Vector2(1, 0)
        direction = direction.normalize()
        start_pos = pygame.Vector2(caster.pos)
        end_pos = caster.pos + direction * RIFT_DASH_DISTANCE
        end_pos.x = clamp(end_pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
        end_pos.y = clamp(end_pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
        game_state["beam_events"].append(BeamEvent(start_pos, end_pos, RIFT_BLUE))
        for enemy in enemies:
            if enemy.alive and distance_point_to_segment(enemy.pos, start_pos, end_pos) <= getattr(enemy, "radius", 0) + 16:
                enemy.take_damage(RIFT_DASH_DAMAGE, source=caster, damage_type="design_spell_rift_dash", game_state=game_state)
                perp = pygame.Vector2(-direction.y, direction.x)
                side = 1.0 if (enemy.pos - start_pos).dot(perp) >= 0 else -1.0
                enemy.apply_knockback(perp * side, RIFT_DASH_KNOCKBACK)
        caster.pos = end_pos
        caster.update_rect()
        add_design_effect(
            game_state,
            DesignEffect("rift_line", caster, (start_pos + end_pos) * 0.5, radius=10.0, lifetime=RIFT_LINE_DURATION, dps=RIFT_LINE_DPS, direction=direction, length=RIFT_DASH_DISTANCE),
        )
        spawn_attack_impact(game_state, end_pos, RIFT_BLUE, radius=18, thickness=4, burst_count=12)
    elif token == "soul_nine_slash":
        living = [enemy for enemy in enemies if enemy.alive]
        blade = getattr(caster, "design_soul_blade", None)
        if not living or blade is None or not blade.alive:
            return False  # 剑灵不在场或场上无敌人：不消耗，等剑灵重生后再触发
        target = select_nearest_enemy(caster, game_state["characters"])
        add_design_effect(
            game_state,
            DesignEffect(
                "soul_slash",
                caster,
                pygame.Vector2(blade.pos),
                radius=10.0,
                lifetime=SOUL_NINE_SLASH_DELAY,
                target_id=id(target) if target is not None else None,
                strikes_left=9,
                max_total=SOUL_NINE_SLASH_MAX_TOTAL,
                total_done=0,
                blade_id=id(blade),
            ),
        )
    elif token == "phantom_lancer_throw":
        target = select_nearest_enemy(caster, game_state["characters"])
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else pygame.Vector2(1, 0)
        if target is not None:
            offset = target.pos - caster.pos
            if offset.length_squared() > 0:
                direction = offset.normalize()
                target.take_damage(30.0, source=caster, damage_type="design_physical_spear_throw", game_state=game_state)
                target.apply_slow(0.3, 2.0)
                spawn_attack_impact(game_state, target.pos, (86, 224, 232), radius=12, thickness=2, burst_count=8)
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        landing_pos = caster.pos + direction * 120.0
        landing_pos.x = clamp(landing_pos.x, ARENA_RECT.left + 12, ARENA_RECT.right - 12)
        landing_pos.y = clamp(landing_pos.y, ARENA_RECT.top + 12, ARENA_RECT.bottom - 12)
        game_state["beam_events"].append(BeamEvent(caster.pos, landing_pos, (86, 224, 232)))
        spawn_attack_impact(game_state, landing_pos, (86, 224, 232), radius=10, thickness=2, burst_count=6)
        if game_state.get("timed_weapon_orb_drops_enabled", True):
            game_state["weapon_orbs"].append(WeaponOrb("ColdSpear", landing_pos, lifetime=PHANTOM_LANCER_SPEAR_LIFETIME))
        caster.phantom_lancer_throw_speed_timer = PHANTOM_LANCER_THROW_SPEED_DURATION
        caster.phantom_lancer_spear_hunt_timer = PHANTOM_LANCER_SPEAR_HUNT_DURATION
    elif token == "soul_arbiter_bond":
        caster.soul_arbiter_hunt_timer = SOUL_ARBITER_HUNT_DURATION
        for enemy in enemies:
            if (enemy.pos - caster.pos).length() <= 60.0 + enemy.radius:
                enemy.take_damage(25.0, source=caster, damage_type="design_spell_soul_purge", game_state=game_state)
    elif token == "element_switch":
        current_mode = caster.design_element_mode
        impact_target = select_nearest_enemy(caster, game_state["characters"])
        if impact_target is not None and current_mode is not None:
            if current_mode == "ice":
                impact_target.take_damage(35.0, source=caster, damage_type="design_spell_elemental_ice_burst", game_state=game_state)
                impact_target.apply_slow(0.5, 2.0)
            elif current_mode == "fire":
                impact_target.take_damage(45.0, source=caster, damage_type="design_spell_elemental_fire_burst", game_state=game_state)
                impact_target.mage_burn_timer = max(getattr(impact_target, "mage_burn_timer", 0.0), 2.5)
            else:
                impact_target.take_damage(30.0, source=caster, damage_type="design_spell_elemental_bolt_burst", game_state=game_state)
                impact_target.apply_knockback(impact_target.pos - caster.pos, 35.0)
                impact_target.apply_stun(0.3)
        caster.design_element_mode = random.choice(("ice", "fire", "electric"))
    elif token == "mimic":
        copied = game_state.get("last_design_skill_token")
        if copied and copied != "mimic":
            cast_design_skill(caster, game_state, copied)
    elif token == "grave_swamp":
        caster.use_gravekeeper_skill(game_state)
    elif token == "eagle_eye":
        caster.design_sentinel_lock = True
    elif token == "joker_box":
        target = select_nearest_enemy(caster, game_state["characters"])
        if random.random() < 0.5 and target is not None:
            spawn_design_projectile(caster, game_state, target.pos - caster.pos, 30.0, "design_physical_joker", (244, 244, 244))
        else:
            caster.heal(20.0)
    elif token == "mortar_barrage":
        caster.apply_root(3.0)
        total_shells = 15
        for index in range(total_shells):
            aim = select_nearest_enemy(caster, game_state["characters"])
            if aim is not None and aim.alive:
                spread_angle = random.uniform(0.0, math.tau)
                spread_radius = random.uniform(0.0, 35.0)
                shell_anchor = pygame.Vector2(aim.pos) + pygame.Vector2(
                    math.cos(spread_angle), math.sin(spread_angle)
                ) * spread_radius
            else:
                shell_anchor = random_spawn_point(ARENA_RECT, 30.0)
            add_design_effect(
                game_state,
                DesignEffect(
                    "meteor",
                    caster,
                    shell_anchor,
                    radius=26.0,
                    lifetime=0.4 + index * 0.18,
                    damage=40.0,
                    damage_type="design_physical_mortar_shell",
                ),
            )
    elif token == "fate_link":
        if len(enemies) >= 2:
            a, b = random.sample(enemies, 2)
            a.design_link_target_id = id(b)
            b.design_link_target_id = id(a)
            a.design_link_timer = DESIGN_ORACLE_LINK_DURATION
            b.design_link_timer = DESIGN_ORACLE_LINK_DURATION
            game_state["beam_events"].append(BeamEvent(a.pos, b.pos, (255, 218, 120)))
    elif token == "dice_roll":
        if random.randint(1, 6) <= 3:
            caster.take_damage(15.0, source=caster, damage_type="true_design_dice_backfire", game_state=game_state)
        else:
            for enemy in enemies:
                enemy.take_damage(20.0, source=caster, damage_type="design_spell_dice", game_state=game_state)
    elif token == "black_hole":
        add_design_effect(game_state, DesignEffect("black_hole", caster, ARENA_RECT.center, radius=120.0, lifetime=3.0, pull=55.0, damage=15.0))
    elif token == "arrow_rain":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return False
        # 猎影锁魂：后跳拉开距离 + 锁定最近敌人(满印记+减速) + 三连穿透箭
        away = caster.pos - target.pos
        if away.length_squared() == 0:
            away = random_unit_vector()
        away = away.normalize()
        caster.pos += away * 50.0
        caster.pos.x = clamp(caster.pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
        caster.pos.y = clamp(caster.pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
        caster.design_ranger_speed_timer = max(caster.design_ranger_speed_timer, RANGER_DASH_SPEED_DURATION)
        target.design_ranger_mark = min(RANGER_MARK_MAX, target.design_ranger_mark + RANGER_MARK_MAX)
        target.apply_slow(0.4, 2.0)
        caster.design_ranger_lock_target_id = target.id
        caster.design_ranger_lock_timer = RANGER_LOCK_DURATION
        aim = target.pos - caster.pos
        if aim.length_squared() == 0:
            aim = random_unit_vector()
        aim = aim.normalize()
        for offset_deg in (-16.0, 0.0, 16.0):
            spawn_design_projectile(
                caster,
                game_state,
                aim.rotate(offset_deg),
                RANGER_ARROW_DAMAGE,
                "design_physical_ranger",
                (160, 255, 180),
                max_range=320.0,
                pierce=True,
            )
        return True
    elif token == "stone_skin":
        caster.clear_negative_states()
        caster.heal(80.0)
        caster.control_immunity_timer = 2.5
    elif token == "swallow_return":
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        direction = direction.normalize()
        beam_end = caster.pos + direction * 80.0
        game_state["beam_events"].append(BeamEvent(caster.pos, beam_end, (226, 226, 226)))
        hits = 0
        for enemy in enemies:
            if distance_point_to_segment(enemy.pos, caster.pos, beam_end) <= enemy.radius + 18:
                enemy.take_damage(40.0, source=caster, damage_type="design_physical_swallow", game_state=game_state)
                call_target_method(enemy, "apply_bleed", 1)
                hits += 1
        for projectile in game_state["projectiles"]:
            if projectile.alive and projectile.owner_id != caster.owner_id and distance_point_to_segment(projectile.pos, caster.pos, beam_end) <= 14.0:
                projectile.alive = False
        caster.heal(caster.max_hp * 0.06 * hits)
    elif token == "frost_burst":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            target.take_damage(20.0, source=caster, damage_type="design_spell_frostburst", game_state=game_state)
            target.apply_freeze(2.0)
    elif token == "guillotine":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            guillotine_damage = 60.0
            if target.hp > 0 and target.hp <= target.max_hp * 0.5:
                guillotine_damage = 120.0
            target.take_damage(guillotine_damage, source=caster, damage_type="true_design_guillotine", game_state=game_state)
            call_target_method(target, "apply_bleed", 2)
    elif token == "deep_sleep":
        target = select_highest_hp_enemy(caster, game_state["characters"])
        if target is not None:
            target.apply_sleep(4.0)
    elif token == "drone":
        game_state["design_summons"].append(DesignSummon(caster, "drone", caster.pos + random_unit_vector() * 18))
    elif token == "blood_contract":
        hp_cost = min(50.0, max(0.0, caster.hp - 1.0))
        if hp_cost > 0:
            caster.take_damage(hp_cost, source=caster, damage_type="true_design_blood_contract", game_state=game_state)
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        direction = direction.normalize()
        beam_end = caster.pos + direction * 150.0
        game_state["beam_events"].append(BeamEvent(caster.pos, beam_end, (214, 72, 72)))
        for enemy in enemies:
            if distance_point_to_segment(enemy.pos, caster.pos, beam_end) <= enemy.radius + 18:
                enemy.take_damage(hp_cost, source=caster, damage_type="true_design_blood_contract_hit", game_state=game_state)
                enemy.apply_silence(2.0)
    elif token == "one_inch_punch":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            punch_damage = caster.get_current_basic_damage() * 4.0
            target.take_damage(punch_damage, source=caster, damage_type="design_physical_punch", game_state=game_state)
            target.apply_knockback(target.pos - caster.pos, 90.0)
            target.apply_stun(0.4)
    elif token == "web_bind":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            target.take_damage(50.0, source=caster, damage_type="design_spell_web", game_state=game_state)
            target.apply_slow(0.8, 3.0)
            target.apply_silence(3.0)
    elif token == "taunt_roar":
        caster.design_damage_reduction = 0.5
        caster.design_taunt_timer = 3.0
        for enemy in enemies:
            if isinstance(enemy, Character) and (enemy.pos - caster.pos).length() <= 90.0 + enemy.radius:
                enemy.design_taunt_timer = max(enemy.design_taunt_timer, 3.0)
                enemy.design_taunt_owner_id = caster.owner_id
    elif token == "monsoon":
        game_state["global_rain_timer"] = 4.0
        game_state["global_rain_owner"] = caster.owner_id
        game_state["global_rain_tick"] = 0.0
    elif token == "arc_blade":
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        spawn_design_projectile(caster, game_state, direction, 20.0, "design_spell_arc_blade", (255, 255, 255), speed=320.0, max_range=320.0, pierce=True)
    elif token == "soul_feast":
        hits = 0
        for enemy in enemies:
            dealt = enemy.take_damage(25.0, source=caster, damage_type="true_design_soul_feast", game_state=game_state)
            if dealt > 0:
                hits += 1
        caster.max_hp += 5.0 * hits
        caster.heal(5.0 * hits)
    elif token == "holy_pillar":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            add_design_effect(game_state, DesignEffect("pillar", caster, target.pos, radius=40.0, lifetime=5.0, dps=25.0, heal=10.0))
    elif token == "broadside":
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        direction = direction.normalize()
        for offset in (-18, -9, 0, 9, 18):
            spawn_design_projectile(caster, game_state, direction.rotate(offset), 12.0, "design_physical_broadside", (196, 196, 196), max_range=240.0)
    elif token == "gravity_field":
        target = select_nearest_enemy(caster, game_state["characters"])
        pos = target.pos if target is not None else caster.pos + caster.recent_move_dir * 80
        add_design_effect(game_state, DesignEffect("gravity", caster, pos, radius=70.0, lifetime=3.0, dps=35.0, pull=50.0))
    elif token == "flying_swords":
        orb_count = max(1, len(game_state["weapon_orbs"]))
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            for _ in range(orb_count):
                spawn_design_projectile(caster, game_state, target.pos - caster.pos, 10.0, "design_physical_sword", (240, 244, 252), speed=320.0, max_range=320.0)
    elif token == "shadow_waltz":
        if caster.design_shadow_blade_pos is not None:
            blade = caster.design_shadow_blade_pos
            caster.design_shadow_blade_pos = None
            caster.pos = pygame.Vector2(blade)
            caster.pos.x = clamp(caster.pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
            caster.pos.y = clamp(caster.pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
            caster.update_rect()
            caster.design_untargetable_timer = max(caster.design_untargetable_timer, SHADOW_WALTZ_INVULN)
            for enemy in enemies:
                if (enemy.pos - caster.pos).length() <= SHADOW_WALTZ_AOE_RADIUS + getattr(enemy, "radius", 0):
                    enemy.take_damage(caster.get_current_basic_damage() * SHADOW_WALTZ_AOE_DAMAGE_RATIO, source=caster, damage_type="design_physical_shadow_waltz", game_state=game_state)
            spawn_attack_impact(game_state, caster.pos, (150, 150, 170), radius=24, thickness=3, burst_count=14)
        else:
            target = select_nearest_enemy(caster, game_state["characters"])
            if target is not None:
                blade_pos = pygame.Vector2(target.pos)
                caster.design_shadow_blade_pos = blade_pos
                game_state["beam_events"].append(BeamEvent(caster.pos, blade_pos, (170, 170, 190)))
                spawn_attack_impact(game_state, blade_pos, (170, 170, 190), radius=10, thickness=2, burst_count=6)
                target.take_damage(caster.get_current_basic_damage() * SHADOW_WALTZ_THROW_RATIO, source=caster, damage_type="design_physical_shadow_throw", game_state=game_state)
    elif token == "hell_charge":
        attack_range = caster.get_current_attack_range()
        burn_targets = []
        for enemy in game_state["characters"]:
            if not enemy.alive or enemy.owner_id == caster.owner_id:
                continue
            distance_sq = (enemy.pos - caster.pos).length_squared()
            max_distance = attack_range + getattr(enemy, "radius", 0)
            if distance_sq <= max_distance * max_distance:
                burn_targets.append((distance_sq, enemy))
        burn_targets.sort(key=lambda item: item[0])
        for _, target in burn_targets[:3]:
            call_target_method(target, "apply_hell_burn", HELLBRINGER_BURN_SKILL_STACKS, HELLBRINGER_BURN_DURATION, caster)
    elif token == "bullet_storm":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            direction = target.pos - caster.pos
        else:
            direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        for _ in range(30):
            spawn_design_projectile(caster, game_state, direction.rotate(random.uniform(-35.0, 35.0)), 5.0, "design_physical_outlaw", (236, 198, 116), max_range=260.0)
    elif token == "time_stop":
        game_state["global_time_stop_timer"] = DESIGN_TIMESTOP_DURATION
        game_state["global_time_stop_owner"] = caster.owner_id
    elif token == "matrix_collapse":
        constructs = [effect for effect in game_state["design_effects"] if effect.alive and effect.effect_type == "construct" and effect.owner_id == caster.owner_id]
        for effect in constructs:
            effect.alive = False
            apply_aoe_damage(effect.pos, 32.0, 20.0, caster.owner_id, game_state, source=caster, damage_type="design_physical_construct")
    elif token == "rend":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            target.take_damage(15.0, source=caster, damage_type="design_physical_rend", game_state=game_state)
            call_target_method(target, "apply_bleed", 1)
    elif token == "aurora_wall":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            direction = target.pos - caster.pos
        else:
            direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        direction = direction.normalize()
        add_design_effect(game_state, DesignEffect("aurora", caster, caster.pos + direction * 24, radius=40.0, lifetime=3.5, damage=60.0, blind=2.0, velocity=direction * 180.0))
    elif token == "swarm_storm":
        for summon in game_state["design_summons"]:
            if summon.alive and summon.owner_id == caster.owner_id and summon.summon_type == "larva":
                summon.alive = False
                apply_aoe_damage(summon.pos, 22.0, 10.0, caster.owner_id, game_state, source=caster, damage_type="design_spell_larva_burst")
    elif token == "sword_dash":
        corners = [
            pygame.Vector2(ARENA_RECT.left + caster.radius, ARENA_RECT.top + caster.radius),
            pygame.Vector2(ARENA_RECT.right - caster.radius, ARENA_RECT.top + caster.radius),
            pygame.Vector2(ARENA_RECT.left + caster.radius, ARENA_RECT.bottom - caster.radius),
            pygame.Vector2(ARENA_RECT.right - caster.radius, ARENA_RECT.bottom - caster.radius),
        ]
        corner = random.choice(corners)
        game_state["beam_events"].append(BeamEvent(caster.pos, corner, (250, 250, 250)))
        for enemy in enemies:
            if distance_point_to_segment(enemy.pos, caster.pos, corner) <= enemy.radius + 16:
                enemy.take_damage(30.0, source=caster, damage_type="design_physical_sword_dash", game_state=game_state)
        caster.pos = corner
        caster.update_rect()
    elif token == "chain_net":
        for enemy in enemies:
            if isinstance(enemy, Character) and getattr(enemy, "design_marked", False) and enemy.design_mark_owner_id == caster.owner_id:
                enemy.design_marked = False
                enemy.design_mark_duration = 0.0
                enemy.take_damage(15.0, source=caster, damage_type="true_design_chain_net", game_state=game_state)
                enemy.apply_stun(1.0)
    elif token == "glacier_shock":
        for enemy in enemies:
            if getattr(enemy, "vel", pygame.Vector2()).length() <= 20.0:
                enemy.take_damage(25.0, source=caster, damage_type="design_spell_glacier", game_state=game_state)
    elif token == "powder_blast":
        apply_aoe_damage(caster.pos, 120.0, 400.0, caster.owner_id, game_state, source=caster, damage_type="design_physical_powder")
        caster.take_damage(max(1.0, caster.hp * 0.3), source=caster, damage_type="true_design_powder_cost", game_state=game_state)
    elif token == "infrasound":
        for index in range(3):
            add_design_effect(
                game_state,
                DesignEffect(
                    "sound_ring",
                    caster,
                    caster.pos,
                    radius=18.0,
                    start_radius=18.0,
                    lifetime=ACOUSTIC_WAVE_DURATION + ACOUSTIC_WAVE_DELAY * index,
                    delay=ACOUSTIC_WAVE_DELAY * index,
                    damage=ACOUSTIC_WAVE_DAMAGE,
                    stun=ACOUSTIC_WAVE_STUN,
                    expand_speed=(ACOUSTIC_WAVE_RADIUS - 18.0) / ACOUSTIC_WAVE_DURATION if index < 2 else (ACOUSTIC_WAVE_LAST_RADIUS - 18.0) / ACOUSTIC_WAVE_DURATION,
                    thickness=14.0,
                ),
            )
    elif token == "throw_arsenal":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            spawn_design_projectile(caster, game_state, target.pos - caster.pos, 100.0, "design_physical_throw", (244, 220, 176), speed=360.0, max_range=320.0)
        caster.clear_weapon()
    return True


class Decoy:
    def __init__(self, owner, pos):
        self.owner = owner
        self.owner_id = owner.owner_id
        self.pos = pygame.Vector2(pos)
        self.radius = 11
        self.color = tuple(clamp(channel + 35, 0, 255) for channel in owner.color)
        self.hp = 1
        self.max_hp = 1
        self.lifetime = 5.5
        self.alive = True
        self.is_decoy = True

    def take_damage(
        self,
        amount,
        source=None,
        damage_type="basic",
        game_state=None,
        count_on_damage_dealt=True,
        ignore_shields=False,
        ignore_equilibrium_thresholds=False,
    ):
        if not self.alive:
            return 0.0
        pre_damage_hp = self.hp
        self.hp -= amount
        handle_equilibrium_thresholds(self, pre_damage_hp, source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None), game_state, ignore_equilibrium_thresholds=ignore_equilibrium_thresholds)
        if self.hp <= 0:
            self.alive = False
            if source is not None and getattr(source, "alive", False):
                source.take_damage(8, source=self.owner, damage_type="decoy_burst", game_state=game_state)
        source_character = source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None)
        if source_character is not None and getattr(source_character, "owner_id", None) != self.owner_id and hasattr(source_character, "on_damage_dealt"):
            source_character.on_damage_dealt(amount, damage_type)
        return amount

    def update(self, dt, game_state):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface):
        points = regular_polygon_points((self.pos.x, self.pos.y), self.radius, 6, math.pi / 6)
        pygame.draw.polygon(surface, self.color, points)
        pygame.draw.polygon(surface, BORDER_COLOR, points, 1)


ROTATABLE_SHAPES = {"triangle", "triangle_down", "half_circle", "crescent", "arrow", "chevron"}


class Character:
    def __init__(self, job_name, character_id, pos, owner_id=None, is_main_character=True, clone_config=None):
        config = JOB_DEFS[job_name]
        resistance_profile = JOB_RESISTANCE_PROFILES.get(job_name, {})
        self.id = character_id
        self.owner_id = character_id if owner_id is None else owner_id
        self.job_name = job_name
        self.config = config
        self.shape = config["shape"]
        self.color = config["color"]
        self.base_radius = CHARACTER_RADIUS * config.get("radius_scale", 1.0)
        self.radius = self.base_radius
        self.max_hp = float(config["max_hp"])
        self.hp = float(config["max_hp"])
        self.mp = 0.0
        self.pos = pygame.Vector2(pos)
        self.vel = random_unit_vector() * random.uniform(35.0, 75.0)
        self.move_speed = config["move_speed"]
        self.base_attack_type = config["attack_type"]
        self.base_attack_damage = config["attack_damage"]
        self.base_attack_range = config["attack_range"]
        self.base_attack_interval = config["attack_interval"]
        self.base_projectile_speed = config["projectile_speed"]
        self.design_meta = DESIGN_ROLE_METADATA.get(job_name, {})
        self.physical_resistance = max(0.0, float(config.get("physical_resistance", resistance_profile.get("physical_resistance", 1.0))))
        self.spell_resistance = max(0.0, float(config.get("spell_resistance", resistance_profile.get("spell_resistance", 1.0))))
        self.base_physical_resistance = self.physical_resistance
        self.base_spell_resistance = self.spell_resistance
        self.attack_cooldown = random.uniform(0.0, self.base_attack_interval)
        self.held_weapon = None
        self.alive = True
        self.is_main_character = is_main_character
        self.is_decoy = False
        self.clone_mode = None
        self.clone_expire_timer = 0.0
        self.damage_multiplier = 1.0
        self.rect = pygame.Rect(0, 0, CHARACTER_SIZE, CHARACTER_SIZE)
        self.wander_dir = random_unit_vector()
        self.wander_timer = random.uniform(0.8, 1.6)
        self.recent_move_dir = pygame.Vector2(self.wander_dir)
        self.facing_angle = 0.0
        self.strafe_sign = random.choice((-1, 1))
        self.strafe_timer = random.uniform(*STRAFE_SWITCH_INTERVAL)
        self.melee_gap_dash_timer = 0.0
        self.melee_gap_dash_cooldown = random.uniform(0.0, 0.6)
        self.chase_noise_angle = random.uniform(-CHASE_NOISE_MAX_DEG, CHASE_NOISE_MAX_DEG)
        self.chase_noise_target = self.chase_noise_angle
        self.chase_noise_timer = random.uniform(*CHASE_NOISE_RETARGET_INTERVAL)
        self.slow_timer = 0.0
        self.slow_factor = 0.0
        self.stun_timer = 0.0
        self.shield_timer = 0.0
        self.guard_timer = 0.0
        self.knight_recorded_damage = 0.0
        self.knight_backlash_timer = 0.0
        self.knight_backlash_tick_accumulator = 0.0
        self.knight_backlash_tick_damage = 0.0
        self.mage_burn_timer = 0.0
        self.mage_arcane_stacks = 0
        self.mage_arcane_field_timer = 0.0
        self.mage_arcane_field_tick_accumulator = 0.0
        self.berserker_spin_timer = 0.0
        self.berserker_tick_accumulator = 0.0
        self.berserker_spin_visual_timer = 0.0
        self.design_soul_moth_soul = 0
        self.design_soul_moth_form = False
        self.design_soul_moth_timer = 0.0
        self.design_confuse_timer = 0.0
        self._soul_moth_base_physical_resistance = self.physical_resistance
        self.design_execute_buff_timer = 0.0
        self.design_banner_zone_timer = 0.0
        self.design_banner_lifesteal_timer = 0.0
        self.design_banner_respawn_timer = 0.0
        self.design_potion_haste_timer = 0.0
        self.design_potion_cooldown_timer = POTION_INTERVAL
        self.design_wild_brew_timer = 0.0
        self.design_protect_timer = 0.0
        self.design_squad_mark_timer = 0.0
        self.design_squad_mark_owner_id = None
        self.design_squad_primary_timer = 0.0
        self.design_squad_primary_owner_id = None
        self.design_banish_mark = 0
        self.design_banished = False
        self.design_banish_points = 0
        self.design_banish_tick_timer = 0.0
        self.design_banish_roll_timer = 0.0
        self.design_sparrow_host_id = None
        self.design_sparrow_reattach_timer = 0.0
        self.design_corrupted_blood = 0.0
        self.design_sparrow_fury_timer = 0.0
        self.design_raikiri_stage = 0
        self.design_raikiri_mark = 0
        self.design_tide_link_active = False
        self.design_tide_link_timer = 0.0
        self.design_tide_heal_tick = 0.0
        self.design_tide_hub_id = None
        self._tide_share = False
        self.design_blood_curse = 0
        self.design_blood_curse_timer = 0.0
        self.design_blood_feast_timer = 0.0
        self.design_kenshi_counter_cd = 0.0
        self.design_kenshi_mark = 0
        self.design_kenshi_mark_timer = 0.0
        self.design_banish_pulse = 0.0
        self.design_banish_dust_timer = 0.0
        self.sniper_charge_timer = 0.0
        self.sniper_beam_direction = pygame.Vector2(1, 0)
        self.sniper_stationary_timer = 0.0
        self.sniper_stationary_ready = False
        self.assassin_bonus_recast_available = False
        self.assassin_haste_timer = 0.0
        self.necromancer_bone_stacks = 0
        self.necromancer_bone_timer = 0.0
        self.necromancer_bone_progress = 0.0
        self.paladin_holy_stacks = 0
        self.paladin_holy_timer = 0.0
        self.paladin_holy_progress = 0.0
        self.ninja_shadow_stacks = 0
        self.ninja_shadow_timer = 0.0
        self.ninja_shadow_progress = 0.0
        self.bomber_fuse_stacks = 0
        self.bomber_fuse_timer = 0.0
        self.bomber_fuse_progress = 0.0
        self.illusion_mirror_stacks = 0
        self.illusion_mirror_timer = 0.0
        self.illusion_mirror_progress = 0.0
        self.behemoth_stone_stacks = 0
        self.behemoth_stone_timer = 0.0
        self.behemoth_stone_progress = 0.0
        self.toxicologist_corrosion_stacks = 0
        self.toxicologist_corrosion_timer = 0.0
        self.toxicologist_corrosion_progress = 0.0
        self.frost_mage_core_stacks = 0
        self.frost_mage_core_timer = 0.0
        self.frost_mage_core_progress = 0.0
        self.pyro_ember_stacks = 0
        self.pyro_ember_timer = 0.0
        self.pyro_ember_progress = 0.0
        self.paladin_buff_timer = 0.0
        self.paladin_tick_accumulator = 0.0
        self.vampire_charge_timer = VAMPIRE_CHARGE_INTERVAL
        self.vampire_channel_timer = 0.0
        self.vampire_channel_target_id = None
        self.vampire_regen_timer = 0.0
        self.ninja_dash_timer = 0.0
        self.freeze_timer = 0.0
        self.true_shield = 0.0
        self.poison_stacks = 0
        self.poison_stack_progress = 0.0
        self.poison_decay_accumulator = 0.0
        self.pyro_breath_timer = 0.0
        self.pyro_breath_tick_accumulator = 0.0
        self.time_rewind_snapshots = []
        self.time_rewind_snapshot_timer = 0.0
        self.druid_form_timer = 0.0
        self.druid_bonus_hp_active = 0.0
        self.doom_timer = 0.0
        self.control_timer = 0.0
        self.control_owner_id = None
        self.smasher_leap_timer = 0.0
        self.smasher_leap_target = None
        self.charm_timer = 0.0
        self.charm_owner_id = None
        self.succubus_barrage_timer = 0.0
        self.swordmaster_invuln_timer = 0.0
        self.swordmaster_haste_timer = 0.0
        self.windrunner_storm_timer = 0.0
        self.hex_curse_timer = 0.0
        self.chaos_charge_timer = CHAOS_CHARGE_INTERVAL
        self.root_timer = 0.0
        self.bard_song_timer = 0.0
        self.bounty_target_id = None
        self.bounty_coins = 0
        self.duel_haste_timer = 0.0
        self.gladiator_duel_timer = 0.0
        self.warlock_charge_timer = WARLOCK_CHARGE_INTERVAL
        self.tinkerer_overclock_timer = 0.0
        self.valkyrie_dive_timer = 0.0
        self.valkyrie_dive_target = None
        self.dark_reflect_timer = 0.0
        self.bloodwraith_rage_active = False
        self.bloodwraith_shield_timer = 0.0
        self.bloodwraith_shield_hp = 0.0
        self.phantom_lancer_throw_speed_timer = 0.0
        self.phantom_lancer_spear_hunt_timer = 0.0
        self.phantom_lancer_spear_charges = 0
        self.soul_arbiter_hunt_timer = 0.0
        self.soul_arbiter_chains = {}
        self.hit_flash_timer = 0.0
        self.damageDealt = 0.0
        self.damageTaken = 0.0
        self.design_untargetable_timer = 0.0
        self.disarm_timer = 0.0
        self.silence_timer = 0.0
        self.blind_timer = 0.0
        self.bleed_stacks = 0
        self.bleed_decay_timers = []
        self.cold_stacks = 0
        self.cold_decay_timer = 0.0
        self.equilibrium_mark_timer = 0.0
        self.hell_burn_timers = []
        self.hell_burn_source = None
        self.sleep_timer = 0.0
        self.control_immunity_timer = 0.0
        self.stationary_timer = 0.0
        self.position_lock = pygame.Vector2(self.pos)
        self.design_misc_timer = 0.0
        self.spawn_fx_timer = SPAWN_FX_DURATION
        self.gold_spawn_fx = False
        self.design_secondary_timer = 0.0
        self.design_tertiary_timer = 0.0
        self.design_passive_timer = 0.0
        self.design_passive_cooldown = 0.0
        self.design_passive_flag = False
        self.design_extra_counter = 0
        self.design_extra_counter_2 = 0
        self.design_marked = False
        self.design_mark_duration = 0.0
        self.design_poison_erosion = 0
        self.design_link_target_id = None
        self.design_link_timer = 0.0
        self.design_time_theft_stacks = 0
        self.design_bonus_speed = 0.0
        self.design_bonus_attack_speed = 0.0
        self.sunfire_combo_step = 1
        self.sunfire_fire_timer = 0.0
        self.sunfire_invuln_timer = 0.0
        self.sunfire_evasion_timer = 0.0
        self.sunfire_damage_reduction_stacks = 0
        self.equilibrium_resistance_penalty_timer = 0.0
        self.equilibrium_resistance_penalty = 0.0
        self.equilibrium_thresholds_triggered = set()
        self.windstorm_qi_stacks = 0
        self.windstorm_idle_timer = 0.0
        self.windstorm_decay_timer = 0.0
        self.windstorm_physical_resistance_bonus = 0.0
        self.windstorm_physical_resistance_timer = 0.0
        self.sea_tide_damage_bank = 0.0
        self.sea_tide_pick_timer = 0.0
        self.sea_tide_shield_hp = 0.0
        self.sea_tide_shield_timer = 0.0
        self.sea_tide_reduction_timers = []
        self.design_shadow_idle = 0.0
        self.design_crit_multiplier = 1.0
        self.design_element_mode = None
        self.design_sentinel_lock = False
        self.design_can_gain_mp = True
        self.design_recent_attack_target = None
        self.design_recent_damage_taken = 0.0
        self.design_has_revived = False
        self.design_low_hp_triggered = False
        self.design_construct_timer = DESIGN_CONSTRUCT_INTERVAL
        self.design_recently_hit = 0.0
        self.design_collect_fervor = 0
        self.design_charge_random_timer = self.config.get("mp_interval", 3.0)
        self.design_effects = []
        self.design_damage_reduction = 0.0
        self.design_fortress_timer = 0.0
        self.design_taunt_timer = 0.0
        self.design_taunt_owner_id = None
        self.design_hell_timer = 0.0
        self.design_hell_target = None
        self.design_hell_trail_distance = 0.0
        self.design_disarm_source = None
        self.design_mark_owner_id = None
        self.design_last_position = pygame.Vector2(self.pos)
        self.design_level = 1
        self.design_xp = 0.0
        self.design_level_fx_timer = 0.0
        self.design_level_fx_scale = 1.0
        self.design_xp_timer = 0.0
        self._design_upgrade_base_max_hp = self.max_hp
        self._design_upgrade_base_damage = self.base_attack_damage
        self._design_upgrade_base_physical_resistance = self.physical_resistance
        self._design_upgrade_base_spell_resistance = self.spell_resistance
        self._design_upgrade_base_move_speed = self.move_speed
        self.design_phoenix_fire = 0
        self.design_phoenix_feather = 0
        self.design_phoenix_fall = 0
        self.design_phoenix_egg_timer = 0.0
        self.design_phoenix_egg_shield = 0.0
        self.design_phoenix_base_max_hp = self.max_hp
        self.design_phoenix_same_target_id = None
        self.design_phoenix_same_hits = 0
        self.design_phoenix_wrath_timer = 0.0
        self.design_phoenix_wrath_accum = 0.0
        self.design_phoenix_wrath_source = None
        self.design_shell_stacks = 0
        self.design_shell_base_max_hp = self.max_hp
        self.design_shell_kill_count = 0
        self.kill_count = 0
        self.kill_streak = 0
        self.killstreak_buff_level = 0
        self.killstreak_buff_timer = 0.0
        # 104 幽灵祭司
        self.design_dread = 0
        self.design_dread_timer = 0.0
        self.design_fear_timer = 0.0
        self.design_fear_source_id = None
        # 105 炎舞姬
        self.design_ember = 0
        self.design_ember_timer = 0.0
        self.design_spell_haste_timer = 0.0
        # 106 深渊观测者
        self.design_gaze = 0
        self.design_gaze_timer = 0.0
        # 107 夺心者
        self.design_stolen_marks = 0
        # 108 裂空者
        self.design_rift_phase_timer = 0.0
        # 109 魂缚剑匣
        self.design_immobile = False
        self.design_soul_blade = None
        self.design_soul_blade_timer = SOUL_BLADE_RESPAWN_DELAY
        self.design_wolf_cd_timer = 0.0
        self.design_shell_hit_counter = 0
        self.design_shell_guard_cooldown = 0.0
        self.design_shell_counter_timer = 0.0
        self.gravekeeper_rot_stacks = 0
        self.gravekeeper_rot_timer = 0.0
        self.design_xuan_bulwark_timer = 0.0
        self.design_xuan_bulwark_shield = 0.0
        self.design_xuan_bulwark_broken_triggered = False
        self.design_tiger_prey_id = None
        self.design_tiger_hunt_value = 0.0
        self.design_tiger_wound = 0
        self.design_tiger_same_target_id = None
        self.design_tiger_same_hits = 0
        self.design_tiger_power = 0
        self.design_tiger_prey_charge_window = 0.0
        self.design_tiger_prey_charge_count = 0
        self.design_tiger_trail_distance = 0.0
        self.design_tiger_blood_speed_timer = 0.0
        self.design_aurora_burn = 0
        self.design_aurora_burn_timer = 0.0
        self.design_aurora_burn_source = None
        self.design_susanoo_prowl = 0
        self.design_ranger_mark = 0
        self.design_ranger_speed_timer = 0.0
        self.design_ranger_lock_target_id = None
        self.design_ranger_lock_timer = 0.0
        self.design_shadow_stacks = 0
        self.design_shadow_blade_pos = None
        self.design_element_stacks = 0
        self.design_last_element = None
        self.design_dragon_form = "thunder"
        self.design_dragon_breath_thunder = 0
        self.design_dragon_breath_wood = 0
        self.design_dragon_hit_count = 0
        self.design_dragon_switch_bonus = 0.0
        self.design_dragon_move_distance = 0.0
        self.design_dragon_move_bonus_ready = False
        self.design_dragon_zap_timer = 0.0
        self.design_dragon_heal_timer = 0.0
        self.design_dragon_sweep_cooldown = 0.0
        self.design_dragon_awe = 0
        if clone_config is not None:
            self.is_main_character = False
            self.clone_mode = clone_config.get("mode", "illusion")
            self.clone_expire_timer = clone_config.get("duration", ILLUSION_CLONE_DURATION)
            self.damage_multiplier = clone_config.get("damage_multiplier", ILLUSION_CLONE_DAMAGE_PORTION)
            self.max_hp = max(1.0, self.max_hp * clone_config.get("hp_multiplier", ILLUSION_CLONE_HP_PORTION))
            self.hp = self.max_hp
            self.mp = 0.0
            self.color = tuple(clamp(channel + 25, 0, 255) for channel in self.color)
        if self.job_name == PHOENIX_JOB_NAME:
            self.design_phoenix_feather = PHOENIX_FEATHER_INITIAL
        if self.job_name == XUANWU_JOB_NAME:
            self.design_shell_base_max_hp = self.max_hp
        if self.is_twin_mirror():
            self.init_twin_mirror_state()
        self.update_rect()

    def update_rect(self):
        size = max(CHARACTER_SIZE, int(round(self.radius * 2)))
        self.rect.width = size
        self.rect.height = size
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def choose_wander_direction(self):
        self.wander_dir = random_unit_vector()
        self.wander_timer = random.uniform(0.7, 1.7)

    def update_strafe_state(self, dt):
        self.strafe_timer -= dt
        if self.strafe_timer <= 0:
            self.strafe_timer = random.uniform(*STRAFE_SWITCH_INTERVAL)
            self.strafe_sign = random.choice((-1, 1))

    def can_use_melee_dash(self):
        return self.get_current_basic_attack_type() == "melee" and self.held_weapon is None

    def can_pick_up_weapons(self):
        return self.is_main_character and self.clone_mode is None

    def is_design_role(self):
        return bool(self.design_meta)

    def is_sunfire_blademaster(self):
        return self.job_name == SUNFIRE_JOB_NAME

    def is_windstorm_fox(self):
        return self.job_name == WINDSTORM_FOX_JOB_NAME

    def is_sea_sage(self):
        return self.job_name == SEA_SAGE_JOB_NAME

    def is_equilibrium_arbiter(self):
        return self.job_name == EQUILIBRIUM_JOB_NAME

    def is_phoenix(self):
        return self.job_name == PHOENIX_JOB_NAME

    def is_necromancer(self):
        return self.job_name == "Necromancer"

    def is_paladin(self):
        return self.job_name == "Paladin"

    def is_ninja(self):
        return self.job_name == "Ninja"

    def is_bomber(self):
        return self.job_name == "Bomber"

    def is_vampire(self):
        return self.job_name == "Vampire"

    def get_vampire_blood_stacks(self):
        if not self.is_vampire():
            return 0
        missing_ratio = clamp((self.max_hp - self.hp) / max(1.0, self.max_hp), 0.0, 1.0)
        return min(5, int(missing_ratio / 0.10))

    def get_visual_color(self):
        if self.is_sunfire_blademaster():
            return SUNFIRE_FIRE_COLOR if self.sunfire_fire_timer > 0 else SUNFIRE_WATER_COLOR
        if self.is_soul_moth() and self.design_soul_moth_form:
            return SOUL_MOTH_FORM_COLOR
        return self.color

    def add_design_xp(self, amount):
        if not self.is_design_role() or not self.is_main_character or not self.alive or amount <= 0:
            return
        self.design_xp += amount
        while self.design_level < 10 and self.design_xp >= 100.0:
            self.design_xp -= 100.0
            self.design_level += 1
            growth = self.design_level - 1
            self.max_hp = self._design_upgrade_base_max_hp * (1.15 ** growth)
            self.base_attack_damage = self._design_upgrade_base_damage * (1.10 ** growth)
            self.physical_resistance = self._design_upgrade_base_physical_resistance + 0.03 * growth
            self.spell_resistance = self._design_upgrade_base_spell_resistance + 0.03 * growth
            self.move_speed = self._design_upgrade_base_move_speed + 2.0 * growth
            self.hp = min(self.max_hp, self.hp + self.max_hp * 0.12)
            self.design_level_fx_timer = 0.7
            self.design_level_fx_scale = 1.18
            self.update_rect()

    def apply_windstorm_physical_resistance(self, amount=WINDSTORM_FOX_PHYS_RESIST_BONUS, duration=WINDSTORM_FOX_PHYS_RESIST_DURATION):
        if not self.is_windstorm_fox() or amount <= 0:
            return
        self.windstorm_physical_resistance_bonus += amount
        self.windstorm_physical_resistance_timer = max(self.windstorm_physical_resistance_timer, duration)

    def apply_equilibrium_resistance_penalty(self, amount=EQUILIBRIUM_THRESHOLD_RESIST_EXCHANGE, duration=EQUILIBRIUM_THRESHOLD_RESIST_DURATION):
        if amount <= 0:
            return
        if self.equilibrium_resistance_penalty_timer > 0 and self.equilibrium_resistance_penalty > 0:
            self.physical_resistance += self.equilibrium_resistance_penalty
            self.spell_resistance += self.equilibrium_resistance_penalty
        self.equilibrium_resistance_penalty = amount
        self.physical_resistance = max(0.0, self.physical_resistance - amount)
        self.spell_resistance = max(0.0, self.spell_resistance - amount)
        self.equilibrium_resistance_penalty_timer = max(self.equilibrium_resistance_penalty_timer, duration)

    def spawn_sea_fish(self, game_state, anchor=None):
        if not self.is_sea_sage() or game_state is None:
            return
        anchor = pygame.Vector2(self.pos if anchor is None else anchor)
        angle = random.uniform(0.0, math.tau)
        distance = random.uniform(self.radius + 14.0, self.radius + 30.0)
        offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
        add_design_effect(
            game_state,
            DesignEffect(
                "water_fish",
                self,
                anchor + offset,
                lifetime=9999.0,
                radius=8.0,
                color=SEA_SAGE_FISH_COLOR,
                orbit_angle=angle,
                orbit_radius=distance,
                orbit_speed=random.uniform(1.2, 2.4),
                follow_owner=True,
            ),
        )

    def get_sea_fish_effects(self, game_state):
        if game_state is None:
            return []
        return [
            effect
            for effect in game_state.get("design_effects", [])
            if effect.alive and effect.effect_type == "water_fish" and effect.owner_id == self.owner_id
        ]

    def consume_sea_fish(self, game_state, fish_effect=None):
        if not self.is_sea_sage() or not self.alive:
            return
        if fish_effect is not None:
            fish_effect.alive = False
        self.heal(SEA_SAGE_FISH_HEAL)
        self.sea_tide_shield_hp += SEA_SAGE_FISH_SHIELD
        self.sea_tide_shield_timer = max(self.sea_tide_shield_timer, SEA_SAGE_FISH_SHIELD_DURATION)
        if len(self.sea_tide_reduction_timers) < SEA_SAGE_REDUCTION_MAX_STACKS:
            self.sea_tide_reduction_timers.append(SEA_SAGE_REDUCTION_DURATION)
        else:
            weakest_index = min(range(len(self.sea_tide_reduction_timers)), key=self.sea_tide_reduction_timers.__getitem__)
            self.sea_tide_reduction_timers[weakest_index] = SEA_SAGE_REDUCTION_DURATION

    def consume_all_sea_fish(self, game_state):
        if not self.is_sea_sage():
            return
        for fish in self.get_sea_fish_effects(game_state):
            self.consume_sea_fish(game_state, fish)

    def spawn_sea_waves(self, game_state, direction):
        if not self.is_sea_sage() or direction.length_squared() == 0:
            return
        direction = direction.normalize()
        start_pos = pygame.Vector2(self.pos) + direction * (self.radius + 10.0)
        for stage, delay in ((1, 0.0), (2, SEA_SAGE_WAVE_DELAY_STEP), (3, SEA_SAGE_WAVE_DELAY_STEP * 2)):
            add_design_effect(
                game_state,
                DesignEffect(
                    "sea_wave",
                    self,
                    start_pos,
                    radius=SEA_SAGE_WAVE_WIDTH,
                    lifetime=4.5,
                    direction=direction,
                    velocity=direction * SEA_SAGE_WAVE_SPEED,
                    stage=stage,
                    delay=delay,
                    speed=SEA_SAGE_WAVE_SPEED,
                    range=SEA_SAGE_WAVE_RANGE,
                    return_speed=SEA_SAGE_WAVE_RETURN_SPEED,
                    return_heal=SEA_SAGE_WAVE_RETURN_HEAL,
                ),
            )

    def is_gravekeeper(self):
        return self.job_name == "DesignRole52_gravekeeper"

    def is_ghost_priest(self):
        return self.job_name == "DesignRole104_ghost_priest"

    def is_flame_dancer(self):
        return self.job_name == "DesignRole105_flame_dancer"

    def is_abyssal_watcher(self):
        return self.job_name == "DesignRole106_abyssal_watcher"

    def is_mind_thief(self):
        return self.job_name == "DesignRole107_mind_thief"

    def is_riftbreaker(self):
        return self.job_name == "DesignRole108_riftbreaker"

    def is_soul_casket(self):
        return self.job_name == SOUL_CASKET_JOB

    def spawn_soul_blade(self, game_state):
        if game_state is None:
            return None
        blade = DesignSummon(self, "soul_blade", self.pos + pygame.Vector2(SOUL_BLADE_ORBIT, 0))
        game_state["design_summons"].append(blade)
        self.design_soul_blade = blade
        return blade

    def update_soul_blade(self, dt, game_state):
        if not self.is_soul_casket() or game_state is None:
            return
        blade = self.design_soul_blade
        if blade is not None and not blade.alive:
            self.design_soul_blade = None
            blade = None
        if blade is None:
            self.design_soul_blade_timer = max(0.0, getattr(self, "design_soul_blade_timer", 0.0) - dt)
            if self.design_soul_blade_timer <= 0:
                self.spawn_soul_blade(game_state)

    def apply_dread(self, stacks=1):
        self.design_dread = min(GHOST_DREAD_MAX, self.design_dread + max(0, int(stacks)))
        self.design_dread_timer = GHOST_DREAD_DURATION

    def apply_fear(self, duration, source_id):
        self.design_fear_timer = max(self.design_fear_timer, duration)
        self.design_fear_source_id = source_id

    def apply_ember(self, stacks=1):
        self.design_ember = min(FLAME_EMBER_MAX, self.design_ember + max(0, int(stacks)))
        self.design_ember_timer = FLAME_EMBER_DURATION

    def apply_gaze(self, stacks=1):
        self.design_gaze = min(GAZE_MAX, self.design_gaze + max(0, int(stacks)))
        self.design_gaze_timer = GAZE_DURATION

    def get_gravekeeper_effects(self, game_state, effect_type):
        if game_state is None:
            return []
        return [
            effect
            for effect in game_state.get("design_effects", [])
            if effect.alive and effect.owner is self and effect.effect_type == effect_type
        ]

    def get_gravekeeper_active_field(self, game_state):
        fields = self.get_gravekeeper_effects(game_state, "grave_field")
        return fields[0] if fields else None

    def resolve_gravekeeper_field(self, field, game_state):
        if field is None or game_state is None or not field.alive:
            return
        stacks = int(field.data.get("grave_stacks", 0))
        field.data["grave_resolved"] = True
        field.alive = False
        wraith_count = max(1, stacks)
        center = pygame.Vector2(field.pos)
        for index in range(wraith_count):
            angle = math.tau * index / max(1, wraith_count) + random.uniform(-0.35, 0.35)
            offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(10.0, max(16.0, field.radius * 0.35))
            add_design_effect(
                game_state,
                DesignEffect(
                    "grave_wraith",
                    self,
                    center + offset,
                    radius=9.0,
                    lifetime=2.6,
                    direction=offset if offset.length_squared() > 0 else random_unit_vector(),
                    speed=GRAVEKEEPER_WRAITH_SPEED,
                    damage=GRAVEKEEPER_WRAITH_DAMAGE,
                    slow=GRAVEKEEPER_WRAITH_SLOW,
                    slow_duration=GRAVEKEEPER_WRAITH_SLOW_DURATION,
                    field_px=center.x,
                    field_py=center.y,
                    field_r=field.radius,
                ),
            )

    def use_gravekeeper_skill(self, game_state):
        if not self.is_gravekeeper() or game_state is None:
            return
        field = self.get_gravekeeper_active_field(game_state)
        if field is not None:
            self.resolve_gravekeeper_field(field, game_state)
            return
        markers = self.get_gravekeeper_effects(game_state, "grave_marker")
        anchor = pygame.Vector2(self.pos)
        if markers:
            markers.sort(key=lambda effect: (effect.pos - self.pos).length_squared())
            anchor = pygame.Vector2(markers[0].pos)
        add_design_effect(
            game_state,
            DesignEffect(
                "grave_field",
                self,
                anchor,
                radius=GRAVEKEEPER_FIELD_RADIUS,
                lifetime=GRAVEKEEPER_FIELD_DURATION,
                grave_stacks=0,
                grave_base_radius=GRAVEKEEPER_FIELD_RADIUS,
                grave_detonate=False,
            ),
        )
        if markers:
            add_design_effect(
                game_state,
                DesignEffect(
                    "grave_wraith",
                    self,
                    pygame.Vector2(anchor),
                    radius=12.0,
                    lifetime=2.6,
                    direction=random_unit_vector(),
                    speed=GRAVEKEEPER_WRAITH_SPEED,
                    damage=GRAVEKEEPER_GUARD_DAMAGE,
                    slow=GRAVEKEEPER_WRAITH_SLOW,
                    slow_duration=GRAVEKEEPER_WRAITH_SLOW_DURATION,
                    max_hits=GRAVEKEEPER_GUARD_HITS,
                    field_px=anchor.x,
                    field_py=anchor.y,
                    field_r=GRAVEKEEPER_FIELD_RADIUS,
                ),
            )

    def get_design_damage_kind(self):
        if self.is_dragon():
            return DAMAGE_KIND_PHYSICAL if self.design_dragon_form == "thunder" else DAMAGE_KIND_SPELL
        return self.design_meta.get("basic_damage_kind", DAMAGE_KIND_PHYSICAL)

    def get_design_damage_type(self, base_name):
        kind = self.get_design_damage_kind()
        if kind == "true":
            return f"true_design_{base_name}"
        if kind == DAMAGE_KIND_SPELL:
            return f"design_spell_{base_name}"
        return f"design_physical_{base_name}"

    def get_current_basic_attack_type(self):
        if self.druid_form_timer > 0 and self.held_weapon is None:
            return "melee"
        if self.is_dragon():
            return "melee" if self.design_dragon_form == "thunder" else "ranged"
        return self.base_attack_type

    def get_current_basic_damage(self):
        damage = self.base_attack_damage * self.damage_multiplier
        if self.is_dragon():
            form_damage = DRAGON_THUNDER_DAMAGE if self.design_dragon_form == "thunder" else DRAGON_WOOD_DAMAGE
            damage = form_damage * self.damage_multiplier
            damage += self.design_dragon_switch_bonus
            self.design_dragon_switch_bonus = 0.0
            if self.design_dragon_move_bonus_ready:
                damage += DRAGON_MOVE_BONUS_BASE + DRAGON_MOVE_BONUS_PER_BREATH * self.get_dragon_breath()
                self.design_dragon_move_bonus_ready = False
        if self.job_name == "Mage" and self.mage_arcane_stacks > 0:
            damage *= 1.0 + self.mage_arcane_stacks * MAGE_ARCANE_DAMAGE_BONUS
        if self.job_name == "Illusionist" and self.illusion_mirror_stacks > 0:
            damage *= 1.0 + self.illusion_mirror_stacks * ILLUSION_MIRROR_STACK_DAMAGE_BONUS
        if self.job_name == "Behemoth" and self.behemoth_stone_stacks > 0:
            damage *= 1.0 + self.behemoth_stone_stacks * BEHEMOTH_STONE_DAMAGE_BONUS
        if self.job_name == "Toxicologist" and self.toxicologist_corrosion_stacks > 0:
            damage *= 1.0 + self.toxicologist_corrosion_stacks * TOXICOLOGIST_CORROSION_DAMAGE_BONUS
        if self.job_name == "Frost Mage" and self.frost_mage_core_stacks > 0:
            damage *= 1.0 + self.frost_mage_core_stacks * FROST_MAGE_CORE_DAMAGE_BONUS
        if self.job_name == "Pyro" and self.pyro_ember_stacks > 0:
            damage *= 1.0 + self.pyro_ember_stacks * PYRO_EMBER_DAMAGE_BONUS
        if self.is_necromancer() and self.necromancer_bone_stacks > 0:
            damage *= 1.0 + self.necromancer_bone_stacks * 0.05
        if self.is_paladin() and self.paladin_holy_stacks > 0:
            damage *= 1.0 + self.paladin_holy_stacks * 0.04
        if self.is_ninja() and self.ninja_shadow_stacks > 0:
            damage *= 1.0 + self.ninja_shadow_stacks * 0.06
        if self.is_bomber() and self.bomber_fuse_stacks > 0:
            damage *= 1.0 + self.bomber_fuse_stacks * 0.05
        if self.is_vampire():
            damage *= 1.0 + self.get_vampire_blood_stacks() * 0.05
        if self.job_name == "Bounty Hunter":
            damage *= 1.0 + self.bounty_coins * BOUNTY_COIN_DAMAGE_BONUS
        if self.druid_form_timer > 0 and self.held_weapon is None:
            damage *= DRUID_FORM_DAMAGE_MULTIPLIER
        if self.job_name == "DesignRole66_blood_mage":
            missing_ratio = clamp((self.max_hp - self.hp) / max(1.0, self.max_hp - 100.0), 0.0, 1.0)
            damage *= 1.0 + 1.2 * missing_ratio
        if self.job_name == "DesignRole77_shadow_dancer" and self.design_shadow_stacks >= SHADOW_VALUE_MAX:
            damage *= 1.5
            self.design_shadow_stacks = 0
        if self.job_name == "DesignRole85_sword_spirit":
            if any(
                other.alive and other.owner_id == self.owner_id and other is not self and other.get_current_basic_attack_type() == "melee"
                for other in getattr(self, "_design_cached_characters", [])
            ):
                damage *= 1.2
        if self.job_name == "DesignRole91_phantom_lancer":
            speed_ratio = (self.move_speed * self.get_speed_modifier()) / 100.0
            damage += max(0.0, speed_ratio - 1.0) * 60.0
        if self.is_phoenix():
            damage += (self.design_phoenix_feather // PHOENIX_FEATHER_PER_BONUS) * PHOENIX_FEATHER_DAMAGE_BONUS
        if self.is_tiger() and random.random() < TIGER_CRIT_CHANCE:
            damage *= 1.5 + TIGER_POWER_CRIT_DAMAGE_PER_STACK * self.design_tiger_power
        if self.job_name == "Bloodwraith" and self.bloodwraith_rage_active:
            damage *= BLOODWRAITH_RAGE_DAMAGE_MULTIPLIER
        if self.design_crit_multiplier > 1.0:
            damage *= self.design_crit_multiplier
            self.design_crit_multiplier = 1.0
        damage *= 1.0 + self.design_collect_fervor * 0.2
        if self.killstreak_buff_level > 0:
            damage *= 1.0 + KILLSTREAK_GAIN_DAMAGE.get(self.killstreak_buff_level, 0.0)
        if self.design_meta.get("role_num") == 63 and self.design_execute_buff_timer > 0:
            damage *= 1.25
        if self.design_sparrow_fury_timer > 0:
            damage *= 1.0 + SPARROW_FURY_DAMAGE_BONUS
        return max(1.0, damage)

    def get_current_melee_stun_duration(self):
        if self.druid_form_timer > 0 and self.held_weapon is None:
            return DRUID_FORM_STUN
        if self.job_name == "DesignRole60_golem":
            return 0.35
        return 0.0

    def is_twin_mirror(self):
        return self.job_name == TWIN_MIRROR_JOB_NAME

    def init_twin_mirror_state(self):
        self.twin_mirror_form = "white"
        self.twin_mirror_white_hp = TWIN_MIRROR_FORM_MAX_HP
        self.twin_mirror_black_hp = TWIN_MIRROR_FORM_MAX_HP
        self.twin_mirror_white_locked = False
        self.twin_mirror_black_locked = False
        self.max_hp = TWIN_MIRROR_FORM_MAX_HP
        self.hp = TWIN_MIRROR_FORM_MAX_HP
        self.color = TWIN_MIRROR_WHITE_COLOR

    def twin_mirror_form_hp_attr(self, form):
        return f"twin_mirror_{form}_hp"

    def twin_mirror_form_lock_attr(self, form):
        return f"twin_mirror_{form}_locked"

    def set_twin_mirror_form(self, form):
        if not self.is_twin_mirror():
            return
        self.twin_mirror_form = form
        self.hp = getattr(self, self.twin_mirror_form_hp_attr(form), self.hp)
        self.max_hp = TWIN_MIRROR_FORM_MAX_HP
        self.color = TWIN_MIRROR_WHITE_COLOR if form == "white" else TWIN_MIRROR_BLACK_COLOR
        self.update_rect()

    def switch_twin_mirror_form(self, force=False):
        if not self.is_twin_mirror():
            return False
        current_form = self.twin_mirror_form
        next_form = "black" if current_form == "white" else "white"
        next_hp = getattr(self, self.twin_mirror_form_hp_attr(next_form), 0.0)
        if next_hp <= 0:
            return False
        if not force and getattr(self, self.twin_mirror_form_lock_attr(next_form), False):
            return False
        setattr(self, self.twin_mirror_form_hp_attr(current_form), max(0.0, self.hp))
        if self.hp <= 0:
            setattr(self, self.twin_mirror_form_lock_attr(current_form), True)
        self.set_twin_mirror_form(next_form)
        return True

    def apply_twin_mirror_background_heal(self, amount):
        if not self.is_twin_mirror() or amount <= 0:
            return 0.0
        inactive_form = "black" if self.twin_mirror_form == "white" else "white"
        hp_attr = self.twin_mirror_form_hp_attr(inactive_form)
        lock_attr = self.twin_mirror_form_lock_attr(inactive_form)
        previous = getattr(self, hp_attr, 0.0)
        healed = min(TWIN_MIRROR_FORM_MAX_HP, previous + amount)
        setattr(self, hp_attr, healed)
        if getattr(self, lock_attr, False) and healed >= TWIN_MIRROR_FORM_MAX_HP * TWIN_MIRROR_UNLOCK_RATIO:
            setattr(self, lock_attr, False)
        return healed - previous

    def handle_twin_mirror_lethal(self):
        if not self.is_twin_mirror():
            return False
        current_form = self.twin_mirror_form
        setattr(self, self.twin_mirror_form_hp_attr(current_form), 0.0)
        setattr(self, self.twin_mirror_form_lock_attr(current_form), True)
        return self.switch_twin_mirror_form(force=True)

    def get_soul_arbiter_chain_limit(self):
        return SOUL_ARBITER_HUNT_CHAIN_LIMIT if self.soul_arbiter_hunt_timer > 0 else 1

    def register_soul_arbiter_kill(self, fallen, game_state):
        if self.job_name != SOUL_ARBITER_JOB_NAME or self.soul_arbiter_hunt_timer <= 0:
            return
        if not isinstance(fallen, Character) or not getattr(fallen, "is_main_character", True) or fallen.owner_id == self.owner_id:
            return
        self.max_hp += 10.0
        if game_state is not None:
            game_state["design_summons"].append(DesignSummon(self, "spirit", fallen.pos, source_character=fallen))

    def start_soul_chain(self, target, game_state):
        if self.job_name != SOUL_ARBITER_JOB_NAME or target is None or not getattr(target, "alive", False):
            return
        chains = self.soul_arbiter_chains
        target_id = id(target)
        if target_id not in chains and len(chains) >= self.get_soul_arbiter_chain_limit():
            oldest_id = next(iter(chains))
            chains.pop(oldest_id, None)
            for effect in game_state.get("design_effects", []):
                if effect.effect_type == "soul_chain" and effect.owner is self and effect.data.get("target_id") == oldest_id:
                    effect.alive = False
        chains[target_id] = {"target_id": target_id, "timer": SOUL_ARBITER_CHAIN_DURATION, "tick": 0.0}
        if game_state is not None:
            add_design_effect(
                game_state,
                DesignEffect("soul_chain", self, self.pos, target_id=target_id, lifetime=SOUL_ARBITER_CHAIN_DURATION),
            )

    def update_soul_arbiter_chains(self, dt, game_state):
        if self.job_name != SOUL_ARBITER_JOB_NAME:
            return
        if self.soul_arbiter_hunt_timer > 0:
            self.soul_arbiter_hunt_timer = max(0.0, self.soul_arbiter_hunt_timer - dt)
        limit = self.get_soul_arbiter_chain_limit()
        while len(self.soul_arbiter_chains) > limit:
            oldest_id = next(iter(self.soul_arbiter_chains))
            self.soul_arbiter_chains.pop(oldest_id, None)
        target_lookup = {id(target): target for target in get_targetables(game_state)}
        updated = {}
        for target_id, data in list(self.soul_arbiter_chains.items()):
            target = target_lookup.get(target_id)
            if target is None or not target.alive or target.owner_id == self.owner_id:
                continue
            if (target.pos - self.pos).length() > self.get_current_attack_range() + getattr(target, "radius", 0) + 8:
                continue
            data["timer"] -= dt
            if data["timer"] <= 0:
                continue
            data["tick"] += dt
            while data["tick"] >= SOUL_ARBITER_CHAIN_TICK and target.alive:
                data["tick"] -= SOUL_ARBITER_CHAIN_TICK
                if target.hp > 0 and target.hp <= target.max_hp * SOUL_ARBITER_EXECUTE_RATIO:
                    target.take_damage(
                        target.hp + 1.0,
                        source=self,
                        damage_type="true_soul_arbiter_exec",
                        game_state=game_state,
                        ignore_shields=True,
                    )
                else:
                    dealt = target.take_damage(
                        SOUL_ARBITER_CHAIN_DAMAGE,
                        source=self,
                        damage_type="design_physical_soul_chain",
                        game_state=game_state,
                    )
                    if target.alive and target.hp > 0 and target.hp <= target.max_hp * SOUL_ARBITER_EXECUTE_RATIO:
                        target.take_damage(
                            target.hp + 1.0,
                            source=self,
                            damage_type="true_soul_arbiter_exec",
                            game_state=game_state,
                            ignore_shields=True,
                        )
                if not target.alive:
                    break
            if target.alive:
                updated[target_id] = data
        self.soul_arbiter_chains = updated

    def apply_phoenix_fire(self, stacks, source=None, game_state=None):
        if not self.alive:
            return
        self.design_phoenix_fire += max(0, int(stacks))
        if self.design_phoenix_fire >= PHOENIX_FIRE_EXPLODE_THRESHOLD:
            self.design_phoenix_fire = 0
            fall_stacks = getattr(source, "design_phoenix_fall", 0) if source is not None else 0
            explosion_damage = PHOENIX_FIRE_EXPLODE_FALL_MULTIPLIER * fall_stacks * PHOENIX_FIRE_EXPLODE_DAMAGE_BASE
            if explosion_damage > 0 and game_state is not None:
                spawn_damage_text(game_state, self, 0.0, text="凤炎爆", color=PHOENIX_EGG_COLOR)
                self.take_damage(
                    explosion_damage,
                    source=source,
                    damage_type="design_spell_phoenix_fire_explode",
                    game_state=game_state,
                )
            if source is not None and source.is_phoenix():
                source.design_phoenix_feather += PHOENIX_FEATHER_EXPLODE_GAIN

    def refresh_phoenix_max_hp(self):
        self.max_hp = round(max(1.0, self.design_phoenix_base_max_hp * (PHOENIX_FALL_MAX_HP_MULTIPLIER ** self.design_phoenix_fall)), 2)
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def add_phoenix_fall(self):
        self.design_phoenix_fall += 1
        self.refresh_phoenix_max_hp()

    def remove_phoenix_fall(self):
        if self.design_phoenix_fall > 0:
            self.design_phoenix_fall -= 1
            self.refresh_phoenix_max_hp()

    def start_phoenix_egg(self, game_state=None):
        egg_shield = (
            self.max_hp * PHOENIX_EGG_SHIELD_MAX_HP_RATIO
            + self.get_current_basic_damage() * PHOENIX_EGG_SHIELD_DAMAGE_RATIO
        )
        self.design_phoenix_feather = max(0, self.design_phoenix_feather - PHOENIX_EGG_FEATHER_COST)
        self.design_phoenix_egg_timer = PHOENIX_EGG_DURATION
        self.design_phoenix_egg_shield = egg_shield
        self.hp = max(1.0, self.hp)
        self.apply_root(PHOENIX_EGG_DURATION)
        if game_state is not None:
            spawn_damage_text(game_state, self, 0.0, text="不灭蛋", color=PHOENIX_EGG_COLOR)

    def end_phoenix_egg(self, game_state=None):
        self.design_phoenix_egg_timer = 0.0
        self.design_phoenix_egg_shield = 0.0
        self.root_timer = 0.0
        self.hp = self.max_hp
        if game_state is not None:
            for enemy in game_state["characters"]:
                if enemy.alive and enemy is not self and enemy.owner_id != self.owner_id:
                    enemy.apply_phoenix_fire(1, source=self, game_state=game_state)
            spawn_damage_text(game_state, self, 0.0, text="涅槃重生", color=PHOENIX_EGG_COLOR)
        self.add_phoenix_fall()

    def is_xuanwu(self):
        return self.job_name == XUANWU_JOB_NAME

    def get_shell_cap(self):
        return XUANWU_SHELL_MAX_BASE + XUANWU_SHELL_MAX_PER_KILL * self.design_shell_kill_count

    def refresh_shell_max_hp(self):
        self.max_hp = max(1.0, round(self.design_shell_base_max_hp + XUANWU_SHELL_MAX_HP_PER_STACK * self.design_shell_stacks, 2))
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def add_shell(self, amount=1):
        if not self.is_xuanwu():
            return
        self.design_shell_stacks = min(self.get_shell_cap(), self.design_shell_stacks + max(0, int(amount)))
        self.refresh_shell_max_hp()

    def consume_shells(self, amount, game_state=None):
        if not self.is_xuanwu():
            return 0
        consumed = min(max(0, int(amount)), self.design_shell_stacks)
        if consumed <= 0:
            return 0
        self.design_shell_stacks -= consumed
        self.gain_mp(XUANWU_SHELL_CONSUME_MP_PER_SHELL * consumed, "xuanwu_shell_consume")
        self.refresh_shell_max_hp()
        return consumed

    def xuanwu_counterattack(self, game_state):
        if game_state is None:
            return
        enemies_list = [e for e in get_targetables(game_state) if e.alive and e.owner_id != self.owner_id]
        if not enemies_list:
            return
        nearest = sorted(enemies_list, key=lambda e: (e.pos - self.pos).length_squared())[:XUANWU_COUNTER_TARGETS]
        counter_damage = XUANWU_COUNTER_DAMAGE_BASE + XUANWU_COUNTER_DAMAGE_PER_SHELL * self.design_shell_stacks
        for enemy in nearest:
            enemy.take_damage(counter_damage, source=self, damage_type="design_spell_xuanwu_counter", game_state=game_state)
            enemy.apply_slow(XUANWU_COUNTER_SLOW, XUANWU_COUNTER_SLOW_DURATION)
        self.consume_shells(XUANWU_COUNTER_SHELL_STEP, game_state)

    def xuanwu_bulwark_burst(self, game_state):
        if game_state is None:
            return
        burst_damage = XUANWU_BULWARK_BURST_BASE + XUANWU_BULWARK_BURST_PER_SHELL * self.design_shell_stacks
        apply_aoe_damage(
            self.pos,
            XUANWU_BULWARK_BURST_RADIUS,
            burst_damage,
            self.owner_id,
            game_state,
            source=self,
            damage_type="design_spell_xuanwu_burst",
        )

    def is_tiger(self):
        return self.job_name == TIGER_JOB_NAME

    def get_tiger_prey(self, game_state):
        if game_state is None or self.design_tiger_prey_id is None:
            return None
        for unit in game_state.get("characters", []):
            if id(unit) == self.design_tiger_prey_id and unit.alive:
                return unit
        return None

    def mark_tiger_prey(self, game_state):
        if game_state is None:
            return
        candidates = [
            e for e in game_state.get("characters", [])
            if e.alive and e.owner_id != self.owner_id
        ]
        if not candidates:
            self.design_tiger_prey_id = None
            return
        prey = min(candidates, key=lambda e: (e.hp, (e.pos - self.pos).length_squared()))
        self.design_tiger_prey_id = id(prey)

    def apply_tiger_wound(self, stacks=1):
        self.design_tiger_wound = min(TIGER_WOUND_MAX, self.design_tiger_wound + max(0, int(stacks)))

    def tiger_prey_charge(self):
        if self.design_tiger_prey_charge_count >= TIGER_PREY_CHARGE_MAX_PER_SEC:
            return
        self.design_tiger_prey_charge_count += 1
        self.gain_mp(TIGER_PREY_CHARGE_PER_HIT, "tiger_prey")

    def tiger_execute_kill(self, game_state):
        self.attack_cooldown = 0.0
        self.design_tiger_power = min(TIGER_POWER_MAX, self.design_tiger_power + TIGER_EXECUTE_POWER_GAIN)
        self.design_tiger_prey_id = None
        self.mark_tiger_prey(game_state)

    def is_dragon(self):
        return self.job_name == DRAGON_JOB_NAME

    def is_susanoo(self):
        return self.job_name == SUSANOO_JOB_NAME

    def get_dragon_breath(self, form=None):
        form = form or self.design_dragon_form
        return self.design_dragon_breath_thunder if form == "thunder" else self.design_dragon_breath_wood

    def set_dragon_breath(self, form, value):
        value = max(0, min(DRAGON_BREATH_MAX, int(value)))
        if form == "thunder":
            self.design_dragon_breath_thunder = value
        else:
            self.design_dragon_breath_wood = value

    def add_dragon_breath(self, amount=1):
        self.set_dragon_breath(self.design_dragon_form, self.get_dragon_breath() + max(0, int(amount)))

    def dragon_roar(self, game_state):
        if game_state is None:
            return
        roar_damage = DRAGON_ROAR_BASE + DRAGON_ROAR_PER_BREATH * DRAGON_BREATH_MAX
        for unit in game_state.get("characters", []):
            if unit.alive and unit is not self and unit.owner_id != self.owner_id:
                if (unit.pos - self.pos).length() <= DRAGON_ROAR_RADIUS + getattr(unit, "radius", 0):
                    unit.take_damage(roar_damage * 0.5, source=self, damage_type="design_physical_dragon_roar", game_state=game_state)
                    unit.take_damage(roar_damage * 0.5, source=self, damage_type="design_spell_dragon_roar", game_state=game_state)
        self.gain_mp(DRAGON_CHARGE_ROAR, "dragon_roar")

    def dragon_switch(self, game_state, breath_before):
        old_form = self.design_dragon_form
        new_form = "wood" if old_form == "thunder" else "thunder"
        self.design_dragon_switch_bonus += breath_before * DRAGON_SWITCH_DAMAGE_PER_BREATH
        self.set_dragon_breath(old_form, 0)
        self.design_dragon_form = new_form
        self.gain_mp(DRAGON_CHARGE_SWITCH, "dragon_switch")
        if breath_before >= DRAGON_BREATH_MAX:
            self.dragon_roar(game_state)
            self.design_dragon_sweep_cooldown *= DRAGON_SWEEP_COOLDOWN_RETURN

    def get_attack_interval_multiplier(self):
        multiplier = 1.0
        if self.job_name == "Illusionist" and self.illusion_mirror_stacks > 0:
            multiplier *= max(0.84, 1.0 - self.illusion_mirror_stacks * ILLUSION_MIRROR_STACK_INTERVAL_BONUS)
        if self.job_name == "Toxicologist" and self.toxicologist_corrosion_stacks > 0:
            multiplier *= max(0.80, 1.0 - self.toxicologist_corrosion_stacks * TOXICOLOGIST_CORROSION_INTERVAL_BONUS)
        if self.job_name == "Frost Mage" and self.frost_mage_core_stacks > 0:
            multiplier *= max(0.78, 1.0 - self.frost_mage_core_stacks * FROST_MAGE_CORE_INTERVAL_BONUS)
        if self.job_name == "Pyro" and self.pyro_ember_stacks > 0:
            multiplier *= max(0.80, 1.0 - self.pyro_ember_stacks * PYRO_EMBER_INTERVAL_BONUS)
        if self.is_necromancer() and self.necromancer_bone_stacks > 0:
            multiplier *= max(0.82, 1.0 - self.necromancer_bone_stacks * 0.03)
        if self.is_paladin() and self.paladin_holy_stacks > 0:
            multiplier *= max(0.80, 1.0 - self.paladin_holy_stacks * 0.04)
        if self.is_ninja() and self.ninja_shadow_stacks > 0:
            multiplier *= max(0.72, 1.0 - self.ninja_shadow_stacks * 0.05)
        if self.is_bomber() and self.bomber_fuse_stacks > 0:
            multiplier *= max(0.86, 1.0 - self.bomber_fuse_stacks * 0.02)
        if self.is_vampire():
            multiplier *= max(0.72, 1.0 - self.get_vampire_blood_stacks() * 0.05)
        if self.swordmaster_haste_timer > 0:
            multiplier *= 0.5
        if self.bard_song_timer > 0:
            multiplier /= BARD_SONG_ATTACK_MULTIPLIER
        if self.gladiator_duel_timer > 0:
            multiplier /= GLADIATOR_SELF_ATTACK_MULTIPLIER
        if self.duel_haste_timer > 0:
            multiplier /= GLADIATOR_TARGET_ATTACK_MULTIPLIER
        if self.cold_stacks > 0:
            multiplier *= 1.0 + min(0.8, self.cold_stacks * 0.02)
        if self.design_bonus_attack_speed > 0:
            multiplier /= 1.0 + self.design_bonus_attack_speed
        if self.is_windstorm_fox() and self.windstorm_qi_stacks > 0:
            multiplier /= 1.0 + self.windstorm_qi_stacks * WINDSTORM_FOX_ATTACK_SPEED_BONUS_PER_QI
        if self.job_name == "Bloodwraith" and self.bloodwraith_rage_active:
            multiplier /= BLOODWRAITH_RAGE_ATTACK_SPEED_MULTIPLIER
        if self.job_name == "DesignRole87_frost_giant":
            nearby_enemy = any(
                other.alive and other.owner_id != self.owner_id and (other.pos - self.pos).length() <= 60 + getattr(other, "radius", 0)
                for other in getattr(self, "_design_cached_characters", [])
            )
            if nearby_enemy:
                multiplier *= 1.3
        if self.is_dragon() and self.design_dragon_form == "thunder":
            multiplier *= 1.0 - DRAGON_THUNDER_ATTACK_SPEED_BONUS
        if self.design_banner_zone_timer > 0:
            multiplier /= 1.0 + BANNER_HASTE_BONUS
        if self.design_potion_haste_timer > 0:
            multiplier /= 1.0 + POTION_HASTE_BONUS
        if self.design_wild_brew_timer > 0:
            multiplier /= 1.0 + WILD_BREW_HASTE
        return max(0.05, multiplier)

    def get_basic_attack_cooldown(self):
        if self.is_soul_moth() and self.design_soul_moth_form:
            return SOUL_MOTH_FORM_ACCELERATION * self.get_attack_interval_multiplier()
        return self.base_attack_interval * self.get_attack_interval_multiplier()

    def get_weapon_attack_cooldown(self, base_interval):
        cooldown = base_interval * self.get_attack_interval_multiplier()
        if self.tinkerer_overclock_timer > 0 and self.held_weapon is not None and self.held_weapon.get("overclocked"):
            cooldown *= 0.5
        return max(0.05, cooldown)

    def get_target_attack_bonus(self, target):
        if self.job_name == "Bounty Hunter" and target is not None and target.owner_id == self.bounty_target_id:
            return 1.0 + BOUNTY_DAMAGE_BONUS
        if self.job_name == "DesignRole73_illuminator" and getattr(target, "job_name", None) == "DesignRole72_soul_eater":
            return 1.2
        if self.job_name == "Sniper" and target is not None:
            distance = (target.pos - self.pos).length()
            distance_bonus = min(SNIPER_DISTANCE_BONUS_CAP, max(0.0, distance / SNIPER_DISTANCE_BONUS_STEP * SNIPER_DISTANCE_BONUS_PER_STEP))
            bonus = 1.0 + distance_bonus
            if self.sniper_stationary_ready:
                bonus *= 1.0 + SNIPER_STATIONARY_BONUS
            return bonus
        return 1.0

    def add_true_shield(self, amount):
        if amount > 0:
            self.true_shield += amount

    def add_poison_progress(self, amount):
        if amount <= 0:
            return
        self.poison_stack_progress += amount
        while self.poison_stack_progress >= 1.0:
            self.poison_stack_progress -= 1.0
            self.poison_stacks += 1

    def apply_disarm(self, duration):
        self.disarm_timer = max(self.disarm_timer, duration)

    def apply_silence(self, duration):
        self.silence_timer = max(self.silence_timer, duration)

    def apply_blind(self, duration):
        self.blind_timer = max(self.blind_timer, duration)

    def apply_bleed(self, stacks=1, duration=DESIGN_BLEED_DURATION):
        stacks = max(1, int(stacks))
        self.bleed_stacks += stacks
        for _ in range(stacks):
            self.bleed_decay_timers.append(duration)

    def apply_hell_burn(self, stacks=1, duration=HELLBRINGER_BURN_DURATION, source=None):
        stacks = max(1, int(stacks))
        duration = max(0.0, float(duration))
        if duration <= 0:
            return
        if source is not None:
            self.hell_burn_source = source
        for _ in range(stacks):
            if len(self.hell_burn_timers) < HELLBRINGER_BURN_MAX_STACKS:
                self.hell_burn_timers.append(duration)
            else:
                weakest_index = min(range(len(self.hell_burn_timers)), key=self.hell_burn_timers.__getitem__)
                self.hell_burn_timers[weakest_index] = duration

    def apply_cold(self, stacks=1):
        self.cold_stacks = min(40, self.cold_stacks + max(1, int(stacks)))
        self.cold_decay_timer = 10.0

    def apply_equilibrium_mark(self, duration=EQUILIBRIUM_MARK_DURATION):
        self.equilibrium_mark_timer = max(self.equilibrium_mark_timer, duration)

    def apply_sleep(self, duration):
        self.sleep_timer = max(self.sleep_timer, duration)
        self.apply_stun(duration)

    def apply_freeze(self, duration):
        self.freeze_timer = max(self.freeze_timer, duration)
        self.apply_stun(duration)

    def apply_doom(self, duration):
        self.doom_timer = max(self.doom_timer, duration)

    def apply_control(self, owner_id, duration):
        self.control_owner_id = owner_id
        self.control_timer = max(self.control_timer, duration)

    def apply_charm(self, owner_id, duration):
        self.charm_owner_id = owner_id
        self.charm_timer = max(self.charm_timer, duration)

    def clear_negative_states(self):
        self.slow_timer = 0.0
        self.slow_factor = 0.0
        self.stun_timer = 0.0
        self.freeze_timer = 0.0
        self.root_timer = 0.0
        self.doom_timer = 0.0
        self.charm_timer = 0.0
        self.charm_owner_id = None
        self.disarm_timer = 0.0
        self.silence_timer = 0.0
        self.blind_timer = 0.0
        self.sleep_timer = 0.0
        self.bleed_stacks = 0
        self.bleed_decay_timers.clear()
        self.cold_stacks = 0
        self.cold_decay_timer = 0.0
        self.equilibrium_mark_timer = 0.0
        self.hell_burn_timers.clear()
        self.hell_burn_source = None
        self.design_poison_erosion = 0
        self.poison_stacks = 0
        self.poison_stack_progress = 0.0
        self.poison_decay_accumulator = 0.0
        self.mage_burn_timer = 0.0
        self.knight_backlash_timer = 0.0
        self.knight_backlash_tick_accumulator = 0.0
        self.hex_curse_timer = 0.0

    def clear_control_states(self):
        self.slow_timer = 0.0
        self.slow_factor = 0.0
        self.stun_timer = 0.0
        self.freeze_timer = 0.0
        self.root_timer = 0.0
        self.charm_timer = 0.0
        self.charm_owner_id = None
        self.disarm_timer = 0.0
        self.silence_timer = 0.0
        self.blind_timer = 0.0
        self.sleep_timer = 0.0
        self.control_timer = 0.0
        self.control_owner_id = None

    def apply_knockback(self, direction, distance):
        if direction.length_squared() == 0 or distance <= 0:
            return
        push = direction.normalize() * distance
        self.pos += push
        self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
        self.vel += push * 1.2
        self.update_rect()

    def record_rewind_snapshot(self, current_time):
        if self.job_name != "Time Walker" or not self.is_main_character:
            return
        self.time_rewind_snapshots.append((current_time, pygame.Vector2(self.pos), float(self.hp)))
        cutoff = current_time - TIME_WALKER_REWIND_SECONDS - 0.5
        self.time_rewind_snapshots = [snapshot for snapshot in self.time_rewind_snapshots if snapshot[0] >= cutoff]

    def rewind_to_snapshot(self, current_time):
        target_time = current_time - TIME_WALKER_REWIND_SECONDS
        snapshot = None
        for candidate in self.time_rewind_snapshots:
            if candidate[0] <= target_time:
                snapshot = candidate
            else:
                break
        if snapshot is None and self.time_rewind_snapshots:
            snapshot = self.time_rewind_snapshots[0]
        if snapshot is None:
            return
        _, pos, hp = snapshot
        self.pos = pygame.Vector2(pos)
        self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
        self.hp = clamp(hp, 1.0, self.max_hp)
        self.vel *= 0.0
        self.update_rect()

    def on_damage_dealt(self, damage, damage_type="basic"):
        if damage <= 0 or not self.alive:
            return
        self.damageDealt += damage
        if self.job_name == "Mage":
            self.mage_arcane_stacks = min(MAGE_ARCANE_MAX_STACKS, self.mage_arcane_stacks + 1)
        if self.job_name == "Illusionist":
            self.illusion_mirror_progress += damage
            while self.illusion_mirror_progress >= ILLUSION_MIRROR_BUILD and self.illusion_mirror_stacks < ILLUSION_MIRROR_STACK_MAX:
                self.illusion_mirror_progress -= ILLUSION_MIRROR_BUILD
                self.illusion_mirror_stacks += 1
            if self.illusion_mirror_stacks > 0:
                self.illusion_mirror_timer = ILLUSION_MIRROR_DURATION
        if self.job_name == "Toxicologist":
            self.toxicologist_corrosion_progress += damage
            while self.toxicologist_corrosion_progress >= TOXICOLOGIST_CORROSION_BUILD and self.toxicologist_corrosion_stacks < TOXICOLOGIST_CORROSION_STACK_MAX:
                self.toxicologist_corrosion_progress -= TOXICOLOGIST_CORROSION_BUILD
                self.toxicologist_corrosion_stacks += 1
            if self.toxicologist_corrosion_stacks > 0:
                self.toxicologist_corrosion_timer = TOXICOLOGIST_CORROSION_DURATION
        if self.job_name == "Frost Mage":
            self.frost_mage_core_progress += damage
            while self.frost_mage_core_progress >= FROST_MAGE_CORE_BUILD and self.frost_mage_core_stacks < FROST_MAGE_CORE_STACK_MAX:
                self.frost_mage_core_progress -= FROST_MAGE_CORE_BUILD
                self.frost_mage_core_stacks += 1
            if self.frost_mage_core_stacks > 0:
                self.frost_mage_core_timer = FROST_MAGE_CORE_DURATION
        if self.job_name == "Pyro":
            self.pyro_ember_progress += damage
            while self.pyro_ember_progress >= PYRO_EMBER_BUILD and self.pyro_ember_stacks < PYRO_EMBER_STACK_MAX:
                self.pyro_ember_progress -= PYRO_EMBER_BUILD
                self.pyro_ember_stacks += 1
            if self.pyro_ember_stacks > 0:
                self.pyro_ember_timer = PYRO_EMBER_DURATION
        if self.is_necromancer():
            self.necromancer_bone_progress += damage
            while self.necromancer_bone_progress >= 15.0 and self.necromancer_bone_stacks < 5:
                self.necromancer_bone_progress -= 15.0
                self.necromancer_bone_stacks += 1
            if self.necromancer_bone_stacks > 0:
                self.necromancer_bone_timer = 8.0
        if self.is_bomber():
            self.bomber_fuse_progress += damage
            while self.bomber_fuse_progress >= 20.0 and self.bomber_fuse_stacks < 4:
                self.bomber_fuse_progress -= 20.0
                self.bomber_fuse_stacks += 1
            if self.bomber_fuse_stacks > 0:
                self.bomber_fuse_timer = 6.0
        if self.config["mp_mode"] == "damage_dealt_flat":
            self.gain_mp(self.config["mp_rate"], "damage_dealt")
        elif self.config["mp_mode"] == "damage_dealt_scaled":
            self.gain_mp(damage * self.config["mp_rate"], "damage_dealt_scaled")
        if self.is_sunfire_blademaster():
            self.sunfire_damage_reduction_stacks = min(
                SUNFIRE_DAMAGE_REDUCTION_STACKS,
                self.sunfire_damage_reduction_stacks + 1,
            )
        if self.is_windstorm_fox():
            self.windstorm_qi_stacks = min(WINDSTORM_FOX_QI_MAX, self.windstorm_qi_stacks + 1)
        if self.is_twin_mirror():
            self.apply_twin_mirror_background_heal(damage)
        if self.job_name == SOUL_ARBITER_JOB_NAME:
            self.add_true_shield(damage * SOUL_ARBITER_SHIELD_RATIO)
        if self.job_name == "Bloodwraith" and self.bloodwraith_shield_timer > 0 and self.bloodwraith_shield_hp > 0 and str(damage_type).startswith("basic"):
            self.heal(damage * BLOODWRAITH_LIFESTEAL_RATIO)
        if self.job_name == "DesignRole90_collector":
            self.design_collect_fervor = min(8, self.design_collect_fervor + 1)
        if self.is_design_role() and self.design_meta.get("role_num") == 98:
            self.add_design_xp(damage)

    def on_attack_committed(self):
        if not self.alive:
            return
        if self.config["mp_mode"] == "attack_count":
            self.gain_mp(self.config["mp_rate"], "attack")
        if self.job_name == "Illusionist" and self.illusion_mirror_stacks > 0:
            self.illusion_mirror_timer = ILLUSION_MIRROR_DURATION
        if self.job_name == "Behemoth" and self.behemoth_stone_stacks > 0:
            self.behemoth_stone_timer = BEHEMOTH_STONE_DECAY
        if self.job_name == "Toxicologist" and self.toxicologist_corrosion_stacks > 0:
            self.toxicologist_corrosion_timer = TOXICOLOGIST_CORROSION_DURATION
        if self.job_name == "Frost Mage" and self.frost_mage_core_stacks > 0:
            self.frost_mage_core_timer = FROST_MAGE_CORE_DURATION
        if self.job_name == "Pyro" and self.pyro_ember_stacks > 0:
            self.pyro_ember_timer = PYRO_EMBER_DURATION
        if self.is_sunfire_blademaster():
            self.gain_mp(10.0, "sunfire_attack")
        if self.is_windstorm_fox():
            self.windstorm_idle_timer = 0.0
            self.windstorm_decay_timer = 0.0
        if self.job_name == "DesignRole66_blood_mage":
            self.design_extra_counter += 1
            if self.design_extra_counter >= 5:
                self.design_extra_counter = 0
                self.take_damage(20.0, source=self, damage_type="true_design_blood_cost", game_state=None)
        if self.job_name == "Sniper" and self.sniper_stationary_ready:
            self.sniper_stationary_ready = False
            self.sniper_stationary_timer = 0.0
        self.design_shadow_idle = 0.0

    def on_distance_moved(self, distance, game_state=None):
        if not self.alive or distance <= 0:
            return
        if self.config["mp_mode"] == "distance_moved":
            self.gain_mp(distance * WINDRUNNER_MP_PER_PIXEL, "move")
        elif self.config["mp_mode"] == "distance_scaled":
            self.gain_mp(distance * self.config["mp_rate"], "move_scaled")
        if self.job_name == "Illusionist" and self.illusion_mirror_stacks > 0:
            self.illusion_mirror_timer = ILLUSION_MIRROR_DURATION
        if self.job_name == "Behemoth" and self.behemoth_stone_stacks > 0:
            self.behemoth_stone_timer = BEHEMOTH_STONE_DECAY
        if self.job_name == "Toxicologist" and self.toxicologist_corrosion_stacks > 0:
            self.toxicologist_corrosion_timer = TOXICOLOGIST_CORROSION_DURATION
        if self.job_name == "Frost Mage" and self.frost_mage_core_stacks > 0:
            self.frost_mage_core_timer = FROST_MAGE_CORE_DURATION
        if self.job_name == "Pyro" and self.pyro_ember_stacks > 0:
            self.pyro_ember_timer = PYRO_EMBER_DURATION
        if self.is_ninja():
            self.ninja_shadow_progress += distance
            while self.ninja_shadow_progress >= 120.0 and self.ninja_shadow_stacks < 3:
                self.ninja_shadow_progress -= 120.0
                self.ninja_shadow_stacks += 1
            if self.ninja_shadow_stacks > 0:
                self.ninja_shadow_timer = 6.0
        if self.job_name == "Sniper":
            self.sniper_stationary_timer = 0.0
            self.sniper_stationary_ready = False
        if self.job_name == "DesignRole78_hellbringer" and game_state is not None:
            self.design_hell_trail_distance += distance
            trail_spacing = max(8.0, self.radius * 0.8)
            while self.design_hell_trail_distance >= trail_spacing:
                self.design_hell_trail_distance -= trail_spacing
                add_design_effect(
                    game_state,
                    DesignEffect(
                        "fire_trail",
                        self,
                        self.pos,
                        radius=self.radius,
                        lifetime=HELLBRINGER_TRAIL_DURATION,
                        dps=HELLBRINGER_TRAIL_DAMAGE,
                        color=HELLBRINGER_TRAIL_COLOR,
                    ),
                )
        if self.design_tiger_wound > 0 and game_state is not None:
            self.design_tiger_trail_distance += distance
            while self.design_tiger_trail_distance >= TIGER_WOUND_TRAIL_SPACING:
                self.design_tiger_trail_distance -= TIGER_WOUND_TRAIL_SPACING
                add_design_effect(
                    game_state,
                    DesignEffect("tiger_blood_trail", self, self.pos, radius=5.0, lifetime=TIGER_WOUND_TRAIL_LIFETIME),
                )
        if self.is_dragon():
            self.design_dragon_move_distance += distance
            while self.design_dragon_move_distance >= DRAGON_MOVE_BONUS_DISTANCE:
                self.design_dragon_move_distance -= DRAGON_MOVE_BONUS_DISTANCE
                self.design_dragon_move_bonus_ready = True
        self.stationary_timer = 0.0

    def on_character_death(self, fallen, game_state):
        if not self.alive or fallen is self:
            return
        if self.config["mp_mode"] == "death_count":
            self.gain_mp(self.config["mp_rate"], "death_count")
        if self.is_gravekeeper() and game_state is not None:
            field = self.get_gravekeeper_active_field(game_state)
            if field is not None:
                stacks = min(GRAVEKEEPER_FIELD_MAX_STACKS, int(field.data.get("grave_stacks", 0)) + 1)
                field.data["grave_stacks"] = stacks
                field.radius = GRAVEKEEPER_FIELD_RADIUS + stacks * GRAVEKEEPER_FIELD_STACK_RADIUS
                field.lifetime = min(
                    field.lifetime + GRAVEKEEPER_FIELD_STACK_DURATION,
                    GRAVEKEEPER_FIELD_DURATION + GRAVEKEEPER_FIELD_MAX_STACKS * GRAVEKEEPER_FIELD_STACK_DURATION,
                )
            if (
                (fallen.pos - self.pos).length() <= GRAVEKEEPER_NEARBY_CHARGE_RANGE + getattr(fallen, "radius", 0)
                or (
                    field is not None
                    and (fallen.pos - field.pos).length() <= field.radius + getattr(fallen, "radius", 0)
                )
            ):
                self.gain_mp(GRAVEKEEPER_NEARBY_CHARGE_BONUS, "gravekeeper_bonus")
            game_state["design_effects"].append(
                DesignEffect(
                    "grave_marker",
                    self,
                    fallen.pos,
                    radius=12.0,
                    lifetime=GRAVEKEEPER_MARKER_DURATION,
                )
            )
        if self.job_name == "DesignRole65_mechanist" and (fallen.pos - self.pos).length() <= 120.0:
            self.heal(10.0)
        if self.job_name == "DesignRole72_soul_eater" and fallen.owner_id != self.owner_id:
            self.max_hp += 2.0
            self.hp = min(self.max_hp, self.hp + 5.0)
        if self.is_design_role() and self.design_meta.get("role_num") == 98 and fallen.owner_id != self.owner_id:
            self.add_design_xp(100.0)

    def get_ranged_attack_targets(self, primary_target, game_state):
        count = max(1, int(self.config.get("attack_targets", 1)))
        targets = [primary_target]
        if count == 1:
            return targets
        candidates = [
            target
            for target in get_targetables(game_state)
            if target.alive and target.owner_id != self.owner_id and target is not primary_target
        ]
        candidates.sort(key=lambda target: (target.pos - self.pos).length_squared())
        for candidate in candidates:
            targets.append(candidate)
            if len(targets) >= count:
                break
        return targets

    def update_chase_noise(self, dt):
        self.chase_noise_timer -= dt
        if self.chase_noise_timer <= 0:
            self.chase_noise_timer = random.uniform(*CHASE_NOISE_RETARGET_INTERVAL)
            self.chase_noise_target = random.uniform(-CHASE_NOISE_MAX_DEG, CHASE_NOISE_MAX_DEG)
        blend = clamp(CHASE_NOISE_LERP * dt, 0.0, 1.0)
        self.chase_noise_angle += (self.chase_noise_target - self.chase_noise_angle) * blend

    def apply_chase_noise(self, direction, dt):
        if direction.length_squared() == 0:
            return pygame.Vector2()
        self.update_chase_noise(dt)
        return direction.rotate(self.chase_noise_angle)

    def get_melee_intercept_position(self, target):
        predicted = pygame.Vector2(target.pos)
        if getattr(target, "vel", pygame.Vector2()).length_squared() > 0:
            distance = (target.pos - self.pos).length()
            own_speed = max(1.0, self.move_speed * self.get_speed_modifier())
            lead_time = clamp(
                distance / (own_speed + 120.0),
                MELEE_INTERCEPT_MIN_LEAD,
                MELEE_INTERCEPT_MAX_LEAD,
            )
            predicted += target.vel * lead_time
        predicted.x = clamp(predicted.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        predicted.y = clamp(predicted.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
        return predicted

    def try_start_melee_dash(self, direction, distance, current_range):
        if not self.can_use_melee_dash():
            return False
        if self.melee_gap_dash_timer > 0 or self.melee_gap_dash_cooldown > 0:
            return False
        if not current_range < distance <= current_range + MELEE_DASH_TRIGGER_BUFFER:
            return False
        if direction.length_squared() == 0:
            return False
        dash_direction = direction.normalize()
        self.melee_gap_dash_timer = MELEE_DASH_DURATION
        self.melee_gap_dash_cooldown = MELEE_DASH_COOLDOWN
        self.vel += dash_direction * self.move_speed * 0.95
        self.recent_move_dir = pygame.Vector2(dash_direction)
        return True

    def get_separation_vector(self, game_state):
        separation = pygame.Vector2()
        neighbors = 0
        for other in game_state["characters"]:
            if other is self or not other.alive:
                continue
            offset = self.pos - other.pos
            distance = offset.length()
            if distance == 0:
                separation += random_unit_vector()
                neighbors += 1
                continue
            if distance >= SEPARATION_RADIUS:
                continue
            strength = (SEPARATION_RADIUS - distance) / SEPARATION_RADIUS
            minimum_gap = self.radius + other.radius
            if distance < minimum_gap:
                strength += (minimum_gap - distance) / minimum_gap
            separation += offset.normalize() * strength
            neighbors += 1
        if neighbors == 0 or separation.length_squared() == 0:
            return pygame.Vector2()
        separation /= neighbors
        if separation.length_squared() > 0:
            separation = separation.normalize() * min(1.0, separation.length())
        return separation

    def heal(self, amount):
        if not self.alive or amount <= 0:
            return 0.0
        if self.is_vampire():
            amount *= 1.0 + self.get_vampire_blood_stacks() * 0.05
        previous = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        healed = self.hp - previous
        if self.is_paladin() and healed > 0:
            self.paladin_holy_progress += healed
            while self.paladin_holy_progress >= 60.0 and self.paladin_holy_stacks < 5:
                self.paladin_holy_progress -= 60.0
                self.paladin_holy_stacks += 1
            if self.paladin_holy_stacks > 0:
                self.paladin_holy_timer = 8.0
        if healed >= 5 and runtime._LIVE_GAME_STATE is not None:
            spawn_damage_text(runtime._LIVE_GAME_STATE, self, healed, text=f"+{int(round(healed))}", color=HEAL_TEXT_COLOR)
            heal_particles = runtime._LIVE_GAME_STATE.setdefault("spell_trail_particles", [])
            for _ in range(2):
                heal_particles.append(
                    SpellTrailParticle(
                        self.pos + pygame.Vector2(0, -self.radius - 8),
                        (110, 230, 150),
                        velocity=pygame.Vector2(random.uniform(-10, 10), random.uniform(-42, -14)),
                        size=2,
                        lifetime=0.45,
                    )
                )
        return healed

    def gain_mp(self, amount, reason):
        if not self.alive or amount <= 0:
            return
        if self.design_banished:
            return
        self.mp = clamp(self.mp + amount, 0.0, MAX_MP)

    def apply_slow(self, amount, duration):
        if self.job_name == "DesignRole64_dreamweaver":
            return
        if self.design_tide_link_active:
            duration *= 1.0 - TIDE_CC_REDUCTION
        self.slow_timer = max(self.slow_timer, duration)
        self.slow_factor = max(self.slow_factor, amount)

    def apply_stun(self, duration):
        if self.control_immunity_timer > 0 or self.job_name == "DesignRole64_dreamweaver":
            return
        if self.design_tide_link_active:
            duration *= 1.0 - TIDE_CC_REDUCTION
        self.stun_timer = max(self.stun_timer, duration)

    def apply_root(self, duration):
        if self.control_immunity_timer > 0 or self.job_name == "DesignRole64_dreamweaver":
            return
        if self.design_tide_link_active:
            duration *= 1.0 - TIDE_CC_REDUCTION
        self.root_timer = max(self.root_timer, duration)

    def try_pickup_weapon(self, weapon_orb):
        if not self.alive or self.held_weapon is not None or not weapon_orb.alive or not self.can_pick_up_weapons():
            return False
        if (self.pos - weapon_orb.pos).length() > self.radius + weapon_orb.radius:
            return False
        weapon_def = WEAPON_DEFS[weapon_orb.weapon_id]
        self.held_weapon = {
            "weapon_id": weapon_orb.weapon_id,
            "ammo": weapon_def["ammo"],
            "cooldown": 0.0,
        }
        if self.job_name == "DesignRole91_phantom_lancer" and weapon_orb.weapon_id == "ColdSpear":
            self.phantom_lancer_spear_charges = 3
            self.clear_weapon()  # 冷锋枪立即化为枪意，普攻转为突刺
        weapon_orb.alive = False
        if self.config["mp_mode"] == "weapon_pickup":
            self.gain_mp(self.config["mp_rate"], "weapon_pickup")
        return True

    def clear_weapon(self):
        self.held_weapon = None

    def is_sparrow(self):
        return self.job_name == SPARROW_JOB_NAME

    def attach_sparrow_host(self, host, game_state=None):
        if not self.is_sparrow() or self.design_sparrow_host_id is not None:
            return
        if host is None or not getattr(host, "alive", False):
            return
        if getattr(host, "design_corrupted_blood", 0.0) > 0:
            return
        cost = min(host.max_hp * SPARROW_BLOOD_RATIO, max(0.0, host.hp - 1.0))
        if cost <= 0:
            return
        host.hp -= cost
        host.design_corrupted_blood = cost
        self.design_sparrow_host_id = host.id
        if game_state is not None:
            spawn_attack_impact(game_state, host.pos, SPARROW_BLOOD_COLOR, radius=16, thickness=2, burst_count=10)

    def get_sparrow_host(self, game_state):
        if self.design_sparrow_host_id is None or game_state is None:
            return None
        return next((c for c in game_state.get("characters", []) if c.id == self.design_sparrow_host_id and c.alive), None)

    def update_sparrow_host(self, dt, game_state):
        if not self.is_sparrow():
            return
        host = self.get_sparrow_host(game_state)
        if host is None:
            if self.design_sparrow_host_id is not None:
                self.design_sparrow_host_id = None
                self.design_sparrow_reattach_timer = SPARROW_REATTACH_DELAY
            if self.design_sparrow_reattach_timer > 0:
                self.design_sparrow_reattach_timer = max(0.0, self.design_sparrow_reattach_timer - dt)
            else:
                allies = [
                    c for c in game_state.get("characters", [])
                    if c.alive and c.owner_id == self.owner_id and c is not self and getattr(c, "design_corrupted_blood", 0.0) <= 0
                ]
                if allies:
                    nearest = min(allies, key=lambda c: (c.pos - self.pos).length_squared())
                    self.attach_sparrow_host(nearest, game_state)
        else:
            # 附着中：雀影隐身挂机，位置跟随宿主（特效用）
            self.vel *= 0.0
            self.pos = pygame.Vector2(host.pos) + pygame.Vector2(0, -host.radius - 16)
            self.update_rect()

    def throw_potion(self, target, game_state=None):
        if not self.alive or target is None or not getattr(target, "alive", False):
            return
        roll = random.random()
        if roll < 0.34:
            target.design_potion_haste_timer = max(getattr(target, "design_potion_haste_timer", 0.0), POTION_HASTE_DURATION)
        elif roll < 0.67:
            if hasattr(target, "heal"):
                target.heal(target.max_hp * POTION_HEAL_RATIO)
        else:
            if hasattr(target, "add_true_shield"):
                target.add_true_shield(target.max_hp * POTION_SHIELD_RATIO)
        if game_state is not None:
            spawn_attack_impact(game_state, target.pos, ALCHEMIST_COLOR, radius=10, thickness=2, burst_count=6)

    def throw_potion_to_nearest_ally(self, game_state):
        allies = [c for c in game_state.get("characters", []) if c.alive and c.owner_id == self.owner_id and c is not self]
        if not allies:
            return
        nearest = min(allies, key=lambda c: (c.pos - self.pos).length_squared())
        self.throw_potion(nearest, game_state)

    def is_soul_moth(self):
        return self.job_name == SOUL_MOTH_JOB_NAME

    def enter_soul_moth_form(self, game_state=None):
        if not self.is_soul_moth():
            return
        self.design_soul_moth_form = True
        self.design_soul_moth_timer = SOUL_MOTH_MOTH_DURATION
        self.design_soul_moth_soul = 0
        self.physical_resistance = max(0.0, self._soul_moth_base_physical_resistance - SOUL_MOTH_FORM_PHYS_RESIST_DELTA)
        if game_state is not None:
            spawn_attack_impact(game_state, self.pos, SOUL_MOTH_FORM_COLOR, radius=30, thickness=4, lifetime=0.3, burst_count=16)
            sparks = game_state.setdefault("spell_trail_particles", [])
            for spark_index in range(8):
                sparks.append(
                    SpellTrailParticle(
                        pygame.Vector2(self.pos),
                        SOUL_MOTH_FORM_COLOR if spark_index % 2 == 0 else (250, 236, 180),
                        velocity=random_unit_vector() * random.uniform(60.0, 160.0),
                        size=3,
                        lifetime=0.6,
                    )
                )

    def exit_soul_moth_form(self):
        if not self.is_soul_moth():
            return
        self.design_soul_moth_form = False
        self.design_soul_moth_timer = 0.0
        self.design_soul_moth_soul = 0
        self.physical_resistance = self._soul_moth_base_physical_resistance

    def take_damage(
        self,
        amount,
        source=None,
        damage_type="basic",
        game_state=None,
        count_on_damage_dealt=True,
        ignore_shields=False,
        ignore_equilibrium_thresholds=False,
    ):
        if not self.alive or amount <= 0:
            return 0.0
        if self.swordmaster_invuln_timer > 0 or self.smasher_leap_timer > 0 or self.valkyrie_dive_timer > 0 or self.design_untargetable_timer > 0:
            return 0.0
        if self.is_soul_moth() and self.design_soul_moth_form and not str(damage_type).startswith("true_") and random.random() < SOUL_MOTH_EVADE_CHANCE:
            if game_state is not None:
                spawn_damage_text(game_state, self, 0.0, text="蝶影", color=SOUL_MOTH_FORM_COLOR)
            return 0.0

        damage = amount
        is_true_damage = str(damage_type).startswith("true_")
        if self.design_tide_link_active and not self._tide_share and damage > 0 and game_state is not None:
            members = [m for m in game_state.get("characters", []) if m.alive and getattr(m, "design_tide_link_active", False)]
            if len(members) >= 2:
                share = damage / len(members)
                for member in members:
                    member._tide_share = True
                    member.take_damage(share, source=source, damage_type=damage_type, game_state=game_state)
                    member._tide_share = False
                hub_id = self.design_tide_hub_id
                if hub_id is not None:
                    hub_char = next((c for c in game_state.get("characters", []) if c.id == hub_id), None)
                    if hub_char is not None and getattr(hub_char, "alive", False):
                        hub_char.gain_mp(damage * TIDE_MP_RATIO, "tide_share")
                return amount
        if self.job_name == "DesignRole91_phantom_lancer" and self.vel.length() > 30.0 and not is_true_damage:
            damage *= 0.88
        # 队友增益互联（112-114）：旗区减伤/掩护减伤/狂野加重/协同与集火增伤/旗区吸血
        src_char = None
        if isinstance(source, Character):
            src_char = source
        elif hasattr(source, "owner") and isinstance(source.owner, Character):
            src_char = source.owner
        if not is_true_damage:
            if self.design_banner_zone_timer > 0:
                damage *= 1.0 - BANNER_REDUCTION
            if self.design_protect_timer > 0:
                damage *= 1.0 - SQUAD_PROTECT_REDUCTION
            if self.design_wild_brew_timer > 0:
                damage *= 1.0 + WILD_BREW_PENALTY
            if self.design_corrupted_blood > 0 and str(damage_type).startswith("design_spell_"):
                damage *= 1.0 - SPARROW_SPELL_REDUCTION
        if src_char is not None and src_char.owner_id != self.owner_id:
            if self.design_squad_mark_timer > 0 and self.design_squad_mark_owner_id == src_char.owner_id:
                friends = max(1, sum(1 for c in game_state.get("characters", []) if c.alive and c.owner_id == src_char.owner_id))
                damage *= 1.0 + min(SQUAD_MARK_BONUS_CAP, friends * SQUAD_MARK_BONUS_PER_FRIEND)
            if self.design_squad_primary_timer > 0 and self.design_squad_primary_owner_id == src_char.owner_id:
                damage *= 1.0 + SQUAD_FOCUS_BONUS
            if getattr(src_char, "design_banner_lifesteal_timer", 0.0) > 0 and damage > 0:
                src_char.heal(damage * BANNER_LIFESTEAL)
            if src_char.design_meta.get("role_num") == 119 and damage > 0:
                curse_lifesteal = BLOODSUCKER_CURSE_LIFESTEAL_PER * min(BLOODSUCKER_CURSE_MAX, getattr(self, "design_blood_curse", 0))
                lifesteal_rate = BLOODSUCKER_LIFESTEAL_RATIO + curse_lifesteal
                if getattr(src_char, "design_blood_feast_timer", 0.0) > 0:
                    lifesteal_rate *= BLOODSUCKER_FEAST_LIFESTEAL_MULT
                src_char.heal(damage * lifesteal_rate)
            if self.design_kenshi_mark > 0 and src_char.design_meta.get("role_num") == 120:
                damage *= 1.0 + KENSHI_MARK_DAMAGE_PER * min(KENSHI_MARK_MAX, self.design_kenshi_mark)
        if self.job_name == KENSHI_JOB_NAME and damage > 0 and src_char is not None and src_char.owner_id != self.owner_id and self.design_kenshi_counter_cd <= 0:
            self.design_kenshi_counter_cd = KENSHI_COUNTER_CD
            away = self.pos - src_char.pos
            if away.length_squared() > 0:
                self.pos += away.normalize() * KENSHI_COUNTER_JUMP
                self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                self.update_rect()
            counter_dealt = src_char.take_damage(KENSHI_COUNTER_DAMAGE, source=self, damage_type="design_physical_kenshi_counter", game_state=game_state)
            if counter_dealt > 0:
                apply_kenshi_mark(self, src_char, 1, game_state)
            self.gain_mp(KENSHI_COUNTER_MP, "kenshi_counter")
            spawn_attack_impact(game_state, src_char.pos, KENSHI_COLOR, radius=12, thickness=2, burst_count=8)
        source_character = None
        if isinstance(source, Character):
            source_character = source
        elif hasattr(source, "owner") and isinstance(source.owner, Character):
            source_character = source.owner
        damage_kind = get_damage_kind(damage_type, source_character)
        if self.is_sunfire_blademaster() and source_character is not self:
            if self.sunfire_invuln_timer > 0:
                return 0.0
            if self.sunfire_evasion_timer > 0 and random.random() < SUNFIRE_EVADE_CHANCE:
                return 0.0
        if source_character is not None and source_character.owner_id == self.owner_id:
            pass
        elif self.job_name == "DesignRole67_martial_artist" and random.random() < 0.15:
            self.design_crit_multiplier = max(1.0, self.design_crit_multiplier, 1.5)
            return 0.0
        elif self.job_name == "DesignRole75_astral_being" and random.random() < 0.5:
            self.heal(self.max_hp * 0.02)
            return 0.0
        if self.is_xuanwu() and self.design_shell_guard_cooldown <= 0:
            self.design_shell_hit_counter += 1
            if self.design_shell_hit_counter >= XUANWU_SHELL_GUARD_INTERVAL:
                self.design_shell_hit_counter = 0
                if self.design_shell_stacks >= XUANWU_SHELL_GUARD_COST:
                    shield_per = XUANWU_SHELL_GUARD_SHIELD_HP_RATIO * self.max_hp
                    self.consume_shells(XUANWU_SHELL_GUARD_COST, game_state)
                    self.add_true_shield(shield_per * XUANWU_SHELL_GUARD_COST)
                    self.design_shell_guard_cooldown = XUANWU_SHELL_GUARD_COOLDOWN
                    if game_state is not None:
                        spawn_damage_text(game_state, self, 0.0, text="玄甲守", color=XUANWU_SHELL_COLOR)
                    return 0.0
        if self.job_name == "DesignRole88_powder_keg" and any(
            token in str(damage_type) for token in ("fire", "burn", "dragon_breath", "hellcharge")
        ):
            if game_state is not None:
                cast_design_skill(self, game_state, "powder_blast")
            return 0.0
        if self.bloodwraith_shield_hp > 0:
            absorbed = min(self.bloodwraith_shield_hp, damage)
            self.bloodwraith_shield_hp -= absorbed
            damage -= absorbed
            if damage <= 0:
                return 0.0
        if self.true_shield > 0 and not ignore_shields:
            absorbed = min(self.true_shield, damage)
            self.true_shield -= absorbed
            damage -= absorbed
            if damage <= 0:
                return 0.0
        if self.bloodwraith_shield_hp > 0 and not ignore_shields:
            absorbed = min(self.bloodwraith_shield_hp, damage)
            self.bloodwraith_shield_hp -= absorbed
            damage -= absorbed
            if damage <= 0:
                return 0.0
        if self.is_sea_sage() and self.sea_tide_shield_hp > 0 and not ignore_shields:
            absorbed = min(self.sea_tide_shield_hp, damage)
            self.sea_tide_shield_hp -= absorbed
            damage -= absorbed
            if damage <= 0:
                return 0.0
        if self.is_phoenix() and self.design_phoenix_egg_timer > 0 and self.design_phoenix_egg_shield > 0 and not ignore_shields:
            absorbed = min(self.design_phoenix_egg_shield, damage)
            self.design_phoenix_egg_shield -= absorbed
            damage -= absorbed
            if damage <= 0:
                return 0.0
        if self.is_xuanwu() and self.design_xuan_bulwark_shield > 0 and not ignore_shields:
            absorbed = min(self.design_xuan_bulwark_shield, damage)
            self.design_xuan_bulwark_shield -= absorbed
            damage -= absorbed
            if self.design_xuan_bulwark_shield <= 0 and not self.design_xuan_bulwark_broken_triggered:
                self.design_xuan_bulwark_broken_triggered = True
                self.xuanwu_bulwark_burst(game_state)
            if damage <= 0:
                return 0.0
        if self.guard_timer > 0 and not is_true_damage:
            damage *= 1.0 - KNIGHT_DAMAGE_REDUCTION
        if self.gladiator_duel_timer > 0 and not is_true_damage:
            damage *= 1.0 - GLADIATOR_DAMAGE_REDUCTION
        if self.design_damage_reduction > 0 and not is_true_damage:
            damage *= max(0.0, 1.0 - self.design_damage_reduction)
        if self.job_name == "Behemoth" and self.behemoth_stone_stacks > 0 and not is_true_damage:
            damage *= max(0.82, 1.0 - self.behemoth_stone_stacks * BEHEMOTH_STONE_DAMAGE_REDUCTION)
        if self.is_paladin() and self.paladin_holy_stacks > 0 and not is_true_damage:
            damage *= max(0.80, 1.0 - self.paladin_holy_stacks * 0.04)
        if self.is_sea_sage() and not is_true_damage and self.sea_tide_reduction_timers:
            damage *= max(0.0, 1.0 - min(SEA_SAGE_REDUCTION_MAX_STACKS, len(self.sea_tide_reduction_timers)) * SEA_SAGE_REDUCTION_PER_STACK)
        if self.hex_curse_timer > 0:
            damage *= HEX_CURSE_DAMAGE_AMP
        if self.sleep_timer > 0:
            damage *= DESIGN_SLEEP_WAKE_MULTIPLIER
            self.sleep_timer = 0.0
            self.stun_timer = 0.0
        if self.is_sunfire_blademaster() and self.sunfire_damage_reduction_stacks > 0:
            damage *= max(0.0, 1.0 - SUNFIRE_DAMAGE_REDUCTION_PER_STACK * self.sunfire_damage_reduction_stacks)
        if self.job_name == "DesignRole69_ironclad":
            damage = min(damage, self.max_hp * DESIGN_IRONCLAD_HIT_CAP)
        if damage_kind == DAMAGE_KIND_PHYSICAL:
            damage *= self.physical_resistance
            if self.is_windstorm_fox() and self.windstorm_physical_resistance_bonus > 0:
                damage *= max(0.0, 1.0 - self.windstorm_physical_resistance_bonus)
        elif damage_kind == DAMAGE_KIND_SPELL:
            damage *= self.spell_resistance
        if self.is_xuanwu() and self.design_shell_stacks > 0 and not is_true_damage:
            damage *= max(0.0, 1.0 - XUANWU_SHELL_DAMAGE_REDUCTION_PER_STACK * self.design_shell_stacks)
        if source_character is not None and source_character.is_tiger() and self.design_tiger_wound > 0 and not is_true_damage:
            damage *= 1.0 + TIGER_WOUND_DAMAGE_AMP_PER_STACK * min(TIGER_WOUND_MAX, self.design_tiger_wound)
        if self.is_dragon() and not is_true_damage:
            if self.design_dragon_form == "thunder":
                damage *= 1.0 - DRAGON_THUNDER_DAMAGE_REDUCTION
            if self.design_dragon_awe > 0:
                damage *= 1.0 - DRAGON_AWE_RESIST_PER_STACK * self.design_dragon_awe
        if self.is_windstorm_fox() and self.windstorm_qi_stacks >= WINDSTORM_FOX_QI_MAX and not is_true_damage:
            damage *= 1.0 - WINDSTORM_FOX_FULL_QI_DAMAGE_REDUCTION
        if self.job_name == "DesignRole83_aurora" and not is_true_damage:
            if not any(tok in str(damage_type) for tok in ("melee", "swing", "slash", "claw", "punch", "dash", "bash")):
                damage *= DESIGN_AURORA_RESIST
        if source_character is not None and source_character.is_susanoo() and "susanoo" in str(damage_type) and not is_true_damage:
            if self.design_susanoo_prowl > 0:
                damage *= 1.0 + SUSANOO_PROWL_BONUS_PER_STACK * min(SUSANOO_PROWL_MAX, self.design_susanoo_prowl)
            if "arc" not in str(damage_type):
                arc_candidates = [
                    c for c in (game_state["characters"] if game_state is not None else [])
                    if c.alive and c is not self and getattr(c, "owner_id", None) != source_character.owner_id
                ]
                if arc_candidates:
                    arc_target = min(arc_candidates, key=lambda c: (c.pos - self.pos).length_squared())
                    arc_target.take_damage(damage * SUSANOO_ARC_RATIO, source=source_character, damage_type="design_spell_susanoo_arc", game_state=game_state)
        if source_character is not None and source_character.design_meta.get("role_num") == 59 and self.design_ranger_mark > 0 and not is_true_damage:
            damage *= 1.0 + RANGER_MARK_DAMAGE_BONUS * min(RANGER_MARK_MAX, self.design_ranger_mark)
        if source_character is not None and source_character.is_ghost_priest() and self.design_dread > 0 and not is_true_damage:
            damage *= 1.0 + GHOST_DREAD_DAMAGE_BONUS_PER_STACK * min(GHOST_DREAD_MAX, self.design_dread)
        if source_character is not None and source_character.is_abyssal_watcher() and self.design_gaze > 0:
            if is_true_damage:
                damage *= 1.0 + GAZE_TRUE_BONUS_PER_STACK * min(GAZE_MAX, self.design_gaze)
            elif (self.pos - source_character.pos).length_squared() > 1.0:
                damage *= 1.0 + GAZE_MOVE_BONUS_PER_STACK * min(GAZE_MAX, self.design_gaze)
        if self.design_stolen_marks > 0 and not is_true_damage:
            damage *= 1.0 - STOLEN_PASSIVE_DAMAGE_BONUS_PER_STACK * min(STOLEN_MARK_MAX, self.design_stolen_marks)
        if self.job_name == MIND_THIEF_JOB and source_character is not None and int(getattr(source_character, "design_stolen_marks", 0)) > 0 and not is_true_damage:
            damage *= 1.0 - STOLEN_CRIT_REDUCTION * 0.3  # 识破：带窃思的敌人对夺心者伤害降低
        if self.is_equilibrium_arbiter() and damage > 0:
            if damage_kind == DAMAGE_KIND_PHYSICAL:
                self.physical_resistance = max(0.0, self.physical_resistance + EQUILIBRIUM_THRESHOLD_RESIST_PHYS_DELTA)
                self.spell_resistance = max(0.0, self.spell_resistance + EQUILIBRIUM_THRESHOLD_RESIST_SPELL_DELTA)
                spawn_damage_text(game_state, self, 0.0, text=f"{EQUILIBRIUM_THRESHOLD_RESIST_PHYS_DELTA:+.2f}", color=EQUILIBRIUM_PHYSICAL_TEXT_COLOR)
                spawn_damage_text(game_state, self, 0.0, text=f"{EQUILIBRIUM_THRESHOLD_RESIST_SPELL_DELTA:+.2f}", color=EQUILIBRIUM_SPELL_TEXT_COLOR)
            elif damage_kind == DAMAGE_KIND_SPELL:
                self.physical_resistance = max(0.0, self.physical_resistance + EQUILIBRIUM_THRESHOLD_RESIST_SPELL_DELTA)
                self.spell_resistance = max(0.0, self.spell_resistance + EQUILIBRIUM_THRESHOLD_RESIST_PHYS_DELTA)
                spawn_damage_text(game_state, self, 0.0, text=f"{EQUILIBRIUM_THRESHOLD_RESIST_SPELL_DELTA:+.2f}", color=EQUILIBRIUM_PHYSICAL_TEXT_COLOR)
                spawn_damage_text(game_state, self, 0.0, text=f"{EQUILIBRIUM_THRESHOLD_RESIST_PHYS_DELTA:+.2f}", color=EQUILIBRIUM_SPELL_TEXT_COLOR)
        if self.is_windstorm_fox() and damage > 0 and (source_character is None or source_character.owner_id != self.owner_id):
            self.gain_mp(5.0, "windstorm_hit")
        if self.job_name == "Behemoth" and damage > 0:
            self.behemoth_stone_progress += damage
            while self.behemoth_stone_progress >= 20.0 and self.behemoth_stone_stacks < BEHEMOTH_STONE_STACK_MAX:
                self.behemoth_stone_progress -= 20.0
                self.behemoth_stone_stacks += 1
            if self.behemoth_stone_stacks > 0:
                self.behemoth_stone_timer = BEHEMOTH_STONE_DECAY
        if self.job_name == "Berserker":
            self.gain_mp(damage, "damage_taken")
        elif self.config["mp_mode"] == "damage_taken_flat":
            self.gain_mp(self.config["mp_rate"], "damage_taken")
        elif self.config["mp_mode"] == "damage_taken_scaled":
            self.gain_mp(damage * self.config["mp_rate"], "damage_taken_scaled")
        if self.job_name == "DesignRole111_railhog" and damage > 0:
            self.gain_mp(damage * RAIL_TAKEN_MP_RATIO, "rail_taken")
        if self.config["mp_mode"] == "damage_event_any":
            self.gain_mp(self.config["mp_rate"], "damage_event_any")

        damage = max(0.0, damage)
        if self.is_sea_sage() and damage > 0:
            self.gain_mp(3.0, "sea_sage_damage_taken")
            self.sea_tide_damage_bank += damage
            while self.sea_tide_damage_bank >= SEA_SAGE_DAMAGE_BANK_THRESHOLD:
                self.sea_tide_damage_bank -= SEA_SAGE_DAMAGE_BANK_THRESHOLD
                self.spawn_sea_fish(game_state, self.pos)
        if self.is_sunfire_blademaster() and damage > 0 and source_character is not self:
            self.gain_mp(5.0, "sunfire_hit")
        if self.job_name == "Knight" and self.guard_timer > 0:
            self.knight_recorded_damage += damage
        pre_damage_hp = self.hp
        self.damageTaken += damage
        if self.design_corrupted_blood > 0:
            hp_absorb = min(damage, self.hp)
            self.hp -= hp_absorb
            leftover = damage - hp_absorb
            if leftover > 0:
                self.design_corrupted_blood -= leftover / SPARROW_BLOOD_ABSORB_RATIO
                if game_state is not None:
                    spawn_damage_text(game_state, self, 0.0, text=f"腐血-{leftover:.0f}", color=SPARROW_BLOOD_COLOR)
                if self.design_corrupted_blood <= 0:
                    self.design_corrupted_blood = 0.0
        else:
            self.hp -= damage
        handle_equilibrium_thresholds(self, pre_damage_hp, source_character, game_state, ignore_equilibrium_thresholds=ignore_equilibrium_thresholds)
        if self.is_phoenix() and self.design_phoenix_egg_timer > 0:
            if self.design_phoenix_egg_shield <= 0:
                self.hp = 0.0
            elif self.hp <= 0:
                self.hp = 1.0
        elif self.is_phoenix() and self.hp <= 0 and self.design_phoenix_feather >= PHOENIX_EGG_FEATHER_COST:
            self.start_phoenix_egg(game_state)
        if self.is_twin_mirror() and self.hp <= 0:
            self.handle_twin_mirror_lethal()
        self.design_recently_hit = 0.0
        self.design_recent_damage_taken += damage
        if damage > 0 and self.job_name == "DesignRole69_ironclad" and source_character is not None and source_character is not self:
            if any(tok in str(damage_type) for tok in ("melee", "swing", "slash", "claw", "punch", "bash", "thrust")):
                source_character.take_damage(damage * IRONCLAD_THORN_RATIO, source=self, damage_type="true_ironclad_thorn", game_state=game_state)
        self.hit_flash_timer = max(self.hit_flash_timer, HIT_FLASH_DURATION)
        if game_state is not None:
            game_state["damage_texts"].append(
                DamageText(
                    self.pos + pygame.Vector2(0, -self.radius - 10),
                    damage,
                    damage_kind=damage_kind,
                    is_true_damage=is_true_damage,
                    crit=is_true_damage or damage >= DAMAGE_TEXT_CRIT_THRESHOLD,
                )
            )
        if self.hp <= 0 and self.design_corrupted_blood <= 0:
            self.design_corrupted_blood = 0.0
            if game_state is not None:
                for candidate in game_state.get("characters", []):
                    if candidate.design_meta.get("role_num") == 116 and candidate.design_sparrow_host_id == self.id:
                        candidate.design_sparrow_host_id = None
                        candidate.design_sparrow_reattach_timer = SPARROW_REATTACH_DELAY
                    if getattr(candidate, "design_tide_hub_id", None) == self.id and candidate is not self:
                        candidate.design_tide_link_active = False
                        candidate.design_tide_link_timer = 0.0
                        candidate.design_tide_hub_id = None
            if self.job_name == "DesignRole62_lich" and not self.design_has_revived:
                self.design_has_revived = True
                self.hp = max(1.0, self.max_hp * 0.3)
                self.freeze_timer = 3.0
                self.stun_timer = 3.0
                return damage
            if self.job_name == "Bloodwraith" and not self.design_has_revived:
                self.design_has_revived = True
                self.clear_negative_states()
                self.control_timer = 0.0
                self.control_owner_id = None
                self.design_marked = False
                self.design_mark_duration = 0.0
                self.design_mark_owner_id = None
                self.design_link_target_id = None
                self.design_link_timer = 0.0
                self.design_taunt_timer = 0.0
                self.design_taunt_owner_id = None
                self.design_hell_timer = 0.0
                self.design_hell_target = None
                self.design_disarm_source = None
                self.bloodwraith_rage_active = True
                self.bloodwraith_shield_timer = 0.0
                self.bloodwraith_shield_hp = 0.0
                self.hp = self.max_hp
                return damage
            self.hp = 0
            self.alive = False
            if self.is_tiger():
                self.design_tiger_power = 0
            self.clear_weapon()
            if game_state is not None:
                game_state.setdefault("design_death_positions", []).append(pygame.Vector2(self.pos))
                soul_execution = (
                    source_character is not None
                    and source_character.job_name == SOUL_ARBITER_JOB_NAME
                    and str(damage_type) == "true_soul_arbiter_exec"
                )
                particle_color = SOUL_ARBITER_EXECUTION_COLOR if soul_execution else self.color
                particle_count = DEATH_PARTICLE_COUNT * 2 if soul_execution else DEATH_PARTICLE_COUNT
                for _ in range(particle_count):
                    game_state["death_particles"].append(DeathParticle(self.pos, particle_color, dust=soul_execution))
                for character in game_state["characters"]:
                    if character.alive and character is not self:
                        character.on_character_death(self, game_state)
                if source_character is not None and source_character.job_name == SOUL_ARBITER_JOB_NAME:
                    source_character.register_soul_arbiter_kill(self, game_state)
                if source_character is not None and source_character.is_phoenix():
                    source_character.design_phoenix_fall = max(0, source_character.design_phoenix_fall - 1)
                    source_character.refresh_phoenix_max_hp()
                if source_character is not None and source_character.is_xuanwu():
                    source_character.design_shell_kill_count += 1
                if source_character is not None and source_character.is_soul_moth():
                    if source_character.design_soul_moth_form:
                        source_character.design_soul_moth_timer = SOUL_MOTH_MOTH_DURATION
                    else:
                        source_character.design_soul_moth_soul = min(
                            SOUL_MOTH_MOTH_SOUL_LIMIT,
                            source_character.design_soul_moth_soul + 1,
                        )
                        if source_character.design_soul_moth_soul >= SOUL_MOTH_MOTH_SOUL_LIMIT:
                            source_character.enter_soul_moth_form(game_state)
                if source_character is not None and source_character.is_dragon():
                    source_character.design_dragon_awe = min(DRAGON_AWE_MAX, source_character.design_dragon_awe + 1)
                if source_character is not None and source_character.is_abyssal_watcher() and getattr(self, "design_gaze", 0) > 0:
                    source_character.heal(source_character.max_hp * GAZE_KILL_HEAL_RATIO)
                if self.is_soul_casket() and self.design_soul_blade is not None:
                    self.design_soul_blade.alive = False
                    self.design_soul_blade = None
                if self.is_soul_casket() and game_state is not None:
                    for summoned in game_state.get("design_summons", []):
                        if summoned.summon_type == "soul_blade" and summoned.owner_id == self.owner_id:
                            summoned.alive = False
                if source_character is not None and source_character is not self and source_character.alive:
                    source_character.kill_count += 1
                    source_character.kill_streak += 1
                    if source_character.kill_streak in KILLSTREAK_BANNERS:
                        game_state.setdefault("kill_banners", []).append(
                            KillBanner(
                                source_character,
                                KILLSTREAK_BANNERS[source_character.kill_streak],
                            )
                        )
                    buff_level = KILLSTREAK_GAIN_THRESHOLDS.get(source_character.kill_streak)
                    if buff_level is not None:
                        source_character.killstreak_buff_level = max(source_character.killstreak_buff_level, buff_level)
                        source_character.killstreak_buff_timer = KILLSTREAK_GAIN_DURATION
                        heal_ratio = KILLSTREAK_GAIN_HEAL.get(buff_level, 0.0)
                        if heal_ratio > 0:
                            source_character.heal(source_character.max_hp * heal_ratio)
                    if game_state is not None:
                        spawn_attack_impact(
                            game_state,
                            source_character.pos,
                            (255, 224, 120),
                            radius=20,
                            thickness=3,
                            lifetime=0.3,
                            burst_count=10,
                        )
                        kill_sparks = game_state.setdefault("spell_trail_particles", [])
                        for _ in range(5):
                            spark_dir = random_unit_vector() * random.uniform(60.0, 150.0)
                            kill_sparks.append(
                                SpellTrailParticle(
                                    pygame.Vector2(self.pos),
                                    (255, 224, 120) if _ % 2 == 0 else (255, 170, 40),
                                    velocity=spark_dir,
                                    size=2,
                                    lifetime=0.5,
                                )
                            )
                        game_state["shake_timer"] = max(game_state.get("shake_timer", 0.0), 0.1)
                        game_state["shake_magnitude"] = max(game_state.get("shake_magnitude", 0.0), 6.0)
                self.kill_streak = 0
        if damage > 0:
            if count_on_damage_dealt and source_character is not None and source_character.owner_id != self.owner_id:
                source_character.on_damage_dealt(damage, damage_type)
                if source_character.is_tiger() and source_character.design_tiger_prey_id == id(self):
                    source_character.design_tiger_hunt_value = min(
                        TIGER_HUNT_VALUE_MAX,
                        source_character.design_tiger_hunt_value + damage,
                    )
                    source_character.tiger_prey_charge()
                if self.design_link_timer > 0 and self.design_link_target_id is not None and not str(damage_type).startswith("true_design_link"):
                    linked = next((target for target in get_targetables(game_state) if id(target) == self.design_link_target_id), None) if game_state is not None else None
                    if linked is not None and linked.alive:
                        linked.take_damage(damage * DESIGN_ORACLE_LINK_SHARE, source=source_character, damage_type="true_design_link", game_state=game_state)
                if (
                    source_character.job_name == "Bounty Hunter"
                    and self.owner_id == source_character.bounty_target_id
                    and (damage_type.startswith("basic") or damage_type.startswith("weapon_"))
                ):
                    source_character.bounty_coins += 1
                if self.dark_reflect_timer > 0 and not is_true_damage and not damage_type.startswith("dark_reflect"):
                    source_character.take_damage(
                        damage * 0.5,
                        source=self,
                        damage_type="true_dark_reflect",
                        game_state=game_state,
                    )
        if damage > 15 and self.job_name == "DesignRole84_hive_mind" and game_state is not None:
            game_state["design_summons"].append(DesignSummon(self, "larva", self.pos + random_unit_vector() * 12))
        if damage > 0 and self.job_name == "DesignRole72_soul_eater":
            self.max_hp += 2.0
            self.hp = min(self.max_hp, self.hp + 5.0)
        if damage > 0 and self.is_xuanwu():
            self.add_shell(1)
        if self.job_name == "DesignRole74_ghost_capt" and not self.design_low_hp_triggered and self.hp > 0 and self.hp <= self.max_hp * 0.3 and game_state is not None:
            self.design_low_hp_triggered = True
            for _ in range(2):
                game_state["design_summons"].append(DesignSummon(self, "sailor", self.pos + random_unit_vector() * 20))
        return damage

    def get_speed_modifier(self):
        modifier = 1.0
        if self.design_protect_timer > 0:
            modifier *= 1.0 + SQUAD_PROTECT_SPEED
        if self.is_soul_moth() and self.design_soul_moth_form:
            modifier *= 1.0 + SOUL_MOTH_FORM_MOVE_BONUS
        if self.job_name == "Illusionist" and self.illusion_mirror_stacks > 0:
            modifier *= 1.0 + self.illusion_mirror_stacks * ILLUSION_MIRROR_STACK_SPEED_BONUS
        if self.job_name == "Behemoth" and self.behemoth_stone_stacks > 0:
            modifier *= 1.0 + self.behemoth_stone_stacks * BEHEMOTH_STONE_SPEED_BONUS
        if self.job_name == "Toxicologist" and self.toxicologist_corrosion_stacks > 0:
            modifier *= 1.0 + self.toxicologist_corrosion_stacks * TOXICOLOGIST_CORROSION_SPEED_BONUS
        if self.job_name == "Frost Mage" and self.frost_mage_core_stacks > 0:
            modifier *= 1.0 + self.frost_mage_core_stacks * FROST_MAGE_CORE_SPEED_BONUS
        if self.job_name == "Pyro" and self.pyro_ember_stacks > 0:
            modifier *= 1.0 + self.pyro_ember_stacks * PYRO_EMBER_SPEED_BONUS
        if self.is_necromancer() and self.necromancer_bone_stacks > 0:
            modifier *= 1.0 + self.necromancer_bone_stacks * 0.04
        if self.is_paladin() and self.paladin_holy_stacks > 0:
            modifier *= 1.0 + self.paladin_holy_stacks * 0.03
        if self.is_ninja() and self.ninja_shadow_stacks > 0:
            modifier *= 1.0 + self.ninja_shadow_stacks * 0.04
        if self.is_bomber() and self.bomber_fuse_stacks > 0:
            modifier *= 1.0 + self.bomber_fuse_stacks * 0.03
        if self.is_vampire():
            modifier *= 1.0 + self.get_vampire_blood_stacks() * 0.03
        if self.slow_timer > 0:
            modifier *= max(0.15, 1.0 - self.slow_factor)
        if self.hex_curse_timer > 0:
            modifier *= 0.5
        if self.berserker_spin_timer > 0:
            modifier *= 1.35
        if self.paladin_buff_timer > 0:
            modifier *= 0.9
        if self.ninja_dash_timer > 0:
            modifier *= 1.7
        if self.melee_gap_dash_timer > 0:
            modifier *= MELEE_DASH_SPEED_MULTIPLIER
        if self.swordmaster_haste_timer > 0:
            modifier *= 1.12
        if self.windrunner_storm_timer > 0:
            modifier *= 1.5
        if self.bard_song_timer > 0:
            modifier *= BARD_SONG_SPEED_MULTIPLIER
        if self.is_sunfire_blademaster() and self.sunfire_fire_timer > 0:
            modifier *= 1.3
        if self.is_windstorm_fox() and self.windstorm_qi_stacks > 0:
            modifier *= 1.0 + self.windstorm_qi_stacks * WINDSTORM_FOX_MOVE_BONUS_PER_QI
        if self.job_name == "Bloodwraith" and self.bloodwraith_rage_active:
            modifier *= BLOODWRAITH_RAGE_SPEED_MULTIPLIER
        if self.job_name == "DesignRole91_phantom_lancer" and self.phantom_lancer_throw_speed_timer > 0:
            modifier *= 1.0 + PHANTOM_LANCER_THROW_SPEED_BONUS
        if self.job_name == SOUL_ARBITER_JOB_NAME and self.soul_arbiter_hunt_timer > 0:
            modifier *= 1.0 + SOUL_ARBITER_HUNT_SPEED_BONUS
        if self.is_tiger():
            modifier *= 1.0 + TIGER_POWER_MOVE_SPEED_PER_STACK * self.design_tiger_power
            if self.design_tiger_blood_speed_timer > 0:
                modifier *= 1.0 + TIGER_WOUND_TRAIL_SPEED_BONUS
        if self.is_dragon():
            modifier *= 1.0 + DRAGON_AWE_MOVE_SPEED_PER_STACK * self.design_dragon_awe
        if self.job_name == "Assassin" and self.assassin_haste_timer > 0:
            modifier *= 1.3
        if self.design_ranger_speed_timer > 0:
            modifier *= 1.0 + RANGER_DASH_SPEED_BONUS
        if self.gravekeeper_rot_stacks > 0:
            modifier *= 1.0 - GRAVEKEEPER_ROT_SLOW_PER_STACK * min(GRAVEKEEPER_ROT_MAX, self.gravekeeper_rot_stacks)
        if self.design_dread > 0:
            modifier *= 1.0 - GHOST_DREAD_SLOW_PER_STACK * min(GHOST_DREAD_MAX, self.design_dread)
        if self.design_spell_haste_timer > 0:
            modifier *= 1.0 + FLAME_DANCER_HASTE_BONUS
        modifier *= max(0.6, 1.0 + self.design_bonus_speed)
        return modifier

    def get_target(self, game_state):
        forced_owner_id = getattr(self, "design_taunt_owner_id", None)
        if self.design_taunt_timer > 0 and forced_owner_id is not None:
            forced = [
                target
                for target in get_targetables(game_state)
                if target.alive and target.owner_id == forced_owner_id and target is not self
            ]
            if forced:
                return min(forced, key=lambda target: (target.pos - self.pos).length_squared())
        if self.job_name == "Bounty Hunter" and self.bounty_target_id is not None:
            for target in get_targetables(game_state):
                if target.alive and target.owner_id == self.bounty_target_id and target.owner_id != self.owner_id:
                    return target
        blocked_owner_id = None
        if self.control_timer > 0:
            blocked_owner_id = self.control_owner_id
        if self.charm_timer > 0:
            return None
        if self.design_fear_timer > 0:
            return None
        if self.job_name == SOUL_ARBITER_JOB_NAME and self.soul_arbiter_hunt_timer > 0:
            chained_ids = set(self.soul_arbiter_chains.keys())
            unchained = [
                target
                for target in get_targetables(game_state)
                if target.owner_id != self.owner_id
                and target is not self
                and (blocked_owner_id is None or target.owner_id != blocked_owner_id)
                and id(target) not in chained_ids
            ]
            if unchained:
                return min(unchained, key=lambda target: (target.pos - self.pos).length_squared())
        nearest = None
        nearest_score = float("inf")
        for target in get_targetables(game_state):
            if target.owner_id == self.owner_id or target is self:
                continue
            if blocked_owner_id is not None and target.owner_id == blocked_owner_id:
                continue
            score = (target.pos - self.pos).length_squared()
            if getattr(target, "is_decoy", False):
                score *= 0.72
            if score < nearest_score:
                nearest_score = score
                nearest = target
        return nearest

    def get_nearest_weapon_orb(self, game_state):
        available_orbs = [orb for orb in game_state["weapon_orbs"] if orb.alive]
        if not available_orbs:
            return None
        if self.job_name == "DesignRole91_phantom_lancer" and self.phantom_lancer_spear_hunt_timer > 0:
            spear_orbs = [orb for orb in available_orbs if orb.weapon_id == "ColdSpear"]
            if spear_orbs:
                return min(spear_orbs, key=lambda orb: (orb.pos - self.pos).length_squared())
        return min(available_orbs, key=lambda orb: (orb.pos - self.pos).length_squared())

    def get_current_attack_range(self):
        if self.held_weapon is None:
            if self.druid_form_timer > 0:
                return 52.0
            if self.is_dragon() and self.design_dragon_form == "wood":
                return DRAGON_WOOD_RANGE_BASE * (1.0 + DRAGON_WOOD_RANGE_BONUS)
            return self.base_attack_range
        return WEAPON_DEFS[self.held_weapon["weapon_id"]]["range"]

    def fire_basic_attack(self, target, game_state):
        if self.is_design_role():
            fire_design_basic_attack(self, target, game_state)
            return
        if self.get_current_basic_attack_type() == "melee":
            self.fire_melee_attack(target, game_state)
        else:
            self.fire_ranged_basic_attack(target, game_state)

    def fire_melee_attack(self, target, game_state):
        direction = target.pos - self.pos
        if direction.length_squared() == 0:
            direction = random_unit_vector()
        else:
            direction = direction.normalize()
        swing_start = self.pos + direction * (self.radius + 2)
        swing_end = self.pos + direction * (self.get_current_attack_range() + 10)
        game_state["melee_effects"].append(MeleeSwingEffect(swing_start, swing_end, self.get_visual_color()))
        damage = self.get_current_basic_damage() * self.get_target_attack_bonus(target)
        if self.job_name == "Smasher":
            apply_aoe_damage(
                self.pos + direction * 14,
                self.config.get("melee_aoe_radius", 0.0),
                damage,
                self.owner_id,
                game_state,
                source=self,
                damage_type="basic_melee",
            )
        else:
            target.take_damage(
                damage,
                source=self,
                damage_type="basic_melee",
                game_state=game_state,
            )
        if self.is_ninja() and self.ninja_shadow_stacks > 0:
            target.apply_blind(1.2 + 0.2 * self.ninja_shadow_stacks)
            self.ninja_shadow_stacks = 0
            self.ninja_shadow_timer = 0.0
        spawn_attack_impact(game_state, target.pos, self.get_visual_color(), radius=max(11, int(self.radius * 1.1)), damage=damage)
        stun_duration = self.get_current_melee_stun_duration()
        if stun_duration > 0:
            target.apply_stun(stun_duration)
        cooldown = self.get_basic_attack_cooldown()
        self.attack_cooldown = cooldown
        self.on_attack_committed()

    def fire_ranged_basic_attack(self, target, game_state):
        targets = self.get_ranged_attack_targets(target, game_state)
        if self.succubus_barrage_timer > 0:
            direction = target.pos - self.pos
            if direction.length_squared() == 0:
                return
            direction = direction.normalize()
            damage = self.get_current_basic_damage() * self.get_target_attack_bonus(target)
            muzzle_pos = self.pos + direction * (self.radius + 6)
            for spread_index in range(SUCCUBUS_BARRAGE_PELLETS):
                offset = 0 if SUCCUBUS_BARRAGE_PELLETS == 1 else ((spread_index / (SUCCUBUS_BARRAGE_PELLETS - 1)) - 0.5) * SUCCUBUS_BARRAGE_SPREAD
                shot_dir = direction.rotate(offset)
                velocity = shot_dir * self.base_projectile_speed
                start = self.pos + shot_dir * (self.radius + 6)
                game_state["projectiles"].append(
                    Projectile(
                        start,
                        velocity,
                        self,
                        damage * SUCCUBUS_BARRAGE_DAMAGE_MULTIPLIER,
                        self.color,
                        source_kind="basic",
                        max_range=self.get_current_attack_range(),
                    )
                )
            spawn_attack_impact(game_state, muzzle_pos, self.color, radius=10, thickness=2, burst_count=5)
        else:
            for chosen in targets:
                direction = chosen.pos - self.pos
                if direction.length_squared() == 0:
                    continue
                damage = self.get_current_basic_damage() * self.get_target_attack_bonus(chosen)
                projectile_speed = self.base_projectile_speed
                if self.job_name == "Mage":
                    projectile_speed *= 1.0 + self.mage_arcane_stacks * MAGE_ARCANE_PROJECTILE_BONUS
                velocity = direction.normalize() * projectile_speed
                start = self.pos + velocity.normalize() * (self.radius + 6)
                projectile_on_hit = None
                if self.job_name == "Bard":

                    def bard_on_hit(projectile, target, dealt, hit_game_state):
                        if dealt > 0 and random.random() < BARD_BASIC_SLOW_CHANCE and hasattr(target, "apply_slow"):
                            target.apply_slow(BARD_BASIC_SLOW_FACTOR, BARD_BASIC_SLOW_DURATION)

                    projectile_on_hit = bard_on_hit
                game_state["projectiles"].append(
                    Projectile(
                        start,
                        velocity,
                        self,
                        damage,
                        self.color,
                        source_kind="basic",
                        max_range=self.get_current_attack_range(),
                        on_hit=projectile_on_hit,
                    )
                )
                spawn_attack_impact(game_state, start, self.color, radius=10, thickness=2, burst_count=4)
                if self.is_ninja() and self.ninja_shadow_stacks > 0 and chosen is target:
                    chosen.apply_blind(1.2 + 0.2 * self.ninja_shadow_stacks)
                    self.ninja_shadow_stacks = 0
                    self.ninja_shadow_timer = 0.0
        cooldown = self.get_basic_attack_cooldown()
        self.attack_cooldown = cooldown
        self.on_attack_committed()

    def fire_equipped_weapon(self, target, game_state):
        if self.held_weapon is None:
            return

        weapon_def = WEAPON_DEFS[self.held_weapon["weapon_id"]]
        if weapon_def.get("special_kind") == "spear_thrust":
            direction = target.pos - self.pos
            if direction.length_squared() == 0:
                return
            direction = direction.normalize()
            start_pos = pygame.Vector2(self.pos)
            dash_distance = min(42.0, max(18.0, (target.pos - self.pos).length() - (target.radius + self.radius + 2.0)))
            self.pos += direction * dash_distance
            self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
            self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
            self.update_rect()
            game_state["melee_effects"].append(MeleeSwingEffect(start_pos, self.pos + direction * (target.radius + 10), self.get_visual_color()))
            game_state["beam_events"].append(BeamEvent(start_pos, self.pos, (86, 224, 232)))
            damage = self.get_current_basic_damage() * 2.0 * self.get_target_attack_bonus(target)
            dealt = target.take_damage(
                damage,
                source=self,
                damage_type="basic_melee",
                game_state=game_state,
            )
            if dealt > 0:
                spawn_attack_impact(game_state, target.pos, (86, 224, 232), radius=12, thickness=2, burst_count=6)
                self.heal(40.0)
                self.phantom_lancer_throw_speed_timer = PHANTOM_LANCER_THROW_SPEED_DURATION
                self.phantom_lancer_spear_hunt_timer = max(self.phantom_lancer_spear_hunt_timer, PHANTOM_LANCER_SPEAR_HUNT_DURATION)
                if self.phantom_lancer_spear_charges <= 1:
                    self.clear_weapon()
                if self.phantom_lancer_spear_charges > 0:
                    self.phantom_lancer_spear_charges -= 1
                if random.random() < 0.5:
                    cast_design_skill(self, game_state, "phantom_lancer_throw")
        elif self.held_weapon["weapon_id"] == "Staff":
            targets = [candidate for candidate in get_targetables(game_state) if candidate.owner_id != self.owner_id]
            if not targets:
                return
            for _ in range(weapon_def["burst_count"]):
                chosen = random.choice(targets)
                direction = chosen.pos - self.pos
                if direction.length_squared() == 0:
                    direction = random_unit_vector()
                velocity = direction.normalize() * weapon_def["projectile_speed"]
                start = self.pos + velocity.normalize() * (self.radius + 6)
                game_state["projectiles"].append(
                    Projectile(
                        start,
                        velocity,
                        self,
                        weapon_def["damage"] * self.get_target_attack_bonus(chosen),
                        weapon_def["projectile_color"],
                        source_kind="weapon_staff",
                        homing_strength=weapon_def["homing"],
                        homing_target_id=id(chosen),
                        max_range=None,
                    )
                )
            trigger_screen_shake(game_state, SCREEN_SHAKE_STAFF)
        else:
            direction = target.pos - self.pos
            if direction.length_squared() == 0:
                return
            direction = direction.normalize().rotate(random.uniform(-weapon_def["spread_deg"], weapon_def["spread_deg"]))
            velocity = direction * weapon_def["projectile_speed"]
            start = self.pos + direction * (self.radius + 6)
            game_state["projectiles"].append(
                Projectile(
                    start,
                    velocity,
                    self,
                    weapon_def["damage"] * self.get_target_attack_bonus(target),
                    weapon_def["projectile_color"],
                    source_kind=f"weapon_{self.held_weapon['weapon_id'].lower()}",
                    stun_duration=weapon_def["stun_duration"],
                    max_range=weapon_def["range"],
                )
            )

        if not self.held_weapon.get("infinite_ammo"):
            self.held_weapon["ammo"] -= 1
        cooldown = self.get_weapon_attack_cooldown(weapon_def["fire_interval"])
        self.attack_cooldown = cooldown
        self.held_weapon["cooldown"] = cooldown
        self.on_attack_committed()
        if self.held_weapon["ammo"] <= 0:
            self.clear_weapon()

    def cast_skill(self, game_state):
        if not self.alive or self.clone_mode is not None:
            return
        if self.design_banished:
            return

        skill_id = self.config["skill_id"]
        if self.is_design_role():
            if self.silence_timer > 0:
                return
            if self.stun_timer > 0 and self.design_meta.get("skill_token") not in {"phase_shift", "sunfire_kagura"}:
                return
            if cast_design_skill(self, game_state):
                self.mp = 0.0
                add_design_effect(
                    game_state,
                    DesignEffect(
                        "skill_precast",
                        self,
                        pygame.Vector2(self.pos),
                        radius=self.radius + 10,
                        lifetime=SKILL_PRECAST_DURATION,
                    ),
                )
            return
        if self.stun_timer > 0 and skill_id != "time_rewind":
            return

        self.mp = 0.0
        if skill_id == "knight_guard":
            self.shield_timer = KNIGHT_SHIELD_DURATION
            self.guard_timer = KNIGHT_GUARD_DURATION
            self.knight_recorded_damage = 0.0
            self.knight_backlash_timer = 0.0
            self.knight_backlash_tick_accumulator = 0.0
            self.knight_backlash_tick_damage = 0.0
        elif skill_id == "mage_nova":
            arcane_stacks = self.mage_arcane_stacks
            projectile_count = 8 + arcane_stacks
            projectile_damage = MAGE_NOVA_DAMAGE * (1.0 + arcane_stacks * MAGE_ARCANE_DAMAGE_BONUS)
            projectile_speed = 250.0 * (1.0 + arcane_stacks * MAGE_ARCANE_PROJECTILE_BONUS)
            for index in range(projectile_count):
                angle = math.tau * index / projectile_count
                direction = pygame.Vector2(math.cos(angle), math.sin(angle))
                game_state["projectiles"].append(
                    Projectile(
                        self.pos + direction * (self.radius + 6),
                        direction * projectile_speed,
                        self,
                        projectile_damage,
                        (205, 165, 255),
                        source_kind="mage_nova",
                        pierce=True,
                        slow_amount=SLOW_FACTOR,
                        slow_duration=SLOW_DURATION,
                    )
                )
            if arcane_stacks >= MAGE_ARCANE_MAX_STACKS:
                add_design_effect(
                    game_state,
                    DesignEffect(
                        "arcane_field",
                        self,
                        self.pos,
                        radius=MAGE_ARCANE_FIELD_RADIUS,
                        lifetime=MAGE_ARCANE_FIELD_DURATION,
                        damage=MAGE_ARCANE_FIELD_DAMAGE,
                        slow=MAGE_ARCANE_FIELD_SLOW,
                        slow_duration=MAGE_ARCANE_FIELD_TICK,
                        tick=MAGE_ARCANE_FIELD_TICK,
                    ),
                )
                self.mage_arcane_field_timer = MAGE_ARCANE_FIELD_DURATION
                self.mage_arcane_field_tick_accumulator = 0.0
            self.mage_arcane_stacks = 0
            self.mage_burn_timer = max(self.mage_burn_timer, MAGE_SELF_DOT_DURATION)
        elif skill_id == "assassin_blink":
            self.assassin_bonus_recast_available = True

            def blink_once():
                target = select_lowest_hp_enemy(self, game_state["characters"])
                if target is None:
                    return False
                offset = target.pos - self.pos
                direction = offset.normalize() if offset.length_squared() > 0 else random_unit_vector()
                destination = target.pos - direction * (target.radius + self.radius + 4)
                self.pos.x = clamp(destination.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.pos.y = clamp(destination.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                self.update_rect()
                backstab_damage = self.get_current_basic_damage() * 2.5
                if target.hp <= target.max_hp * 0.4:
                    backstab_damage *= 1.5
                target.take_damage(backstab_damage, source=self, damage_type="assassin_blink", game_state=game_state)
                self.assassin_haste_timer = 1.0
                return not target.alive

            if blink_once() and self.assassin_bonus_recast_available:
                self.assassin_bonus_recast_available = False
                blink_once()
        elif skill_id == "berserker_spin":
            self.berserker_spin_timer = BERSERKER_SPIN_DURATION
            self.berserker_tick_accumulator = 0.0
            self.berserker_spin_visual_timer = 0.0
            # D: 起手一次性圈闪（快速展开到范围边界）
            spawn_attack_impact(game_state, self.pos, (255, 90, 90), radius=BERSERKER_SPIN_RADIUS, thickness=3, lifetime=0.22, burst_count=14)
        elif skill_id == "sniper_beam":
            target = select_farthest_enemy(self, game_state["characters"])
            if target is not None:
                direction = target.pos - self.pos
                if direction.length_squared() == 0:
                    direction = pygame.Vector2(1, 0)
                self.sniper_beam_direction = direction.normalize()
                self.sniper_charge_timer = SNIPER_CHARGE_TIME
                self.sniper_stationary_ready = False
                self.sniper_stationary_timer = 0.0
        elif skill_id == "necro_summon":
            angles = (-0.8, 0.8)
            if self.necromancer_bone_stacks >= 5:
                angles = (-0.8, 0.0, 0.8)
            for angle in angles:
                direction = self.recent_move_dir.rotate_rad(angle)
                spawn_pos = self.pos + direction * 18
                game_state["summons"].append(Summon(self, spawn_pos, summon_type="skeleton"))
        elif skill_id == "paladin_heal":
            self.heal(self.max_hp * 0.20)
            if self.paladin_holy_stacks > 0:
                self.add_true_shield(20.0 * self.paladin_holy_stacks)
            self.paladin_buff_timer = PALADIN_BUFF_DURATION
            self.paladin_tick_accumulator = 0.0
        elif skill_id == "ninja_decoy":
            game_state["decoys"].append(Decoy(self, self.pos))
            dash_dir = -self.recent_move_dir if self.recent_move_dir.length_squared() > 0 else -self.wander_dir
            if dash_dir.length_squared() == 0:
                dash_dir = random_unit_vector()
            dash_dir = dash_dir.normalize()
            self.pos += dash_dir * 70
            self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
            self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
            self.vel += dash_dir * 90
            self.ninja_dash_timer = 0.45
            self.update_rect()
        elif skill_id == "bomber_mines":
            basis = self.recent_move_dir if self.recent_move_dir.length_squared() > 0 else self.wander_dir
            if basis.length_squared() == 0:
                basis = random_unit_vector()
            basis = basis.normalize()
            mine_count = 3 + (1 if self.bomber_fuse_stacks >= 4 else 0)
            for step in range(mine_count):
                placement = self.pos - basis * (step * 24)
                placement.x = clamp(placement.x, ARENA_RECT.left + 10, ARENA_RECT.right - 10)
                placement.y = clamp(placement.y, ARENA_RECT.top + 10, ARENA_RECT.bottom - 10)
                game_state["mines"].append(Mine(self, placement))
        elif skill_id == "vampire_drain":
            target = select_nearest_enemy(self, game_state["characters"])
            if target is not None:
                self.vampire_channel_target_id = target.owner_id
                self.vampire_channel_timer = VAMPIRE_CHANNEL_DURATION
                self.vampire_regen_timer = VAMPIRE_REGEN_DURATION
                self.heal(10)
        elif skill_id == "illusion_twins":
            clone_count = 2 + (1 if self.illusion_mirror_stacks >= ILLUSION_MIRROR_STACK_MAX else 0)
            clone_duration = ILLUSION_CLONE_DURATION + self.illusion_mirror_stacks * 0.5
            spread_angles = (-0.65, 0.65, 1.15)
            for angle in spread_angles[:clone_count]:
                direction = self.recent_move_dir.rotate_rad(angle) if self.recent_move_dir.length_squared() > 0 else random_unit_vector()
                direction = direction.normalize() if direction.length_squared() > 0 else random_unit_vector()
                spawn_pos = self.pos + direction * 24
                spawn_pos.x = clamp(spawn_pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                spawn_pos.y = clamp(spawn_pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                game_state["characters"].append(
                    Character(
                        self.job_name,
                        self.id,
                        spawn_pos,
                        owner_id=self.owner_id,
                        is_main_character=False,
                        clone_config={"mode": "illusion", "duration": clone_duration},
                    )
                )
        elif skill_id == "behemoth_stomp":
            stomp_damage = BEHEMOTH_STOMP_DAMAGE * (1.0 + self.behemoth_stone_stacks * BEHEMOTH_STONE_ATTACK_BONUS)
            for target in get_targetables(game_state):
                if not target.alive or target.owner_id == self.owner_id:
                    continue
                if (target.pos - self.pos).length() <= BEHEMOTH_STOMP_RADIUS + getattr(target, "radius", 0):
                    target.take_damage(stomp_damage, source=self, damage_type="behemoth_stomp", game_state=game_state)
                    if hasattr(target, "apply_stun"):
                        target.apply_stun(BEHEMOTH_STOMP_STUN)
            self.add_true_shield(BEHEMOTH_TRUE_SHIELD + self.behemoth_stone_stacks * 20.0)
        elif skill_id == "toxic_nova":
            game_state["poison_fields"].append(PoisonField(self, self.pos))
        elif skill_id == "absolute_zero":
            target = select_nearest_enemy(self, game_state["characters"])
            if target is not None:
                game_state["frost_comets"].append(FrostComet(self, target))
        elif skill_id == "dragon_breath":
            self.pyro_breath_timer = PYRO_BREATH_DURATION + self.pyro_ember_stacks * PYRO_EMBER_DURATION_BONUS
            self.pyro_breath_tick_accumulator = 0.0
        elif skill_id == "time_rewind":
            self.clear_negative_states()
            self.rewind_to_snapshot(game_state["elapsed_time"])
        elif skill_id == "qi_wave":
            direction = self.recent_move_dir if self.recent_move_dir.length_squared() > 0 else random_unit_vector()
            direction = direction.normalize()
            beam_start = self.pos
            beam_end = self.pos + direction * 180
            game_state["beam_events"].append(BeamEvent(beam_start, beam_end, (255, 230, 120)))
            for target in get_targetables(game_state):
                if not target.alive or target.owner_id == self.owner_id:
                    continue
                if distance_point_to_segment(target.pos, beam_start, beam_end) <= target.radius + 12:
                    target.take_damage(MONK_WAVE_DAMAGE, source=self, damage_type="qi_wave", game_state=game_state)
                    if hasattr(target, "apply_stun"):
                        target.apply_stun(MONK_WAVE_STUN)
                    if hasattr(target, "apply_knockback"):
                        target.apply_knockback(direction, MONK_WAVE_KNOCKBACK)
        elif skill_id == "missile_barrage":
            enemies = [enemy for enemy in get_targetables(game_state) if enemy.alive and enemy.owner_id != self.owner_id]
            if enemies:
                target_pool = random.sample(enemies, min(MECH_MISSILE_TARGETS, len(enemies)))
                for _ in range(MECH_MISSILE_COUNT):
                    chosen = random.choice(target_pool)
                    direction = chosen.pos - self.pos
                    if direction.length_squared() == 0:
                        direction = random_unit_vector()
                    velocity = direction.normalize() * 210.0
                    start = self.pos + velocity.normalize() * (self.radius + 8)
                    game_state["projectiles"].append(
                        Projectile(
                            start,
                            velocity,
                            self,
                            0.0,
                            (184, 194, 208),
                            source_kind="missile_barrage",
                            homing_strength=7.0,
                            homing_target_id=id(chosen),
                            max_range=WEAPON_RANGE_INFINITE,
                            explosion_radius=MECH_MISSILE_BLAST_RADIUS,
                            explosion_damage=MECH_MISSILE_DAMAGE,
                            explosion_damage_type="missile_barrage",
                        )
                    )
        elif skill_id == "bear_form":
            if self.druid_form_timer <= 0 and self.druid_bonus_hp_active <= 0:
                self.max_hp += DRUID_FORM_BONUS_HP
                self.druid_bonus_hp_active = DRUID_FORM_BONUS_HP
            self.druid_form_timer = DRUID_FORM_DURATION
            self.radius = self.base_radius * 1.5
            self.heal(DRUID_FORM_HEAL)
            self.update_rect()
        elif skill_id == "chain_lightning":
            current = select_nearest_enemy(self, game_state["characters"])
            hit_ids = set()
            last_pos = pygame.Vector2(self.pos)
            bounce_count = 0
            while current is not None and bounce_count < ELECTRO_CHAIN_BOUNCES:
                current.take_damage(ELECTRO_CHAIN_DAMAGE, source=self, damage_type="chain_lightning", game_state=game_state)
                if hasattr(current, "apply_doom"):
                    current.apply_doom(ELECTRO_DOOM_DURATION)
                game_state["beam_events"].append(BeamEvent(last_pos, current.pos, (255, 232, 90)))
                hit_ids.add(current.owner_id)
                last_pos = pygame.Vector2(current.pos)
                bounce_count += 1
                next_targets = [
                    target
                    for target in get_targetables(game_state)
                    if target.alive and target.owner_id != self.owner_id and target.owner_id not in hit_ids
                ]
                if not next_targets:
                    break
                current = min(next_targets, key=lambda target: (target.pos - last_pos).length_squared())
        elif skill_id == "mind_control":
            target = select_nearest_enemy(self, game_state["characters"])
            if target is not None:
                target.apply_control(self.owner_id, PUPPETEER_CONTROL_DURATION)
        elif skill_id == "ground_slam":
            target = select_nearest_enemy(self, game_state["characters"])
            leap_pos = pygame.Vector2(target.pos if target is not None else self.pos + self.recent_move_dir * 80)
            leap_pos.x = clamp(leap_pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
            leap_pos.y = clamp(leap_pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
            self.smasher_leap_target = leap_pos
            self.smasher_leap_timer = SMASHER_LEAP_DURATION
            self.vel *= 0.0
        elif skill_id == "charm_kiss":
            target = select_nearest_enemy(self, game_state["characters"])
            if target is not None:
                direction = target.pos - self.pos
                if direction.length_squared() == 0:
                    direction = random_unit_vector()
                velocity = direction.normalize() * SUCCUBUS_KISS_SPEED
                start = self.pos + velocity.normalize() * (self.radius + 6)
                game_state["projectiles"].append(
                    Projectile(
                        start,
                        velocity,
                        self,
                        10.0,
                        (255, 122, 210),
                        source_kind="charm_kiss",
                        charm_duration=SUCCUBUS_CHARM_DURATION,
                        max_range=self.get_current_attack_range(),
                    )
                )
                self.succubus_barrage_timer = SUCCUBUS_CHARM_DURATION
        elif skill_id == "bullet_rain":
            self.vel *= 0.0
            for _ in range(GUNSLINGER_BARRAGE_COUNT):
                angle = random.uniform(0.0, math.tau)
                direction = pygame.Vector2(math.cos(angle), math.sin(angle))
                velocity = direction * 300.0
                start = self.pos + direction * (self.radius + 6)
                game_state["projectiles"].append(
                    Projectile(
                        start,
                        velocity,
                        self,
                        4.0,
                        self.color,
                        source_kind="bullet_rain",
                        max_range=250.0,
                    )
                )
        elif skill_id == "energy_bulwark":
            facing = self.recent_move_dir if self.recent_move_dir.length_squared() > 0 else self.wander_dir
            if facing.length_squared() == 0:
                facing = pygame.Vector2(1, 0)
            game_state["shield_walls"].append(ShieldWall(self, facing))
        elif skill_id == "bladestorm_dash":
            enemies = [enemy for enemy in get_targetables(game_state) if enemy.alive and enemy.owner_id != self.owner_id]
            enemies.sort(key=lambda enemy: (enemy.pos - self.pos).length_squared())
            self.swordmaster_invuln_timer = SWORDMASTER_INVULN_DURATION
            if game_state is not None:
                spawn_damage_text(game_state, self, 0.0, text="无敌斩", color=(255, 255, 255))
            for slash_index in range(SWORDMASTER_SLASH_COUNT):
                if not enemies:
                    break
                target = enemies[slash_index % len(enemies)]
                blink_direction = random_unit_vector()
                blink_distance = target.radius + self.radius + 2
                destination = target.pos + blink_direction * blink_distance
                self.pos.x = clamp(destination.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.pos.y = clamp(destination.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                self.recent_move_dir = (target.pos - self.pos).normalize() if (target.pos - self.pos).length_squared() > 0 else blink_direction
                self.update_rect()
                game_state["melee_effects"].append(MeleeSwingEffect(self.pos, target.pos, self.get_visual_color()))
                game_state["beam_events"].append(BeamEvent(self.pos, target.pos, (255, 255, 255)))
                spawn_attack_impact(game_state, target.pos, (255, 255, 255), radius=14, thickness=2, burst_count=8)
                slash_damage = self.get_current_basic_damage() * SWORDMASTER_SLASH_DAMAGE_MULTIPLIER
                target.take_damage(slash_damage, source=self, damage_type="bladestorm_dash", game_state=game_state)
            self.swordmaster_haste_timer = SWORDMASTER_HASTE_DURATION
        elif skill_id == "hurricane_storm":
            self.windrunner_storm_timer = WINDRUNNER_STORM_DURATION
        elif skill_id == "doom_curse":
            target = select_highest_hp_enemy(self, game_state["characters"])
            if target is not None:
                target.hex_curse_timer = max(target.hex_curse_timer, HEX_CURSE_DURATION)
                target.apply_slow(0.5, HEX_CURSE_DURATION)
        elif skill_id == "chaos_law":
            roll = random.uniform(0.0, 100.0)
            if roll < 20.0:
                self.heal(self.max_hp * 0.25)
            elif roll < 25.0:
                target = select_random_targetable(self, game_state)
                if target is not None:
                    target.take_damage(240.0, source=self, damage_type="true_chaos_burst", game_state=game_state)
            elif roll < 45.0:
                target = select_nearest_enemy(self, game_state["characters"])
                if target is not None:
                    target.take_damage(180.0, source=self, damage_type="chaos_bolt", game_state=game_state)
                    if hasattr(target, "apply_stun"):
                        target.apply_stun(1.5)
            elif roll < 65.0:
                for target in get_targetables(game_state):
                    if target.alive and target.owner_id != self.owner_id and hasattr(target, "apply_stun"):
                        target.apply_stun(1.5)
            else:
                target = select_nearest_enemy(self, game_state["characters"])
                if target is not None:
                    for index in range(10):
                        angle_offset = random.uniform(-18.0, 18.0)
                        direction = (target.pos - self.pos)
                        if direction.length_squared() == 0:
                            direction = random_unit_vector()
                        direction = direction.normalize().rotate(angle_offset)
                        velocity = direction * 290.0
                        start = self.pos + direction * (self.radius + 6)
                        game_state["projectiles"].append(
                            Projectile(
                                start,
                                velocity,
                                self,
                                22.0,
                                (218, 120, 255),
                                source_kind="chaos_law",
                                homing_strength=5.2,
                                homing_target_id=id(target),
                                max_range=WEAPON_RANGE_INFINITE,
                            )
                        )
        elif skill_id == "ultimate_bounty":
            enemies = [
                enemy
                for enemy in game_state["characters"]
                if enemy.alive and enemy.owner_id != self.owner_id and getattr(enemy, "is_main_character", True)
            ]
            if enemies:
                self.bounty_target_id = random.choice(enemies).owner_id
        elif skill_id == "stone_spikes":
            enemies = [enemy for enemy in game_state["characters"] if enemy.alive and enemy.owner_id != self.owner_id]
            if enemies:
                for target in random.sample(enemies, min(3, len(enemies))):
                    target.take_damage(GEOMANCER_SPIKE_DAMAGE, source=self, damage_type="stone_spikes", game_state=game_state)
                    target.apply_root(GEOMANCER_ROOT_DURATION)
                    game_state["beam_events"].append(BeamEvent(target.pos + pygame.Vector2(0, 24), target.pos, (168, 120, 80)))
        elif skill_id == "battle_song":
            for target in game_state["characters"]:
                if target.alive and target.owner_id == self.owner_id and (target.pos - self.pos).length() <= BARD_SONG_RADIUS + target.radius:
                    target.bard_song_timer = max(target.bard_song_timer, BARD_SONG_DURATION)
        elif skill_id == "lightning_totem":
            for totem in game_state.get("totems", []):
                if totem.alive and totem.owner_id == self.owner_id:
                    totem.alive = False
            game_state["totems"].append(Totem(self, self.pos))
        elif skill_id == "fatal_duel":
            target = select_nearest_enemy(self, game_state["characters"])
            if target is not None:
                direction = target.pos - self.pos
                if direction.length_squared() == 0:
                    direction = self.recent_move_dir if self.recent_move_dir.length_squared() > 0 else random_unit_vector()
                direction = direction.normalize()
                destination = self.pos + direction * (self.radius + target.radius + 4)
                target.pos.x = clamp(destination.x, ARENA_RECT.left + target.radius, ARENA_RECT.right - target.radius)
                target.pos.y = clamp(destination.y, ARENA_RECT.top + target.radius, ARENA_RECT.bottom - target.radius)
                target.vel *= 0.0
                target.apply_root(GLADIATOR_DUEL_DURATION)
                target.duel_haste_timer = max(target.duel_haste_timer, GLADIATOR_DUEL_DURATION)
                target.update_rect()
                self.gladiator_duel_timer = GLADIATOR_DUEL_DURATION
                game_state["beam_events"].append(BeamEvent(self.pos, target.pos, (212, 170, 116)))
        elif skill_id == "soul_siphon":
            hp_cost = min(WARLOCK_SKILL_HP_COST, max(0.0, self.hp - 1.0))
            if hp_cost > 0:
                self.take_damage(hp_cost, source=self, damage_type="true_soul_siphon_cost", game_state=game_state)
            target = select_nearest_enemy(self, game_state["characters"])
            direction = self.recent_move_dir if self.recent_move_dir.length_squared() > 0 else pygame.Vector2(1, 0)
            if target is not None and (target.pos - self.pos).length_squared() > 0:
                direction = (target.pos - self.pos).normalize()
            else:
                direction = direction.normalize()
            beam_start = self.pos
            beam_end = self.pos + direction * WARLOCK_BEAM_RANGE
            game_state["beam_events"].append(BeamEvent(beam_start, beam_end, (96, 214, 136)))
            hits = 0
            for victim in get_targetables(game_state):
                if not victim.alive or victim.owner_id == self.owner_id:
                    continue
                if distance_point_to_segment(victim.pos, beam_start, beam_end) <= victim.radius + WARLOCK_BEAM_WIDTH:
                    dealt = victim.take_damage(WARLOCK_BEAM_DAMAGE, source=self, damage_type="soul_siphon", game_state=game_state)
                    if dealt > 0:
                        hits += 1
            for _ in range(hits):
                self.heal(max(0.0, self.max_hp - self.hp) * 0.2)
        elif skill_id == "overclock_weapon":
            weapon_id = random.choice(WEAPON_ORB_POOL)
            weapon_def = WEAPON_DEFS[weapon_id]
            self.held_weapon = {
                "weapon_id": weapon_id,
                "ammo": weapon_def["ammo"],
                "cooldown": 0.0,
                "overclocked": True,
                "infinite_ammo": True,
            }
            self.tinkerer_overclock_timer = TINKERER_OVERCLOCK_DURATION
        elif skill_id == "skyfall_strike":
            enemies = [enemy for enemy in get_targetables(game_state) if enemy.alive and enemy.owner_id != self.owner_id]
            if enemies:
                best_target = max(
                    enemies,
                    key=lambda enemy: (
                        sum(1 for other in enemies if (other.pos - enemy.pos).length() <= VALKYRIE_SLAM_RADIUS),
                        -sum((other.pos - enemy.pos).length() for other in enemies),
                    ),
                )
                self.valkyrie_dive_target = pygame.Vector2(best_target.pos)
            else:
                self.valkyrie_dive_target = pygame.Vector2(self.pos)
            self.valkyrie_dive_timer = VALKYRIE_DIVE_DURATION
            self.vel *= 0.0
        elif skill_id == "revenge_thorns":
            self.dark_reflect_timer = DARK_REFLECT_DURATION
        elif skill_id == "telekinetic_redirect":
            candidates = [enemy for enemy in game_state["characters"] if enemy.alive and enemy.owner_id != self.owner_id]
            if candidates:
                target = random.choice(candidates)
                for projectile in game_state["projectiles"]:
                    if projectile.alive and projectile.owner_id != target.owner_id:
                        projectile.homing_target_id = id(target)
                        projectile.homing_strength = max(projectile.homing_strength, PSIONIC_REDIRECT_HOMING)
                game_state["beam_events"].append(BeamEvent(self.pos, target.pos, (255, 126, 228)))

    def apply_passive_mp(self, dt, game_state):
        if self.clone_mode is not None:
            return
        if self.config["mp_mode"] == "passive":
            self.gain_mp(self.config["mp_rate"] * dt, "passive")
        elif self.config["mp_mode"] == "damage_taken_scaled":
            pass
        elif self.config["mp_mode"] == "damage_dealt_scaled":
            pass
        elif self.config["mp_mode"] == "distance_scaled":
            pass
        elif self.config["mp_mode"] == "stationary":
            if (self.pos - self.position_lock).length() <= 4.0:
                self.stationary_timer += dt
                while self.stationary_timer >= 1.0:
                    self.stationary_timer -= 1.0
                    self.gain_mp(self.config["mp_rate"], "stationary")
            else:
                self.position_lock = pygame.Vector2(self.pos)
                self.stationary_timer = 0.0
        elif self.config["mp_mode"] == "timed_random":
            self.design_charge_random_timer -= dt
            if self.design_charge_random_timer <= 0:
                low, high = self.config.get("mp_random_range", (5.0, 25.0))
                self.gain_mp(random.uniform(low, high), "timed_random")
                self.design_charge_random_timer = self.config.get("mp_interval", 3.0)
        elif self.config["mp_mode"] == "death_count":
            pass
        elif self.config["mp_mode"] == "damage_event_any":
            pass
        elif self.config["mp_mode"] == "weapon_pickup":
            pass
        elif self.config["mp_mode"] == "timed":
            self.vampire_charge_timer -= dt
            if self.vampire_charge_timer <= 0:
                self.gain_mp(VAMPIRE_CHARGE_AMOUNT, "timed")
                self.vampire_charge_timer += VAMPIRE_CHARGE_INTERVAL
        elif self.config["mp_mode"] == "chaos_random":
            self.chaos_charge_timer -= dt
            if self.chaos_charge_timer <= 0:
                self.gain_mp(random.uniform(10.0, 25.0), "chaos_random")
                self.chaos_charge_timer += CHAOS_CHARGE_INTERVAL
        elif self.config["mp_mode"] == "health_sacrifice_timed":
            self.warlock_charge_timer -= dt
            if self.warlock_charge_timer <= 0:
                self.take_damage(WARLOCK_CHARGE_COST, source=self, damage_type="true_warlock_charge", game_state=game_state)
                if self.alive:
                    self.gain_mp(WARLOCK_CHARGE_MP, "health_sacrifice_timed")
                self.warlock_charge_timer += WARLOCK_CHARGE_INTERVAL

    def process_effects(self, dt, game_state):
        self.apply_passive_mp(dt, game_state)
        self._design_cached_characters = game_state["characters"]
        self.design_recently_hit += dt
        self.design_shadow_idle += dt
        self.design_recent_damage_taken = 0.0
        if self.design_confuse_timer > 0:
            self.design_confuse_timer = max(0.0, self.design_confuse_timer - dt)
        if self.design_execute_buff_timer > 0:
            self.design_execute_buff_timer = max(0.0, self.design_execute_buff_timer - dt)
        if self.design_banner_zone_timer > 0:
            self.design_banner_zone_timer = max(0.0, self.design_banner_zone_timer - dt)
        if self.design_banner_lifesteal_timer > 0:
            self.design_banner_lifesteal_timer = max(0.0, self.design_banner_lifesteal_timer - dt)
        if self.design_banner_respawn_timer > 0:
            self.design_banner_respawn_timer = max(0.0, self.design_banner_respawn_timer - dt)
        if self.design_potion_haste_timer > 0:
            self.design_potion_haste_timer = max(0.0, self.design_potion_haste_timer - dt)
        if self.design_wild_brew_timer > 0:
            self.design_wild_brew_timer = max(0.0, self.design_wild_brew_timer - dt)
        if self.design_protect_timer > 0:
            self.design_protect_timer = max(0.0, self.design_protect_timer - dt)
        if self.design_sparrow_fury_timer > 0:
            self.design_sparrow_fury_timer = max(0.0, self.design_sparrow_fury_timer - dt)
        if self.design_tide_link_active:
            self.design_tide_link_timer = max(0.0, self.design_tide_link_timer - dt)
            self.design_tide_heal_tick += dt
            while self.design_tide_heal_tick >= TIDE_HEAL_INTERVAL:
                self.design_tide_heal_tick -= TIDE_HEAL_INTERVAL
                self.heal(self.max_hp * TIDE_HEAL_RATIO)
            if self.design_tide_link_timer <= 0:
                self.design_tide_link_active = False
                self.design_tide_link_timer = 0.0
                self.design_tide_hub_id = None
        else:
            self.design_tide_heal_tick = 0.0
        if self.design_blood_feast_timer > 0:
            self.design_blood_feast_timer = max(0.0, self.design_blood_feast_timer - dt)
        if self.design_blood_curse_timer > 0:
            self.design_blood_curse_timer = max(0.0, self.design_blood_curse_timer - dt)
            if self.design_blood_curse_timer <= 0:
                self.design_blood_curse = 0
        if self.design_kenshi_mark_timer > 0:
            self.design_kenshi_mark_timer = max(0.0, self.design_kenshi_mark_timer - dt)
            if self.design_kenshi_mark_timer <= 0:
                self.design_kenshi_mark = 0
        if self.design_kenshi_counter_cd > 0:
            self.design_kenshi_counter_cd = max(0.0, self.design_kenshi_counter_cd - dt)
        if self.design_squad_mark_timer > 0:
            self.design_squad_mark_timer = max(0.0, self.design_squad_mark_timer - dt)
            if self.design_squad_mark_timer <= 0:
                self.design_squad_mark_owner_id = None
        if self.design_squad_primary_timer > 0:
            self.design_squad_primary_timer = max(0.0, self.design_squad_primary_timer - dt)
            if self.design_squad_primary_timer <= 0:
                self.design_squad_primary_owner_id = None
        if self.design_banished:
            self.design_banish_tick_timer -= dt
            while self.design_banish_tick_timer <= 0:
                self.design_banish_tick_timer += BANISH_TICK_INTERVAL
                self.take_damage(self.max_hp * BANISH_TICK_RATIO, source=None, damage_type="true_design_banish", game_state=game_state)
            self.design_banish_roll_timer -= dt
            while self.design_banish_roll_timer <= 0:
                self.design_banish_roll_timer += BANISH_ROLL_INTERVAL
                roll = random.randint(BANISH_ROLL_MIN, BANISH_ROLL_MAX)
                self.design_banish_points += roll
                self.design_banish_pulse = 0.35
                if game_state is not None:
                    spawn_damage_text(game_state, self, 0.0, text=f"判定{roll}/累计{self.design_banish_points}", color=BANISH_COLOR)
                if self.design_banish_points >= BANISH_POINTS_THRESHOLD:
                    self.design_banished = False
                    self.design_banish_points = 0
                    if game_state is not None:
                        spawn_damage_text(game_state, self, 0.0, text="放逐解除", color=(190, 215, 255))
            if self.design_banish_pulse > 0:
                self.design_banish_pulse = max(0.0, self.design_banish_pulse - dt)
            self.design_banish_dust_timer -= dt
            if self.design_banish_dust_timer <= 0:
                self.design_banish_dust_timer = 0.4
                if game_state is not None:
                    dust_velocity = pygame.Vector2(random.uniform(-6.0, 6.0), random.uniform(-26.0, -14.0))
                    game_state.setdefault("spell_trail_particles", []).append(
                        SpellTrailParticle(
                            pygame.Vector2(self.pos.x, self.pos.y + self.radius + 2),
                            BANISH_COLOR,
                            velocity=dust_velocity,
                            size=2,
                            lifetime=0.5,
                        )
                    )
        if self.job_name == BANNER_JOB_NAME:
            my_banners = [ban for ban in game_state.get("banners", []) if ban.owner_id == self.owner_id and ban.alive]
            if not my_banners and self.design_banner_respawn_timer <= 0:
                game_state.setdefault("banners", []).append(Banner(self, pygame.Vector2(self.pos)))
        elif self.job_name == ALCHEMIST_JOB_NAME:
            self.design_potion_cooldown_timer -= dt
            while self.design_potion_cooldown_timer <= 0:
                self.design_potion_cooldown_timer += POTION_INTERVAL
                self.throw_potion_to_nearest_ally(game_state)
        self.update_sparrow_host(dt, game_state)
        if self.is_soul_moth() and self.design_soul_moth_form:
            self.design_soul_moth_timer = max(0.0, self.design_soul_moth_timer - dt)
            if self.design_soul_moth_timer <= 0:
                self.exit_soul_moth_form()
        if self.job_name == "DesignRole69_ironclad" and self.design_recently_hit >= 5.0:
            self.heal(self.max_hp * IRONCLAD_IDLE_REGEN_RATIO * dt)
        if self.is_twin_mirror():
            self.design_misc_timer += dt
        if self.illusion_mirror_timer > 0:
            self.illusion_mirror_timer = max(0.0, self.illusion_mirror_timer - dt)
            if self.illusion_mirror_timer == 0:
                self.illusion_mirror_stacks = 0
                self.illusion_mirror_progress = 0.0
        if self.behemoth_stone_timer > 0:
            self.behemoth_stone_timer = max(0.0, self.behemoth_stone_timer - dt)
            if self.behemoth_stone_timer == 0:
                self.behemoth_stone_stacks = 0
                self.behemoth_stone_progress = 0.0
        if self.toxicologist_corrosion_timer > 0:
            self.toxicologist_corrosion_timer = max(0.0, self.toxicologist_corrosion_timer - dt)
            if self.toxicologist_corrosion_timer == 0:
                self.toxicologist_corrosion_stacks = 0
                self.toxicologist_corrosion_progress = 0.0
        if self.frost_mage_core_timer > 0:
            self.frost_mage_core_timer = max(0.0, self.frost_mage_core_timer - dt)
            if self.frost_mage_core_timer == 0:
                self.frost_mage_core_stacks = 0
                self.frost_mage_core_progress = 0.0
        if self.pyro_ember_timer > 0:
            self.pyro_ember_timer = max(0.0, self.pyro_ember_timer - dt)
            if self.pyro_ember_timer == 0:
                self.pyro_ember_stacks = 0
                self.pyro_ember_progress = 0.0
        if self.job_name == "Time Walker":
            self.time_rewind_snapshot_timer += dt
            if self.time_rewind_snapshot_timer >= TIME_WALKER_SNAPSHOT_INTERVAL:
                self.time_rewind_snapshot_timer = 0.0
                self.record_rewind_snapshot(game_state["elapsed_time"])

        if self.slow_timer > 0:
            self.slow_timer = max(0.0, self.slow_timer - dt)
            if self.slow_timer == 0:
                self.slow_factor = 0.0

        if self.control_timer > 0:
            self.control_timer = max(0.0, self.control_timer - dt)
            if self.control_timer == 0:
                self.control_owner_id = None
        if self.charm_timer > 0:
            self.charm_timer = max(0.0, self.charm_timer - dt)
            if self.charm_timer == 0:
                self.charm_owner_id = None
        if self.disarm_timer > 0:
            self.disarm_timer = max(0.0, self.disarm_timer - dt)
        if self.silence_timer > 0:
            self.silence_timer = max(0.0, self.silence_timer - dt)
        if self.blind_timer > 0:
            self.blind_timer = max(0.0, self.blind_timer - dt)
        if self.sleep_timer > 0:
            self.sleep_timer = max(0.0, self.sleep_timer - dt)
        if self.stun_timer > 0:
            self.stun_timer = max(0.0, self.stun_timer - dt)
        if self.freeze_timer > 0:
            self.freeze_timer = max(0.0, self.freeze_timer - dt)
        if self.root_timer > 0:
            self.root_timer = max(0.0, self.root_timer - dt)
        if self.design_untargetable_timer > 0:
            self.design_untargetable_timer = max(0.0, self.design_untargetable_timer - dt)
        if self.control_immunity_timer > 0:
            self.control_immunity_timer = max(0.0, self.control_immunity_timer - dt)
        if self.equilibrium_mark_timer > 0:
            self.equilibrium_mark_timer = max(0.0, self.equilibrium_mark_timer - dt)
        if self.design_mark_duration > 0:
            self.design_mark_duration = max(0.0, self.design_mark_duration - dt)
            if self.design_mark_duration == 0:
                self.design_marked = False
        if self.gravekeeper_rot_timer > 0:
            self.gravekeeper_rot_timer = max(0.0, self.gravekeeper_rot_timer - dt)
            if self.gravekeeper_rot_timer == 0:
                self.gravekeeper_rot_stacks = 0
        if self.design_dread_timer > 0:
            self.design_dread_timer = max(0.0, self.design_dread_timer - dt)
            if self.design_dread_timer == 0:
                self.design_dread = 0
        if self.design_ember_timer > 0:
            self.design_ember_timer = max(0.0, self.design_ember_timer - dt)
            if self.design_ember_timer == 0:
                self.design_ember = 0
        if self.design_gaze_timer > 0:
            self.design_gaze_timer = max(0.0, self.design_gaze_timer - dt)
            if self.design_gaze_timer == 0:
                self.design_gaze = 0
        if self.design_fear_timer > 0:
            self.design_fear_timer = max(0.0, self.design_fear_timer - dt)
            if self.design_fear_timer == 0:
                self.design_fear_source_id = None
        if self.design_spell_haste_timer > 0:
            self.design_spell_haste_timer = max(0.0, self.design_spell_haste_timer - dt)
        if self.design_wolf_cd_timer > 0:
            self.design_wolf_cd_timer = max(0.0, self.design_wolf_cd_timer - dt)
        if self.design_link_timer > 0:
            self.design_link_timer = max(0.0, self.design_link_timer - dt)
            if self.design_link_timer == 0:
                self.design_link_target_id = None
        if self.necromancer_bone_timer > 0:
            self.necromancer_bone_timer = max(0.0, self.necromancer_bone_timer - dt)
            if self.necromancer_bone_timer == 0:
                self.necromancer_bone_stacks = 0
                self.necromancer_bone_progress = 0.0
        if self.paladin_holy_timer > 0:
            self.paladin_holy_timer = max(0.0, self.paladin_holy_timer - dt)
            if self.paladin_holy_timer == 0:
                self.paladin_holy_stacks = 0
                self.paladin_holy_progress = 0.0
        if self.ninja_shadow_timer > 0:
            self.ninja_shadow_timer = max(0.0, self.ninja_shadow_timer - dt)
            if self.ninja_shadow_timer == 0:
                self.ninja_shadow_stacks = 0
                self.ninja_shadow_progress = 0.0
        if self.bomber_fuse_timer > 0:
            self.bomber_fuse_timer = max(0.0, self.bomber_fuse_timer - dt)
            if self.bomber_fuse_timer == 0:
                self.bomber_fuse_stacks = 0
                self.bomber_fuse_progress = 0.0
        if self.design_taunt_timer > 0:
            self.design_taunt_timer = max(0.0, self.design_taunt_timer - dt)
            if self.design_taunt_timer == 0:
                self.design_taunt_owner_id = None
        if self.design_fortress_timer > 0:
            self.design_fortress_timer = max(0.0, self.design_fortress_timer - dt)
            if self.design_fortress_timer == 0:
                self.design_damage_reduction = 0.0
        if self.sunfire_fire_timer > 0:
            self.sunfire_fire_timer = max(0.0, self.sunfire_fire_timer - dt)
        if self.sunfire_invuln_timer > 0:
            self.sunfire_invuln_timer = max(0.0, self.sunfire_invuln_timer - dt)
        if self.sunfire_evasion_timer > 0:
            self.sunfire_evasion_timer = max(0.0, self.sunfire_evasion_timer - dt)
        if self.equilibrium_resistance_penalty_timer > 0:
            self.equilibrium_resistance_penalty_timer = max(0.0, self.equilibrium_resistance_penalty_timer - dt)
            if self.equilibrium_resistance_penalty_timer == 0 and self.equilibrium_resistance_penalty > 0:
                self.physical_resistance += self.equilibrium_resistance_penalty
                self.spell_resistance += self.equilibrium_resistance_penalty
                self.equilibrium_resistance_penalty = 0.0
        if self.is_sea_sage():
            self.sea_tide_pick_timer += dt
            while self.sea_tide_pick_timer >= SEA_SAGE_FISH_AUTO_INTERVAL:
                self.sea_tide_pick_timer -= SEA_SAGE_FISH_AUTO_INTERVAL
                fishes = self.get_sea_fish_effects(game_state)
                if fishes:
                    self.consume_sea_fish(game_state, fishes[0])
            if self.sea_tide_shield_timer > 0:
                self.sea_tide_shield_timer = max(0.0, self.sea_tide_shield_timer - dt)
                if self.sea_tide_shield_timer == 0:
                    self.sea_tide_shield_hp = 0.0
            if self.sea_tide_reduction_timers:
                updated = []
                for timer in self.sea_tide_reduction_timers:
                    timer -= dt
                    if timer > 0:
                        updated.append(timer)
                self.sea_tide_reduction_timers = updated
        if self.killstreak_buff_timer > 0:
            self.killstreak_buff_timer = max(0.0, self.killstreak_buff_timer - dt)
            if self.killstreak_buff_timer <= 0:
                self.killstreak_buff_level = 0
        if self.is_windstorm_fox():
            self.windstorm_idle_timer += dt
            if self.windstorm_physical_resistance_timer > 0:
                self.windstorm_physical_resistance_timer = max(0.0, self.windstorm_physical_resistance_timer - dt)
                if self.windstorm_physical_resistance_timer <= 0:
                    self.windstorm_physical_resistance_bonus = 0.0
            if self.windstorm_qi_stacks > 0:
                if self.windstorm_qi_stacks >= WINDSTORM_FOX_QI_MAX:
                    self.windstorm_decay_timer = 0.0
                    self.windstorm_idle_timer = 0.0
                elif self.windstorm_idle_timer >= WINDSTORM_FOX_IDLE_DECAY_DELAY:
                    self.windstorm_decay_timer += dt
                    while self.windstorm_decay_timer >= WINDSTORM_FOX_IDLE_DECAY_INTERVAL and self.windstorm_qi_stacks > 0:
                        self.windstorm_decay_timer -= WINDSTORM_FOX_IDLE_DECAY_INTERVAL
                        self.windstorm_qi_stacks -= 1
                else:
                    self.windstorm_decay_timer = 0.0
            else:
                self.windstorm_decay_timer = 0.0
        if self.design_aurora_burn > 0:
            self.design_aurora_burn_timer += dt
            while self.design_aurora_burn_timer >= AURORA_BURN_TICK:
                self.design_aurora_burn_timer -= AURORA_BURN_TICK
                self.design_aurora_burn -= 1
                if self.alive:
                    self.take_damage(AURORA_BURN_DAMAGE, source=self.design_aurora_burn_source, damage_type="design_spell_aurora_tick", game_state=game_state)
                    self.apply_blind(AURORA_BURN_DURATION)
        if self.assassin_haste_timer > 0:
            self.assassin_haste_timer = max(0.0, self.assassin_haste_timer - dt)
        if self.design_ranger_speed_timer > 0:
            self.design_ranger_speed_timer = max(0.0, self.design_ranger_speed_timer - dt)
        if self.design_ranger_lock_timer > 0:
            self.design_ranger_lock_timer = max(0.0, self.design_ranger_lock_timer - dt)
            if self.design_ranger_lock_timer <= 0:
                self.design_ranger_lock_target_id = None
        if self.doom_timer > 0:
            self.doom_timer = max(0.0, self.doom_timer - dt)
            self.take_damage(ELECTRO_DOOM_DPS * dt, source=self, damage_type="true_doom", game_state=game_state)
            if self.hp > 0 and self.hp <= self.max_hp * ELECTRO_DOOM_EXECUTE_RATIO:
                self.take_damage(self.hp + 1.0, source=self, damage_type="true_doom_execute", game_state=game_state)
        if self.hit_flash_timer > 0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        if self.clone_expire_timer > 0:
            self.clone_expire_timer = max(0.0, self.clone_expire_timer - dt)
            if self.clone_expire_timer == 0:
                self.alive = False
                return
        if self.poison_stacks > 0:
            self.take_damage(self.poison_stacks * POISON_STACK_DAMAGE * dt, source=self, damage_type="true_poison_stack", game_state=game_state)
            self.poison_decay_accumulator += dt
            while self.poison_decay_accumulator >= POISON_STACK_DECAY and self.poison_stacks > 0:
                self.poison_decay_accumulator -= POISON_STACK_DECAY
                self.poison_stacks -= 1
        else:
            self.poison_decay_accumulator = 0.0
        if self.toxicologist_corrosion_stacks > 0:
            self.toxicologist_corrosion_timer = max(self.toxicologist_corrosion_timer, TOXICOLOGIST_CORROSION_DURATION)
        if self.hell_burn_timers:
            updated = []
            for timer in self.hell_burn_timers:
                timer -= dt
                if timer > 0:
                    updated.append(timer)
            self.hell_burn_timers = updated
            if self.hell_burn_timers:
                burn_damage = self.max_hp * HELLBRINGER_BURN_DAMAGE_PER_STACK * len(self.hell_burn_timers) * dt
                self.take_damage(
                    burn_damage,
                    source=self.hell_burn_source if self.hell_burn_source is not None else self,
                    damage_type="true_design_hell_burn",
                    game_state=game_state,
                    ignore_shields=True,
                )
            else:
                self.hell_burn_source = None
        if self.design_poison_erosion > 0:
            self.spell_resistance = max(0.0, self.base_spell_resistance + self.design_poison_erosion * 0.02)
        else:
            self.spell_resistance = self.base_spell_resistance
        if self.bleed_stacks > 0:
            self.take_damage(self.bleed_stacks * DESIGN_BLEED_DAMAGE * dt, source=self, damage_type="true_design_bleed", game_state=game_state)
            updated = []
            for timer in self.bleed_decay_timers:
                timer -= dt
                if timer > 0:
                    updated.append(timer)
            self.bleed_decay_timers = updated
            self.bleed_stacks = len(updated)
        if self.cold_stacks > 0:
            self.cold_decay_timer -= dt
            if self.cold_decay_timer <= 0:
                self.cold_stacks = max(0, self.cold_stacks - 1)
                self.cold_decay_timer = 10.0 if self.cold_stacks > 0 else 0.0
        if self.job_name == "DesignRole70_raincaller" and self.design_recently_hit >= 3.0:
            self.heal(2.0 * dt)
        if self.job_name == "DesignRole76_qi_cultivator" and self.design_recently_hit >= 3.0:
            self.heal(2.0 * dt)
        if self.job_name == "DesignRole81_architect":
            self.design_construct_timer -= dt
            if self.design_construct_timer <= 0:
                self.design_construct_timer += DESIGN_CONSTRUCT_INTERVAL
                add_design_effect(game_state, DesignEffect("construct", self, random_spawn_point(ARENA_RECT, 20.0), radius=DESIGN_CONSTRUCT_RADIUS, lifetime=999.0))
        if self.job_name == "DesignRole70_raincaller":
            allies = [character for character in game_state["characters"] if character.alive and character.owner_id == self.owner_id]
            if allies:
                ally = min(allies, key=lambda candidate: (candidate.pos - self.pos).length_squared())
                ally.clear_negative_states()
                self.clear_negative_states()
        if self.job_name == "DesignRole73_illuminator":
            for enemy in get_targetables(game_state):
                if enemy.alive and enemy.owner_id != self.owner_id:
                    offset = self.pos - enemy.pos
                    if offset.length_squared() > 0 and getattr(enemy, "vel", pygame.Vector2()).length_squared() > 0:
                        if enemy.vel.normalize().dot(offset.normalize()) > 0.35:
                            enemy.apply_slow(0.2, 0.2)
        if self.job_name == "Sniper":
            if (self.pos - self.position_lock).length() <= 4.0:
                self.sniper_stationary_timer = min(SNIPER_STATIONARY_READY_TIME, self.sniper_stationary_timer + dt)
                if self.sniper_stationary_timer >= SNIPER_STATIONARY_READY_TIME:
                    self.sniper_stationary_ready = True
            else:
                self.position_lock = pygame.Vector2(self.pos)
                self.sniper_stationary_timer = 0.0
                self.sniper_stationary_ready = False

        if self.shield_timer > 0:
            self.shield_timer = max(0.0, self.shield_timer - dt)
        if self.guard_timer > 0:
            previous_guard_timer = self.guard_timer
            self.guard_timer = max(0.0, self.guard_timer - dt)
            self.heal(self.max_hp * KNIGHT_GUARD_HEAL_RATE * dt)
            if previous_guard_timer > 0 and self.guard_timer == 0:
                self.knight_backlash_timer = KNIGHT_BACKLASH_DURATION
                self.knight_backlash_tick_accumulator = 0.0
                total_backlash = self.knight_recorded_damage * KNIGHT_BACKLASH_DAMAGE_FACTOR
                self.knight_backlash_tick_damage = total_backlash / max(1.0, KNIGHT_BACKLASH_DURATION / KNIGHT_BACKLASH_INTERVAL)
        if self.knight_backlash_timer > 0:
            self.knight_backlash_timer = max(0.0, self.knight_backlash_timer - dt)
            self.knight_backlash_tick_accumulator += dt
            while self.knight_backlash_tick_accumulator >= KNIGHT_BACKLASH_INTERVAL:
                self.knight_backlash_tick_accumulator -= KNIGHT_BACKLASH_INTERVAL
                if self.alive:
                    self.take_damage(
                        self.knight_backlash_tick_damage,
                        source=self,
                        damage_type="knight_backlash",
                        game_state=game_state,
                    )

        if self.mage_burn_timer > 0:
            self.mage_burn_timer = max(0.0, self.mage_burn_timer - dt)
            burn_rate = self.max_hp * MAGE_SELF_DOT_PORTION / MAGE_SELF_DOT_DURATION
            self.hp = max(0.0, self.hp - burn_rate * dt)
            if self.hp == 0:
                self.alive = False
                self.clear_weapon()

        if self.berserker_spin_timer > 0:
            self.berserker_spin_timer = max(0.0, self.berserker_spin_timer - dt)
            self.berserker_spin_visual_timer += dt
            self.berserker_tick_accumulator += dt
            while self.berserker_tick_accumulator >= BERSERKER_SPIN_INTERVAL:
                self.berserker_tick_accumulator -= BERSERKER_SPIN_INTERVAL
                hits = apply_aoe_damage(
                    self.pos,
                    BERSERKER_SPIN_RADIUS,
                    BERSERKER_SPIN_DAMAGE,
                    self.owner_id,
                    game_state,
                    source=self,
                    damage_type="berserker_spin",
                )
                if hits > 0:
                    self.heal(BERSERKER_SPIN_HEAL * hits)
                # A: 圈内受击敌人各自爆点（视觉：全圈同时挨打，而非向外扩散）
                for target in get_targetables(game_state):
                    if target.alive and target.owner_id != self.owner_id:
                        if (target.pos - self.pos).length() <= BERSERKER_SPIN_RADIUS + getattr(target, "radius", 0):
                            spawn_attack_impact(game_state, target.pos, (255, 110, 90), radius=9, thickness=2, burst_count=5)

        if self.sniper_charge_timer > 0:
            self.sniper_charge_timer = max(0.0, self.sniper_charge_timer - dt)
            if self.sniper_charge_timer == 0:
                beam_start = self.pos
                beam_end = self.pos + self.sniper_beam_direction * 1200
                for target in get_targetables(game_state):
                    if not target.alive or target.owner_id == self.owner_id:
                        continue
                    if distance_point_to_segment(target.pos, beam_start, beam_end) <= target.radius + 10:
                        target.take_damage(SNIPER_BEAM_DAMAGE, source=self, damage_type="design_spell_sniper_beam", game_state=game_state)
                game_state["beam_events"].append(BeamEvent(beam_start, beam_end, (130, 255, 160)))
                trigger_screen_shake(game_state, SCREEN_SHAKE_SNIPER)

        if self.paladin_buff_timer > 0:
            self.paladin_buff_timer = max(0.0, self.paladin_buff_timer - dt)
            self.paladin_tick_accumulator += dt
            while self.paladin_tick_accumulator >= PALADIN_HEAL_TICK:
                self.paladin_tick_accumulator -= PALADIN_HEAL_TICK
                self.heal(1)

        if self.vampire_channel_timer > 0:
            self.vampire_channel_timer = max(0.0, self.vampire_channel_timer - dt)
            target = next(
                (
                    character
                    for character in game_state["characters"]
                    if character.alive and character.owner_id == self.vampire_channel_target_id
                ),
                None,
            )
            if target is not None:
                damage_rate = VAMPIRE_CHANNEL_DAMAGE / VAMPIRE_CHANNEL_DURATION
                target.take_damage(damage_rate * dt, source=self, damage_type="vampire_drain", game_state=game_state)
            else:
                self.vampire_channel_timer = 0.0

        if self.vampire_regen_timer > 0:
            self.vampire_regen_timer = max(0.0, self.vampire_regen_timer - dt)
            self.heal((VAMPIRE_REGEN_TOTAL / VAMPIRE_REGEN_DURATION) * dt)
        if self.succubus_barrage_timer > 0:
            self.succubus_barrage_timer = max(0.0, self.succubus_barrage_timer - dt)
        if self.bard_song_timer > 0:
            self.bard_song_timer = max(0.0, self.bard_song_timer - dt)
            self.hp = max(0.0, self.hp - self.max_hp * BARD_SONG_SELF_DRAIN * dt)
            if self.hp == 0:
                self.alive = False
                self.clear_weapon()
        if self.pyro_breath_timer > 0:
            self.pyro_breath_timer = max(0.0, self.pyro_breath_timer - dt)
            self.pyro_breath_tick_accumulator += dt
            while self.pyro_breath_tick_accumulator >= PYRO_BREATH_INTERVAL:
                self.pyro_breath_tick_accumulator -= PYRO_BREATH_INTERVAL
                facing = self.recent_move_dir if self.recent_move_dir.length_squared() > 0 else self.wander_dir
                if facing.length_squared() == 0:
                    facing = pygame.Vector2(1, 0)
                facing = facing.normalize()
                for target in get_targetables(game_state):
                    if not target.alive or target.owner_id == self.owner_id:
                        continue
                    offset = target.pos - self.pos
                    distance = offset.length()
                    if distance <= PYRO_BREATH_RANGE + target.radius and distance > 0:
                        direction = offset.normalize()
                        angle = math.degrees(math.acos(clamp(facing.dot(direction), -1.0, 1.0)))
                        if angle <= PYRO_BREATH_HALF_ANGLE:
                            breath_damage = PYRO_BREATH_DAMAGE * (1.0 + self.pyro_ember_stacks * 0.08)
                            target.take_damage(breath_damage, source=self, damage_type="dragon_breath", game_state=game_state)
                            if hasattr(target, "apply_hell_burn"):
                                target.apply_hell_burn(1, duration=2.0 + self.pyro_ember_stacks * 0.2, source=self)
                            if hasattr(target, "apply_slow"):
                                target.apply_slow(0.08 + self.pyro_ember_stacks * PYRO_EMBER_CHILL_BONUS * 0.1, 0.5)
        if self.druid_form_timer > 0:
            self.druid_form_timer = max(0.0, self.druid_form_timer - dt)
            self.radius = self.base_radius * 1.5
            if self.druid_form_timer == 0:
                self.radius = self.base_radius
                if self.druid_bonus_hp_active > 0:
                    self.max_hp -= self.druid_bonus_hp_active
                    self.druid_bonus_hp_active = 0.0
                    self.hp = min(self.hp, self.max_hp)
                self.update_rect()
        if self.smasher_leap_timer > 0:
            self.smasher_leap_timer = max(0.0, self.smasher_leap_timer - dt)
            if self.smasher_leap_timer == 0 and self.smasher_leap_target is not None:
                self.pos = pygame.Vector2(self.smasher_leap_target)
                self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                self.update_rect()
                for target in get_targetables(game_state):
                    if not target.alive or target.owner_id == self.owner_id:
                        continue
                    if (target.pos - self.pos).length() <= SMASHER_SLAM_RADIUS + getattr(target, "radius", 0):
                        target.take_damage(SMASHER_SLAM_DAMAGE, source=self, damage_type="ground_slam", game_state=game_state)
                        if hasattr(target, "apply_slow"):
                            target.apply_slow(0.8, 3.0)
                self.smasher_leap_target = None
        if self.swordmaster_invuln_timer > 0:
            self.swordmaster_invuln_timer = max(0.0, self.swordmaster_invuln_timer - dt)
        if self.swordmaster_haste_timer > 0:
            self.swordmaster_haste_timer = max(0.0, self.swordmaster_haste_timer - dt)
        if self.windrunner_storm_timer > 0:
            self.windrunner_storm_timer = max(0.0, self.windrunner_storm_timer - dt)
            for target in get_targetables(game_state):
                if not target.alive or target.owner_id == self.owner_id or not hasattr(target, "get_current_basic_attack_type"):
                    continue
                if target.get_current_basic_attack_type() == "melee" and (target.pos - self.pos).length() <= WINDRUNNER_REPEL_RADIUS + target.radius:
                    target.apply_knockback(target.pos - self.pos, WINDRUNNER_REPEL_DISTANCE)
        if self.hex_curse_timer > 0:
            self.hex_curse_timer = max(0.0, self.hex_curse_timer - dt)
        if self.design_ember > 0 and game_state is not None:
            # 灼炎 dot + 满层小爆炸
            self.take_damage(
                FLAME_EMBER_DPS * dt * self.design_ember,
                source=next((c for c in game_state["characters"] if c.is_flame_dancer() and c.owner_id != self.owner_id), None),
                damage_type="design_spell_flame_ember",
                game_state=game_state,
            )
        if self.is_ghost_priest() and game_state is not None:
            self.design_misc_timer += dt
            while self.design_misc_timer >= GHOST_WHISPER_INTERVAL:
                self.design_misc_timer -= GHOST_WHISPER_INTERVAL
                whisper_target = None
                for candidate in get_targetables(game_state):
                    if candidate.alive and candidate.owner_id != self.owner_id and int(getattr(candidate, "design_dread", 0)) > 0:
                        if whisper_target is None or (candidate.pos - self.pos).length_squared() < (whisper_target.pos - self.pos).length_squared():
                            whisper_target = candidate
                if whisper_target is not None:
                    whisper_target.take_damage(GHOST_WHISPER_DAMAGE, source=self, damage_type="design_spell_ghost_whisper", game_state=game_state)
                    whisper_target.apply_fear(GHOST_WHISPER_FEAR, self.owner_id)
                    spawn_attack_impact(game_state, whisper_target.pos, GHOST_FEAR_TEAL, radius=12, thickness=2, burst_count=8)
        if self.is_abyssal_watcher() and game_state is not None:
            for candidate in get_targetables(game_state):
                if candidate.alive and candidate.owner_id != self.owner_id and int(getattr(candidate, "design_gaze", 0)) > 0:
                    pass  # 凝视伤害加成在 take_damage 里处理
        if self.is_riftbreaker() and game_state is not None:
            self.design_rift_phase_timer += dt
            while self.design_rift_phase_timer >= RIFT_PHASE_INTERVAL:
                self.design_rift_phase_timer -= RIFT_PHASE_INTERVAL
                phase_dir = random_unit_vector()
                phase_target = self.pos + phase_dir * RIFT_PHASE_DISTANCE
                phase_target.x = clamp(phase_target.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                phase_target.y = clamp(phase_target.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                self.pos = phase_target
                self.update_rect()
                if game_state is not None:
                    spawn_attack_impact(game_state, self.pos, RIFT_BLUE, radius=16, thickness=3, burst_count=10)
        if self.duel_haste_timer > 0:
            self.duel_haste_timer = max(0.0, self.duel_haste_timer - dt)
        if self.gladiator_duel_timer > 0:
            self.gladiator_duel_timer = max(0.0, self.gladiator_duel_timer - dt)
        if self.tinkerer_overclock_timer > 0:
            self.tinkerer_overclock_timer = max(0.0, self.tinkerer_overclock_timer - dt)
            if self.tinkerer_overclock_timer == 0 and self.held_weapon is not None and self.held_weapon.get("overclocked"):
                self.clear_weapon()
        if self.valkyrie_dive_timer > 0:
            self.valkyrie_dive_timer = max(0.0, self.valkyrie_dive_timer - dt)
            if self.valkyrie_dive_timer == 0 and self.valkyrie_dive_target is not None:
                current_enemies = [enemy for enemy in get_targetables(game_state) if enemy.alive and enemy.owner_id != self.owner_id]
                if current_enemies:
                    fresh_anchor = max(
                        current_enemies,
                        key=lambda enemy: (
                            sum(1 for other in current_enemies if (other.pos - enemy.pos).length() <= VALKYRIE_SLAM_RADIUS),
                            -sum((other.pos - enemy.pos).length() for other in current_enemies),
                        ),
                    )
                    if (fresh_anchor.pos - self.valkyrie_dive_target).length() > VALKYRIE_RETARGET_RADIUS:
                        self.valkyrie_dive_target = pygame.Vector2(fresh_anchor.pos)
                self.pos = pygame.Vector2(self.valkyrie_dive_target)
                self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                if game_state is not None:
                    add_design_effect(
                        game_state,
                        DesignEffect(
                            "valkyrie_landing",
                            self,
                            pygame.Vector2(self.pos),
                            radius=VALKYRIE_SLAM_RADIUS,
                            lifetime=VALKYRIE_LANDING_LIFETIME,
                        ),
                    )
                    for _ in range(14):
                        game_state["death_particles"].append(DeathParticle(self.pos, VALKYRIE_LANDING_COLOR, dust=True))
                self.add_true_shield(VALKYRIE_TRUE_SHIELD)
                for target in get_targetables(game_state):
                    if not target.alive or target.owner_id == self.owner_id:
                        continue
                    if (target.pos - self.pos).length() <= VALKYRIE_SLAM_RADIUS + getattr(target, "radius", 0):
                        target.take_damage(VALKYRIE_SLAM_DAMAGE, source=self, damage_type="skyfall_strike", game_state=game_state)
                        if hasattr(target, "apply_stun"):
                            target.apply_stun(VALKYRIE_SLAM_STUN)
                self.valkyrie_dive_target = None
                self.update_rect()
        if self.dark_reflect_timer > 0:
            self.dark_reflect_timer = max(0.0, self.dark_reflect_timer - dt)
        if self.job_name == SOUL_ARBITER_JOB_NAME:
            self.update_soul_arbiter_chains(dt, game_state)
        if self.bloodwraith_shield_timer > 0:
            self.bloodwraith_shield_timer = max(0.0, self.bloodwraith_shield_timer - dt)
            if self.bloodwraith_shield_timer == 0:
                self.bloodwraith_shield_hp = 0.0
        if self.phantom_lancer_throw_speed_timer > 0:
            self.phantom_lancer_throw_speed_timer = max(0.0, self.phantom_lancer_throw_speed_timer - dt)
        if self.phantom_lancer_spear_hunt_timer > 0:
            self.phantom_lancer_spear_hunt_timer = max(0.0, self.phantom_lancer_spear_hunt_timer - dt)
        if self.bloodwraith_rage_active:
            self.take_damage(self.max_hp * BLOODWRAITH_RAGE_DRAIN_RATIO * dt, source=self, damage_type="true_bloodwraith_rage_drain", game_state=game_state)
        if self.design_phoenix_wrath_timer > 0:
            self.design_phoenix_wrath_timer = max(0.0, self.design_phoenix_wrath_timer - dt)
            self.design_phoenix_wrath_accum += dt
            while self.design_phoenix_wrath_accum >= 1.0:
                self.design_phoenix_wrath_accum -= 1.0
                if self.alive:
                    self.take_damage(
                        PHOENIX_WRATH_DOT_BASE + self.design_phoenix_fire,
                        source=self.design_phoenix_wrath_source,
                        damage_type="design_spell_phoenix_wrath",
                        game_state=game_state,
                    )
            if self.design_phoenix_wrath_timer == 0:
                self.design_phoenix_wrath_accum = 0.0
                self.design_phoenix_wrath_source = None
        if self.is_phoenix() and self.design_phoenix_egg_timer > 0:
            self.design_phoenix_egg_timer = max(0.0, self.design_phoenix_egg_timer - dt)
            if self.design_phoenix_egg_timer == 0:
                self.end_phoenix_egg(game_state)
        if self.is_xuanwu():
            if self.design_shell_guard_cooldown > 0:
                self.design_shell_guard_cooldown = max(0.0, self.design_shell_guard_cooldown - dt)
            self.design_shell_counter_timer += dt
            while self.design_shell_counter_timer >= XUANWU_COUNTER_INTERVAL:
                self.design_shell_counter_timer -= XUANWU_COUNTER_INTERVAL
                while self.design_shell_stacks >= XUANWU_COUNTER_SHELL_STEP:
                    self.xuanwu_counterattack(game_state)
            if self.design_xuan_bulwark_timer > 0:
                self.design_xuan_bulwark_timer = max(0.0, self.design_xuan_bulwark_timer - dt)
                if self.design_xuan_bulwark_timer == 0:
                    self.design_xuan_bulwark_shield = 0.0
        if self.is_tiger():
            if self.design_tiger_prey_charge_window > 0:
                self.design_tiger_prey_charge_window = max(0.0, self.design_tiger_prey_charge_window - dt)
                if self.design_tiger_prey_charge_window == 0:
                    self.design_tiger_prey_charge_count = 0
            if self.design_tiger_blood_speed_timer > 0:
                self.design_tiger_blood_speed_timer = max(0.0, self.design_tiger_blood_speed_timer - dt)
            prey = self.get_tiger_prey(game_state)
            if prey is None:
                self.mark_tiger_prey(game_state)
            if game_state is not None:
                near_trail = False
                for effect in game_state.get("design_effects", []):
                    if effect.alive and effect.effect_type == "tiger_blood_trail" and (effect.pos - self.pos).length() <= effect.radius + self.radius + 30.0:
                        near_trail = True
                        break
                if near_trail:
                    self.design_tiger_blood_speed_timer = max(self.design_tiger_blood_speed_timer, TIGER_WOUND_TRAIL_SPEED_GRACE)
        if self.is_dragon():
            if self.design_dragon_sweep_cooldown > 0:
                self.design_dragon_sweep_cooldown = max(0.0, self.design_dragon_sweep_cooldown - dt)
            if self.design_dragon_form == "thunder":
                self.design_dragon_zap_timer += dt
                while self.design_dragon_zap_timer >= DRAGON_THUNDER_ZAP_INTERVAL:
                    self.design_dragon_zap_timer -= DRAGON_THUNDER_ZAP_INTERVAL
                    zap_target = select_nearest_enemy(self, game_state["characters"]) if game_state is not None else None
                    if zap_target is not None and zap_target.alive:
                        zap_target.take_damage(DRAGON_THUNDER_ZAP_DAMAGE, source=self, damage_type="true_dragon_zap", game_state=game_state)
            else:
                self.design_dragon_heal_timer += dt
                while self.design_dragon_heal_timer >= DRAGON_WOOD_HEAL_INTERVAL:
                    self.design_dragon_heal_timer -= DRAGON_WOOD_HEAL_INTERVAL
                    self.heal(self.max_hp * DRAGON_WOOD_HEAL_RATIO)
        if self.is_design_role() and self.design_meta.get("role_num") == 98:
            self.design_xp_timer += dt
            while self.design_xp_timer >= 5.0:
                self.design_xp_timer -= 5.0
                self.add_design_xp(25.0)
            if self.design_level_fx_timer > 0:
                self.design_level_fx_timer = max(0.0, self.design_level_fx_timer - dt)
                if self.design_level_fx_timer == 0:
                    self.design_level_fx_scale = 1.0

        if self.ninja_dash_timer > 0:
            self.ninja_dash_timer = max(0.0, self.ninja_dash_timer - dt)
        if self.melee_gap_dash_timer > 0:
            self.melee_gap_dash_timer = max(0.0, self.melee_gap_dash_timer - dt)
        if self.melee_gap_dash_cooldown > 0:
            self.melee_gap_dash_cooldown = max(0.0, self.melee_gap_dash_cooldown - dt)

        if self.mp >= MAX_MP and self.clone_mode is None and (
            self.stun_timer <= 0
            or self.config["skill_id"] in {"time_rewind", "sunfire_kagura"}
        ):
            self.cast_skill(game_state)

    def update(self, dt, game_state):
        if not self.alive:
            return

        self.spawn_fx_timer = max(0.0, self.spawn_fx_timer - dt)
        if self.spawn_fx_timer > 0 and game_state is not None and game_state.get("elapsed_time", 0.0) <= SPAWN_FX_DURATION:
            # 开场登场演出：角色定格站立，仅播放登场特效
            self.vel *= 0.0
            self.recent_move_dir = pygame.Vector2(0, 0)
            self.update_rect()
            self.update_facing(game_state)
            return

        self.update_soul_blade(dt, game_state)
        if self.design_sparrow_host_id is not None:
            self.update_sparrow_host(dt, game_state)
            return

        self.process_effects(dt, game_state)
        if not self.alive:
            return

        if self.held_weapon is not None:
            self.held_weapon["cooldown"] = max(0.0, self.held_weapon["cooldown"] - dt)
            self.attack_cooldown = self.held_weapon["cooldown"]
        else:
            self.attack_cooldown = max(0.0, self.attack_cooldown - dt)

        self.wander_timer -= dt
        if self.wander_timer <= 0:
            self.choose_wander_direction()
        self.update_strafe_state(dt)

        if game_state.get("global_time_stop_timer", 0.0) > 0 and self.owner_id != game_state.get("global_time_stop_owner"):
            self.vel *= 0.0
            self.update_rect()
            return

        if self.stun_timer > 0 or self.smasher_leap_timer > 0 or self.valkyrie_dive_timer > 0 or self.sleep_timer > 0:
            self.vel *= 0.0
            self.update_rect()
            return

        target = self.get_target(game_state)
        weapon_orb_target = self.get_nearest_weapon_orb(game_state) if self.held_weapon is None else None
        desired = pygame.Vector2(self.wander_dir)
        current_range = self.get_current_attack_range()
        current_attack_type = self.get_current_basic_attack_type()
        hold_position = False
        apply_chase_noise = False
        orb_distance = None
        orb_direction = None
        if self.clone_mode == "illusion":
            weapon_orb_target = None
            desired = pygame.Vector2(self.wander_dir)
        if self.charm_timer > 0 and self.charm_owner_id is not None:
            weapon_orb_target = None
            source = next((character for character in game_state["characters"] if character.alive and character.owner_id == self.charm_owner_id), None)
            if source is not None:
                to_source = source.pos - self.pos
                if to_source.length_squared() > 0:
                    desired = to_source.normalize()
            hold_position = False
            apply_chase_noise = False
            target = None
        if weapon_orb_target is not None:
            to_orb = weapon_orb_target.pos - self.pos
            orb_distance = to_orb.length()
            if orb_distance > 0:
                orb_direction = to_orb.normalize()
                desired = orb_direction
                apply_chase_noise = True
        if target is not None:
            to_target = target.pos - self.pos
            distance = to_target.length()
            if distance > 0:
                direction = to_target.normalize()
                pursuit_direction = direction
                if self.can_use_melee_dash():
                    intercept_pos = self.get_melee_intercept_position(target)
                    intercept_offset = intercept_pos - self.pos
                    if intercept_offset.length_squared() > 0:
                        pursuit_direction = intercept_offset.normalize()
                    if self.try_start_melee_dash(pursuit_direction, distance, current_range):
                        desired = pursuit_direction
                        apply_chase_noise = False
                if current_attack_type == "ranged" and distance < RANGED_SAFE_DISTANCE:
                    desired = -direction
                    apply_chase_noise = False
                    hold_position = False
                    if self.vel.length_squared() > 0:
                        self.vel *= -0.4
                elif current_attack_type == "ranged" and distance <= current_range:
                    perpendicular = pygame.Vector2(-direction.y, direction.x) * self.strafe_sign
                    midpoint = (RANGED_SAFE_DISTANCE + current_range) * 0.5
                    span = max(1.0, (current_range - RANGED_SAFE_DISTANCE) * 0.5)
                    radial_correction = clamp((distance - midpoint) / span, -1.0, 1.0)
                    desired = perpendicular * STRAFE_ORBIT_WEIGHT + direction * radial_correction * STRAFE_RADIAL_WEIGHT
                    apply_chase_noise = True
                    hold_position = False
                elif self.clone_mode == "illusion":
                    desired = pygame.Vector2(self.wander_dir)
                    apply_chase_noise = True
                    hold_position = False
                elif self.can_use_melee_dash() and distance > current_range:
                    if orb_direction is not None and orb_distance is not None and orb_distance > self.radius + weapon_orb_target.radius:
                        if distance <= current_range + MELEE_DASH_TRIGGER_BUFFER:
                            desired = pursuit_direction
                            apply_chase_noise = self.melee_gap_dash_timer <= 0
                        else:
                            desired = (orb_direction * 0.72 + pursuit_direction * 0.28)
                            apply_chase_noise = True
                    else:
                        desired = pursuit_direction
                        apply_chase_noise = self.melee_gap_dash_timer <= 0
                elif self.held_weapon is None and orb_direction is not None and orb_distance is not None:
                    if orb_distance > self.radius + weapon_orb_target.radius:
                        if distance <= current_range:
                            desired = (orb_direction * 0.8 + direction * 0.2)
                            apply_chase_noise = True
                        else:
                            desired = orb_direction
                            apply_chase_noise = True
                    else:
                        if distance > current_range:
                            desired = direction
                            apply_chase_noise = True
                        else:
                            desired = pygame.Vector2()
                            hold_position = True
                            apply_chase_noise = False
                elif distance > current_range:
                    desired = pursuit_direction
                    apply_chase_noise = True
                else:
                    desired = pygame.Vector2()
                    hold_position = True
                    apply_chase_noise = False

                can_fire = self.attack_cooldown <= 0 and self.sniper_charge_timer <= 0 and self.charm_timer <= 0 and self.disarm_timer <= 0 and self.blind_timer <= 0
                if self.is_soul_casket():
                    can_fire = False  # 本体不出手，由剑灵代打
                in_range = distance <= current_range or current_range >= WEAPON_RANGE_INFINITE
                if can_fire and in_range:
                    if self.held_weapon is None:
                        self.fire_basic_attack(target, game_state)
                    else:
                        self.fire_equipped_weapon(target, game_state)

        if self.root_timer > 0:
            desired = pygame.Vector2()
            hold_position = True
            apply_chase_noise = False

        if self.design_immobile:
            desired = pygame.Vector2()
            hold_position = True
            apply_chase_noise = False

        if self.design_fear_timer > 0 and self.design_fear_source_id is not None and game_state is not None:
            fear_source = next((c for c in game_state["characters"] if c.owner_id == self.design_fear_source_id and c.alive), None)
            if fear_source is not None:
                away = self.pos - fear_source.pos
                if away.length_squared() > 0:
                    desired = away.normalize()
                    hold_position = False
                    apply_chase_noise = True
                else:
                    desired = random_unit_vector()
                    hold_position = False
                    apply_chase_noise = True
            else:
                desired = random_unit_vector()
                hold_position = False
                apply_chase_noise = True

        if apply_chase_noise and desired.length_squared() > 0:
            desired = self.apply_chase_noise(desired.normalize(), dt)
        separation = self.get_separation_vector(game_state)

        if hold_position:
            self.vel *= 0.12
        steer_vector = pygame.Vector2()
        if desired.length_squared() > 0:
            desired = desired.normalize()
            self.vel += desired * CHARACTER_ACCELERATION * dt
            steer_vector += desired
        if separation.length_squared() > 0:
            separation_scale = SEPARATION_FORCE * (SEPARATION_HOLD_BIAS if hold_position else 1.0)
            self.vel += separation * CHARACTER_ACCELERATION * separation_scale * dt
            steer_vector += separation * separation_scale
        if steer_vector.length_squared() > 0:
            self.recent_move_dir = steer_vector.normalize()

        max_speed = self.move_speed * self.get_speed_modifier()
        friction_scale = max(0.0, 1.0 - CHARACTER_FRICTION * dt)
        self.vel *= friction_scale
        if self.vel.length() > max_speed:
            self.vel.scale_to_length(max_speed)

        previous_pos = pygame.Vector2(self.pos)
        self.pos += self.vel * dt
        self.on_distance_moved((self.pos - previous_pos).length(), game_state)
        hit_x = False
        hit_y = False
        if self.pos.x - self.radius < ARENA_RECT.left:
            self.pos.x = ARENA_RECT.left + self.radius
            hit_x = True
        elif self.pos.x + self.radius > ARENA_RECT.right:
            self.pos.x = ARENA_RECT.right - self.radius
            hit_x = True
        if self.pos.y - self.radius < ARENA_RECT.top:
            self.pos.y = ARENA_RECT.top + self.radius
            hit_y = True
        elif self.pos.y + self.radius > ARENA_RECT.bottom:
            self.pos.y = ARENA_RECT.bottom - self.radius
            hit_y = True

        if hit_x:
            self.vel.x *= -CHARACTER_BOUNCE
            self.choose_wander_direction()
        if hit_y:
            self.vel.y *= -CHARACTER_BOUNCE
            self.choose_wander_direction()

        self.update_rect()
        self.update_facing(game_state)

    def update_facing(self, game_state):
        near = None
        near_d2 = float("inf")
        for other in game_state.get("characters", []):
            if other.alive and other.owner_id != self.owner_id:
                d2 = (other.pos - self.pos).length_squared()
                if d2 < near_d2:
                    near_d2 = d2
                    near = other
        if near is not None:
            self.facing_angle = math.degrees(math.atan2(near.pos.y - self.pos.y, near.pos.x - self.pos.x))
        elif self.recent_move_dir.length_squared() > 0.001:
            self.facing_angle = math.degrees(math.atan2(self.recent_move_dir.y, self.recent_move_dir.x))

    def resolve_overlap(self, other):
        if not self.alive or not other.alive:
            return

        offset = other.pos - self.pos
        distance = offset.length()
        min_distance = self.radius + other.radius - 1
        if 0 < distance < min_distance:
            normal = offset / distance
            overlap = min_distance - distance
            self.pos -= normal * (overlap / 2)
            other.pos += normal * (overlap / 2)
            self.vel -= normal * CHARACTER_PUSH_SPEED
            other.vel += normal * CHARACTER_PUSH_SPEED
        elif distance == 0:
            normal = random_unit_vector()
            self.pos -= normal * 1.5
            other.pos += normal * 1.5
            self.vel -= normal * CHARACTER_PUSH_SPEED
            other.vel += normal * CHARACTER_PUSH_SPEED

        self.pos.x = clamp(self.pos.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.pos.y = clamp(self.pos.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
        other.pos.x = clamp(other.pos.x, ARENA_RECT.left + other.radius, ARENA_RECT.right - other.radius)
        other.pos.y = clamp(other.pos.y, ARENA_RECT.top + other.radius, ARENA_RECT.bottom - other.radius)
        self.update_rect()
        other.update_rect()

    def draw_shape(self, surface):
        center = pygame.Vector2(self.pos)
        if self.is_twin_mirror():
            angle = self.design_misc_timer * 2.4
            orbit = pygame.Vector2(self.radius * 0.34, 0).rotate_rad(angle)
            primary = self.color
            secondary = TWIN_MIRROR_BLACK_COLOR if self.twin_mirror_form == "white" else TWIN_MIRROR_WHITE_COLOR
            left_center = (round(center.x - orbit.x), round(center.y - orbit.y))
            right_center = (round(center.x + orbit.x), round(center.y + orbit.y))
            pygame.draw.circle(surface, secondary, left_center, max(6, self.radius - 5))
            pygame.draw.circle(surface, primary, right_center, max(7, self.radius - 3))
            pygame.draw.circle(surface, BORDER_COLOR, left_center, max(6, self.radius - 5), 1)
            pygame.draw.circle(surface, BORDER_COLOR, right_center, max(7, self.radius - 3), 1)
            return
        draw_color = (255, 72, 72) if self.hit_flash_timer > 0 else self.get_visual_color()
        if self.shape in ROTATABLE_SHAPES:
            size = int(self.radius * 2 + 12)
            icon_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            draw_shape_icon(icon_surface, self.shape, draw_color, (size // 2, size // 2), self.radius - 2)
            rotate_deg = -90.0 - self.facing_angle
            rotated_surface = pygame.transform.rotozoom(icon_surface, rotate_deg, 1.0)
            surface.blit(rotated_surface, rotated_surface.get_rect(center=(round(center.x), round(center.y))))
        else:
            draw_shape_icon(surface, self.shape, draw_color, (round(center.x), round(center.y)), self.radius - 2)
            rad = math.radians(self.facing_angle)
            dir_vec = pygame.Vector2(math.cos(rad), math.sin(rad))
            perpendicular = pygame.Vector2(-dir_vec.y, dir_vec.x) * 3
            tip = center + dir_vec * (self.radius + 6)
            base_1 = center + dir_vec * (self.radius + 1) + perpendicular
            base_2 = center + dir_vec * (self.radius + 1) - perpendicular
            pygame.draw.polygon(
                surface,
                (235, 240, 248),
                [(round(tip.x), round(tip.y)), (round(base_1.x), round(base_1.y)), (round(base_2.x), round(base_2.y))],
            )

    def draw_spawn_fx(self, surface):
        if self.spawn_fx_timer <= 0:
            return
        if self.gold_spawn_fx:
            self.draw_spawn_fx_gold(surface)
            return
        progress = 1.0 - self.spawn_fx_timer / max(0.1, SPAWN_FX_DURATION)
        center_x = round(self.pos.x)
        center_y = round(self.pos.y)
        local_radius = max(8, int(self.radius))
        # 局部叠加层，避免全屏 SRCALPHA 开销
        extents = local_radius * 3 + 24
        overlay = pygame.Surface((extents, extents), pygame.SRCALPHA)
        cx = extents // 2
        cy = extents // 2
        # 光柱：角色颜色垂直光带，随登场进度收缩
        pillar_half = max(3, int(local_radius * 0.55 * (1.0 - progress * 0.45)))
        pillar_height = int(extents * 0.72 * (1.15 - progress * 0.35))
        pillar_alpha = int(120 * (1.0 - progress))
        if pillar_alpha > 0:
            pillar_rect = pygame.Rect(cx - pillar_half, cy - local_radius - pillar_height, pillar_half * 2, pillar_height + local_radius * 2)
            pygame.draw.rect(overlay, (*self.get_visual_color(), min(255, pillar_alpha)), pillar_rect, border_radius=pillar_half)
            pygame.draw.rect(overlay, (*SPAWN_FX_GLOW_COLOR, max(30, pillar_alpha // 2)), pillar_rect.inflate(pillar_half, 6), border_radius=pillar_half + 4)
        # 扩散光环：从角色底部向四周扩散并淡出
        ring_radius = int(local_radius * (0.6 + progress * 1.6))
        ring_alpha = int(180 * (1.0 - progress))
        if ring_alpha > 0:
            pygame.draw.circle(overlay, (*self.get_visual_color(), max(28, ring_alpha)), (cx, cy), max(4, ring_radius), 3)
            pygame.draw.circle(overlay, (*SPAWN_FX_GLOW_COLOR, max(16, ring_alpha // 2)), (cx, cy), max(3, ring_radius - 4), 1)
        # 顶部星芒：登场初期向上扬起的闪光颗粒
        if progress < 0.65:
            spark_alpha = int(200 * (1.0 - progress / 0.65))
            spark_count = 6
            for index in range(spark_count):
                angle = math.tau * index / spark_count
                start_r = local_radius * 0.5
                end_r = local_radius * (0.75 + progress * 1.4)
                sx = cx + math.cos(angle) * start_r
                sy = cy + math.sin(angle) * start_r * 0.85
                ex = cx + math.cos(angle) * end_r
                ey = cy + math.sin(angle) * end_r * 0.85 - (progress * 14.0)
                pygame.draw.line(overlay, (*SPAWN_FX_GLOW_COLOR, max(24, spark_alpha)), (round(sx), round(sy)), (round(ex), round(ey)), 2)
        surface.blit(overlay, (center_x - extents // 2, center_y - extents // 2))

    def draw_spawn_fx_gold(self, surface):
        progress = 1.0 - self.spawn_fx_timer / max(0.1, SPAWN_FX_DURATION)
        center_x = round(self.pos.x)
        center_y = round(self.pos.y)
        local_radius = max(8, int(self.radius))
        gold = (255, 208, 54)
        gold_light = (255, 246, 190)
        extents = local_radius * 4 + 40
        overlay = pygame.Surface((extents, extents), pygame.SRCALPHA)
        cx = extents // 2
        cy = extents // 2
        fade = 1.0 - progress
        # 底部金色光晕垫片
        if fade > 0:
            glow_r = int(local_radius * (1.1 + progress * 0.9))
            pygame.draw.circle(overlay, (*gold, int(52 * fade)), (cx, cy), max(6, glow_r))
        # 金色双光柱：亮金主柱 + 暖白描边，更宽更高
        pillar_half = max(4, int(local_radius * 0.72 * (1.0 - progress * 0.4)))
        pillar_height = int(extents * 0.82 * (1.18 - progress * 0.3))
        pillar_alpha = int(170 * fade)
        if pillar_alpha > 0:
            pillar_rect = pygame.Rect(cx - pillar_half, cy - local_radius - pillar_height, pillar_half * 2, pillar_height + local_radius * 2)
            pygame.draw.rect(overlay, (*gold, min(255, pillar_alpha)), pillar_rect, border_radius=pillar_half)
            pygame.draw.rect(overlay, (*gold_light, max(34, pillar_alpha // 2)), pillar_rect.inflate(pillar_half - 2, 8), border_radius=pillar_half + 3)
            pygame.draw.rect(overlay, (*gold_light, max(18, pillar_alpha // 3)), pillar_rect.inflate(pillar_half + 4, 12), border_radius=pillar_half + 6)
        # 金色双层光环
        ring_alpha = int(200 * fade)
        if ring_alpha > 0:
            ring_r = int(local_radius * (0.7 + progress * 1.9))
            pygame.draw.circle(overlay, (*gold, max(34, ring_alpha)), (cx, cy), max(4, ring_r), 4)
            pygame.draw.circle(overlay, (*gold_light, max(18, ring_alpha // 2)), (cx, cy), max(3, ring_r - 7), 1)
        # 金色 8 道射线 + 顶部小皇冠
        if progress < 0.7:
            spark_alpha = int(230 * (1.0 - progress / 0.7))
            for index in range(8):
                angle = math.tau * index / 8
                start_r = local_radius * 0.55
                end_r = local_radius * (0.9 + progress * 1.6)
                sx = cx + math.cos(angle) * start_r
                sy = cy + math.sin(angle) * start_r * 0.9
                ex = cx + math.cos(angle) * end_r
                ey = cy + math.sin(angle) * end_r * 0.9 - (progress * 18.0)
                pygame.draw.line(overlay, (*gold_light, max(28, spark_alpha)), (round(sx), round(sy)), (round(ex), round(ey)), 3)
            crown_y = cy - local_radius - int(extents * 0.68)
            crown_width = local_radius * 0.9
            crown_alpha = max(60, int(255 * (1.0 - progress * 0.75)))
            pygame.draw.polygon(
                overlay,
                (*gold, crown_alpha),
                [
                    (cx - int(crown_width), crown_y),
                    (cx - int(crown_width * 0.55), crown_y - int(crown_width * 0.55)),
                    (cx - int(crown_width * 0.22), crown_y + int(crown_width * 0.06)),
                    (cx, crown_y - int(crown_width * 0.72)),
                    (cx + int(crown_width * 0.22), crown_y + int(crown_width * 0.06)),
                    (cx + int(crown_width * 0.55), crown_y - int(crown_width * 0.55)),
                    (cx + int(crown_width), crown_y),
                ],
            )
            pygame.draw.polygon(
                overlay,
                (*gold_light, min(255, crown_alpha)),
                [
                    (cx - int(crown_width), crown_y),
                    (cx - int(crown_width * 0.55), crown_y - int(crown_width * 0.55)),
                    (cx - int(crown_width * 0.22), crown_y + int(crown_width * 0.06)),
                    (cx, crown_y - int(crown_width * 0.72)),
                    (cx + int(crown_width * 0.22), crown_y + int(crown_width * 0.06)),
                    (cx + int(crown_width * 0.55), crown_y - int(crown_width * 0.55)),
                    (cx + int(crown_width), crown_y),
                ],
                2,
            )
        surface.blit(overlay, (center_x - extents // 2, center_y - extents // 2))

    def draw_bars(self, surface, label_font):
        if self.is_twin_mirror():
            bar_width = 34
            bar_height = 4
            active_form = self.twin_mirror_form
            passive_form = "black" if active_form == "white" else "white"
            active_hp = getattr(self, self.twin_mirror_form_hp_attr(active_form), 0.0)
            passive_hp = getattr(self, self.twin_mirror_form_hp_attr(passive_form), 0.0)
            active_locked = getattr(self, self.twin_mirror_form_lock_attr(active_form), False)
            passive_locked = getattr(self, self.twin_mirror_form_lock_attr(passive_form), False)
            active_rect = pygame.Rect(round(self.pos.x - bar_width / 2), round(self.pos.y - self.radius - 16), bar_width, bar_height)
            passive_rect = pygame.Rect(round(self.pos.x - bar_width / 2), round(self.pos.y - self.radius - 10), bar_width, bar_height)
            mp_rect = pygame.Rect(round(self.pos.x - bar_width / 2), round(self.pos.y - self.radius - 4), bar_width, bar_height)
            for rect, hp_value, color, locked, label in (
                (active_rect, active_hp, self.color, active_locked, "W" if active_form == "white" else "B"),
                (passive_rect, passive_hp, TWIN_MIRROR_BLACK_COLOR if passive_form == "black" else TWIN_MIRROR_WHITE_COLOR, passive_locked, "W" if passive_form == "white" else "B"),
            ):
                pygame.draw.rect(surface, HEALTH_BG, rect, border_radius=2)
                if hp_value > 0:
                    fill = rect.copy()
                    fill.width = max(1, int(rect.width * (hp_value / TWIN_MIRROR_FORM_MAX_HP)))
                    pygame.draw.rect(surface, color, fill, border_radius=2)
                pygame.draw.rect(surface, (76, 76, 76) if locked else BORDER_COLOR, rect, 1, border_radius=2)
                tag = label_font.render(label, True, BORDER_COLOR)
                surface.blit(tag, (rect.left - tag.get_width() - 2, rect.top - 1))
            pygame.draw.rect(surface, MANA_BG, mp_rect, border_radius=2)
            mp_ratio = self.mp / MAX_MP
            if mp_ratio > 0:
                fill = mp_rect.copy()
                fill.width = max(1, int(mp_rect.width * mp_ratio))
                pygame.draw.rect(surface, MANA_COLOR, fill, border_radius=2)
            pygame.draw.rect(surface, BORDER_COLOR, mp_rect, 1, border_radius=2)
            total_shield = self.true_shield + self.bloodwraith_shield_hp + self.sea_tide_shield_hp
            if total_shield > 0:
                shield_rect = pygame.Rect(active_rect.left, active_rect.top - 7, active_rect.width, 4)
                pygame.draw.rect(surface, (46, 58, 78), shield_rect, border_radius=2)
                shield_cap = max(BEHEMOTH_TRUE_SHIELD, self.max_hp * BLOODWRAITH_SHIELD_RATIO, total_shield)
                shield_ratio = clamp(total_shield / shield_cap, 0.0, 1.0)
                fill = shield_rect.copy()
                fill.width = max(1, int(shield_rect.width * shield_ratio))
                shield_color = (198, 226, 255) if self.true_shield > 0 else (198, 88, 108) if self.bloodwraith_shield_hp > 0 else SEA_SAGE_WAVE_OUTER_COLOR
                pygame.draw.rect(surface, shield_color, fill, border_radius=2)
                pygame.draw.rect(surface, BORDER_COLOR, shield_rect, 1, border_radius=2)
            if self.held_weapon is not None:
                weapon_id = self.held_weapon["weapon_id"]
                display_name = weapon_id.replace("Gun", " Gun")
                label = f"{display_name} {self.held_weapon['ammo']}"
                text = label_font.render(label, True, WEAPON_DEFS[weapon_id]["projectile_color"])
                text_rect = text.get_rect(center=(round(self.pos.x), round(self.pos.y - self.radius - 22)))
                surface.blit(text, text_rect)
            return
        bar_width = 34
        bar_height = 5
        hp_rect = pygame.Rect(round(self.pos.x - bar_width / 2), round(self.pos.y - self.radius - 12), bar_width, bar_height)
        mp_rect = pygame.Rect(round(self.pos.x - bar_width / 2), round(self.pos.y - self.radius - 5), bar_width, bar_height)
        pygame.draw.rect(surface, HEALTH_BG, hp_rect, border_radius=2)
        pygame.draw.rect(surface, MANA_BG, mp_rect, border_radius=2)

        hp_ratio = self.hp / self.max_hp if self.max_hp else 0
        mp_ratio = self.mp / MAX_MP
        if hp_ratio > 0:
            fill = hp_rect.copy()
            fill.width = max(1, int(hp_rect.width * hp_ratio))
            pygame.draw.rect(surface, self.get_visual_color(), fill, border_radius=2)
        if mp_ratio > 0:
            fill = mp_rect.copy()
            fill.width = max(1, int(mp_rect.width * mp_ratio))
            pygame.draw.rect(surface, MANA_COLOR, fill, border_radius=2)

        pygame.draw.rect(surface, BORDER_COLOR, hp_rect, 1, border_radius=2)
        pygame.draw.rect(surface, BORDER_COLOR, mp_rect, 1, border_radius=2)
        if self.design_corrupted_blood > 0:
            blood_rect = pygame.Rect(hp_rect.left, mp_rect.bottom + 2, hp_rect.width, 4)
            pygame.draw.rect(surface, (40, 34, 52), blood_rect, border_radius=2)
            blood_cap = max(1.0, self.max_hp * SPARROW_BLOOD_RATIO)
            blood_ratio = clamp(self.design_corrupted_blood / blood_cap, 0.0, 1.0)
            if blood_ratio > 0:
                fill = blood_rect.copy()
                fill.width = max(1, int(blood_rect.width * blood_ratio))
                pygame.draw.rect(surface, SPARROW_BLOOD_COLOR, fill, border_radius=2)
            pygame.draw.rect(surface, BORDER_COLOR, blood_rect, 1, border_radius=2)
        total_shield = self.true_shield + self.bloodwraith_shield_hp + self.sea_tide_shield_hp
        if total_shield > 0:
            shield_rect = pygame.Rect(hp_rect.left, hp_rect.top - 7, hp_rect.width, 4)
            pygame.draw.rect(surface, (46, 58, 78), shield_rect, border_radius=2)
            shield_cap = max(BEHEMOTH_TRUE_SHIELD, self.max_hp * BLOODWRAITH_SHIELD_RATIO, total_shield)
            shield_ratio = clamp(total_shield / shield_cap, 0.0, 1.0)
            fill = shield_rect.copy()
            fill.width = max(1, int(shield_rect.width * shield_ratio))
            shield_color = (198, 226, 255) if self.true_shield > 0 else (198, 88, 108) if self.bloodwraith_shield_hp > 0 else SEA_SAGE_WAVE_OUTER_COLOR
            pygame.draw.rect(surface, shield_color, fill, border_radius=2)
            pygame.draw.rect(surface, BORDER_COLOR, shield_rect, 1, border_radius=2)

        if self.held_weapon is not None:
            weapon_id = self.held_weapon["weapon_id"]
            display_name = weapon_id.replace("Gun", " Gun")
            label = f"{display_name} {self.held_weapon['ammo']}"
            text = label_font.render(label, True, WEAPON_DEFS[weapon_id]["projectile_color"])
            text_rect = text.get_rect(center=(round(self.pos.x), round(self.pos.y - self.radius - 20)))
            surface.blit(text, text_rect)
        if self.is_design_role() and self.design_meta.get("role_num") == 98:
            level_text = label_font.render(f"Lv.{self.design_level}", True, BORDER_COLOR)
            level_y = round(self.pos.y - self.radius - 22)
            surface.blit(level_text, level_text.get_rect(center=(round(self.pos.x), level_y)))

    def draw_skill_fx(self, surface):
        center = (round(self.pos.x), round(self.pos.y))
        if self.is_design_role() and self.design_meta.get("role_num") == 98 and self.design_level_fx_timer > 0:
            pulse_radius = round((self.radius + 6) * self.design_level_fx_scale)
            pygame.draw.circle(surface, (242, 242, 248), center, pulse_radius, 2)
        if self.is_windstorm_fox() and self.windstorm_qi_stacks > 0:
            aura_radius = self.radius + 6 + self.windstorm_qi_stacks
            aura_width = 3 if self.windstorm_qi_stacks >= WINDSTORM_FOX_QI_MAX else 2
            pygame.draw.circle(surface, WINDSTORM_FOX_AURA_COLOR, center, round(aura_radius), aura_width)
        if self.is_phoenix() and self.design_phoenix_egg_timer > 0:
            egg_pulse = 0.5 + 0.5 * math.sin(self.design_phoenix_egg_timer * 6.0)
            pygame.draw.circle(surface, PHOENIX_EGG_COLOR, center, round(self.radius + 9 + egg_pulse * 4), 2)
            if self.design_phoenix_egg_shield > 0:
                pygame.draw.circle(surface, PHOENIX_EGG_SHIELD_COLOR, center, round(self.radius + 14), 2)
        if self.is_xuanwu():
            if self.design_shell_stacks > 0:
                shell_ring = round(self.radius + 7 + min(6, self.design_shell_stacks // 2))
                pygame.draw.circle(surface, XUANWU_SHELL_COLOR, center, shell_ring, 2)
            if self.design_xuan_bulwark_timer > 0:
                pygame.draw.circle(surface, XUANWU_BULWARK_COLOR, center, round(self.radius + 13), 2)
        if self.is_dragon():
            form_color = DRAGON_THUNDER_COLOR if self.design_dragon_form == "thunder" else DRAGON_WOOD_COLOR
            pygame.draw.circle(surface, form_color, center, round(self.radius + 8), 2)
            breath = self.get_dragon_breath()
            if breath > 0:
                dot_y = round(self.pos.y - self.radius) - 14
                for i in range(breath):
                    pygame.draw.circle(surface, form_color, (round(self.pos.x - 14 + i * 7), dot_y), 3)
        if self.is_susanoo():
            pygame.draw.circle(surface, SUSANOO_THUNDER_COLOR, center, round(self.radius + 8), 2)
        if self.is_sunfire_blademaster():
            pygame.draw.circle(surface, self.get_visual_color(), center, round(self.radius + 8), 2)
        if self.is_sea_sage() and (self.sea_tide_shield_hp > 0 or self.sea_tide_reduction_timers):
            pygame.draw.circle(surface, SEA_SAGE_WAVE_OUTER_COLOR, center, round(self.radius + 8), 2)
        if self.is_twin_mirror():
            ring_color = TWIN_MIRROR_WHITE_COLOR if self.twin_mirror_form == "white" else TWIN_MIRROR_BLACK_COLOR
            pygame.draw.circle(surface, ring_color, center, round(self.radius + 8), 1)
        if self.is_soul_moth():
            if self.design_soul_moth_form:
                pygame.draw.circle(surface, SOUL_MOTH_FORM_COLOR, center, round(self.radius + 7), 2)
                pygame.draw.circle(surface, (250, 236, 180), center, round(self.radius + 4), 1)
            else:
                for soul_index in range(self.design_soul_moth_soul):
                    dot_x = center[0] + (soul_index - 1) * 10
                    pygame.draw.circle(surface, SOUL_MOTH_COLOR, (dot_x, center[1] - self.radius - 9), 3)
                    pygame.draw.circle(surface, (232, 202, 120), (dot_x, center[1] - self.radius - 9), 3, 1)
        if self.design_banished:
            # 脚下虚空裂口（椭圆底座）
            base_center = (center[0], round(self.pos.y + self.radius - 2))
            base_rect = pygame.Rect(0, 0, round(max(14, self.radius * 2.6)), round(max(8, self.radius * 0.85)))
            base_rect.center = base_center
            pygame.draw.ellipse(surface, BANISH_COLOR, base_rect, 2)
            pygame.draw.ellipse(surface, (86, 58, 128), base_rect.inflate(-6, -3), 1)
            # roll 爆闪环（脉动扩散）
            pulse_ratio = clamp(self.design_banish_pulse / 0.35, 0.0, 1.0)
            if pulse_ratio > 0:
                pulse_r = round(self.radius + 7 + pulse_ratio * 13)
                pygame.draw.circle(surface, BANISH_COLOR, center, pulse_r, max(1, round(4 - pulse_ratio * 3)))
                pygame.draw.circle(surface, (206, 170, 255), center, max(1, pulse_r - 4), 1)
            # 头顶放逐进度条（points/20）
            progress_ratio = clamp(self.design_banish_points / BANISH_POINTS_THRESHOLD, 0.0, 1.0)
            bar_rect = pygame.Rect(center[0] - 15, center[1] - self.radius - 38, 30, 4)
            pygame.draw.rect(surface, (30, 30, 44), bar_rect, border_radius=2)
            pygame.draw.rect(surface, (26, 20, 40), bar_rect, 1, border_radius=2)
            if progress_ratio > 0:
                fill = bar_rect.copy()
                fill.width = max(1, int(bar_rect.width * progress_ratio))
                pygame.draw.rect(surface, BANISH_COLOR, fill, border_radius=2)
        if self.design_corrupted_blood > 0:
            pygame.draw.circle(surface, SPARROW_COLOR, (center[0], center[1] - self.radius - 8), 3)
            pygame.draw.circle(surface, (255, 236, 210), (center[0], center[1] - self.radius - 8), 3, 1)
        if self.design_tide_link_active:
            pygame.draw.circle(surface, TIDE_COLOR, (center[0] - 5, center[1] - self.radius - 24), 2)
            pygame.draw.circle(surface, (180, 240, 255), (center[0] - 5, center[1] - self.radius - 24), 2, 1)
        if self.design_blood_feast_timer > 0:
            pygame.draw.circle(surface, BLOODSUCKER_COLOR, center, round(self.radius + 9), 2)
            pygame.draw.circle(surface, (120, 20, 30), center, round(self.radius + 5), 1)
        if self.shield_timer > 0:
            pygame.draw.circle(surface, (120, 180, 255), center, round(self.radius + 6), 2)
        if self.berserker_spin_timer > 0:
            # B: 固定范围警戒圈（圈即伤害范围，不扩散）
            pygame.draw.circle(surface, (255, 90, 90), center, round(BERSERKER_SPIN_RADIUS), 2)
            # C: 旋转斩痕（随自转扫过的扇形红弧 + 边线）
            spin_angle = self.berserker_spin_visual_timer * 5.0
            half_sweep = 0.9
            sweep_start = spin_angle - half_sweep
            sweep_end = spin_angle + half_sweep
            circle_rect = pygame.Rect(0, 0, int(BERSERKER_SPIN_RADIUS * 2), int(BERSERKER_SPIN_RADIUS * 2))
            circle_rect.center = center
            pygame.draw.arc(surface, (255, 126, 90), circle_rect, sweep_start, sweep_end, 4)
            for sweep_a in (sweep_start, sweep_end):
                edge = pygame.Vector2(center) + pygame.Vector2(math.cos(sweep_a), math.sin(sweep_a)) * BERSERKER_SPIN_RADIUS
                pygame.draw.line(surface, (255, 126, 90), center, (round(edge.x), round(edge.y)), 2)
        if self.sniper_charge_timer > 0:
            aim = self.pos + self.sniper_beam_direction * 28
            pygame.draw.line(surface, (150, 255, 170), center, (round(aim.x), round(aim.y)), 2)
        if self.vampire_channel_timer > 0:
            pygame.draw.circle(surface, (220, 40, 70), center, round(self.radius + 5), 1)
        if self.stun_timer > 0:
            pygame.draw.circle(surface, (255, 228, 90), center, round(self.radius + 4), 1)
        if self.freeze_timer > 0:
            pygame.draw.circle(surface, (140, 226, 255), center, round(self.radius + 7), 2)
        if self.true_shield > 0:
            pygame.draw.circle(surface, (210, 228, 255), center, round(self.radius + 9), 1)
        if self.druid_form_timer > 0:
            pygame.draw.circle(surface, (104, 190, 104), center, round(self.radius + 6), 2)
        if self.pyro_breath_timer > 0:
            aim = self.pos + self.recent_move_dir.normalize() * (self.radius + 18) if self.recent_move_dir.length_squared() > 0 else self.pos + pygame.Vector2(18, 0)
            pygame.draw.line(surface, (255, 122, 90), center, (round(aim.x), round(aim.y)), 3)
        if self.doom_timer > 0:
            pygame.draw.circle(surface, (255, 210, 84), center, round(self.radius + 10), 1)
        if self.control_timer > 0:
            pygame.draw.circle(surface, (176, 112, 255), center, round(self.radius + 8), 2)
        if self.charm_timer > 0:
            pygame.draw.circle(surface, (255, 118, 214), center, round(self.radius + 8), 1)
        if self.equilibrium_mark_timer > 0:
            pulse_phase = (EQUILIBRIUM_MARK_DURATION - self.equilibrium_mark_timer) * 8.0
            pulse_strength = 0.5 + 0.5 * math.sin(pulse_phase)
            outer_alpha = int(110 + 80 * pulse_strength)
            inner_alpha = int(70 + 60 * pulse_strength)
            pygame.draw.circle(surface, (*EQUILIBRIUM_MARK_COLOR, outer_alpha), center, round(self.radius + 10 + pulse_strength * 2), 2)
            pygame.draw.circle(surface, (*EQUILIBRIUM_MARK_GLOW, inner_alpha), center, round(self.radius + 5), 1)
        if self.smasher_leap_timer > 0:
            pygame.draw.circle(surface, (255, 184, 122), center, round(self.radius + 10), 2)
        if self.swordmaster_invuln_timer > 0:
            pygame.draw.circle(surface, (250, 250, 250), center, round(self.radius + 10), 2)
            pygame.draw.circle(surface, (235, 244, 255), center, round(self.radius + 15), 1)
        if self.windrunner_storm_timer > 0:
            pygame.draw.circle(surface, (120, 248, 204), center, round(self.radius + 12), 2)
        if self.hex_curse_timer > 0:
            pygame.draw.circle(surface, (180, 72, 126), center, round(self.radius + 6), 2)
        if self.root_timer > 0:
            pygame.draw.circle(surface, (166, 132, 94), center, round(self.radius + 5), 1)
        if self.bard_song_timer > 0:
            pygame.draw.circle(surface, (142, 226, 188), center, round(self.radius + 11), 2)
        if self.gladiator_duel_timer > 0:
            pygame.draw.circle(surface, (206, 154, 98), center, round(self.radius + 9), 2)
        if self.dark_reflect_timer > 0:
            pygame.draw.circle(surface, (92, 92, 92), center, round(self.radius + 10), 2)
        if self.valkyrie_dive_timer > 0:
            pygame.draw.circle(surface, (255, 214, 88), center, round(self.radius + 12), 2)
        if self.bloodwraith_shield_timer > 0:
            pygame.draw.circle(surface, (184, 74, 92), center, round(self.radius + 7), 2)
        if self.bloodwraith_rage_active:
            pygame.draw.circle(surface, (120, 18, 24), center, round(self.radius + 11), 2)

    def draw(self, surface, label_font):
        if not self.alive:
            return
        self.draw_spawn_fx(surface)
        self.draw_shape(surface)
        self.draw_bars(surface, label_font)
        self.draw_skill_fx(surface)
        if self.is_tiger() and self.design_tiger_prey_id is not None:
            prey = next((c for c in getattr(self, "_design_cached_characters", []) if id(c) == self.design_tiger_prey_id and c.alive), None)
            if prey is not None:
                marker = label_font.render("猎", True, TIGER_HUNT_MARKER_COLOR)
                surface.blit(marker, marker.get_rect(center=(round(prey.pos.x), round(prey.pos.y - prey.radius - 30))))


def spawn_characters(count, arena_rect):
    characters = []
    job_names = get_battle_job_names()
    attempts = 0
    while len(characters) < count and attempts < 600:
        attempts += 1
        pos = random_spawn_point(arena_rect, CHARACTER_RADIUS + 14)
        if all((other.pos - pos).length() > CHARACTER_SIZE * 1.9 for other in characters):
            job_name = random.choice(job_names)
            characters.append(Character(job_name, len(characters) + 1, pos))
    while len(characters) < count:
        characters.append(
            Character(random.choice(job_names), len(characters) + 1, random_spawn_point(arena_rect, CHARACTER_RADIUS + 4))
        )
    return characters


def draw_grid(surface):
    surface.fill(BACKGROUND_COLOR)
    for x in range(0, SCREEN_WIDTH, 40):
        pygame.draw.line(surface, (22, 28, 36), (x, 0), (x, SCREEN_HEIGHT), 1)
    for y in range(0, SCREEN_HEIGHT, 40):
        pygame.draw.line(surface, (22, 28, 36), (0, y), (SCREEN_WIDTH, y), 1)
    for x in range(0, SCREEN_WIDTH, 160):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT), 1)
    for y in range(0, SCREEN_HEIGHT, 160):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (SCREEN_WIDTH, y), 1)


def draw_ui(surface, title_font, small_font, game_state):
    header_rect = pygame.Rect(ARENA_RECT.left, 10, ARENA_RECT.width, 46)
    draw_panel(surface, header_rect, (16, 22, 30), accent_color=MENU_ACCENT, radius=12, shadow_offset=(2, 3))

    title = title_font.render("圆环斗场 · 自动对战", True, TEXT_COLOR)
    surface.blit(title, (header_rect.left + 14, header_rect.top + 8))
    alive_characters = get_living_main_characters(game_state)
    elapsed = small_font.render(f"时间 {int(game_state.get('elapsed_time', 0.0)) // 60:02d}:{int(game_state.get('elapsed_time', 0.0)) % 60:02d}", True, (150, 164, 180))
    surface.blit(elapsed, (header_rect.left + 320, header_rect.top + 13))
    alive_label = small_font.render(f"存活 {len(alive_characters)}/{len(game_state.get('battle_participants', []))}", True, (110, 190, 140))
    surface.blit(alive_label, alive_label.get_rect(topright=(header_rect.right - 16, header_rect.top + 13)))

    if game_state["winner_text"]:
        banner = title_font.render(game_state["winner_text"], True, BORDER_COLOR)
        banner_rect = banner.get_rect(center=(SCREEN_WIDTH // 2, 64))
        background = banner_rect.inflate(28, 12)
        draw_panel(surface, background, (20, 26, 36), accent_color=(198, 212, 236), radius=10, shadow_offset=(2, 2))
        surface.blit(banner, banner_rect)


def create_game_state(player_count, timed_weapon_orb_drops_enabled=True):
    characters = spawn_characters(player_count, ARENA_RECT)
    initial_orb = spawn_weapon_orb(ARENA_RECT, characters, []) if timed_weapon_orb_drops_enabled else None
    weapon_orbs = [initial_orb] if initial_orb is not None else []
    return {
        "characters": characters,
        "battle_participants": list(characters),
        "projectiles": [],
        "melee_effects": [],
        "summons": [],
        "mines": [],
        "decoys": [],
        "beam_events": [],
        "attack_fx": [],
        "spell_trail_particles": [],
        "poison_fields": [],
        "frost_comets": [],
        "shield_walls": [],
        "totems": [],
        "banners": [],
        "design_summons": [],
        "design_effects": [],
        "design_death_positions": [],
        "global_time_stop_timer": 0.0,
        "global_time_stop_owner": None,
        "global_rain_timer": 0.0,
        "global_rain_owner": None,
        "global_rain_tick": 0.0,
        "last_design_skill_token": None,
        "weapon_orbs": weapon_orbs,
        "weapon_orb_target": WEAPON_ORB_TARGET if timed_weapon_orb_drops_enabled else 0,
        "weapon_orb_timer": WEAPON_ORB_RESPAWN_DELAY if timed_weapon_orb_drops_enabled else 0.0,
        "timed_weapon_orb_drops_enabled": timed_weapon_orb_drops_enabled,
        "damage_texts": [],
        "death_particles": [],
        "kill_banners": [],
        "shake_timer": 0.0,
        "shake_magnitude": 0.0,
        "winner_text": "",
        "winner_character": None,
        "result_recorded": False,
        "elapsed_time": 0.0,
    }


def update_weapon_orbs(game_state, dt):
    for orb in game_state["weapon_orbs"]:
        if orb.alive and orb.lifetime is not None:
            orb.lifetime -= dt
            if orb.lifetime <= 0:
                orb.alive = False
    game_state["weapon_orbs"] = [orb for orb in game_state["weapon_orbs"] if orb.alive]
    if not game_state.get("timed_weapon_orb_drops_enabled", True):
        return
    if len(game_state["weapon_orbs"]) >= game_state["weapon_orb_target"]:
        game_state["weapon_orb_timer"] = WEAPON_ORB_RESPAWN_DELAY
        return
    game_state["weapon_orb_timer"] -= dt
    if game_state["weapon_orb_timer"] <= 0:
        orb = spawn_weapon_orb(ARENA_RECT, game_state["characters"], game_state["weapon_orbs"])
        game_state["weapon_orbs"].append(orb)
        game_state["weapon_orb_timer"] = WEAPON_ORB_RESPAWN_DELAY


def update_world_lists(game_state, dt):
    if game_state["global_time_stop_timer"] > 0:
        game_state["global_time_stop_timer"] = max(0.0, game_state["global_time_stop_timer"] - dt)
        if game_state["global_time_stop_timer"] == 0:
            game_state["global_time_stop_owner"] = None
    if game_state["global_rain_timer"] > 0:
        game_state["global_rain_timer"] = max(0.0, game_state["global_rain_timer"] - dt)
        game_state["global_rain_tick"] += dt
        while game_state["global_rain_tick"] >= DESIGN_RAIN_INTERVAL:
            game_state["global_rain_tick"] -= DESIGN_RAIN_INTERVAL
            for target in get_targetables(game_state):
                if target.alive and target.owner_id != game_state["global_rain_owner"]:
                    target.apply_slow(0.3, 0.3)
                    target.take_damage(DESIGN_RAIN_DAMAGE, source=next((c for c in game_state["characters"] if c.owner_id == game_state["global_rain_owner"]), None), damage_type="design_spell_rain", game_state=game_state)
        if game_state["global_rain_timer"] == 0:
            game_state["global_rain_owner"] = None

    for damage_text in game_state["damage_texts"]:
        damage_text.update(dt)
    for banner in game_state.get("kill_banners", []):
        banner.update(dt)
    for particle in game_state["death_particles"]:
        particle.update(dt)
    for particle in game_state["spell_trail_particles"]:
        particle.update(dt)
    for melee_effect in game_state["melee_effects"]:
        melee_effect.update(dt)
    for projectile in game_state["projectiles"]:
        projectile.update(dt, game_state)
    for summon in game_state["summons"]:
        summon.update(dt, game_state)
    for mine in game_state["mines"]:
        mine.update(dt, game_state)
    for decoy in game_state["decoys"]:
        decoy.update(dt, game_state)
    for beam_event in game_state["beam_events"]:
        beam_event.update(dt, game_state)
    for attack_fx in game_state["attack_fx"]:
        attack_fx.update(dt)
    for poison_field in game_state["poison_fields"]:
        poison_field.update(dt, game_state)
    for frost_comet in game_state["frost_comets"]:
        frost_comet.update(dt, game_state)
    for shield_wall in game_state["shield_walls"]:
        shield_wall.update(dt, game_state)
    for totem in game_state["totems"]:
        totem.update(dt, game_state)
    for banner in game_state.get("banners", []):
        banner.update(dt, game_state)
    for summon in game_state["design_summons"]:
        summon.update(dt, game_state)
    for effect in game_state["design_effects"]:
        effect.update(dt, game_state)

    game_state["projectiles"] = [projectile for projectile in game_state["projectiles"] if projectile.alive]
    game_state["summons"] = [summon for summon in game_state["summons"] if summon.alive]
    game_state["design_summons"] = [summon for summon in game_state["design_summons"] if summon.alive]
    game_state["mines"] = [mine for mine in game_state["mines"] if mine.alive]
    game_state["decoys"] = [decoy for decoy in game_state["decoys"] if decoy.alive]
    game_state["beam_events"] = [beam for beam in game_state["beam_events"] if beam.alive]
    game_state["attack_fx"] = [attack_fx for attack_fx in game_state["attack_fx"] if attack_fx.alive]
    game_state["poison_fields"] = [field for field in game_state["poison_fields"] if field.alive]
    game_state["frost_comets"] = [comet for comet in game_state["frost_comets"] if comet.alive]
    game_state["shield_walls"] = [shield_wall for shield_wall in game_state["shield_walls"] if shield_wall.alive]
    game_state["totems"] = [totem for totem in game_state["totems"] if totem.alive]
    game_state["banners"] = [banner for banner in game_state.get("banners", []) if banner.alive]
    game_state["design_effects"] = [effect for effect in game_state["design_effects"] if effect.alive]
    game_state["weapon_orbs"] = [orb for orb in game_state["weapon_orbs"] if orb.alive]
    game_state["damage_texts"] = [damage_text for damage_text in game_state["damage_texts"] if damage_text.alive]
    game_state["death_particles"] = [particle for particle in game_state["death_particles"] if particle.alive]
    game_state["kill_banners"] = [banner for banner in game_state.get("kill_banners", []) if banner.alive]
    game_state["spell_trail_particles"] = [particle for particle in game_state["spell_trail_particles"] if particle.alive]
    game_state["melee_effects"] = [melee_effect for melee_effect in game_state["melee_effects"] if melee_effect.alive]
    if game_state["shake_timer"] > 0:
        game_state["shake_timer"] = max(0.0, game_state["shake_timer"] - dt)
        if game_state["shake_timer"] == 0:
            game_state["shake_magnitude"] = 0.0


def draw_world(surface, game_state, label_font):
    for orb in game_state["weapon_orbs"]:
        orb.draw(surface, label_font)
    for mine in game_state["mines"]:
        mine.draw(surface)
    for effect in game_state["design_effects"]:
        effect.draw(surface)
    for poison_field in game_state["poison_fields"]:
        poison_field.draw(surface)
    for shield_wall in game_state["shield_walls"]:
        shield_wall.draw(surface)
    for totem in game_state["totems"]:
        totem.draw(surface)
    for banner in game_state.get("banners", []):
        banner.draw(surface)
    for decoy in game_state["decoys"]:
        decoy.draw(surface)
    for summon in game_state["summons"]:
        summon.draw(surface)
    for summon in game_state["design_summons"]:
        summon.draw(surface)
    for melee_effect in game_state["melee_effects"]:
        melee_effect.draw(surface)
    for frost_comet in game_state["frost_comets"]:
        frost_comet.draw(surface)
    for projectile in game_state["projectiles"]:
        projectile.draw(surface)
    for beam_event in game_state["beam_events"]:
        beam_event.draw(surface)
    for attack_fx in game_state["attack_fx"]:
        attack_fx.draw(surface)
    for particle in game_state["spell_trail_particles"]:
        particle.draw(surface)
    for character in game_state["characters"]:
        character.draw(surface, label_font)
    executioner_present = any(
        character.alive and character.design_meta.get("role_num") == 63 for character in game_state["characters"]
    )
    if executioner_present:
        for character in game_state["characters"]:
            if character.alive and character.hp > 0 and character.hp <= character.max_hp * 0.15:
                mark = label_font.render("!", True, (255, 72, 72))
                surface.blit(mark, mark.get_rect(midbottom=(round(character.pos.x), round(character.pos.y - character.radius - 15))))
    for particle in game_state["death_particles"]:
        particle.draw(surface)
    if GAME_SETTINGS.get("show_damage_numbers", True):
        for damage_text in game_state["damage_texts"]:
            damage_text.draw(surface, label_font)
    for banner in game_state.get("kill_banners", []):
        banner.draw(surface, label_font)
    active_members = [c for c in game_state.get("characters", []) if getattr(c, "design_tide_link_active", False)]
    if len(active_members) >= 2:
        hub = next((c for c in active_members if getattr(c, "design_tide_hub_id", None) is None), None)
        if hub is None:
            hub_id = active_members[0].design_tide_hub_id
            hub = next((c for c in game_state.get("characters", []) if c.alive and c.id == hub_id), None)
        if hub is not None:
            for member in active_members:
                if member is not hub:
                    pygame.draw.line(
                        surface,
                        TIDE_COLOR,
                        (round(hub.pos.x), round(hub.pos.y)),
                        (round(member.pos.x), round(member.pos.y)),
                        2,
                    )