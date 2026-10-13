# -*- coding: utf-8 -*-
"""绘制辅助：形状图标 / 图鉴与效果详情面板。"""
import pygame

from game.data import *
from game.utils import *

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
    elif shape == "hammer":
        # 钉锤形：圆锤头 + 短柄（随朝向旋转由 draw_shape 处理）
        pygame.draw.circle(surface, color, (center[0] - int(radius * 0.22), center[1]), round(radius * 0.82))
        handle = pygame.Rect(0, 0, radius * 0.34, radius * 1.5)
        handle.center = (center[0] + int(radius * 0.52), center[1])
        pygame.draw.rect(surface, tuple(max(50, int(channel * 0.8)) for channel in color), handle, border_radius=3)
        pygame.draw.line(surface, tuple(min(255, int(channel + 42)) for channel in color), (center[0] - int(radius * 0.6), center[1]), (center[0] + int(radius * 0.15), center[1]), max(2, int(radius * 0.18)))
    elif shape == "slab":
        # 方砖形：菱形砖块 + 十字砖缝
        points = [
            (center[0], center[1] - radius),
            (center[0] + radius, center[1]),
            (center[0], center[1] + radius),
            (center[0] - radius, center[1]),
        ]
        pygame.draw.polygon(surface, color, points)
        mortar = tuple(min(255, int(channel + 50)) for channel in color)
        pygame.draw.line(surface, mortar, (center[0] - int(radius * 0.55), center[1]), (center[0] + int(radius * 0.55), center[1]), max(2, int(radius * 0.2)))
        pygame.draw.line(surface, mortar, (center[0], center[1] - int(radius * 0.55)), (center[0], center[1] + int(radius * 0.55)), max(2, int(radius * 0.2)))
    elif shape == "bulwark":
        # 重盾形：椭圆大盾 + 盾面中线 + 顶部铆钉
        shield_rect = pygame.Rect(0, 0, radius * 1.75, radius * 2.2)
        shield_rect.center = center
        pygame.draw.ellipse(surface, color, shield_rect)
        pygame.draw.line(surface, tuple(min(255, int(channel + 40)) for channel in color), (center[0], shield_rect.top + 4), (center[0], shield_rect.bottom - 6), max(2, int(radius * 0.16)))
        rivet_y = shield_rect.top + int(radius * 0.35)
        pygame.draw.circle(surface, (255, 214, 120), (center[0] - int(radius * 0.4), rivet_y), max(2, int(radius * 0.14)))
        pygame.draw.circle(surface, (255, 214, 120), (center[0] + int(radius * 0.4), rivet_y), max(2, int(radius * 0.14)))
    elif shape == "long_blade":
        # 长剑形：细长剑刃 + 中脊线（随朝向旋转）
        blade = [
            (center[0], center[1] - radius * 1.35),
            (center[0] + radius * 0.5, center[1] + radius * 0.35),
            (center[0] + radius * 0.28, center[1] + radius * 0.7),
            (center[0] - radius * 0.28, center[1] + radius * 0.7),
            (center[0] - radius * 0.5, center[1] + radius * 0.35),
        ]
        pygame.draw.polygon(surface, color, blade)
        pygame.draw.line(surface, tuple(min(255, int(channel + 46)) for channel in color), (center[0], center[1] - radius * 1.15), (center[0], center[1] + radius * 0.5), max(1, int(radius * 0.14)))
    elif shape == "squad_flag":
        # 指挥旗形：旗杆 + 上方指挥三角旗 + 底端旗穗
        pole = pygame.Rect(0, 0, radius * 0.18, radius * 2.1)
        pole.center = (center[0], center[1])
        pygame.draw.rect(surface, tuple(min(255, int(channel + 40)) for channel in color), pole, border_radius=2)
        flag = [
            (center[0] + radius * 0.1, center[1] - radius * 0.95),
            (center[0] + radius * 1.05, center[1] - radius * 0.62),
            (center[0] + radius * 0.1, center[1] - radius * 0.28),
        ]
        pygame.draw.polygon(surface, color, flag)
        pygame.draw.line(surface, (255, 230, 160), (center[0], center[1] - radius * 0.95), (center[0], center[1] + radius * 1.05), max(2, int(radius * 0.16)))
    elif shape == "sparrow_feather":
        # 雀羽形：两片斜羽 + 中心羽轴点
        feather_a = [
            (center[0] - radius * 0.1, center[1] - radius),
            (center[0] + radius * 0.95, center[1] - radius * 0.18),
            (center[0] + radius * 0.1, center[1] + radius * 0.62),
        ]
        feather_b = [
            (center[0] + radius * 0.1, center[1] - radius * 0.62),
            (center[0] + radius * 0.98, center[1] + radius * 0.18),
            (center[0] - radius * 0.1, center[1] + radius),
        ]
        pygame.draw.polygon(surface, color, feather_a)
        pygame.draw.polygon(surface, color, feather_b)
        pygame.draw.circle(surface, tuple(min(255, int(channel + 24)) for channel in color), center, max(2, int(radius * 0.22)))
    elif shape == "raikiri_blade":
        # 雷刃形：锯齿闪电刃条 + 亮蓝电芯线
        blade = [
            (center[0], center[1] - radius * 1.2),
            (center[0] + radius * 0.5, center[1] - radius * 0.55),
            (center[0] + radius * 0.12, center[1] - radius * 0.5),
            (center[0] + radius * 0.75, center[1] + radius * 0.15),
            (center[0] + radius * 0.05, center[1] + radius * 0.2),
            (center[0] + radius * 0.6, center[1] + radius * 0.85),
            (center[0] - radius * 0.45, center[1] + radius * 0.1),
            (center[0] - radius * 0.15, center[1] + radius * 0.15),
            (center[0] - radius * 0.6, center[1] - radius * 0.6),
            (center[0] - radius * 0.05, center[1] - radius * 0.55),
        ]
        pygame.draw.polygon(surface, color, blade)
        pygame.draw.line(surface, (235, 250, 255), (center[0], center[1] - radius * 0.9), (center[0] - radius * 0.05, center[1] + radius * 0.5), max(1, int(radius * 0.15)))
    elif shape == "shiro_fox":
        # 狐尾燕尾形：分叉狐尾 + 顶部两片狐耳
        tail = [
            (center[0], center[1] + radius * 0.7),
            (center[0] + radius * 0.85, center[1] + radius * 0.8),
            (center[0] + radius * 0.55, center[1] + radius * 0.1),
            (center[0] + radius * 0.95, center[1] - radius * 0.65),
            (center[0] + radius * 0.2, center[1] - radius * 0.3),
            (center[0], center[1] - radius * 0.95),
            (center[0] - radius * 0.2, center[1] - radius * 0.3),
            (center[0] - radius * 0.95, center[1] - radius * 0.65),
            (center[0] - radius * 0.55, center[1] + radius * 0.1),
            (center[0] - radius * 0.85, center[1] + radius * 0.8),
        ]
        pygame.draw.polygon(surface, color, tail)
        pygame.draw.circle(surface, (150, 168, 210), (center[0] - int(radius * 0.42), center[1] - int(radius * 0.4)), max(1, int(radius * 0.16)))
        pygame.draw.circle(surface, (150, 168, 210), (center[0] + int(radius * 0.42), center[1] - int(radius * 0.4)), max(1, int(radius * 0.16)))
    else:
        pygame.draw.polygon(surface, color, regular_polygon_points(center, radius, 8, math.pi / 8))
    if outline:
        pygame.draw.circle(surface, BORDER_COLOR, center, round(radius + 2), 2)


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
        (POKEDEX_UI_TEXT["labels"]["hp_regen"], f"{data['hp_regen']:g} 点/秒"),
        (POKEDEX_UI_TEXT["labels"]["mp_charge"], data["display_mp_charge_style"]),
        (POKEDEX_UI_TEXT["labels"]["skill"], data["display_skill_name"]),
    ]
    # 绝影枪客【追风之触】：普攻伤害 = 基础 + (移速/100 - 1)×60，图鉴标注当前移速下的实际普攻
    if job_name == PHANTOM_LANCER_JOB_NAME:
        speed_ratio = float(data["move_speed"]) / 100.0
        wind_bonus = max(0.0, speed_ratio - 1.0) * 60.0
        details[3] = (
            POKEDEX_UI_TEXT["labels"]["attack_damage"],
            f"{data['attack_damage']:g}（追风+{wind_bonus:.0f}={data['attack_damage'] + wind_bonus:.0f}）",
        )
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

