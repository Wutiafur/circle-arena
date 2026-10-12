# -*- coding: utf-8 -*-
"""世界层：刷怪 / 场景绘制 / 游戏状态创建 / 世界列表更新（顶层消费者）。"""
import random

import pygame

from game.data import *
from game.utils import *
from game.engine import *
from game.character import *

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
        "rain_splashes": [],
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
                    if isinstance(target, Character):
                        target.apply_slow(0.3, 0.3)
                    target.take_damage(DESIGN_RAIN_DAMAGE, source=next((c for c in game_state["characters"] if c.owner_id == game_state["global_rain_owner"]), None), damage_type="design_spell_rain", game_state=game_state)
        # 雨特效：斜雨丝（时间相位推进）+ 随机溅水花
        rain_elapsed = DESIGN_RAIN_DURATION - game_state["global_rain_timer"]
        game_state["rain_elapsed"] = rain_elapsed
        splashes = game_state.get("rain_splashes", [])
        for splash in splashes:
            splash["t"] += dt
        if len(splashes) < RAIN_SPLASH_COUNT and random.random() < 0.75:
            splashes.append({
                "x": random.uniform(ARENA_RECT.left + 8.0, ARENA_RECT.right - 8.0),
                "y": random.uniform(ARENA_RECT.top + 6.0, ARENA_RECT.bottom - 6.0),
                "t": 0.0,
            })
        game_state["rain_splashes"] = [s for s in splashes if s["t"] < RAIN_SPLASH_LIFETIME]
        if game_state["global_rain_timer"] == 0:
            game_state["global_rain_owner"] = None
            game_state["rain_splashes"] = []

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
    # 唤雨师【季风骤雨】特效：斜雨丝 + 地面溅水花
    if game_state["global_rain_timer"] > 0:
        rain_elapsed = game_state.get("rain_elapsed", 0.0)
        slope = RAIN_FX_ANGLE_SLOPE
        fall_dist = ARENA_RECT.height + RAIN_FX_DROP_LEN * 3.0
        seed_base = 97
        for i in range(RAIN_FX_COUNT):
            phase = ((i * 2654435761) % 100000) / 100000.0
            x0 = ARENA_RECT.left + ((i * 31) % 1000) / 1000.0 * ARENA_RECT.width
            length = RAIN_FX_DROP_LEN * (0.7 + 0.6 * ((i * 17) % 100) / 100.0)
            progress = ((rain_elapsed * RAIN_FX_SPEED + phase * fall_dist) % fall_dist) / fall_dist
            y0 = ARENA_RECT.top + progress * fall_dist - RAIN_FX_DROP_LEN
            x1 = x0 + slope * RAIN_FX_DROP_LEN
            y1 = y0 + RAIN_FX_DROP_LEN
            darker = i % 3 == 0
            color = (102, 148, 208) if darker else RAIN_FX_COLOR
            pygame.draw.line(surface, color, (round(x0 + slope * length * 0.2), round(y0)), (round(x1), round(y1)), 1)
        for splash in game_state.get("rain_splashes", []):
            splash_progress = splash["t"] / RAIN_SPLASH_LIFETIME
            alpha = 1.0 - splash_progress
            radius = 2.0 + splash_progress * 5.0
            pygame.draw.circle(surface, RAIN_SPLASH_COLOR, (round(splash["x"]), round(splash["y"])), max(1, round(radius)), max(1, round(1 + alpha * 2)))
            pygame.draw.circle(surface, (210, 232, 252), (round(splash["x"]), round(splash["y"])), max(1, round(radius * 0.3)))
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


def apply_faction_bonuses(game_state):
    """结算阵营羁绊：同队同阵营存活 ≥2 人一阶、≥3 人二阶，写入每个角色的 faction_bonus。

    死斗战各自为战（owner_id 全不同）时，同队计数恒为 1，羁绊自然不生效。
    """
    faction_counts = {}  # owner_id -> {faction: count}
    for c in game_state["characters"]:
        if not c.alive:
            continue
        tag = getattr(c, "faction_tag", None)
        if tag:
            d = faction_counts.setdefault(c.owner_id, {})
            d[tag] = d.get(tag, 0) + 1

    for c in game_state["characters"]:
        tag = getattr(c, "faction_tag", None)
        bonus = {"damage": 0.0, "reduction": 0.0, "attack_speed": 0.0, "move_speed": 0.0}
        tier = 0
        if tag and c.alive:
            count = faction_counts.get(c.owner_id, {}).get(tag, 0)
            tier_def = FACTION_DEFS.get(tag, {})
            if count >= 3:
                bonus = dict(tier_def.get("tier2", bonus))
                tier = 2
            elif count >= 2:
                bonus = dict(tier_def.get("tier1", bonus))
                tier = 1
        c.faction_bonus = bonus
        c.faction_bonus_tier = tier
        # 保存神域·遮断友方增益：同队钉锤工 sanctury 且保存>0 时，
        # 普攻伤害 +（保存/3 向下取整，≤+2）、双抗提升 20%（受伤 ×0.8）
        c.hammer_faction_damage_bonus = 0.0
        c.hammer_faction_reduction = 0.0
        if c.alive and getattr(c, "faction_tag", None) == "遮断":
            for ally in game_state["characters"]:
                if ally.alive and ally.owner_id == c.owner_id and getattr(ally, "hammer_sanctuary", False) and getattr(ally, "hammer_save", 0.0) > 0:
                    save = getattr(ally, "hammer_save", 0.0)
                    c.hammer_faction_damage_bonus = min(SANCTUARY_FACTION_DAMAGE_CAP, int(save // SANCTUARY_FACTION_DAMAGE_DIV))
                    c.hammer_faction_reduction = SANCTUARY_FACTION_REDUCTION
                    break


def apply_interrupt_ticks(game_state, dt):
    """遮断阵营专属结算（边狱巴士震颤式）：
    - 场上任一 owner 的遮断角色 ≥2 时，「遮断」机制对所有目标生效
    - 每 3 秒：遮断条 += 当前强度 × 1；遮断层数 -1（归零 → 状态消散，条保留）
    - 遮断条 ≥ 目标当前生命值 → 爆发：条消失、眩晕 5 秒、期间物抗/法抗 = 2.5（5 秒后恢复）
    """
    # 玄血条视觉开关：仅玄血武者(132)存活时显示全体玄血条
    Character._blood_visual_enabled = any(
        c.alive and getattr(c, "job_name", None) == BLOODARTIST_JOB_NAME for c in game_state["characters"]
    )
    # 判定场上是否存在触发的遮断阵营（任一 owner 的遮断角色 ≥2）
    interrupt_active_global = False
    faction_counts = {}
    for c in game_state["characters"]:
        if not c.alive:
            continue
        tag = getattr(c, "faction_tag", None)
        if tag:
            d = faction_counts.setdefault(c.owner_id, {})
            d[tag] = d.get(tag, 0) + 1
            if d[tag] >= 2 and tag == "遮断":
                interrupt_active_global = True

    # 保存神域：场上任意钉锤工 sanctury 激活且保存>0 时，其敌方全体减速 + 爆引前移 +10%
    hammer_buff_owners = set()
    for c in game_state["characters"]:
        if c.alive and getattr(c, "hammer_sanctuary", False) and getattr(c, "hammer_save", 0.0) > 0:
            hammer_buff_owners.add(c.owner_id)

    for target in get_targetables(game_state):
        if not target.alive or not hasattr(target, "design_interrupt_bar"):
            continue
        if target.owner_id in hammer_buff_owners and hasattr(target, "apply_slow"):
            target.apply_slow(SANCTUARY_ENEMY_SLOW, 0.2)
        # 爆发状态计时（5 秒后恢复抗性）
        if getattr(target, "design_interrupt_break_timer", 0.0) > 0:
            target.design_interrupt_break_timer = max(0.0, target.design_interrupt_break_timer - dt)
            if target.design_interrupt_break_timer == 0:
                if getattr(target, "design_interrupt_break_phys_saved", 0.0) > 0:
                    target.physical_resistance = target.design_interrupt_break_phys_saved
                    target.design_interrupt_break_phys_saved = 0.0
                if getattr(target, "design_interrupt_break_spell_saved", 0.0) > 0:
                    target.spell_resistance = target.design_interrupt_break_spell_saved
                    target.design_interrupt_break_spell_saved = 0.0
        # 3 秒 tick 结算（仅遮断机制激活时增长）
        if interrupt_active_global and getattr(target, "design_interrupt_active", False):
            target.design_interrupt_tick += dt
            while target.design_interrupt_tick >= INTERRUPT_TICK_INTERVAL:
                target.design_interrupt_tick -= INTERRUPT_TICK_INTERVAL
                potency = float(getattr(target, "design_interrupt_potency", 0.0))
                count = float(getattr(target, "design_interrupt_count", 0.0))
                if potency > 0:
                    target.design_interrupt_bar += potency * INTERRUPT_BAR_GAIN_PER_POTENCY
                count -= INTERRUPT_COUNT_DECAY_PER_TICK
                target.design_interrupt_count = max(0.0, count)
                if count <= 0:
                    target.design_interrupt_active = False
                    target.design_interrupt_potency = 0.0
        # 爆发判定：遮断条 ≥ 当前生命值（只要有条就判，即使状态已消散）
        if target.design_interrupt_bar >= max(1.0, getattr(target, "hp", 1.0)):
            if getattr(target, "design_interrupt_break_timer", 0.0) <= 0:
                target.design_interrupt_break_phys_saved = getattr(target, "physical_resistance", 1.0)
                target.design_interrupt_break_spell_saved = getattr(target, "spell_resistance", 1.0)
            target.physical_resistance = INTERRUPT_BREAK_RESIST
            target.spell_resistance = INTERRUPT_BREAK_RESIST
            target.design_interrupt_break_timer = INTERRUPT_BREAK_RESIST_DURATION
            if hasattr(target, "apply_stun"):
                target.apply_stun(INTERRUPT_BREAK_STUN_DURATION)
            if game_state is not None:
                spawn_damage_text(game_state, target, 0.0, text="遮断爆发！", color=INTERRUPT_BAR_COLOR)
                spawn_attack_impact(game_state, target.pos, INTERRUPT_BAR_COLOR, radius=26, thickness=4, burst_count=20)
            # 清空遮断状态，重新累积
            target.design_interrupt_bar = 0.0
            target.design_interrupt_potency = 0.0
            target.design_interrupt_count = 0.0
            target.design_interrupt_active = False
            target.design_interrupt_tick = 0.0