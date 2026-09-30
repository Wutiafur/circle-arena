# -*- coding: utf-8 -*-
"""战斗核心：目标选择 / 特效实体 / 技能分派。

与 character.py 相互引用（isinstance / 构造），由 character.py 底部导入本模块解环。
"""
import math
import random

import pygame

from game.data import *
from game.utils import *
from game.drawing import *
from game.character import Character

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


class _TargetableProps:
    """非角色「可被选为目标」实体（诱饵/召唤物/图腾/旗帜）的宽容属性兜底。

    get_targetables 会混入这些非角色实体，而技能/普攻代码可能访问 Character
    专属属性（design_* / id），此前会抛 AttributeError 崩溃。这里统一兜底：
      - id          -> None（表示非角色、无角色编号）
      - design_*    -> 按后缀返回 None/False/[]/0.0（等效"未施加该状态"）
    注意：__getattr__ 仅在属性未定义时被调用，不影响真实属性与 take_damage 等方法。
    """
    def __getattr__(self, name):
        if name == "id":
            return None
        if not name.startswith("design_"):
            raise AttributeError(name)
        if name.endswith(("_owner_id", "_target_id", "_source", "_target")):
            return None
        if name.endswith(("_marked", "_flag", "_locked")):
            return False
        if name.endswith("_effects"):
            return []
        return 0.0


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


class Summon(_TargetableProps):
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


class Totem(_TargetableProps):
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


class Banner(_TargetableProps):
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
                    missing_hp = max(0.0, getattr(target, "max_hp", 0.0) - max(0.0, getattr(target, "hp", 0.0)))
                    damage = (SOUL_NINE_SLASH_DAMAGE + SOUL_NINE_SLASH_LOST_HP_RATIO * missing_hp) * (SOUL_NINE_SLASH_CRIT_MULT if crit else 1.0)
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
        elif self.effect_type == "charge_siphon":
            # 吸能流光（纯视觉）：金色光点从目标起沿直线飞向充能师，0.4 秒后消散
            owner = self.owner
            if owner is not None and getattr(owner, "alive", False):
                start_vec = pygame.Vector2(self.data.get("start_pos", pygame.Vector2(self.pos)))
                progress = clamp(self.timer / max(0.001, CHARGE_SIPHON_FX_DURATION), 0.0, 1.0)
                self.pos = start_vec.lerp(owner.pos, progress)
            if self.lifetime <= 0:
                self.alive = False
        elif self.effect_type == "laze":
            # 聚光使【激光滋人】：跟随目标，第 1/2/3 秒各结算 30/40/50 法伤，每次结算给自身回蓝
            target_id = self.data.get("target_id")
            target = None
            for candidate in get_targetables(game_state):
                if id(candidate) == target_id and candidate.alive:
                    target = candidate
                    break
            if target is None or not target.alive or self.owner is None or not getattr(self.owner, "alive", False):
                self.alive = False
                return
            self.pos = pygame.Vector2(target.pos)
            schedule = self.data.get("damage_schedule", (30.0, 40.0, 50.0))
            step = int(min(len(schedule), self.timer // 1.0))
            done = int(self.data.get("ticks_done", 0))
            while done < step:
                done += 1
                if done <= len(schedule):
                    target.take_damage(
                        float(schedule[done - 1]),
                        source=self.owner,
                        damage_type="design_spell_laze",
                        game_state=game_state,
                    )
                    if self.owner is not None and getattr(self.owner, "alive", False):
                        self.owner.gain_mp(getattr(self.owner, "max_hp", 1000.0) * self.data.get("mp_gain_ratio", LAZE_MP_GAIN_RATIO), "laze_hit")
                    game_state["beam_events"].append(BeamEvent(self.owner.pos, target.pos, LAZE_CORE_COLOR))
                    spawn_attack_impact(game_state, target.pos, LAZE_COLOR, radius=10, thickness=2, burst_count=6)
            self.data["ticks_done"] = done
            if self.lifetime <= 0:
                self.alive = False
        elif self.effect_type == "pierce_ray":
            # 贯穿激光：慢速转向跟随最近敌人，每秒对激光命中敌人造成 40 法伤 + 削减 1% 法抗
            owner = self.owner
            if owner is None or not getattr(owner, "alive", False):
                self.alive = False
                return
            # 慢速转向最近敌人（转角速度限制）
            nearest = select_nearest_enemy(owner, game_state["characters"])
            if nearest is not None:
                desired = nearest.pos - owner.pos
                if desired.length_squared() > 0.001:
                    desired = desired.normalize()
                    current = self.direction
                    max_turn = self.data.get("turn_speed", RAY_TURN_SPEED) * dt
                    # 计算当前方向与期望方向夹角，一帧内最多转过 max_turn 弧度
                    cross = current.x * desired.y - current.y * desired.x
                    dot = clamp(current.x * desired.x + current.y * desired.y, -1.0, 1.0)
                    angle_diff = math.acos(dot)
                    if angle_diff > 1e-4:
                        turn = min(angle_diff, max_turn)
                        sign = 1.0 if cross >= 0 else -1.0
                        self.direction = current.rotate(math.degrees(sign * turn))
            # 每秒结算一次（每秒 40 法伤 + 每秒 -1% 法抗）
            self.data["tick_acc"] = self.data.get("tick_acc", 0.0) + dt
            if self.data["tick_acc"] >= 1.0:
                self.data["tick_acc"] -= 1.0
                start_pos = self.pos - self.direction * 750.0
                end_pos = self.pos + self.direction * 750.0
                beam_hit = False
                for victim in get_targetables(game_state):
                    if not victim.alive or victim.owner_id == self.owner_id:
                        continue
                    dist_to_ray = distance_point_to_segment(victim.pos, start_pos, end_pos)
                    if dist_to_ray <= victim.radius + self.radius:
                        victim.take_damage(float(self.data.get("dps", RAY_DPS)), source=owner, damage_type="design_spell_pierce_ray", game_state=game_state)
                        if hasattr(victim, "apply_laser_resist_penalty"):
                            victim.apply_laser_resist_penalty(self.data.get("resist_step", RAY_RESIST_STEP), self.lifetime)
                        beam_hit = True
                if beam_hit:
                    spawn_attack_impact(game_state, start_pos + (end_pos - start_pos) * 0.3, RAY_COLOR, radius=16, thickness=3, burst_count=6)
            if self.lifetime <= 0:
                self.alive = False
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
        elif self.effect_type == "charge_siphon":
            # 吸能流光：飞行光点 + 累积拖尾（沿起点→充能师方向渐隐）
            owner = self.owner
            if owner is not None and getattr(owner, "alive", False):
                start_vec = pygame.Vector2(self.data.get("start_pos", pygame.Vector2(self.pos)))
                progress = clamp(self.timer / max(0.001, CHARGE_SIPHON_FX_DURATION), 0.0, 1.0)
                flow = start_vec - owner.pos
                flow_len = flow.length()
                flow_dir = flow / flow_len if flow_len > 0.001 else pygame.Vector2(1, 0)
                center = (round(self.pos.x), round(self.pos.y))
                pygame.draw.circle(overlay, (*CHARGE_GOLD, 200), center, 3)
                pygame.draw.circle(overlay, (255, 244, 190, 220), center, 1)
                # 拖尾：往回 3 段渐隐小点
                for i in range(3):
                    tail_p = self.pos + flow_dir * (6 + i * 7)
                    pygame.draw.circle(overlay, (*CHARGE_GOLD, max(24, 120 - i * 34)), (round(tail_p.x), round(tail_p.y)), max(1, 2 - i // 2))
        elif self.effect_type == "laze":
            # 激光滋人：从充能师到目标的细激光束（红芯 + 白炽描边）
            owner = self.owner
            if owner is not None and getattr(owner, "alive", False):
                start = (round(owner.pos.x), round(owner.pos.y))
                end = (round(self.pos.x), round(self.pos.y))
                pulse = 0.7 + 0.3 * math.sin(self.timer * 20.0)
                pygame.draw.line(overlay, (*LAZE_COLOR, int(150 * pulse)), start, end, 7)
                pygame.draw.line(overlay, (*LAZE_CORE_COLOR, int(235 * pulse)), start, end, 3)
        elif self.effect_type == "pierce_ray":
            # 贯穿激光：宽 50 的粗光束（红晕外层 + 白炽内核），贯穿全场
            owner = self.owner
            if owner is not None and getattr(owner, "alive", False):
                start_pos = self.pos - self.direction * 750.0
                end_pos = self.pos + self.direction * 750.0
                perp = pygame.Vector2(-self.direction.y, self.direction.x)
                half = RAY_WIDTH / 2.0
                pulse = 0.85 + 0.15 * math.sin(self.timer * 14.0)
                outer_color = (*RAY_COLOR, int(70 * pulse))
                inner_color = (*RAY_CORE_COLOR, int(180 * pulse))
                poly = [
                    (round(start_pos.x + perp.x * half), round(start_pos.y + perp.y * half)),
                    (round(end_pos.x + perp.x * half), round(end_pos.y + perp.y * half)),
                    (round(end_pos.x), round(end_pos.y)),
                    (round(end_pos.x - perp.x * half), round(end_pos.y - perp.y * half)),
                    (round(start_pos.x - perp.x * half), round(start_pos.y - perp.y * half)),
                ]
                pygame.draw.polygon(overlay, outer_color, poly)
                pygame.draw.line(overlay, inner_color, (round(start_pos.x), round(start_pos.y)), (round(end_pos.x), round(end_pos.y)), 5)
                pygame.draw.line(overlay, (*LAZE_CORE_COLOR, int(90 * pulse)), (round(start_pos.x), round(start_pos.y)), (round(end_pos.x), round(end_pos.y)), 10)
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


class DesignSummon(_TargetableProps):
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
    if role_num == 128:
        # 聚光使被动【激光滋人】：普攻替换为锁定目标照射 3 秒的激光（逐秒 30/40/50 法伤），攻击间隔 6 秒
        add_design_effect(
            game_state,
            DesignEffect(
                "laze",
                attacker,
                pygame.Vector2(target.pos),
                radius=LAZE_CORE_WIDTH,
                lifetime=LAZE_DURATION,
                target_id=id(target),
                damage_schedule=LAZE_DAMAGES,
                mp_gain_ratio=LAZE_MP_GAIN_RATIO,
            ),
        )
        game_state["beam_events"].append(BeamEvent(attacker.pos, target.pos, LAZE_CORE_COLOR))
        attacker.attack_cooldown = LAZE_INTERVAL
        attacker.on_attack_committed()
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
        thrust_damage = attacker.get_current_basic_damage() * 0.8 * attacker.get_target_attack_bonus(target)
        dealt = target.take_damage(thrust_damage, source=attacker, damage_type="basic_melee", game_state=game_state, ignore_physical_resistance=True)
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
    if role_num == 59 and isinstance(target, Character) and attacker.design_ranger_lock_timer > 0 and attacker.design_ranger_lock_target_id == target.id:
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
                    if isinstance(victim, Character):
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
                        if isinstance(enemy, Character):
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
                if (enemy.pos - caster.pos).length() <= 40.0 + getattr(enemy, "radius", 0) and isinstance(enemy, Character):
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
                    if isinstance(enemy, Character):
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
            if isinstance(enemy, Character):
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
                if isinstance(enemy, Character):
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
                if knock_dir.length_squared() > 0 and isinstance(enemy, Character):
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
                if isinstance(enemy, Character):
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
    elif token == "charge_drain":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None and target.alive:
            target_mp = max(0.0, float(getattr(target, "mp", 0.0)))
            # 能量强夺：削减 15% 当前 MP + 12 法伤；转化 5% 目标当前 MP 存入 stash，
            # 待 cast_skill 技能消耗(mp=0)后在下一帧 update 注入自身，避免被归零抹掉
            target.mp = max(0.0, target_mp - target_mp * CHARGE_DRAIN_MP_RATIO)
            caster.design_drain_stash = getattr(caster, "design_drain_stash", 0.0) + target_mp * CHARGE_DRAIN_SELF_MP_RATIO
            target.take_damage(CHARGE_DRAIN_DAMAGE, source=caster, damage_type="design_spell_charge_drain", game_state=game_state)
            game_state["beam_events"].append(BeamEvent(caster.pos, target.pos, CHARGE_GOLD))
            spawn_attack_impact(game_state, target.pos, CHARGE_GOLD, radius=13, thickness=3, burst_count=10)
            # 吸能流光：0.4 秒金色光点从目标飞向充能师
            add_design_effect(
                game_state,
                DesignEffect(
                    "charge_siphon",
                    caster,
                    pygame.Vector2(target.pos),
                    lifetime=CHARGE_SIPHON_FX_DURATION,
                    target_id=id(target),
                    start_pos=pygame.Vector2(target.pos),
                ),
            )
    elif token == "pierce_ray":
        # 聚光使【贯穿激光】：从角色面向方向发射宽 50 全场激光，持续 5 秒；
        # 引导期间角色定身、不回复 MP 且不能再次释放主动技能
        if getattr(caster, "design_ray_channel_timer", 0.0) > 0:
            return False
        # 初始方向 = 角色当前面向（facing_angle），而非直接瞄准最近敌人
        face_rad = math.radians(getattr(caster, "facing_angle", 0.0))
        direction = pygame.Vector2(math.cos(face_rad), math.sin(face_rad))
        if direction.length_squared() < 0.01:
            direction = pygame.Vector2(caster.recent_move_dir) if caster.recent_move_dir.length_squared() > 0.01 else pygame.Vector2(1, 0)
        direction = direction.normalize()
        add_design_effect(
            game_state,
            DesignEffect(
                "pierce_ray",
                caster,
                pygame.Vector2(caster.pos),
                lifetime=RAY_DURATION,
                radius=RAY_WIDTH / 2.0,
                direction=pygame.Vector2(direction),
                dps=RAY_DPS,
                resist_step=RAY_RESIST_STEP,
                turn_speed=RAY_TURN_SPEED,
            ),
        )
        caster.design_ray_channel_timer = RAY_DURATION
        game_state["beam_events"].append(BeamEvent(caster.pos, caster.pos + direction * 1200, RAY_COLOR))
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
        # 冷锋枪插地实体：这是技能自带的实体长枪（有绘制、可拾取、5 秒后消失），
        # 不受「定时武器掉落」开关限制——关掉定时掉落时冷锋枪实体依然存在
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
                if isinstance(enemy, Character):
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
    elif token == "thunder_breath":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return False
        if caster.thunder_enhance_timer > 0:
            # 第二形态：霹雳一闪·六连（用一次后变回常态）
            caster.thunder_enhance_timer = 0.0
            caster.design_untargetable_timer = max(caster.design_untargetable_timer, 1.0)
            dash_dir = target.pos - caster.pos
            if dash_dir.length_squared() > 0:
                dash_dir = dash_dir.normalize()
                caster.pos = target.pos - dash_dir * (target.radius + caster.radius + 6.0)
                caster.pos.x = clamp(caster.pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
                caster.pos.y = clamp(caster.pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
                caster.update_rect()
            game_state["beam_events"].append(BeamEvent(caster.pos, target.pos, THUNDER_COLOR))
            knock = target.pos - caster.pos
            if knock.length_squared() == 0:
                knock = random_unit_vector()
            target.apply_knockup(knock, THUNDER_SIX_KNOCKUP_DISTANCE, THUNDER_SIX_KNOCKUP_DURATION)
            for _ in range(5):
                target.take_damage(THUNDER_SIX_FIRST_DAMAGE, source=caster, damage_type="design_physical_thunder_six", game_state=game_state)
            for enemy in enemies:
                if enemy.alive and (enemy.pos - target.pos).length() <= THUNDER_SIX_FINAL_RADIUS + getattr(enemy, "radius", 0):
                    final_damage = THUNDER_SIX_FINAL_DAMAGE
                    if enemy is target:
                        final_damage += max(0.0, target.max_hp - target.hp) * THUNDER_SIX_EXECUTE_RATIO
                    enemy.take_damage(final_damage, source=caster, damage_type="design_physical_thunder_lightning", game_state=game_state)
            spawn_attack_impact(game_state, target.pos, THUNDER_COLOR, radius=THUNDER_SIX_FINAL_RADIUS, thickness=3, burst_count=20)
            return True
        # 第一形态：霹雳一闪（三段冲刺，命中叠雷印，满 4 层进入强化）
        caster.thunder_resist_timer = THUNDER_SLASH_RESIST_DURATION
        slash_dir = target.pos - caster.pos
        if slash_dir.length_squared() == 0:
            slash_dir = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        slash_dir = slash_dir.normalize()
        for _ in range(3):
            start = pygame.Vector2(caster.pos)
            end = caster.pos + slash_dir * THUNDER_SLASH_DASH
            end.x = clamp(end.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
            end.y = clamp(end.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
            game_state["beam_events"].append(BeamEvent(start, end, THUNDER_COLOR))
            for enemy in enemies:
                if enemy.alive and distance_point_to_segment(enemy.pos, start, end) <= getattr(enemy, "radius", 0) + 16:
                    mark = min(THUNDER_MARK_MAX, int(getattr(enemy, "thunder_mark", 0)))
                    slash_damage = THUNDER_SLASH_DAMAGE * (1.0 + mark * THUNDER_SLASH_MARK_DAMAGE_BONUS)
                    enemy.take_damage(slash_damage, source=caster, damage_type="design_physical_thunder_slash", game_state=game_state)
                    if isinstance(enemy, Character):
                        caster.heal(THUNDER_SLASH_HEAL_CHAR)
                        enemy.thunder_mark = mark + 1
                        if enemy.thunder_mark >= THUNDER_MARK_MAX:
                            enemy.thunder_mark = 0
                            caster.thunder_enhance_timer = max(caster.thunder_enhance_timer, THUNDER_ENHANCE_DURATION)
                    else:
                        caster.heal(THUNDER_SLASH_HEAL_PROP)
            caster.pos = end
            caster.update_rect()
        return True
    elif token == "grudge_ult":
        # 加倍奉还：最近敌人 20+1×普攻 + 2流血 + 击退40，流血≥6时威力+20%
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            ult_damage = GRUDGE_ULT_DAMAGE_BASE + GRUDGE_ULT_ATTACK * caster.get_current_basic_damage()
            if int(getattr(target, "bleed_stacks", 0)) >= GRUDGE_ULT_BLEED_THRESHOLD:
                ult_damage *= 1.0 + GRUDGE_ULT_BLEED_BONUS
            target.take_damage(ult_damage, source=caster, damage_type="design_physical_grudge_ult", game_state=game_state)
            if isinstance(target, Character):
                target.apply_bleed(GRUDGE_ULT_BLEED)
                knock = target.pos - caster.pos
                if knock.length_squared() > 0:
                    target.apply_knockback(knock.normalize(), GRUDGE_ULT_KNOCKBACK)
            spawn_attack_impact(game_state, target.pos, GRUDGE_COLOR, radius=14, thickness=3, burst_count=12)
        return True
    elif token == "prelate_ult":
        # 消耗全部嫉妒-仇怨 → 长姊；技能后可拆开包装；莱瓦汀时改用即刻处刑
        caster.gain_prelate_elder_from_resentment()
        caster.prelate_resentment = 0
        caster.prelate_wrap_pending = True
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is None:
            return True
        if caster.prelate_leavatin:
            # 即刻处刑：长姊+10%、目标燃烧+流血每2层+1%(≤40%)、前三下2×普攻、第四眩晕+60、第五蓄力3s
            bonus = 1.0 + (PRELATE_EXE_ELDER_BONUS if caster.prelate_elder_mark >= 1 else 0.0)
            burnbleed = int(getattr(target, "burn_stacks", 0)) + int(getattr(target, "bleed_stacks", 0))
            bonus += min(PRELATE_EXE_MAX_BONUS, (burnbleed // PRELATE_EXE_BURNBLEED_PER) * 0.01)
            first = PRELATE_EXE_ATTACK_MULT * caster.get_current_basic_damage() * bonus
            target.take_damage(first * PRELATE_EXE_FIRST_HITS, source=caster, damage_type="design_physical_prelate_exe", game_state=game_state)
            if isinstance(target, Character):
                target.apply_burn(PRELATE_EXE_BURN)
                target.apply_bleed(PRELATE_EXE_BLEED)
            target.take_damage(PRELATE_EXE_FOURTH_DAMAGE * bonus, source=caster, damage_type="design_physical_prelate_exe3", game_state=game_state)
            if isinstance(target, Character):
                target.apply_stun(PRELATE_EXE_STUN)
            caster.prelate_exe_charge = PRELATE_EXE_CHARGE
            caster.prelate_exe_target_id = target.id
        else:
            # 仇怨重踏：4 次攻击，每次 12 物理 + 1 流血
            for _ in range(PRELATE_ULT_HITS):
                target.take_damage(PRELATE_ULT_DAMAGE, source=caster, damage_type="design_physical_prelate_ult", game_state=game_state)
                if isinstance(target, Character):
                    target.apply_bleed(PRELATE_ULT_BLEED)
        return True
    elif token == "loyal_vanguard":
        # 忠义的证明：对最近敌人造成 40+1×普攻 物理伤害并眩晕 3 秒
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            ult_damage = LOYAL_ULT_DAMAGE_BASE + LOYAL_ULT_ATTACK * caster.get_current_basic_damage()
            target.take_damage(ult_damage, source=caster, damage_type="design_physical_loyal_ult", game_state=game_state)
            if isinstance(target, Character):
                target.apply_stun(LOYAL_ULT_STUN)
            spawn_attack_impact(game_state, target.pos, LOYAL_COLOR, radius=16, thickness=3, burst_count=12)
        return True
    elif token == "envy_priest":
        if caster.anger >= ENVY_ANGER_MAX:
            # 清算：消耗全部怒火，蓄力 5 秒（蓄力期间受伤 -40% 在 take_damage 处理）
            caster.anger = 0
            caster.envy_cast_type = "liquidation"
            caster.envy_charge_timer = ENVY_LIQUIDATION_CHARGE
        else:
            # 尝尝这个：蓄力 3 秒，记录面朝方向
            direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
            caster.envy_cast_type = "flash"
            caster.envy_charge_timer = ENVY_FLASH_CHARGE
            caster.envy_cast_dir = direction.normalize()
        return True
    elif token == "zashiki":
        # 祸福相生：消耗 8% 当前生命，半径 100 AoE，缺失生命越高伤害越高，命中角色 +2 鬼火
        caster.take_damage(caster.hp * 0.08, source=caster, damage_type="true_zashiki_cost", game_state=game_state)
        for enemy in enemies:
            if enemy.alive and (enemy.pos - caster.pos).length() <= ZASHIKI_ULT_RADIUS + getattr(enemy, "radius", 0):
                base = ZASHIKI_ULT_DAMAGE_BASE + ZASHIKI_ULT_ATTACK_RATIO * caster.get_current_basic_damage() + ZASHIKI_ULT_MAXHP_RATIO * caster.max_hp
                missing_pct = max(0.0, enemy.max_hp - enemy.hp) / max(1.0, enemy.max_hp) * 100.0
                execute_bonus = min(ZASHIKI_ULT_EXECUTE_CAP, missing_pct * 0.01)
                dealt = enemy.take_damage(base * (1.0 + execute_bonus), source=caster, damage_type="design_spell_zashiki_ult", game_state=game_state)
                if isinstance(enemy, Character) and dealt > 0:
                    caster.soul_fire = min(SOUL_FIRE_MAX, caster.soul_fire + ZASHIKI_ULT_FIRE_GAIN)
        spawn_attack_impact(game_state, caster.pos, ZASHIKI_COLOR, radius=ZASHIKI_ULT_RADIUS, thickness=3, burst_count=20)
        return True
    elif token == "throw_arsenal":
        target = select_nearest_enemy(caster, game_state["characters"])
        if target is not None:
            spawn_design_projectile(caster, game_state, target.pos - caster.pos, 100.0, "design_physical_throw", (244, 220, 176), speed=360.0, max_range=320.0)
        caster.clear_weapon()
    return True


class Decoy(_TargetableProps):
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

