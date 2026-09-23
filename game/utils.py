# -*- coding: utf-8 -*-
"""纯工具函数：颜色 / 几何 / 文本 / 随机（仅依赖 data 常量，无游戏状态依赖）。"""
import math
import random

import pygame

from game.data import *

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
