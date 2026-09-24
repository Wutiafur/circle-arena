# -*- coding: utf-8 -*-
"""Character 角色类（约 4600 行）。

底部导入 game.engine 以解 character ↔ engine 循环：
engine 顶部 `from game.character import Character`，此处待类定义完成后才导入 engine。
"""
import math
import random

import pygame

from game.data import *
from game.utils import *
from game.drawing import *

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
        self.faction_tag = FACTION_TAGS.get(job_name)
        self.faction_bonus = {"damage": 0.0, "reduction": 0.0, "attack_speed": 0.0, "move_speed": 0.0}
        self.thunder_mark = 0
        self.thunder_enhance_timer = 0.0
        self.thunder_resist_timer = 0.0
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
        damage *= 1.0 + self.faction_bonus.get("damage", 0.0)
        if self.thunder_enhance_timer > 0:
            damage *= 1.0 + THUNDER_ENHANCE_ATTACK_BONUS
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
            if isinstance(enemy, Character):
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
        if self.faction_bonus.get("attack_speed", 0.0) > 0:
            multiplier /= 1.0 + self.faction_bonus["attack_speed"]
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

    def apply_knockup(self, direction, distance, duration):
        """击飞：沿方向抛起并短暂失控（击退 + 眩晕的组合硬控）。"""
        self.apply_knockback(direction, distance)
        self.apply_stun(duration)

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
        if self.faction_bonus.get("reduction", 0.0) > 0 and not is_true_damage:
            damage *= max(0.0, 1.0 - self.faction_bonus["reduction"])
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
            if self.thunder_resist_timer > 0:
                damage *= max(0.0, 1.0 - THUNDER_SLASH_RESIST_BONUS)
        elif damage_kind == DAMAGE_KIND_SPELL:
            damage *= self.spell_resistance
            if self.thunder_resist_timer > 0:
                damage *= max(0.0, 1.0 - THUNDER_SLASH_RESIST_BONUS)
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
        if self.faction_bonus.get("move_speed", 0.0) > 0:
            modifier *= 1.0 + self.faction_bonus["move_speed"]
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
            if isinstance(target, Character):
                target.apply_blind(1.2 + 0.2 * self.ninja_shadow_stacks)
            self.ninja_shadow_stacks = 0
            self.ninja_shadow_timer = 0.0
        spawn_attack_impact(game_state, target.pos, self.get_visual_color(), radius=max(11, int(self.radius * 1.1)), damage=damage)
        stun_duration = self.get_current_melee_stun_duration()
        if stun_duration > 0 and isinstance(target, Character):
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
                if self.is_ninja() and self.ninja_shadow_stacks > 0 and chosen is target and isinstance(chosen, Character):
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

        cooldown = self.get_weapon_attack_cooldown(weapon_def["fire_interval"])
        self.attack_cooldown = cooldown
        self.on_attack_committed()
        # 冷锋枪(spear_thrust)分支可能在上面 clear_weapon() 把 held_weapon 置 None，
        # 故弹药结算需在冷却/提交之后、并以 None 守卫包裹，避免 AttributeError。
        if self.held_weapon is not None:
            if not self.held_weapon.get("infinite_ammo"):
                self.held_weapon["ammo"] -= 1
            self.held_weapon["cooldown"] = cooldown
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
        if self.thunder_enhance_timer > 0:
            self.thunder_enhance_timer = max(0.0, self.thunder_enhance_timer - dt)
        if self.thunder_resist_timer > 0:
            self.thunder_resist_timer = max(0.0, self.thunder_resist_timer - dt)
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
                            if isinstance(enemy, Character):
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



# 底部导入：解 character ↔ engine 循环（须在 Character 定义完成后）
from game.engine import *
