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