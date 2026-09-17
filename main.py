import math
import json
import os
import random
import sys
import traceback
from datetime import datetime
from pathlib import Path

os.environ.setdefault("SDL_VIDEO_HIGHDPI", "1")

import pygame

from design_characters import load_design_roles


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
FPS = 60
WINDOW_DEFAULT_WIDTH = SCREEN_WIDTH
WINDOW_DEFAULT_HEIGHT = SCREEN_HEIGHT
WINDOW_FLAGS = pygame.RESIZABLE | pygame.DOUBLEBUF
BATTLE_SIDEBAR_WIDTH = 300
BATTLE_WINDOW_WIDTH = SCREEN_WIDTH + BATTLE_SIDEBAR_WIDTH
BATTLE_WINDOW_HEIGHT = SCREEN_HEIGHT
BATTLE_WINDOW_FLAGS = pygame.DOUBLEBUF
LETTERBOX_COLOR = (0, 0, 0)

UI_HEIGHT = 64
ARENA_MARGIN = 30
ARENA_RECT = pygame.Rect(
    ARENA_MARGIN,
    UI_HEIGHT,
    SCREEN_WIDTH - ARENA_MARGIN * 2,
    SCREEN_HEIGHT - UI_HEIGHT - ARENA_MARGIN,
)

BACKGROUND_COLOR = (12, 16, 22)
GRID_COLOR = (28, 36, 46)
TEXT_COLOR = (232, 238, 244)
BORDER_COLOR = (245, 245, 245)
HEALTH_BG = (54, 60, 70)
MANA_BG = (32, 44, 62)
MANA_COLOR = (72, 156, 255)
MENU_PANEL = (20, 26, 34)
MENU_BUTTON = (44, 54, 70)
MENU_BUTTON_HOVER = (68, 82, 105)
MENU_BUTTON_DISABLED = (30, 36, 44)
MENU_ACCENT = (110, 170, 255)
DAMAGE_TEXT_PHYSICAL = (255, 88, 88)
DAMAGE_TEXT_SPELL = (255, 132, 214)
DAMAGE_TEXT_TRUE = (255, 255, 255)


def shade_color(color, factor):
    factor = max(0.0, factor)
    return tuple(max(0, min(255, int(round(channel * factor)))) for channel in color)


def mix_color(color_a, color_b, amount):
    amount = max(0.0, min(1.0, float(amount)))
    return tuple(
        max(0, min(255, int(round(a * (1.0 - amount) + b * amount))))
        for a, b in zip(color_a, color_b)
    )


def draw_panel(surface, rect, fill_color, border_color=BORDER_COLOR, accent_color=None, radius=16, shadow_offset=(4, 5)):
    shadow_rect = rect.move(shadow_offset[0], shadow_offset[1])
    pygame.draw.rect(surface, (6, 8, 12), shadow_rect, border_radius=radius)
    pygame.draw.rect(surface, fill_color, rect, border_radius=radius)
    if accent_color is not None:
        accent_rect = pygame.Rect(rect.left + 2, rect.top + 2, max(0, rect.width - 4), 4)
        pygame.draw.rect(surface, accent_color, accent_rect, border_radius=2)
    pygame.draw.rect(surface, border_color, rect, 2, border_radius=radius)


BUG_REPORT_DIR = Path(__file__).resolve().parent / "bug"
WIN_RATE_STATS_PATH = Path(__file__).resolve().parent / "win_rate_stats.json"

CHARACTER_SIZE = 30
CHARACTER_RADIUS = CHARACTER_SIZE / 2
CHARACTER_ACCELERATION = 260.0
CHARACTER_FRICTION = 4.0
CHARACTER_PUSH_SPEED = 36.0
CHARACTER_BOUNCE = 0.78
SEPARATION_RADIUS = 46.0
SEPARATION_FORCE = 0.95
SEPARATION_HOLD_BIAS = 1.3
MELEE_DASH_TRIGGER_BUFFER = 30.0
MELEE_DASH_DURATION = 0.5
MELEE_DASH_COOLDOWN = 2.0
MELEE_DASH_SPEED_MULTIPLIER = 2.0
MELEE_INTERCEPT_MIN_LEAD = 0.12
MELEE_INTERCEPT_MAX_LEAD = 0.38
RANGED_SAFE_DISTANCE = 100.0
STRAFE_SWITCH_INTERVAL = (0.9, 1.8)
STRAFE_ORBIT_WEIGHT = 0.92
STRAFE_RADIAL_WEIGHT = 0.42
CHASE_NOISE_MAX_DEG = 10.0
CHASE_NOISE_RETARGET_INTERVAL = (0.16, 0.34)
CHASE_NOISE_LERP = 6.0


def save_crash_report(exc_type, exc_value, exc_traceback):
    BUG_REPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = BUG_REPORT_DIR / f"crash_{timestamp}.txt"
    traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    report_lines = [
        "Circle Crash Report",
        f"Time: {datetime.now().isoformat(timespec='seconds')}",
        f"Python: {sys.version}",
        f"Pygame: {pygame.version.ver}",
        f"Executable: {sys.executable}",
        f"Working Directory: {Path.cwd()}",
        f"Game File: {Path(__file__).resolve()}",
        "",
        "Traceback:",
        traceback_text,
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path


def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    try:
        report_path = save_crash_report(exc_type, exc_value, exc_traceback)
        print(f"Severe error captured. Crash report saved to: {report_path}")
    except Exception as report_error:
        print(f"Failed to save crash report: {report_error}")
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def load_win_rate_stats():
    stats = {}
    try:
        if WIN_RATE_STATS_PATH.exists():
            payload = json.loads(WIN_RATE_STATS_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload = payload.get("roles", payload)
                if isinstance(payload, dict):
                    for job_name, data in payload.items():
                        if not isinstance(data, dict):
                            continue
                        matches = max(0, int(data.get("matches", 0)))
                        wins = max(0, int(data.get("wins", 0)))
                        stats[job_name] = {"matches": matches, "wins": min(wins, matches)}
    except Exception:
        stats = {}
    for job_name in JOB_DEFS.keys():
        stats.setdefault(job_name, {"matches": 0, "wins": 0})
    return stats


def save_win_rate_stats(stats):
    WIN_RATE_STATS_PATH.write_text(
        json.dumps({"roles": stats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_win_rate_result(game_state):
    stats = load_win_rate_stats()
    for character in game_state.get("battle_participants", []):
        job_name = getattr(character, "job_name", None)
        if job_name not in JOB_DEFS:
            continue
        stats[job_name]["matches"] += 1
    winner = game_state.get("winner_character")
    if winner is not None and getattr(winner, "job_name", None) in stats:
        stats[winner.job_name]["wins"] += 1
    save_win_rate_stats(stats)

PROJECTILE_RADIUS = 4
PROJECTILE_LIFETIME = 3.0
MAX_CHARACTERS = 20
MIN_CHARACTERS = 1
MAX_MP = 100.0

MP_RATE_SLOW = 10.0
MP_RATE_MEDIUM = 15.0
MP_RATE_FAST = 20.0
MP_RATE_VERY_FAST = 30.0

SPAWN_FX_DURATION = 1.5
SPAWN_FX_RAISE_HEIGHT = 46.0
SPAWN_FX_GLOW_COLOR = (214, 224, 244)

SLOW_DURATION = 1.8
SLOW_FACTOR = 0.8

KNIGHT_SHIELD_DURATION = 6.0
KNIGHT_GUARD_DURATION = 6.0
KNIGHT_DAMAGE_REDUCTION = 0.30
KNIGHT_GUARD_HEAL_RATE = 0.03
KNIGHT_BACKLASH_DURATION = 3.0
KNIGHT_BACKLASH_INTERVAL = 1.0
KNIGHT_BACKLASH_DAMAGE_FACTOR = 0.25

MAGE_NOVA_DAMAGE = 12
MAGE_SELF_DOT_DURATION = 15.0
MAGE_SELF_DOT_PORTION = 0.10
MAGE_ARCANE_MAX_STACKS = 5
MAGE_ARCANE_DAMAGE_BONUS = 0.05
MAGE_ARCANE_PROJECTILE_BONUS = 0.04
MAGE_ARCANE_FIELD_RADIUS = 72.0
MAGE_ARCANE_FIELD_DURATION = 2.0
MAGE_ARCANE_FIELD_TICK = 0.4
MAGE_ARCANE_FIELD_DAMAGE = 6.0
MAGE_ARCANE_FIELD_SLOW = 0.25

BERSERKER_SPIN_DURATION = 4.0
BERSERKER_SPIN_INTERVAL = 0.25
BERSERKER_SPIN_DAMAGE = 6.0
BERSERKER_SPIN_HEAL = 8.0
BERSERKER_SPIN_RADIUS = 62.0

SNIPER_CHARGE_TIME = 0.65
SNIPER_DISTANCE_BONUS_STEP = 50.0
SNIPER_DISTANCE_BONUS_PER_STEP = 0.06
SNIPER_DISTANCE_BONUS_CAP = 0.30
SNIPER_STATIONARY_READY_TIME = 1.0
SNIPER_STATIONARY_BONUS = 0.20
SNIPER_BEAM_DAMAGE = 55.0

PALADIN_BUFF_DURATION = 8.0
PALADIN_HEAL_TICK = 2.0

VAMPIRE_CHARGE_INTERVAL = 4.0
VAMPIRE_CHARGE_AMOUNT = 30.0
VAMPIRE_CHANNEL_DURATION = 3.0
VAMPIRE_CHANNEL_DAMAGE = 20.0
VAMPIRE_REGEN_DURATION = 5.0
VAMPIRE_REGEN_TOTAL = 20.0
ILLUSION_CLONE_DURATION = 5.0
ILLUSION_CLONE_HP_PORTION = 0.60
ILLUSION_CLONE_DAMAGE_PORTION = 0.20
ILLUSION_MIRROR_BUILD = 18.0
ILLUSION_MIRROR_DURATION = 6.0
ILLUSION_MIRROR_STACK_DAMAGE_BONUS = 0.04
ILLUSION_MIRROR_STACK_SPEED_BONUS = 0.03
ILLUSION_MIRROR_STACK_INTERVAL_BONUS = 0.03
ILLUSION_MIRROR_STACK_MAX = 3
BEHEMOTH_STONE_STACK_MAX = 5
BEHEMOTH_STONE_DAMAGE_REDUCTION = 0.03
BEHEMOTH_STONE_DAMAGE_BONUS = 0.05
BEHEMOTH_STONE_SPEED_BONUS = 0.02
BEHEMOTH_STONE_ATTACK_BONUS = 0.03
BEHEMOTH_STONE_DECAY = 6.0
TOXICOLOGIST_CORROSION_STACK_MAX = 5
TOXICOLOGIST_CORROSION_DAMAGE_BONUS = 0.05
TOXICOLOGIST_CORROSION_SPEED_BONUS = 0.03
TOXICOLOGIST_CORROSION_INTERVAL_BONUS = 0.03
TOXICOLOGIST_CORROSION_BUILD = 24.0
TOXICOLOGIST_CORROSION_DURATION = 7.0
TOXICOLOGIST_CORROSION_FIELD_RADIUS_BONUS = 6.0
TOXICOLOGIST_CORROSION_FIELD_DURATION_BONUS = 0.5
TOXICOLOGIST_CORROSION_FIELD_DPS_BONUS = 2.0
TOXICOLOGIST_CORROSION_FIELD_PROGRESS_BONUS = 0.5
TOXICOLOGIST_POISON_RADIUS_BONUS = 6.0
TOXICOLOGIST_POISON_DURATION_BONUS = 0.5
TOXICOLOGIST_POISON_DPS_BONUS = 2.0
FROST_MAGE_CORE_STACK_MAX = 5
FROST_MAGE_CORE_DAMAGE_BONUS = 0.04
FROST_MAGE_CORE_SPEED_BONUS = 0.03
FROST_MAGE_CORE_INTERVAL_BONUS = 0.04
FROST_MAGE_CORE_BUILD = 22.0
FROST_MAGE_CORE_DURATION = 7.0
FROST_MAGE_CORE_FREEZE_BONUS = 0.35
FROST_MAGE_CORE_TICKS_BONUS = 2
PYRO_EMBER_STACK_MAX = 5
PYRO_EMBER_DAMAGE_BONUS = 0.05
PYRO_EMBER_SPEED_BONUS = 0.03
PYRO_EMBER_INTERVAL_BONUS = 0.04
PYRO_EMBER_BUILD = 22.0
PYRO_EMBER_DURATION = 7.0
PYRO_EMBER_DURATION_BONUS = 0.2
PYRO_EMBER_TICK_BONUS = 1.5
PYRO_EMBER_CHILL_BONUS = 0.15
BEHEMOTH_STOMP_RADIUS = 110.0
BEHEMOTH_STOMP_DAMAGE = 50
BEHEMOTH_STOMP_STUN = 2.5
BEHEMOTH_TRUE_SHIELD = 200.0
TOXIC_FIELD_RADIUS = 60.0
TOXIC_FIELD_DURATION = 8.0
TOXIC_FIELD_DPS = 18.0
POISON_STACK_DAMAGE = 15.0
POISON_STACK_DECAY = 3.0
FROST_NOVA_FREEZE = 3.0
FROST_NOVA_RADIUS = 72.0
FROST_NOVA_TICKS = 12
PYRO_BREATH_DURATION = 2.8
PYRO_BREATH_INTERVAL = 0.2
PYRO_BREATH_DAMAGE = 8.0
PYRO_BREATH_RANGE = 120.0
PYRO_BREATH_HALF_ANGLE = 38.0
TIME_WALKER_REWIND_SECONDS = 5.0
TIME_WALKER_SNAPSHOT_INTERVAL = 0.2
MONK_WAVE_DAMAGE = 80.0
MONK_WAVE_STUN = 5.0
MONK_WAVE_KNOCKBACK = 80.0
MECH_MISSILE_COUNT = 15
MECH_MISSILE_TARGETS = 3
MECH_MISSILE_BLAST_RADIUS = 36.0
MECH_MISSILE_DAMAGE = 15.0
DRUID_FORM_DURATION = 8.0
DRUID_FORM_BONUS_HP = 150.0
DRUID_FORM_HEAL = 100.0
DRUID_FORM_DAMAGE_MULTIPLIER = 1.6
DRUID_FORM_STUN = 0.8
ELECTRO_CHAIN_BOUNCES = 4
ELECTRO_CHAIN_DAMAGE = 12.0
ELECTRO_DOOM_DURATION = 4.0
ELECTRO_DOOM_DPS = 10.0
ELECTRO_DOOM_EXECUTE_RATIO = 0.15
PUPPETEER_CONTROL_DURATION = 8.0
SMASHER_LEAP_DURATION = 0.65
SMASHER_SLAM_RADIUS = 40.0
SMASHER_SLAM_DAMAGE = 30.0
SUCCUBUS_CHARM_DURATION = 3.0
SUCCUBUS_KISS_SPEED = 250.0
SUCCUBUS_BARRAGE_SPREAD = 16.0
SUCCUBUS_BARRAGE_PELLETS = 5
SUCCUBUS_BARRAGE_DAMAGE_MULTIPLIER = 0.3
GUNSLINGER_BARRAGE_COUNT = 20
SHIELD_WALL_DURATION = 5.0
SHIELD_WALL_LENGTH = 160.0
SHIELD_WALL_THICKNESS = 18.0
SWORDMASTER_INVULN_DURATION = 1.2
SWORDMASTER_SLASH_COUNT = 5
SWORDMASTER_SLASH_DAMAGE_MULTIPLIER = 1.35
SWORDMASTER_HASTE_DURATION = 5.0
WINDRUNNER_STORM_DURATION = 4.0
WINDRUNNER_REPEL_RADIUS = 70.0
WINDRUNNER_REPEL_DISTANCE = 55.0
WINDRUNNER_MP_PER_PIXEL = 0.08
HEX_CURSE_DURATION = 5.0
HEX_CURSE_DAMAGE_AMP = 1.5
CHAOS_CHARGE_INTERVAL = 5.0
GEOMANCER_SPIKE_DAMAGE = 50.0
GEOMANCER_ROOT_DURATION = 5.0
BARD_SONG_DURATION = 6.0
BARD_SONG_RADIUS = 150.0
BARD_SONG_SELF_DRAIN = 0.01
BARD_SONG_SPEED_MULTIPLIER = 1.5
BARD_SONG_ATTACK_MULTIPLIER = 1.5
BARD_BASIC_SLOW_CHANCE = 0.25
BARD_BASIC_SLOW_FACTOR = 0.2
BARD_BASIC_SLOW_DURATION = 1.0
GLADIATOR_DUEL_DURATION = 3.0
GLADIATOR_DAMAGE_REDUCTION = 0.30
GLADIATOR_SELF_ATTACK_MULTIPLIER = 3.0
GLADIATOR_TARGET_ATTACK_MULTIPLIER = 2.0
WARLOCK_CHARGE_INTERVAL = 3.0
WARLOCK_CHARGE_COST = 50.0
WARLOCK_CHARGE_MP = 40.0
WARLOCK_SKILL_HP_COST = 10.0
WARLOCK_BEAM_DAMAGE = 80.0
WARLOCK_BEAM_WIDTH = 22.0
WARLOCK_BEAM_RANGE = 1200.0
TINKERER_OVERCLOCK_DURATION = 3.0
VALKYRIE_DIVE_DURATION = 1.4
VALKYRIE_TRUE_SHIELD = 500.0
VALKYRIE_SLAM_RADIUS = 70.0
VALKYRIE_SLAM_DAMAGE = 80.0
VALKYRIE_SLAM_STUN = 1.0
VALKYRIE_RETARGET_RADIUS = 90.0
VALKYRIE_LANDING_LIFETIME = 0.7
VALKYRIE_LANDING_COLOR = (255, 214, 96)
DARK_REFLECT_DURATION = 5.0
BLOODWRAITH_SHIELD_DURATION = 4.0
BLOODWRAITH_SHIELD_RATIO = 0.25
BLOODWRAITH_LIFESTEAL_RATIO = 0.60
BLOODWRAITH_RAGE_DRAIN_RATIO = 0.08
BLOODWRAITH_RAGE_ATTACK_SPEED_MULTIPLIER = 3.0
BLOODWRAITH_RAGE_DAMAGE_MULTIPLIER = 4.0
BLOODWRAITH_RAGE_SPEED_MULTIPLIER = 2.0
PHANTOM_LANCER_THROW_SPEED_BONUS = 0.30
PHANTOM_LANCER_THROW_SPEED_DURATION = 4.0
PHANTOM_LANCER_SPEAR_LIFETIME = 5.0
PHANTOM_LANCER_SPEAR_HUNT_DURATION = 5.0
SOUL_ARBITER_CHAIN_DURATION = 3.0
SOUL_ARBITER_CHAIN_TICK = 0.5
SOUL_ARBITER_CHAIN_DAMAGE = 10.0
SOUL_ARBITER_EXECUTE_RATIO = 0.10
SOUL_ARBITER_SHIELD_RATIO = 1.5
SOUL_ARBITER_EXECUTION_COLOR = (238, 140, 216)
SOUL_ARBITER_HUNT_DURATION = 8.0
SOUL_ARBITER_HUNT_SPEED_BONUS = 0.30
SOUL_ARBITER_HUNT_CHAIN_LIMIT = 3
SOUL_ARBITER_SPIRIT_LIFETIME = 10.0
SOUL_ARBITER_SPIRIT_SCALE = 0.30
SUNFIRE_JOB_NAME = "DesignRole94_sunfire_blademaster"
SUNFIRE_WATER_COLOR = (96, 212, 255)
SUNFIRE_FIRE_COLOR = (214, 62, 58)
SUNFIRE_FIRE_DURATION = 8.0
SUNFIRE_INVULN_DURATION = 2.0
SUNFIRE_EVADE_DURATION = 3.0
SUNFIRE_EVADE_CHANCE = 0.30
SUNFIRE_DAMAGE_REDUCTION_STACKS = 10
SUNFIRE_DAMAGE_REDUCTION_PER_STACK = 0.04
WINDSTORM_FOX_JOB_NAME = "DesignRole95_windstorm_fox"
WINDSTORM_FOX_FAN_COLOR = (170, 174, 180)
WINDSTORM_FOX_BLADE_COLOR = (248, 248, 255)
WINDSTORM_FOX_AURA_COLOR = (46, 82, 56)
WINDSTORM_FOX_QI_MAX = 5
WINDSTORM_FOX_MOVE_BONUS_PER_QI = 0.03
WINDSTORM_FOX_ATTACK_SPEED_BONUS_PER_QI = 0.06
WINDSTORM_FOX_IDLE_DECAY_DELAY = 8.0
WINDSTORM_FOX_IDLE_DECAY_INTERVAL = 3.0
WINDSTORM_FOX_BASE_BLADE_DAMAGE = 10.0
WINDSTORM_FOX_SKILL_BLADE_DAMAGE = 12.0
WINDSTORM_FOX_GLOBAL_BLADE_DAMAGE = 14.0
WINDSTORM_FOX_DOUBLE_BLADE_RATIO = 0.75
WINDSTORM_FOX_DOUBLE_BLADE_ROTATION = 10.0
WINDSTORM_FOX_DASH_CHANCE = 0.2
WINDSTORM_FOX_DASH_DISTANCE = 34.0
WINDSTORM_FOX_RICOCHET_CHANCE = 0.4
WINDSTORM_FOX_LIFESTEAL_RATIO = 0.35
WINDSTORM_FOX_PHYS_RESIST_BONUS = 0.5
WINDSTORM_FOX_PHYS_RESIST_DURATION = 3.0
WINDSTORM_FOX_FULL_QI_DAMAGE_REDUCTION = 0.15
SEA_SAGE_JOB_NAME = "DesignRole96_sea_sage"
SEA_SAGE_BLUE_COLOR = (27, 74, 150)
SEA_SAGE_FISH_COLOR = (76, 224, 232)
SEA_SAGE_WAVE_OUTER_COLOR = (44, 112, 208)
SEA_SAGE_WAVE_INNER_COLOR = (180, 232, 255)
SEA_SAGE_FISH_AUTO_INTERVAL = 6.0
SEA_SAGE_FISH_HEAL = 30.0
SEA_SAGE_FISH_SHIELD = 15.0
SEA_SAGE_FISH_SHIELD_DURATION = 3.0
SEA_SAGE_DAMAGE_BANK_THRESHOLD = 80.0
SEA_SAGE_REDUCTION_PER_STACK = 0.05
SEA_SAGE_REDUCTION_DURATION = 8.0
SEA_SAGE_REDUCTION_MAX_STACKS = 4
EQUILIBRIUM_JOB_NAME = "DesignRole97_equilibrium_arbiter"
EQUILIBRIUM_GOLD_COLOR = (230, 196, 84)
EQUILIBRIUM_PHYSICAL_TEXT_COLOR = (226, 92, 92)
EQUILIBRIUM_SPELL_TEXT_COLOR = (176, 108, 236)
EQUILIBRIUM_THRESHOLD_DICE_DAMAGE = 70.0
EQUILIBRIUM_THRESHOLD_EXECUTE_DAMAGE = 100.0
EQUILIBRIUM_THRESHOLD_FIELD_DAMAGE = 40.0
EQUILIBRIUM_THRESHOLD_RESIST_PHYS_DELTA = -0.02
EQUILIBRIUM_THRESHOLD_RESIST_SPELL_DELTA = 0.01
EQUILIBRIUM_THRESHOLD_RESIST_EXCHANGE = 0.2
EQUILIBRIUM_THRESHOLD_RESIST_DURATION = 5.0
EQUILIBRIUM_MARK_DURATION = 4.0
EQUILIBRIUM_MARK_COLOR = (232, 204, 108)
EQUILIBRIUM_MARK_GLOW = (160, 128, 224)
EQUILIBRIUM_PULSE_DURATION = 0.42
EQUILIBRIUM_PULSE_COLOR = (240, 214, 122)
PHOENIX_JOB_NAME = "DesignRole99_phoenix"
PHOENIX_FEATHER_INITIAL = 30
PHOENIX_FEATHER_PER_BONUS = 5
PHOENIX_FEATHER_DAMAGE_BONUS = 3.0
PHOENIX_FEATHER_EXPLODE_GAIN = 2
PHOENIX_EGG_FEATHER_COST = 5
PHOENIX_EGG_DURATION = 20.0
PHOENIX_EGG_SHIELD_MAX_HP_RATIO = 4.0
PHOENIX_EGG_SHIELD_DAMAGE_RATIO = 8.0
PHOENIX_FIRE_EXPLODE_THRESHOLD = 5
PHOENIX_FIRE_EXPLODE_FALL_MULTIPLIER = 2.0
PHOENIX_FIRE_EXPLODE_DAMAGE_BASE = 40.0
PHOENIX_FALL_MAX_HP_MULTIPLIER = 0.9
PHOENIX_WRATH_TARGETS = 2
PHOENIX_WRATH_DOT_DURATION = 2.0
PHOENIX_WRATH_DOT_BASE = 12.0
PHOENIX_EGG_COLOR = (255, 214, 120)
PHOENIX_EGG_SHIELD_COLOR = (255, 178, 74)
XUANWU_JOB_NAME = "DesignRole100_xuanwu"
XUANWU_SHELL_MAX_BASE = 10
XUANWU_SHELL_MAX_PER_KILL = 5
XUANWU_SHELL_MAX_HP_PER_STACK = 20.0
XUANWU_SHELL_DAMAGE_REDUCTION_PER_STACK = 0.02
XUANWU_SHELL_GUARD_INTERVAL = 5
XUANWU_SHELL_GUARD_COST = 2
XUANWU_SHELL_GUARD_COOLDOWN = 8.0
XUANWU_SHELL_GUARD_SHIELD_HP_RATIO = 0.2
XUANWU_COUNTER_INTERVAL = 3.0
XUANWU_COUNTER_SHELL_STEP = 5
XUANWU_COUNTER_DAMAGE_BASE = 20.0
XUANWU_COUNTER_DAMAGE_PER_SHELL = 5.0
XUANWU_COUNTER_TARGETS = 2
XUANWU_COUNTER_SLOW = 0.3
XUANWU_COUNTER_SLOW_DURATION = 1.0
XUANWU_SHELL_CONSUME_MP_PER_SHELL = 10.0
XUANWU_BULWARK_DURATION = 8.0
XUANWU_BULWARK_SHIELD_BASE = 80.0
XUANWU_BULWARK_SHIELD_PER_SHELL = 15.0
XUANWU_BULWARK_DAMAGE_REDUCTION = 0.4
XUANWU_BULWARK_TAUNT_DURATION = 1.5
XUANWU_BULWARK_TAUNT_RADIUS = 110.0
XUANWU_BULWARK_BURST_BASE = 30.0
XUANWU_BULWARK_BURST_PER_SHELL = 5.0
XUANWU_BULWARK_BURST_RADIUS = 110.0
XUANWU_SHELL_COLOR = (148, 156, 170)
XUANWU_BULWARK_COLOR = (96, 190, 236)
TIGER_JOB_NAME = "DesignRole101_tiger"
TIGER_WOUND_MAX = 3
TIGER_WOUND_DAMAGE_AMP_PER_STACK = 0.05
TIGER_WOUND_THIRD_DAMAGE_LOST_HP_RATIO = 0.06
TIGER_WOUND_TRAIL_SPACING = 26.0
TIGER_WOUND_TRAIL_LIFETIME = 1.5
TIGER_WOUND_TRAIL_SPEED_GRACE = 0.6
TIGER_WOUND_TRAIL_SPEED_BONUS = 0.15
TIGER_HUNT_VALUE_MAX = 100.0
TIGER_PREY_CHARGE_PER_HIT = 5.0
TIGER_PREY_CHARGE_MAX_PER_SEC = 3
TIGER_PREY_CHARGE_WINDOW = 1.0
TIGER_EXECUTE_CHARGE = 30.0
TIGER_EXECUTE_DAMAGE_BASE = 100.0
TIGER_EXECUTE_DAMAGE_LOST_HP_RATIO = 0.35
TIGER_EXECUTE_POWER_GAIN = 3
TIGER_ROAR_RANGE = 40.0
TIGER_ROAR_HALF_ANGLE = 15.0
TIGER_ROAR_DAMAGE_BASE = 40.0
TIGER_ROAR_DAMAGE_PER_POWER = 15.0
TIGER_ROAR_SLOW = 0.4
TIGER_ROAR_SLOW_DURATION = 1.5
TIGER_ROAR_HEAL_RATIO = 0.2
TIGER_POWER_MAX = 3
TIGER_POWER_MOVE_SPEED_PER_STACK = 0.08
TIGER_POWER_CRIT_DAMAGE_PER_STACK = 0.15
TIGER_CRIT_CHANCE = 0.25
TIGER_HUNT_MARKER_COLOR = (255, 132, 84)
TIGER_WOUND_COLOR = (214, 70, 60)
DRAGON_JOB_NAME = "DesignRole102_azure_dragon"
DRAGON_THUNDER_DAMAGE = 12.0
DRAGON_WOOD_DAMAGE = 10.0
DRAGON_THUNDER_ATTACK_SPEED_BONUS = 0.3
DRAGON_THUNDER_DAMAGE_REDUCTION = 0.2
DRAGON_THUNDER_ZAP_INTERVAL = 3.0
DRAGON_THUNDER_ZAP_DAMAGE = 35.0
DRAGON_WOOD_HEAL_INTERVAL = 4.0
DRAGON_WOOD_HEAL_RATIO = 0.02
DRAGON_WOOD_RANGE_BASE = 285.0
DRAGON_WOOD_RANGE_BONUS = 0.5
DRAGON_BREATH_MAX = 5
DRAGON_BREATH_HIT_INTERVAL = 3
DRAGON_SWITCH_DAMAGE_PER_BREATH = 6.0
DRAGON_ROAR_RADIUS = 35.0
DRAGON_ROAR_BASE = 40.0
DRAGON_ROAR_PER_BREATH = 10.0
DRAGON_SWEEP_RANGE = 200.0
DRAGON_SWEEP_PATH_WIDTH = 30.0
DRAGON_SWEEP_DAMAGE = 120.0
DRAGON_SWEEP_COOLDOWN = 8.0
DRAGON_SWEEP_COOLDOWN_RETURN = 0.5
DRAGON_MOVE_BONUS_DISTANCE = 200.0
DRAGON_MOVE_BONUS_BASE = 10.0
DRAGON_MOVE_BONUS_PER_BREATH = 5.0
DRAGON_AWE_MAX = 3
DRAGON_AWE_MOVE_SPEED_PER_STACK = 0.03
DRAGON_AWE_RESIST_PER_STACK = 0.02
DRAGON_CHARGE_SWITCH = 10.0
DRAGON_CHARGE_ROAR = 10.0
DRAGON_THUNDER_COLOR = (244, 200, 72)
DRAGON_WOOD_COLOR = (92, 214, 120)
SUSANOO_JOB_NAME = "DesignRole103_susanoo"
SUSANOO_PROWL_MAX = 5
SUSANOO_PROWL_BONUS_PER_STACK = 0.04
SUSANOO_PROWL_APPLY_ON_HIT = 2
SUSANOO_RAIJIN_BOLTS = 5
SUSANOO_BOLT_DAMAGE = 30.0
SUSANOO_PROWL_EXPLODE_DAMAGE = 15.0
SUSANOO_CAST_INVULN = 1.5
SUSANOO_ARC_RATIO = 0.3
SUSANOO_THUNDER_COLOR = (176, 132, 255)
SUSANOO_ARC_COLOR = (214, 178, 255)
RANGER_MARK_MAX = 3
RANGER_MARK_DAMAGE_BONUS = 0.08
RANGER_DASH_SPEED_DURATION = 0.5
RANGER_DASH_SPEED_BONUS = 0.2
SHADOW_VALUE_MAX = 3
SHADOW_WALTZ_THROW_RATIO = 1.5
SHADOW_WALTZ_AOE_RADIUS = 60.0
SHADOW_WALTZ_AOE_DAMAGE_RATIO = 2.0
SHADOW_WALTZ_INVULN = 1.0
ELEMENTALIST_RESONANCE_MAX = 3
IRONCLAD_THORN_RATIO = 0.2
IRONCLAD_IDLE_REGEN_RATIO = 0.01
SEA_SAGE_WAVE_STAGE1_DAMAGE = 20.0
SEA_SAGE_WAVE_STAGE2_DAMAGE = 30.0
SEA_SAGE_WAVE_STAGE3_DAMAGE = 60.0
SEA_SAGE_WAVE_STAGE1_STUN = 0.4
SEA_SAGE_WAVE_STAGE2_STUN = 0.4
SEA_SAGE_WAVE_STAGE3_STUN = 1.0
SEA_SAGE_WAVE_STAGE2_SLOW = 0.4
SEA_SAGE_WAVE_SLOW_DURATION = 2.0
SEA_SAGE_WAVE_RETURN_HEAL = 30.0
SEA_SAGE_WAVE_SPEED = 390.0
SEA_SAGE_WAVE_RANGE = 300.0
SEA_SAGE_WAVE_WIDTH = 60.0
SEA_SAGE_WAVE_RETURN_SPEED = 460.0
SEA_SAGE_WAVE_DELAY_STEP = 0.16
ACOUSTIC_WAVE_DAMAGE = 40.0
ACOUSTIC_WAVE_STUN = 1.0
ACOUSTIC_WAVE_RADIUS = 100.0
ACOUSTIC_WAVE_LAST_RADIUS = 140.0
ACOUSTIC_WAVE_DURATION = 1.0
ACOUSTIC_WAVE_DELAY = 1.0
GRAVEKEEPER_FIELD_RADIUS = 60.0
GRAVEKEEPER_FIELD_DURATION = 5.0
GRAVEKEEPER_FIELD_STACK_RADIUS = 8.0
GRAVEKEEPER_FIELD_STACK_DURATION = 1.0
GRAVEKEEPER_FIELD_MAX_STACKS = 3
GRAVEKEEPER_FIELD_SLOW = 0.45
GRAVEKEEPER_FIELD_EMPOWERED_SLOW = 0.60
GRAVEKEEPER_MARKER_DURATION = 18.0
GRAVEKEEPER_NEARBY_CHARGE_RANGE = 140.0
GRAVEKEEPER_NEARBY_CHARGE_BONUS = 20.0
GRAVEKEEPER_WRAITH_SPEED = 240.0
GRAVEKEEPER_WRAITH_DAMAGE = 55.0
GRAVEKEEPER_WRAITH_SLOW = 0.35
GRAVEKEEPER_WRAITH_SLOW_DURATION = 1.0
GRAVEKEEPER_WRAITH_FIELD_BONUS = 40.0
GRAVEKEEPER_FIELD_TICK_INTERVAL = 0.5
GRAVEKEEPER_FIELD_BASE_DPS = 12.0
GRAVEKEEPER_FIELD_STACK_DPS = 6.0
GRAVEKEEPER_FIELD_MARKER_DPS_MULTIPLIER = 2.0
GRAVEKEEPER_ROT_MAX = 5
GRAVEKEEPER_ROT_SLOW_PER_STACK = 0.03
GRAVEKEEPER_ROT_DURATION = 2.0
GRAVEKEEPER_ROT_BONUS_DAMAGE = 45.0
GRAVEKEEPER_GUARD_DAMAGE = 40.0
GRAVEKEEPER_GUARD_HITS = 3
GRAVEKEEPER_GUARD_HIT_COOLDOWN = 0.35
GRAVEKEEPER_MARKER_DRAIN_INTERVAL = 6.0
GRAVEKEEPER_MARKER_DRAIN_DAMAGE = 30.0
GRAVEKEEPER_FIELD_COLOR = (124, 94, 72)
GRAVEKEEPER_FIELD_EDGE_COLOR = (170, 142, 108)
GRAVEKEEPER_MARKER_COLOR = (92, 92, 96)
GRAVEKEEPER_MARKER_EDGE_COLOR = (48, 48, 52)
GRAVEKEEPER_WRAITH_COLOR = (228, 232, 238)
GRAVEKEEPER_WRAITH_TRAIL_COLOR = (166, 132, 224)
HELLBRINGER_TRAIL_DURATION = 2.0
HELLBRINGER_TRAIL_DAMAGE = 5.0
HELLBRINGER_TRAIL_COLOR = (255, 118, 118)
HELLBRINGER_BURN_DURATION = 3.0
HELLBRINGER_BURN_MAX_STACKS = 5
HELLBRINGER_BURN_DAMAGE_PER_STACK = 0.01
HELLBRINGER_BURN_SKILL_STACKS = 2
SEA_SAGE_WAVE_LENGTH = 48.0
BOUNTY_DAMAGE_BONUS = 0.10
BOUNTY_COIN_DAMAGE_BONUS = 0.06
SHAMAN_TOTEM_RANGE = 60.0
SHAMAN_TOTEM_DAMAGE = 8.0
SHAMAN_TOTEM_HP = 30.0
SHAMAN_TOTEM_INTERVAL = 1.0
PSIONIC_REDIRECT_HOMING = 12.0
DESIGN_STATUS_TICK = 1.0
DESIGN_BLEED_DAMAGE = 5.0
DESIGN_BLEED_DURATION = 3.0
DESIGN_SLEEP_WAKE_MULTIPLIER = 2.0
DESIGN_FORTRESS_RADIUS = 80.0
DESIGN_FORTRESS_REDUCTION = 0.80
DESIGN_TIMESTOP_DURATION = 3.0
DESIGN_CONSTRUCT_INTERVAL = 6.0
DESIGN_CONSTRUCT_RADIUS = 22.0
DESIGN_AURORA_RESIST = 0.70
AURORA_BURN_TICK = 0.9
AURORA_BURN_DAMAGE = 25.0
AURORA_BURN_DURATION = 2.0
AURORA_BURN_STACKS = 3
DESIGN_IRONCLAD_HIT_CAP = 0.05
DESIGN_ORACLE_LINK_DURATION = 4.0
DESIGN_ORACLE_LINK_SHARE = 1.0
DESIGN_RAIN_INTERVAL = 0.2
DESIGN_RAIN_DAMAGE = 11.0
DESIGN_WOLF_DURATION = 30.0
DESIGN_DRONE_DURATION = 5.0
DESIGN_GHOST_SAILOR_DURATION = 8.0
DESIGN_LARVA_DURATION = 8.0

WEAPON_ORB_TARGET = 2
WEAPON_ORB_RESPAWN_DELAY = 3.0
WEAPON_ORB_RADIUS = 12

WEAPON_RANGE_SHORT = 155.0
WEAPON_RANGE_MEDIUM = 225.0
WEAPON_RANGE_INFINITE = 9999.0

HIT_FLASH_DURATION = 0.10
DAMAGE_TEXT_DURATION = 0.55
SCREEN_SHAKE_STAFF = 8.0
SCREEN_SHAKE_SNIPER = 12.0
SCREEN_SHAKE_DURATION = 0.22
DEATH_PARTICLE_COUNT = 12
DEATH_PARTICLE_DURATION = 0.7
BASIC_ATTACK_COOLDOWN = 1.0
FIREARM_ATTACK_SPEED_MULTIPLIER = 1.8
FIREARM_WEAPON_IDS = ("Pistol", "SMG", "MachineGun", "Rifle")

DAMAGE_KIND_PHYSICAL = "physical"
DAMAGE_KIND_SPELL = "spell"

SPELL_BASIC_JOBS = {
    "Mage",
    "Necromancer",
    "Vampire",
    "Toxicologist",
    "Frost Mage",
    "Pyro",
    "Time Walker",
    "Druid",
    "Electro Trooper",
    "Puppeteer",
    "Succubus",
    "Hexer",
    "Chaos Demon",
    "Bard",
    "Shaman",
    "Warlock",
    "Psionic",
}

TRUE_BASIC_JOBS = set()

PHYSICAL_DAMAGE_TYPES = {
    "assassin_blink",
    "behemoth_stomp",
    "bladestorm_dash",
    "berserker_spin",
    "bullet_rain",
    "decoy_burst",
    "ground_slam",
    "mine",
    "missile_barrage",
    "summon",
    "skyfall_strike",
    "weapon_machinegun",
    "weapon_pistol",
    "weapon_rifle",
    "weapon_smg",
}

SPELL_DAMAGE_TYPES = {
    "absolute_zero",
    "chain_lightning",
    "chaos_bolt",
    "chaos_law",
    "charm_kiss",
    "dragon_breath",
    "knight_backlash",
    "lightning_totem",
    "mage_nova",
    "sniper_beam",
    "qi_wave",
    "soul_siphon",
    "stone_spikes",
    "vampire_drain",
    "weapon_staff",
}

JOB_RESISTANCE_PROFILES = {
    "Knight": {"physical_resistance": 0.78, "spell_resistance": 0.94},
    "Mage": {"physical_resistance": 1.12, "spell_resistance": 0.82},
    "Assassin": {"physical_resistance": 0.95, "spell_resistance": 1.08},
    "Berserker": {"physical_resistance": 0.84, "spell_resistance": 1.02},
    "Sniper": {"physical_resistance": 1.08, "spell_resistance": 1.05},
    "Necromancer": {"physical_resistance": 1.02, "spell_resistance": 0.88},
    "Paladin": {"physical_resistance": 0.86, "spell_resistance": 0.88},
    "Ninja": {"physical_resistance": 0.96, "spell_resistance": 1.00},
    "Bomber": {"physical_resistance": 1.00, "spell_resistance": 0.96},
    "Vampire": {"physical_resistance": 0.97, "spell_resistance": 0.90},
    "Illusionist": {"physical_resistance": 1.06, "spell_resistance": 0.90},
    "Behemoth": {"physical_resistance": 0.72, "spell_resistance": 0.96},
    "Toxicologist": {"physical_resistance": 1.04, "spell_resistance": 0.86},
    "Frost Mage": {"physical_resistance": 1.08, "spell_resistance": 0.80},
    "Pyro": {"physical_resistance": 1.10, "spell_resistance": 0.84},
    "Time Walker": {"physical_resistance": 1.14, "spell_resistance": 0.82},
    "Monk": {"physical_resistance": 0.88, "spell_resistance": 0.92},
    "Mech Armor": {"physical_resistance": 0.80, "spell_resistance": 1.00},
    "Druid": {"physical_resistance": 0.90, "spell_resistance": 0.90},
    "Electro Trooper": {"physical_resistance": 1.02, "spell_resistance": 0.84},
    "Puppeteer": {"physical_resistance": 1.00, "spell_resistance": 0.86},
    "Smasher": {"physical_resistance": 0.76, "spell_resistance": 1.02},
    "Succubus": {"physical_resistance": 1.06, "spell_resistance": 0.88},
    "Gunslinger": {"physical_resistance": 0.98, "spell_resistance": 1.06},
    "Shield Guard": {"physical_resistance": 0.70, "spell_resistance": 1.02},
    "Swordmaster": {"physical_resistance": 0.92, "spell_resistance": 1.00},
    "Windrunner": {"physical_resistance": 1.08, "spell_resistance": 0.94},
    "Hexer": {"physical_resistance": 1.00, "spell_resistance": 0.84},
    "Chaos Demon": {"physical_resistance": 1.04, "spell_resistance": 0.80},
    "Bounty Hunter": {"physical_resistance": 0.94, "spell_resistance": 1.02},
    "Geomancer": {"physical_resistance": 0.82, "spell_resistance": 0.94},
    "Bard": {"physical_resistance": 1.02, "spell_resistance": 0.90},
    "Shaman": {"physical_resistance": 1.00, "spell_resistance": 0.88},
    "Gladiator": {"physical_resistance": 0.80, "spell_resistance": 1.00},
    "Warlock": {"physical_resistance": 1.06, "spell_resistance": 0.82},
    "Tinkerer": {"physical_resistance": 0.98, "spell_resistance": 0.94},
    "Valkyrie": {"physical_resistance": 0.84, "spell_resistance": 0.92},
    "Dark Knight": {"physical_resistance": 0.78, "spell_resistance": 0.90},
    "Psionic": {"physical_resistance": 1.05, "spell_resistance": 0.84},
}


JOB_DEFS = {
    "Knight": {
        "shape": "square",
        "color": (70, 120, 255),
        "max_hp": 1300,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_SLOW,
        "attack_type": "melee",
        "attack_damage": 11,
        "attack_range": 42,
        "attack_interval": 0.75,
        "projectile_speed": 285.0,
        "move_speed": 110.0,
        "skill_id": "knight_guard",
    },
    "Mage": {
        "shape": "circle",
        "color": (170, 82, 255),
        "max_hp": 600,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_SLOW,
        "attack_type": "ranged",
        "attack_damage": 10,
        "attack_range": 300,
        "attack_interval": 0.70,
        "projectile_speed": 310.0,
        "move_speed": 120.0,
        "skill_id": "mage_nova",
    },
    "Assassin": {
        "shape": "triangle",
        "color": (20, 24, 28),
        "max_hp": 500,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_VERY_FAST,
        "attack_type": "melee",
        "attack_damage": 10,
        "attack_range": 36,
        "attack_interval": 0.52,
        "use_design_attack_speed": True,
        "projectile_speed": 305.0,
        "move_speed": 150.0,
        "skill_id": "assassin_blink",
    },
    "Berserker": {
        "shape": "pentagon",
        "color": (225, 60, 60),
        "max_hp": 1200,
        "mp_mode": "damage_taken",
        "mp_rate": 0.0,
        "attack_type": "melee",
        "attack_damage": 11,
        "attack_range": 48,
        "attack_interval": 0.60,
        "projectile_speed": 260.0,
        "move_speed": 130.0,
        "skill_id": "berserker_spin",
    },
    "Sniper": {
        "shape": "diamond",
        "color": (72, 204, 92),
        "max_hp": 400,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_SLOW,
        "attack_type": "ranged",
        "attack_damage": 15,
        "attack_range": 340,
        "attack_interval": 1.10,
        "projectile_speed": 380.0,
        "move_speed": 100.0,
        "skill_id": "sniper_beam",
    },
    "Necromancer": {
        "shape": "circle",
        "color": (70, 70, 78),
        "max_hp": 800,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_MEDIUM,
        "attack_type": "ranged",
        "attack_damage": 7,
        "attack_range": 280,
        "attack_interval": 0.75,
        "projectile_speed": 295.0,
        "move_speed": 116.0,
        "skill_id": "necro_summon",
    },
    "Paladin": {
        "shape": "cross",
        "color": (235, 190, 62),
        "max_hp": 1000,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_MEDIUM,
        "attack_type": "melee",
        "attack_damage": 8,
        "attack_range": 44,
        "attack_interval": 0.72,
        "projectile_speed": 300.0,
        "move_speed": 124.0,
        "skill_id": "paladin_heal",
    },
    "Ninja": {
        "shape": "hexagon",
        "color": (54, 210, 220),
        "max_hp": 600,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_FAST,
        "attack_type": "melee",
        "attack_damage": 7,
        "attack_range": 34,
        "attack_interval": 0.55,
        "projectile_speed": 320.0,
        "move_speed": 144.0,
        "skill_id": "ninja_decoy",
    },
    "Bomber": {
        "shape": "square",
        "color": (255, 144, 44),
        "max_hp": 700,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_MEDIUM,
        "attack_type": "ranged",
        "attack_damage": 8,
        "attack_range": 260,
        "attack_interval": 0.78,
        "projectile_speed": 285.0,
        "move_speed": 112.0,
        "skill_id": "bomber_mines",
    },
    "Vampire": {
        "shape": "circle",
        "color": (184, 26, 46),
        "max_hp": 800,
        "mp_mode": "timed",
        "mp_rate": 0.0,
        "attack_type": "ranged",
        "attack_damage": 8,
        "attack_range": 240,
        "attack_interval": 0.70,
        "projectile_speed": 295.0,
        "move_speed": 118.0,
        "skill_id": "vampire_drain",
    },
    "Illusionist": {
        "shape": "star5",
        "color": (255, 112, 188),
        "max_hp": 550,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_FAST,
        "attack_type": "melee",
        "attack_damage": 9,
        "attack_range": 40,
        "attack_interval": 0.58,
        "projectile_speed": 300.0,
        "move_speed": 146.0,
        "skill_id": "illusion_twins",
    },
    "Behemoth": {
        "shape": "circle",
        "color": (110, 108, 104),
        "max_hp": 1800,
        "mp_mode": "damage_taken_flat",
        "mp_rate": 2.0,
        "attack_type": "melee",
        "attack_damage": 18,
        "attack_range": 54,
        "attack_interval": 1.2,
        "projectile_speed": 240.0,
        "move_speed": 72.0,
        "skill_id": "behemoth_stomp",
        "radius_scale": 1.35,
    },
    "Toxicologist": {
        "shape": "diamond",
        "color": (132, 255, 74),
        "max_hp": 700,
        "mp_mode": "damage_dealt_flat",
        "mp_rate": 6.0,
        "attack_type": "ranged",
        "attack_damage": 8,
        "attack_range": 290,
        "attack_interval": 0.82,
        "projectile_speed": 300.0,
        "move_speed": 118.0,
        "skill_id": "toxic_nova",
    },
    "Frost Mage": {
        "shape": "star6",
        "color": (124, 214, 255),
        "max_hp": 600,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_MEDIUM,
        "attack_type": "ranged",
        "attack_damage": 8,
        "attack_range": 300,
        "attack_interval": 0.92,
        "projectile_speed": 285.0,
        "move_speed": 102.0,
        "skill_id": "absolute_zero",
    },
    "Pyro": {
        "shape": "triangle",
        "color": (255, 82, 70),
        "max_hp": 505,
        "mp_mode": "damage_dealt_flat",
        "mp_rate": 10.0,
        "attack_type": "ranged",
        "attack_damage": 8,
        "attack_range": 250,
        "attack_interval": 0.78,
        "projectile_speed": 305.0,
        "move_speed": 136.0,
        "skill_id": "dragon_breath",
    },
    "Time Walker": {
        "shape": "hourglass",
        "color": (225, 230, 236),
        "max_hp": 450,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_VERY_FAST,
        "attack_type": "ranged",
        "attack_damage": 7,
        "attack_range": 270,
        "attack_interval": 0.70,
        "projectile_speed": 315.0,
        "move_speed": 148.0,
        "skill_id": "time_rewind",
    },
    "Monk": {
        "shape": "circle",
        "color": (245, 218, 74),
        "max_hp": 900,
        "mp_mode": "attack_count",
        "mp_rate": 5.0,
        "attack_type": "melee",
        "attack_damage": 10,
        "attack_range": 46,
        "attack_interval": 0.62,
        "projectile_speed": 300.0,
        "move_speed": 144.0,
        "skill_id": "qi_wave",
    },
    "Mech Armor": {
        "shape": "wide",
        "color": (126, 132, 142),
        "max_hp": 1300.8,
        "mp_mode": "damage_taken_flat",
        "mp_rate": 5.0,
        "attack_type": "ranged",
        "attack_damage": 9,
        "attack_range": 285,
        "attack_interval": 0.88,
        "projectile_speed": 290.0,
        "move_speed": 96.0,
        "skill_id": "missile_barrage",
    },
    "Druid": {
        "shape": "oval",
        "color": (76, 152, 78),
        "max_hp": 850,
        "mp_mode": "passive",
        "mp_rate": MP_RATE_MEDIUM,
        "attack_type": "ranged",
        "attack_damage": 8,
        "attack_range": 255,
        "attack_interval": 0.82,
        "projectile_speed": 290.0,
        "move_speed": 118.0,
        "skill_id": "bear_form",
    },
}

JOB_DEFS.update(
    {
        "Electro Trooper": {
            "shape": "diamond",
            "color": (255, 226, 68),
            "max_hp": 750,
            "mp_mode": "damage_dealt_flat",
            "mp_rate": 8.0,
            "attack_type": "ranged",
            "attack_damage": 8,
            "attack_range": 285,
            "attack_interval": 0.76,
            "projectile_speed": 315.0,
            "move_speed": 134.0,
            "skill_id": "chain_lightning",
            "attack_targets": 2,
        },
        "Puppeteer": {
            "shape": "pentagon",
            "color": (82, 34, 110),
            "max_hp": 651.0,
            "mp_mode": "passive",
            "mp_rate": MP_RATE_SLOW,
            "attack_type": "melee",
            "attack_damage": 8,
            "attack_range": 40,
            "attack_interval": 0.68,
            "projectile_speed": 300.0,
            "move_speed": 118.0,
            "skill_id": "mind_control",
        },
        "Smasher": {
            "shape": "truck",
            "color": (164, 72, 56),
            "max_hp": 1400.7,
            "mp_mode": "damage_taken_flat",
            "mp_rate": 8.0,
            "attack_type": "melee",
            "attack_damage": 12,
            "attack_range": 52,
            "attack_interval": 0.92,
            "projectile_speed": 260.0,
            "move_speed": 94.0,
            "skill_id": "ground_slam",
            "radius_scale": 1.18,
            "melee_aoe_radius": 36.0,
        },
        "Succubus": {
            "shape": "heart_down",
            "color": (255, 66, 196),
            "max_hp": 652,
            "mp_mode": "damage_dealt_flat",
            "mp_rate": 10.0,
            "attack_type": "ranged",
            "attack_damage": 8,
            "attack_range": 275,
            "attack_interval": 0.72,
            "projectile_speed": 310.0,
            "move_speed": 146.0,
            "skill_id": "charm_kiss",
        },
        "Gunslinger": {
            "shape": "cross_x",
            "color": (228, 228, 228),
            "max_hp": 555,
            "mp_mode": "attack_count",
            "mp_rate": 5.0,
            "attack_type": "ranged",
            "attack_damage": 8,
            "attack_range": 285,
            "attack_interval": 0.64,
            "projectile_speed": 325.0,
            "move_speed": 142.0,
            "skill_id": "bullet_rain",
        },
        "Shield Guard": {
            "shape": "wide",
            "color": (112, 116, 122),
            "max_hp": 1600,
            "mp_mode": "damage_taken_flat",
            "mp_rate": 5.0,
            "attack_type": "melee",
            "attack_damage": 11,
            "attack_range": 48,
            "attack_interval": 0.86,
            "projectile_speed": 280.0,
            "move_speed": 78.0,
            "skill_id": "energy_bulwark",
            "radius_scale": 1.16,
        },
        "Swordmaster": {
            "shape": "triangle",
            "color": (245, 245, 245),
            "max_hp": 750,
            "mp_mode": "attack_count",
            "mp_rate": 10.0,
            "attack_type": "melee",
            "attack_damage": 12,
            "attack_range": 42,
            "attack_interval": 0.58,
            "use_design_attack_speed": True,
            "projectile_speed": 300.0,
            "move_speed": 150.0,
            "skill_id": "bladestorm_dash",
        },
        "Windrunner": {
            "shape": "slim_diamond",
            "color": (66, 220, 178),
            "max_hp": 502,
            "mp_mode": "distance_moved",
            "mp_rate": 0.0,
            "attack_type": "ranged",
            "attack_damage": 7,
            "attack_range": 290,
            "attack_interval": 0.70,
            "projectile_speed": 330.0,
            "move_speed": 168.0,
            "skill_id": "hurricane_storm",
        },
        "Hexer": {
            "shape": "circle",
            "color": (116, 36, 86),
            "max_hp": 650.0,
            "mp_mode": "passive",
            "mp_rate": MP_RATE_MEDIUM,
            "attack_type": "melee",
            "attack_damage": 8,
            "attack_range": 40,
            "attack_interval": 0.72,
            "projectile_speed": 285.0,
            "move_speed": 116.0,
            "skill_id": "doom_curse",
        },
        "Chaos Demon": {
            "shape": "shards",
            "color": (188, 112, 255),
            "max_hp": 888,
            "mp_mode": "chaos_random",
            "mp_rate": 0.0,
            "attack_type": "ranged",
            "attack_damage": 9,
            "attack_range": 280,
            "attack_interval": 0.78,
            "use_design_attack_speed": True,
            "projectile_speed": 300.0,
            "move_speed": 116.0,
            "skill_id": "chaos_law",
        },
        "Bounty Hunter": {
            "shape": "pentagon",
            "color": (134, 108, 40),
            "max_hp": 720,
            "mp_mode": "damage_dealt_flat",
            "mp_rate": 10.0,
            "attack_type": "ranged",
            "attack_damage": 9,
            "attack_range": 290,
            "attack_interval": 0.74,
            "projectile_speed": 320.0,
            "move_speed": 146.0,
            "skill_id": "ultimate_bounty",
        },
        "Geomancer": {
            "shape": "trapezoid",
            "color": (126, 92, 58),
            "max_hp": 1100.8,
            "mp_mode": "damage_taken_flat",
            "mp_rate": 10.0,
            "attack_type": "melee",
            "attack_damage": 11,
            "attack_range": 46,
            "attack_interval": 0.86,
            "projectile_speed": 280.0,
            "move_speed": 92.0,
            "skill_id": "stone_spikes",
        },
        "Bard": {
            "shape": "music_note",
            "color": (142, 226, 188),
            "max_hp": 551,
            "mp_mode": "passive",
            "mp_rate": MP_RATE_FAST,
            "attack_type": "ranged",
            "attack_damage": 9,
            "attack_range": 255,
            "attack_interval": 0.76,
            "projectile_speed": 300.0,
            "move_speed": 134.0,
            "skill_id": "battle_song",
        },
        "Shaman": {
            "shape": "diamond",
            "color": (210, 44, 44),
            "max_hp": 800,
            "mp_mode": "passive",
            "mp_rate": MP_RATE_MEDIUM,
            "attack_type": "ranged",
            "attack_damage": 8,
            "attack_range": 270,
            "attack_interval": 0.82,
            "projectile_speed": 300.0,
            "move_speed": 104.0,
            "skill_id": "lightning_totem",
        },
        "Gladiator": {
            "shape": "half_circle",
            "color": (176, 128, 74),
            "max_hp": 1300,
            "mp_mode": "damage_taken_flat",
            "mp_rate": 5.0,
            "attack_type": "melee",
            "attack_damage": 12,
            "attack_range": 50,
            "attack_interval": 0.82,
            "projectile_speed": 285.0,
            "move_speed": 136.0,
            "skill_id": "fatal_duel",
        },
        "Warlock": {
            "shape": "star5_down",
            "color": (86, 202, 120),
            "max_hp": 666,
            "mp_mode": "health_sacrifice_timed",
            "mp_rate": 0.0,
            "attack_type": "ranged",
            "attack_damage": 8,
            "attack_range": 275,
            "attack_interval": 0.80,
            "projectile_speed": 300.0,
            "move_speed": 116.0,
            "skill_id": "soul_siphon",
        },
        "Tinkerer": {
            "shape": "gear",
            "color": (182, 110, 58),
            "max_hp": 752,
            "mp_mode": "passive",
            "mp_rate": MP_RATE_FAST,
            "attack_type": "ranged",
            "attack_damage": 8,
            "attack_range": 265,
            "attack_interval": 0.78,
            "projectile_speed": 300.0,
            "move_speed": 144.0,
            "skill_id": "overclock_weapon",
        },
        "Valkyrie": {
            "shape": "triangle_down",
            "color": (255, 208, 54),
            "max_hp": 1000,
            "mp_mode": "damage_taken_scaled",
            "mp_rate": 1.2,
            "attack_type": "melee",
            "attack_damage": 50,
            "attack_range": 48,
            "attack_interval": 0.74,
            "use_design_attack_speed": True,
            "use_design_attack_damage": True,
            "projectile_speed": 300.0,
            "move_speed": 148.0,
            "skill_id": "skyfall_strike",
        },
        "Dark Knight": {
            "shape": "square",
            "color": (18, 18, 22),
            "max_hp": 1400,
            "mp_mode": "damage_taken_flat",
            "mp_rate": 8.0,
            "attack_type": "melee",
            "attack_damage": 12,
            "attack_range": 48,
            "attack_interval": 0.84,
            "projectile_speed": 280.0,
            "move_speed": 102.0,
            "skill_id": "revenge_thorns",
        },
        "Psionic": {
            "shape": "ring",
            "color": (255, 116, 214),
            "max_hp": 700,
            "mp_mode": "passive",
            "mp_rate": MP_RATE_VERY_FAST,
            "attack_type": "ranged",
            "attack_damage": 8,
            "attack_range": 285,
            "attack_interval": 0.76,
            "projectile_speed": 315.0,
            "move_speed": 118.0,
            "skill_id": "telekinetic_redirect",
        },
    }
)


CHARACTER_DATA = {
        "Knight": {
            "name": "Knight",
            "shape": JOB_DEFS["Knight"]["shape"],
            "color": JOB_DEFS["Knight"]["color"],
            "max_hp": JOB_DEFS["Knight"]["max_hp"],
            "move_speed": JOB_DEFS["Knight"]["move_speed"],
            "attack_type": JOB_DEFS["Knight"]["attack_type"],
            "attack_range": JOB_DEFS["Knight"]["attack_range"],
            "mp_charge_style": "Slow passive charge",
            "skill_name": "Knight Spirit",
            "skill_description": "Raises a blue shield for 6 seconds, reduces incoming damage by 30 percent, heals 3 percent max HP each second, and stores damage taken for a 3 second backlash after it ends.",
        },
        "Mage": {
            "name": "Mage",
            "shape": JOB_DEFS["Mage"]["shape"],
            "color": JOB_DEFS["Mage"]["color"],
        "max_hp": JOB_DEFS["Mage"]["max_hp"],
        "move_speed": JOB_DEFS["Mage"]["move_speed"],
            "attack_type": JOB_DEFS["Mage"]["attack_type"],
            "attack_range": JOB_DEFS["Mage"]["attack_range"],
            "mp_charge_style": "Slow passive charge",
            "skill_name": "Arcane Nova",
            "skill_description": "Launches 8 piercing projectiles in a full circle that damage and heavily slow enemies. Arcane hits build stacks, and full stacks trigger an overcharged nova with a lingering arcane field before the caster begins to burn over time.",
        },
        "Assassin": {
            "name": "Assassin",
            "shape": JOB_DEFS["Assassin"]["shape"],
            "color": JOB_DEFS["Assassin"]["color"],
        "max_hp": JOB_DEFS["Assassin"]["max_hp"],
        "move_speed": JOB_DEFS["Assassin"]["move_speed"],
            "attack_type": JOB_DEFS["Assassin"]["attack_type"],
            "attack_range": JOB_DEFS["Assassin"]["attack_range"],
            "mp_charge_style": "Very fast passive charge",
            "skill_name": "Blink Backstab",
            "skill_description": "Teleports next to the lowest-HP enemy and delivers an instant burst of melee damage. If the strike kills, the assassin can immediately blink again.",
        },
        "Berserker": {
            "name": "Berserker",
            "shape": JOB_DEFS["Berserker"]["shape"],
            "color": JOB_DEFS["Berserker"]["color"],
        "max_hp": JOB_DEFS["Berserker"]["max_hp"],
        "move_speed": JOB_DEFS["Berserker"]["move_speed"],
        "attack_type": JOB_DEFS["Berserker"]["attack_type"],
            "attack_range": JOB_DEFS["Berserker"]["attack_range"],
            "mp_charge_style": "Charge from damage taken",
            "skill_name": "Cyclone Rage",
            "skill_description": "Spins for 4 seconds, gains speed, deals repeated area damage, and heals when the whirlwind connects. The cyclone is accompanied by a visible spinning shock ring.",
        },
        "Sniper": {
            "name": "Sniper",
            "shape": JOB_DEFS["Sniper"]["shape"],
            "color": JOB_DEFS["Sniper"]["color"],
        "max_hp": JOB_DEFS["Sniper"]["max_hp"],
        "move_speed": JOB_DEFS["Sniper"]["move_speed"],
            "attack_type": JOB_DEFS["Sniper"]["attack_type"],
            "attack_range": JOB_DEFS["Sniper"]["attack_range"],
            "mp_charge_style": "Slow passive charge",
            "skill_name": "Death Ray",
            "skill_description": "Charges briefly, then fires a piercing beam across the arena toward the farthest enemy. Distance increases basic attack damage, and steady aim briefly empowers the next shot.",
        },
    "Necromancer": {
        "name": "Necromancer",
        "shape": JOB_DEFS["Necromancer"]["shape"],
        "color": JOB_DEFS["Necromancer"]["color"],
        "max_hp": JOB_DEFS["Necromancer"]["max_hp"],
        "move_speed": JOB_DEFS["Necromancer"]["move_speed"],
        "attack_type": JOB_DEFS["Necromancer"]["attack_type"],
        "attack_range": JOB_DEFS["Necromancer"]["attack_range"],
        "mp_charge_style": "Medium passive charge",
        "skill_name": "Raise Dead",
        "skill_description": "Summons two skeleton minions that chase enemies and explode on contact.",
        "passive_name": "Bone Resonance",
        "passive_description": "Each time the necromancer deals damage, bone stacks build up. Each stack raises move speed and summon damage, and skeletons burst when they fall.",
    },
    "Paladin": {
        "name": "Paladin",
        "shape": JOB_DEFS["Paladin"]["shape"],
        "color": JOB_DEFS["Paladin"]["color"],
        "max_hp": JOB_DEFS["Paladin"]["max_hp"],
        "move_speed": JOB_DEFS["Paladin"]["move_speed"],
        "attack_type": JOB_DEFS["Paladin"]["attack_type"],
        "attack_range": JOB_DEFS["Paladin"]["attack_range"],
        "mp_charge_style": "Medium passive charge",
        "skill_name": "Holy Recovery",
        "skill_description": "Instantly heals a chunk of health, then gains a slower but steady regeneration effect for several seconds.",
        "passive_name": "Holy Vow",
        "passive_description": "Every time the paladin restores health, holy stacks build up. Each stack raises damage, movement speed, and durability, and Holy Recovery grants extra shielding when charged.",
    },
    "Ninja": {
        "name": "Ninja",
        "shape": JOB_DEFS["Ninja"]["shape"],
        "color": JOB_DEFS["Ninja"]["color"],
        "max_hp": JOB_DEFS["Ninja"]["max_hp"],
        "move_speed": JOB_DEFS["Ninja"]["move_speed"],
        "attack_type": JOB_DEFS["Ninja"]["attack_type"],
        "attack_range": JOB_DEFS["Ninja"]["attack_range"],
        "mp_charge_style": "Fast passive charge",
        "skill_name": "Shadow Decoy",
        "skill_description": "Leaves behind a fragile decoy and dashes backward to reposition out of danger.",
        "passive_name": "Shadow Focus",
        "passive_description": "Travel distance builds shadow stacks. Each stack raises move speed and basic damage, and the next basic attack consumes all stacks to blind the target.",
    },
    "Bomber": {
        "name": "Bomber",
        "shape": JOB_DEFS["Bomber"]["shape"],
        "color": JOB_DEFS["Bomber"]["color"],
        "max_hp": JOB_DEFS["Bomber"]["max_hp"],
        "move_speed": JOB_DEFS["Bomber"]["move_speed"],
        "attack_type": JOB_DEFS["Bomber"]["attack_type"],
        "attack_range": JOB_DEFS["Bomber"]["attack_range"],
        "mp_charge_style": "Medium passive charge",
        "skill_name": "Mine Trail",
        "skill_description": "Drops three explosive mines behind the current path that detonate when enemies step on them.",
        "passive_name": "Fuse Calibration",
        "passive_description": "Dealing damage builds fuse stacks. Each stack increases move speed, basic damage, and mine explosion power, making every minefield progressively deadlier.",
    },
    "Vampire": {
        "name": "Vampire",
        "shape": JOB_DEFS["Vampire"]["shape"],
        "color": JOB_DEFS["Vampire"]["color"],
        "max_hp": JOB_DEFS["Vampire"]["max_hp"],
        "move_speed": JOB_DEFS["Vampire"]["move_speed"],
        "attack_type": JOB_DEFS["Vampire"]["attack_type"],
        "attack_range": JOB_DEFS["Vampire"]["attack_range"],
        "mp_charge_style": "Timed burst charge every 4 seconds",
        "skill_name": "Blood Siphon",
        "skill_description": "Channels a life-drain on the nearest enemy, heals immediately, then continues regenerating over time.",
        "passive_name": "Blood Moon Hunger",
        "passive_description": "The lower the vampire's health, the stronger the hunger. Missing health grants move speed, attack speed, and basic damage, and all healing effects become stronger.",
    },
    "Illusionist": {
        "name": "Illusionist",
        "shape": JOB_DEFS["Illusionist"]["shape"],
        "color": JOB_DEFS["Illusionist"]["color"],
        "max_hp": JOB_DEFS["Illusionist"]["max_hp"],
        "move_speed": JOB_DEFS["Illusionist"]["move_speed"],
        "attack_type": JOB_DEFS["Illusionist"]["attack_type"],
        "attack_range": JOB_DEFS["Illusionist"]["attack_range"],
        "mp_charge_style": "Fast passive charge",
        "skill_name": "Mirror Twins",
        "skill_description": "Creates two pink mirror clones with 60 percent of the caster's HP. The clones roam unpredictably, deal only 20 percent of the main body's damage, and vanish after 5 seconds. At full mirror resonance, the skill summons one additional clone and lasts longer.",
        "passive_name": "Mirror Resonance",
        "passive_description": "Every 18 damage dealt grants 1 mirror stack, up to 3. Each stack raises move speed by 3 percent, basic damage by 4 percent, and attack speed by 3 percent. At 3 stacks, Mirror Twins creates one extra clone and extends clone duration.",
    },
    "Behemoth": {
        "name": "Behemoth",
        "shape": JOB_DEFS["Behemoth"]["shape"],
        "color": JOB_DEFS["Behemoth"]["color"],
        "max_hp": JOB_DEFS["Behemoth"]["max_hp"],
        "move_speed": JOB_DEFS["Behemoth"]["move_speed"],
        "attack_type": JOB_DEFS["Behemoth"]["attack_type"],
        "attack_range": JOB_DEFS["Behemoth"]["attack_range"],
        "mp_charge_style": "Gain 2 percent MP when damaged",
        "skill_name": "Stomp",
        "skill_description": "Smashes the ground to stun nearby enemies for 2.5 seconds, deals 50 damage, and gains a 200-point true shield that blocks the same amount of incoming damage. Higher stonehide stacks increase the impact and shield strength.",
        "passive_name": "Stonehide Rampart",
        "passive_description": "Every 20 damage taken grants 1 stone stack, up to 5. Each stack reduces incoming damage by 3 percent, raises move speed by 2 percent, and basic damage by 5 percent. At full stacks, Stomp strikes harder and reinforces the true shield.",
    },
    "Toxicologist": {
        "name": "Toxicologist",
        "shape": JOB_DEFS["Toxicologist"]["shape"],
        "color": JOB_DEFS["Toxicologist"]["color"],
        "max_hp": JOB_DEFS["Toxicologist"]["max_hp"],
        "move_speed": JOB_DEFS["Toxicologist"]["move_speed"],
        "attack_type": JOB_DEFS["Toxicologist"]["attack_type"],
        "attack_range": JOB_DEFS["Toxicologist"]["attack_range"],
        "mp_charge_style": "Gain 6 percent MP per damage event",
        "skill_name": "Toxic Nova",
        "skill_description": "Creates a poison field underfoot for 8 seconds. Enemies inside take true damage each second and gain stacking poison that keeps draining true damage until it decays. Corrosion stacks widen the field and intensify the toxins.",
        "passive_name": "Corrosive Saturation",
        "passive_description": "Every 24 damage dealt grants 1 corrosion stack, up to 5. Each stack raises move speed by 3 percent, basic damage by 5 percent, and attack speed by 3 percent. Toxic Nova becomes wider, lasts longer, and applies stronger poison pressure as corrosion builds.",
    },
    "Frost Mage": {
        "name": "Frost Mage",
        "shape": JOB_DEFS["Frost Mage"]["shape"],
        "color": JOB_DEFS["Frost Mage"]["color"],
        "max_hp": JOB_DEFS["Frost Mage"]["max_hp"],
        "move_speed": JOB_DEFS["Frost Mage"]["move_speed"],
        "attack_type": JOB_DEFS["Frost Mage"]["attack_type"],
        "attack_range": JOB_DEFS["Frost Mage"]["attack_range"],
        "mp_charge_style": "Medium passive charge",
        "skill_name": "Absolute Zero",
        "skill_description": "Launches a giant ice spike that freezes the target area for 3 seconds. Frozen enemies take 12 bursts of damage based on their missing health. Core stacks extend the freeze and amplify the burst damage.",
        "passive_name": "Frozen Core",
        "passive_description": "Every 22 damage dealt grants 1 core stack, up to 5. Each stack raises move speed by 3 percent, basic damage by 4 percent, and attack speed by 4 percent. Absolute Zero freezes longer and shatters harder as the core deepens.",
    },
    "Pyro": {
        "name": "Pyro",
        "shape": JOB_DEFS["Pyro"]["shape"],
        "color": JOB_DEFS["Pyro"]["color"],
        "max_hp": JOB_DEFS["Pyro"]["max_hp"],
        "move_speed": JOB_DEFS["Pyro"]["move_speed"],
        "attack_type": JOB_DEFS["Pyro"]["attack_type"],
        "attack_range": JOB_DEFS["Pyro"]["attack_range"],
        "mp_charge_style": "Gain 10 percent MP per damage event",
        "skill_name": "Dragon Breath",
        "skill_description": "Breathes fire in a cone for 2.8 seconds, burning every 0.2 seconds in the current facing direction. Ember stacks extend the breath and deepen the burn.",
        "passive_name": "Ember Pressure",
        "passive_description": "Every 22 damage dealt grants 1 ember stack, up to 5. Each stack raises move speed by 3 percent, basic damage by 5 percent, and attack speed by 4 percent. Dragon Breath lasts longer, burns hotter, and adds a brief chill on contact when ember stacks rise.",
    },
    "Time Walker": {
        "name": "Time Walker",
        "shape": JOB_DEFS["Time Walker"]["shape"],
        "color": JOB_DEFS["Time Walker"]["color"],
        "max_hp": JOB_DEFS["Time Walker"]["max_hp"],
        "move_speed": JOB_DEFS["Time Walker"]["move_speed"],
        "attack_type": JOB_DEFS["Time Walker"]["attack_type"],
        "attack_range": JOB_DEFS["Time Walker"]["attack_range"],
        "mp_charge_style": "Very fast passive charge",
        "skill_name": "Time Rewind",
        "skill_description": "Clears all negative states and rewinds the caster's HP and position to a snapshot from 5 seconds earlier.",
    },
    "Monk": {
        "name": "Monk",
        "shape": JOB_DEFS["Monk"]["shape"],
        "color": JOB_DEFS["Monk"]["color"],
        "max_hp": JOB_DEFS["Monk"]["max_hp"],
        "move_speed": JOB_DEFS["Monk"]["move_speed"],
        "attack_type": JOB_DEFS["Monk"]["attack_type"],
        "attack_range": JOB_DEFS["Monk"]["attack_range"],
        "mp_charge_style": "Gain 5 percent MP per attack",
        "skill_name": "Qi Wave",
        "skill_description": "Unleashes a straight shockwave that deals 80 damage, knocks enemies back 80 pixels, and stuns them for 5 seconds.",
    },
    "Mech Armor": {
        "name": "Mech Armor",
        "shape": JOB_DEFS["Mech Armor"]["shape"],
        "color": JOB_DEFS["Mech Armor"]["color"],
        "max_hp": JOB_DEFS["Mech Armor"]["max_hp"],
        "move_speed": JOB_DEFS["Mech Armor"]["move_speed"],
        "attack_type": JOB_DEFS["Mech Armor"]["attack_type"],
        "attack_range": JOB_DEFS["Mech Armor"]["attack_range"],
        "mp_charge_style": "Gain 5 percent MP when damaged",
        "skill_name": "Missile Barrage",
        "skill_description": "Launches 15 homing missiles split across up to 3 random enemies. Each missile explodes for area damage on impact.",
    },
        "Druid": {
            "name": "Druid",
            "shape": JOB_DEFS["Druid"]["shape"],
            "color": JOB_DEFS["Druid"]["color"],
        "max_hp": JOB_DEFS["Druid"]["max_hp"],
        "move_speed": JOB_DEFS["Druid"]["move_speed"],
        "attack_type": JOB_DEFS["Druid"]["attack_type"],
            "attack_range": JOB_DEFS["Druid"]["attack_range"],
            "mp_charge_style": "Medium passive charge",
            "skill_name": "Bear Form",
            "skill_description": "Normally fights in ranged form. Bear Form lasts 8 seconds, increases size, grants bonus max HP, heals instantly, switches the Druid to melee attacks, and adds a stun on hit.",
        },
}

CHARACTER_DATA.update(
    {
        "Electro Trooper": {
            "name": "Electro Trooper",
            "shape": JOB_DEFS["Electro Trooper"]["shape"],
            "color": JOB_DEFS["Electro Trooper"]["color"],
            "max_hp": JOB_DEFS["Electro Trooper"]["max_hp"],
            "move_speed": JOB_DEFS["Electro Trooper"]["move_speed"],
            "attack_type": JOB_DEFS["Electro Trooper"]["attack_type"],
            "attack_range": JOB_DEFS["Electro Trooper"]["attack_range"],
            "mp_charge_style": "Gain 8 percent MP per damage event",
            "skill_name": "Chain Lightning",
            "skill_description": "Fires a lightning arc that can bounce across up to 4 enemies. Each hit deals 12 damage and applies Doom for 4 seconds, dealing damage over time and executing targets under 15 percent HP.",
        },
        "Puppeteer": {
            "name": "Puppeteer",
            "shape": JOB_DEFS["Puppeteer"]["shape"],
            "color": JOB_DEFS["Puppeteer"]["color"],
            "max_hp": JOB_DEFS["Puppeteer"]["max_hp"],
            "move_speed": JOB_DEFS["Puppeteer"]["move_speed"],
            "attack_type": JOB_DEFS["Puppeteer"]["attack_type"],
            "attack_range": JOB_DEFS["Puppeteer"]["attack_range"],
            "mp_charge_style": "Slow passive charge",
            "skill_name": "Mind Control",
            "skill_description": "Seizes control of the nearest enemy for 8 seconds and forces them to turn on the rest of the arena.",
        },
        "Smasher": {
            "name": "Smasher",
            "shape": JOB_DEFS["Smasher"]["shape"],
            "color": JOB_DEFS["Smasher"]["color"],
            "max_hp": JOB_DEFS["Smasher"]["max_hp"],
            "move_speed": JOB_DEFS["Smasher"]["move_speed"],
            "attack_type": JOB_DEFS["Smasher"]["attack_type"],
            "attack_range": JOB_DEFS["Smasher"]["attack_range"],
            "mp_charge_style": "Gain 8 percent MP when damaged",
            "skill_name": "Groundbreaker",
            "skill_description": "Leaps into the air with brief invulnerability, crashes down on a target area, deals 30 area damage, and heavily slows enemies caught in the impact.",
        },
        "Succubus": {
            "name": "Succubus",
            "shape": JOB_DEFS["Succubus"]["shape"],
            "color": JOB_DEFS["Succubus"]["color"],
            "max_hp": JOB_DEFS["Succubus"]["max_hp"],
            "move_speed": JOB_DEFS["Succubus"]["move_speed"],
            "attack_type": JOB_DEFS["Succubus"]["attack_type"],
            "attack_range": JOB_DEFS["Succubus"]["attack_range"],
            "mp_charge_style": "Gain 10 percent MP per damage event",
            "skill_name": "Charm Kiss",
            "skill_description": "Launches a heart projectile that charms an enemy for 3 seconds. During the charm, the victim cannot attack and is drawn slowly inward while the Succubus fires a five-shot reduced-damage barrage.",
        },
        "Gunslinger": {
            "name": "Gunslinger",
            "shape": JOB_DEFS["Gunslinger"]["shape"],
            "color": JOB_DEFS["Gunslinger"]["color"],
            "max_hp": JOB_DEFS["Gunslinger"]["max_hp"],
            "move_speed": JOB_DEFS["Gunslinger"]["move_speed"],
            "attack_type": JOB_DEFS["Gunslinger"]["attack_type"],
            "attack_range": JOB_DEFS["Gunslinger"]["attack_range"],
            "mp_charge_style": "Charge from attack count",
            "skill_name": "Bullet Rain",
            "skill_description": "Plants in place and erupts into a 360-degree spray of 20 random bullets around the arena.",
        },
        "Shield Guard": {
            "name": "Shield Guard",
            "shape": JOB_DEFS["Shield Guard"]["shape"],
            "color": JOB_DEFS["Shield Guard"]["color"],
            "max_hp": JOB_DEFS["Shield Guard"]["max_hp"],
            "move_speed": JOB_DEFS["Shield Guard"]["move_speed"],
            "attack_type": JOB_DEFS["Shield Guard"]["attack_type"],
            "attack_range": JOB_DEFS["Shield Guard"]["attack_range"],
            "mp_charge_style": "Gain 5 percent MP when damaged",
            "skill_name": "Energy Bulwark",
            "skill_description": "Raises a wide energy wall in front of the user for 5 seconds, blocking hostile projectiles and acting as an impassable barrier.",
        },
        "Swordmaster": {
            "name": "Swordmaster",
            "shape": JOB_DEFS["Swordmaster"]["shape"],
            "color": JOB_DEFS["Swordmaster"]["color"],
            "max_hp": JOB_DEFS["Swordmaster"]["max_hp"],
            "move_speed": JOB_DEFS["Swordmaster"]["move_speed"],
            "attack_type": JOB_DEFS["Swordmaster"]["attack_type"],
            "attack_range": JOB_DEFS["Swordmaster"]["attack_range"],
            "mp_charge_style": "Gain 20 percent MP per damage event",
            "skill_name": "Invincible Slash",
            "skill_description": "Turns invulnerable, slashes across the nearest enemies 5 times for 20 damage each, then gains 5 seconds of doubled attack speed.",
        },
        "Windrunner": {
            "name": "Windrunner",
            "shape": JOB_DEFS["Windrunner"]["shape"],
            "color": JOB_DEFS["Windrunner"]["color"],
            "max_hp": JOB_DEFS["Windrunner"]["max_hp"],
            "move_speed": JOB_DEFS["Windrunner"]["move_speed"],
            "attack_type": JOB_DEFS["Windrunner"]["attack_type"],
            "attack_range": JOB_DEFS["Windrunner"]["attack_range"],
            "mp_charge_style": "Charge from movement distance",
            "skill_name": "Hurricane Storm",
            "skill_description": "Accelerates even further for 4 seconds and creates a storm shell that pushes back nearby melee threats and hostile bullets.",
        },
        "Hexer": {
            "name": "Hexer",
            "shape": JOB_DEFS["Hexer"]["shape"],
            "color": JOB_DEFS["Hexer"]["color"],
            "max_hp": JOB_DEFS["Hexer"]["max_hp"],
            "move_speed": JOB_DEFS["Hexer"]["move_speed"],
            "attack_type": JOB_DEFS["Hexer"]["attack_type"],
            "attack_range": JOB_DEFS["Hexer"]["attack_range"],
            "mp_charge_style": "Medium passive charge",
            "skill_name": "Doom Curse",
            "skill_description": "Marks the healthiest enemy for 5 seconds, cutting their speed in half and causing them to take 50 percent more damage.",
        },
        "Chaos Demon": {
            "name": "Chaos Demon",
            "shape": JOB_DEFS["Chaos Demon"]["shape"],
            "color": JOB_DEFS["Chaos Demon"]["color"],
            "max_hp": JOB_DEFS["Chaos Demon"]["max_hp"],
            "move_speed": JOB_DEFS["Chaos Demon"]["move_speed"],
            "attack_type": JOB_DEFS["Chaos Demon"]["attack_type"],
            "attack_range": JOB_DEFS["Chaos Demon"]["attack_range"],
            "mp_charge_style": "Every 5 seconds gains a random 5 to 50 percent MP",
            "skill_name": "Chaos Law",
            "skill_description": "Triggers a random effect: self-heal, extreme single-target true damage, heavy direct damage, full-arena stun, or a volley of homing chaos bolts.",
        },
        "Bounty Hunter": {
            "name": "Bounty Hunter",
            "shape": JOB_DEFS["Bounty Hunter"]["shape"],
            "color": JOB_DEFS["Bounty Hunter"]["color"],
            "max_hp": JOB_DEFS["Bounty Hunter"]["max_hp"],
            "move_speed": JOB_DEFS["Bounty Hunter"]["move_speed"],
            "attack_type": JOB_DEFS["Bounty Hunter"]["attack_type"],
            "attack_range": JOB_DEFS["Bounty Hunter"]["attack_range"],
            "mp_charge_style": "Gain 10 percent MP per damage event",
            "skill_name": "Ultimate Bounty",
            "skill_description": "Randomly marks one enemy as the bounty target. Attacks against that target deal extra damage, earn coins, and each coin permanently boosts the hunter's basic attack damage.",
        },
        "Geomancer": {
            "name": "Geomancer",
            "shape": JOB_DEFS["Geomancer"]["shape"],
            "color": JOB_DEFS["Geomancer"]["color"],
            "max_hp": JOB_DEFS["Geomancer"]["max_hp"],
            "move_speed": JOB_DEFS["Geomancer"]["move_speed"],
            "attack_type": JOB_DEFS["Geomancer"]["attack_type"],
            "attack_range": JOB_DEFS["Geomancer"]["attack_range"],
            "mp_charge_style": "Gain 10 percent MP when damaged",
            "skill_name": "Stone Spikes",
            "skill_description": "Raises stone spikes beneath 3 random enemies, dealing 50 damage and rooting them in place for 5 seconds.",
        },
        "Bard": {
            "name": "Bard",
            "shape": JOB_DEFS["Bard"]["shape"],
            "color": JOB_DEFS["Bard"]["color"],
            "max_hp": JOB_DEFS["Bard"]["max_hp"],
            "move_speed": JOB_DEFS["Bard"]["move_speed"],
            "attack_type": JOB_DEFS["Bard"]["attack_type"],
            "attack_range": JOB_DEFS["Bard"]["attack_range"],
            "mp_charge_style": "Fast passive charge",
            "skill_name": "Frenzy Anthem",
            "skill_description": "Empowers every character within 100 range, friend or foe, with 50 percent move speed and attack speed, but drains 2 percent max HP per second for 4 seconds.",
        },
        "Shaman": {
            "name": "Shaman",
            "shape": JOB_DEFS["Shaman"]["shape"],
            "color": JOB_DEFS["Shaman"]["color"],
            "max_hp": JOB_DEFS["Shaman"]["max_hp"],
            "move_speed": JOB_DEFS["Shaman"]["move_speed"],
            "attack_type": JOB_DEFS["Shaman"]["attack_type"],
            "attack_range": JOB_DEFS["Shaman"]["attack_range"],
            "mp_charge_style": "Medium passive charge",
            "skill_name": "Lightning Totem",
            "skill_description": "Plants a red totem at the caster's feet. The totem has 30 HP, stays still, and each second blasts the farthest enemy within 60 range with lightning.",
        },
        "Gladiator": {
            "name": "Gladiator",
            "shape": JOB_DEFS["Gladiator"]["shape"],
            "color": JOB_DEFS["Gladiator"]["color"],
            "max_hp": JOB_DEFS["Gladiator"]["max_hp"],
            "move_speed": JOB_DEFS["Gladiator"]["move_speed"],
            "attack_type": JOB_DEFS["Gladiator"]["attack_type"],
            "attack_range": JOB_DEFS["Gladiator"]["attack_range"],
            "mp_charge_style": "Gain 5 percent MP when damaged",
            "skill_name": "Fatal Duel",
            "skill_description": "Hooks the nearest enemy in front, roots them for 3 seconds, grants them double attack speed, while the Gladiator gains damage reduction and a massive attack-speed burst.",
        },
        "Warlock": {
            "name": "Warlock",
            "shape": JOB_DEFS["Warlock"]["shape"],
            "color": JOB_DEFS["Warlock"]["color"],
            "max_hp": JOB_DEFS["Warlock"]["max_hp"],
            "move_speed": JOB_DEFS["Warlock"]["move_speed"],
            "attack_type": JOB_DEFS["Warlock"]["attack_type"],
            "attack_range": JOB_DEFS["Warlock"]["attack_range"],
            "mp_charge_style": "Every 3 seconds sacrifices HP for 40 percent MP",
            "skill_name": "Soul Siphon",
            "skill_description": "Spends 10 current HP to fire a wide infinite void wave forward for 80 damage, healing 20 percent of missing HP for each enemy struck.",
        },
        "Tinkerer": {
            "name": "Tinkerer",
            "shape": JOB_DEFS["Tinkerer"]["shape"],
            "color": JOB_DEFS["Tinkerer"]["color"],
            "max_hp": JOB_DEFS["Tinkerer"]["max_hp"],
            "move_speed": JOB_DEFS["Tinkerer"]["move_speed"],
            "attack_type": JOB_DEFS["Tinkerer"]["attack_type"],
            "attack_range": JOB_DEFS["Tinkerer"]["attack_range"],
            "mp_charge_style": "Fast passive charge",
            "skill_name": "Overclock Weapon",
            "skill_description": "Equips a random weapon and overclocks it for 3 seconds with halved fire interval and infinite ammo, then discards it.",
        },
        "Valkyrie": {
            "name": "Valkyrie",
            "shape": JOB_DEFS["Valkyrie"]["shape"],
            "color": JOB_DEFS["Valkyrie"]["color"],
            "max_hp": JOB_DEFS["Valkyrie"]["max_hp"],
            "move_speed": JOB_DEFS["Valkyrie"]["move_speed"],
            "attack_type": JOB_DEFS["Valkyrie"]["attack_type"],
            "attack_range": JOB_DEFS["Valkyrie"]["attack_range"],
            "mp_charge_style": "Charge from damage taken",
            "skill_name": "Skyfall Strike",
            "skill_description": "Flies upward invulnerably, gains a 500-point true shield, retargets the densest enemy cluster on landing, then crashes down with a golden pillar shockwave and a short stun.",
        },
        "Dark Knight": {
            "name": "Dark Knight",
            "shape": JOB_DEFS["Dark Knight"]["shape"],
            "color": JOB_DEFS["Dark Knight"]["color"],
            "max_hp": JOB_DEFS["Dark Knight"]["max_hp"],
            "move_speed": JOB_DEFS["Dark Knight"]["move_speed"],
            "attack_type": JOB_DEFS["Dark Knight"]["attack_type"],
            "attack_range": JOB_DEFS["Dark Knight"]["attack_range"],
            "mp_charge_style": "Gain 8 percent MP when damaged",
            "skill_name": "Revenge Thorns",
            "skill_description": "Enters a thorn state for 5 seconds and reflects 50 percent of all received damage back to the attacker.",
        },
        "Psionic": {
            "name": "Psionic",
            "shape": JOB_DEFS["Psionic"]["shape"],
            "color": JOB_DEFS["Psionic"]["color"],
            "max_hp": JOB_DEFS["Psionic"]["max_hp"],
            "move_speed": JOB_DEFS["Psionic"]["move_speed"],
            "attack_type": JOB_DEFS["Psionic"]["attack_type"],
            "attack_range": JOB_DEFS["Psionic"]["attack_range"],
            "mp_charge_style": "Very fast passive charge",
            "skill_name": "Telekinetic Redirect",
            "skill_description": "Seizes every projectile already flying through the arena and bends them toward one random enemy target.",
        },
    }
)

POKEDEX_LOCALIZATION = {
    "Knight": {
        "name": "骑士",
        "mp_charge_style": "慢速时间充能",
        "skill_name": "盾誓 / 骑士精神",
        "skill_description": "展开持续 6 秒的蓝色护盾，期间受到的伤害降低 30%，并以每秒 3% 最大生命值的速度恢复；护盾结束后，将把护盾期间承受总伤害的 25% 转化为反噬伤害，并在 3 秒内分次结算。",
    },
    "Mage": {
        "name": "法师",
        "mp_charge_style": "慢速时间充能",
        "skill_name": "秘法回路 / 奥术新星",
        "skill_description": "每次普攻命中或技能命中敌人时，获得 1 层秘法，最多 5 层；每层使法术伤害提升 5%，飞弹速度提升 4%。满层后释放奥术新星时会消耗全部秘法并进入超载状态，额外生成飞弹，并在中心展开持续 2 秒的秘法法阵，每 0.4 秒造成 6 点伤害并附加减速。技能结束后，法师会进入持续掉血状态，总计流失 10% 最大生命值。",
    },
    "Assassin": {
        "name": "刺客",
        "mp_charge_style": "极快时间充能",
        "skill_name": "猎影 / 闪烁背刺",
        "skill_description": "锁定当前生命值最低的敌人并瞬移至其身旁，立刻打出一次 20 点高爆发刺杀；若该次背刺直接击杀目标，则可立即再释放一次。",
    },
    "Berserker": {
        "name": "狂战士",
        "mp_charge_style": "受伤充能",
        "skill_name": "血怒 / 旋风怒斩",
        "skill_description": "每受到 1 点伤害便转化为 1 点充能。进入旋风状态后，每 0.25 秒对周围敌人造成 6 点范围伤害，命中后回复 8 点生命值，并伴随可见的赤红色范围特效。",
    },
    "Sniper": {
        "name": "狙击手",
        "mp_charge_style": "慢速时间充能",
        "skill_name": "远镜校准 / 死亡射线",
        "skill_description": "狙击手离目标越远，普攻伤害越高；每拉开 50 距离，普攻伤害提升 6%，最多提升 30%。静止一段时间后，下一次射击还会额外提升 20% 伤害。主动技能短暂瞄准全场最远的敌人后，发射一条贯穿竞技场的高能法术射线，对路径上的目标造成 55 点伤害。",
    },
    "Necromancer": {
        "name": "死灵法师",
        "mp_charge_style": "中速时间充能",
        "skill_name": "亡者苏生",
        "skill_description": "召唤两只骷髅小兵自动追击敌人，接触后造成伤害并消失。",
        "passive_name": "亡骨共鸣",
        "passive_description": "每次造成伤害都会积攒亡骨层数。每层提升自身移速与骨灵伤害，骨灵退场时还会爆裂，并为死灵法师回复生命。",
    },
    "Paladin": {
        "name": "圣骑士",
        "mp_charge_style": "中速时间充能",
        "skill_name": "神圣治愈",
        "skill_description": "立刻恢复一段生命，并在接下来数秒内以较慢节奏持续回复。",
        "passive_name": "圣辉誓约",
        "passive_description": "每累计回复一定生命值，便会获得圣辉层数。每层提升移动速度、普攻伤害与减伤，神圣治愈命中时还会额外转化为圣盾。",
    },
    "Ninja": {
        "name": "忍者",
        "mp_charge_style": "快速时间充能",
        "skill_name": "影分身",
        "skill_description": "留下一个脆弱分身吸引火力，本体向后高速撤离重新拉开站位。",
        "passive_name": "影行专注",
        "passive_description": "每移动一段距离就获得影行层数。每层提升移动速度与普攻伤害，下一次普攻命中后会消耗全部层数并致盲目标。",
    },
    "Bomber": {
        "name": "爆破手",
        "mp_charge_style": "中速时间充能",
        "skill_name": "地雷轨迹",
        "skill_description": "沿着当前移动方向连续丢下 3 颗地雷，敌人触碰后会引发爆炸。",
        "passive_name": "火药预热",
        "passive_description": "每次造成伤害都会积攒火药预热层数。每层提高移动速度、普攻伤害与地雷爆炸威力，让连战中的火力不断上升。",
    },
    "Vampire": {
        "name": "吸血鬼",
        "mp_charge_style": "每 4 秒爆发充能",
        "skill_name": "鲜血虹吸",
        "skill_description": "锁定最近敌人持续吸血，施法瞬间回复生命，随后在一段时间内继续恢复。",
        "passive_name": "血月饥渴",
        "passive_description": "吸血鬼生命越低，血月越强。流失生命会提升移动速度、攻击速度与普攻伤害，同时让所有治疗效果更强。",
    },
    "Illusionist": {
        "name": "幻术师",
        "mp_charge_style": "快速时间充能",
        "skill_name": "镜像双生",
        "skill_description": "生成 2 个粉色镜像分身，拥有本体 60% 生命值，只能造成 20% 伤害，并会在场上随机乱跑。",
        "passive_name": "镜影共鸣",
        "passive_description": "每造成 18 点伤害获得 1 层镜影，最多 3 层。每层提升 3% 移速、4% 普攻伤害与 3% 攻速；满 3 层时，镜像双生额外生成 1 个分身，并延长分身持续时间。",
    },
    "Behemoth": {
        "name": "巨兽",
        "mp_charge_style": "受伤固定充能",
        "skill_name": "践踏",
        "skill_description": "猛砸地面震晕周围敌人并造成伤害，同时获得可吸收固定伤害的真实护盾。",
        "passive_name": "岩壳重压",
        "passive_description": "每受到 20 点伤害获得 1 层岩壳，最多 5 层。每层降低 3% 受到的伤害、提升 2% 移速与 5% 普攻伤害；满层时，践踏会造成更高伤害并强化真实护盾。",
    },
    "Toxicologist": {
        "name": "毒师",
        "mp_charge_style": "造成伤害充能",
        "skill_name": "剧毒新星",
        "skill_description": "在脚下展开持续 8 秒的毒阵，敌人停留其中会受到真实伤害并不断叠加中毒层数。",
        "passive_name": "腐蚀饱和",
        "passive_description": "每造成 24 点伤害获得 1 层腐蚀，最多 5 层。每层提升 3% 移速、5% 普攻伤害与 3% 攻速；腐蚀越高，剧毒新星的毒阵越大、持续越久，中毒压力也越强。",
    },
    "Frost Mage": {
        "name": "冰霜法师",
        "mp_charge_style": "中速时间充能",
        "skill_name": "绝对零度",
        "skill_description": "发射巨型冰锥冻结目标区域，范围内敌人无法行动，并按已损生命比例承受多段伤害。",
        "passive_name": "冰核蓄势",
        "passive_description": "每造成 22 点伤害获得 1 层冰核，最多 5 层。每层提升 3% 移速、4% 普攻伤害与 4% 攻速；满层时，绝对零度的冻结时间更长，爆发伤害更高。",
    },
    "Pyro": {
        "name": "炎术士",
        "mp_charge_style": "造成伤害充能",
        "skill_name": "龙息怒火",
        "skill_description": "朝当前面向持续喷出扇形火焰，在数秒内每隔很短时间反复灼烧敌人。",
        "passive_name": "余烬压迫",
        "passive_description": "每造成 22 点伤害获得 1 层余烬，最多 5 层。每层提升 3% 移速、5% 普攻伤害与 4% 攻速；龙息怒火会随余烬延长持续时间、提高单段伤害，并在命中时附带短暂寒灼压制。",
    },
    "Time Walker": {
        "name": "时间行者",
        "mp_charge_style": "极快时间充能",
        "skill_name": "时光倒流",
        "skill_description": "清除自身负面状态，并把生命值与位置回溯到 5 秒前记录的快照。",
    },
    "Monk": {
        "name": "武僧",
        "mp_charge_style": "攻击次数充能",
        "skill_name": "气功波",
        "skill_description": "向前打出一道强力冲击波，造成高伤害、击退目标并附带长时间眩晕。",
    },
    "Mech Armor": {
        "name": "机械装甲",
        "mp_charge_style": "受伤固定充能",
        "skill_name": "导弹齐射",
        "skill_description": "向随机敌人群发射多枚追踪导弹，命中后产生范围爆炸伤害。",
    },
    "Druid": {
        "name": "德鲁伊",
        "mp_charge_style": "中速时间充能",
        "skill_name": "巨熊形态",
        "skill_description": "暂时变大并进入巨熊形态，获得额外生命值与治疗，切换为近战并附带眩晕打击。",
    },
    "Electro Trooper": {
        "name": "电磁兵",
        "mp_charge_style": "造成伤害充能",
        "skill_name": "闪电链",
        "skill_description": "释放可在多个敌人间弹射的闪电，每次弹射造成伤害并附加毁灭状态，持续掉血且可斩杀残血目标。",
    },
    "Puppeteer": {
        "name": "傀儡师",
        "mp_charge_style": "慢速时间充能",
        "skill_name": "控制精神",
        "skill_description": "强行控制最近的一名敌人，使其在持续时间内转而攻击场上的其他目标。",
    },
    "Smasher": {
        "name": "重锤手",
        "mp_charge_style": "受伤固定充能",
        "skill_name": "裂地猛击",
        "skill_description": "跃入空中获得短暂无敌，随后砸向目标区域，对范围内敌人造成伤害并附加强减速。",
    },
    "Succubus": {
        "name": "魅魔",
        "mp_charge_style": "造成伤害充能",
        "skill_name": "魅惑之吻",
        "skill_description": "射出爱心弹幕魅惑敌人，令其无法攻击并缓慢走向魅魔，同时魅魔暂时获得五连发低伤普攻。",
    },
    "Gunslinger": {
        "name": "枪神",
        "mp_charge_style": "攻击次数充能",
        "skill_name": "枪林弹雨",
        "skill_description": "短暂停桩，向四周 360 度随机喷射 20 发子弹，形成大范围压制火力。",
    },
    "Shield Guard": {
        "name": "盾卫",
        "mp_charge_style": "受伤固定充能",
        "skill_name": "坚壁清野",
        "skill_description": "在身前竖起巨宽能量盾，持续阻挡敌方飞行弹幕并形成不可穿越的屏障。",
    },
    "Swordmaster": {
        "name": "剑圣",
        "mp_charge_style": "造成伤害高额充能",
        "skill_name": "无敌斩",
        "skill_description": "进入短暂无敌状态，在附近敌人间高速穿梭斩击多次，随后获得数秒攻击速度翻倍增益。",
    },
    "Windrunner": {
        "name": "风行者",
        "mp_charge_style": "按移动距离充能",
        "skill_name": "飓风风暴",
        "skill_description": "再次提高移速，并在身边形成风暴外壳，持续弹开靠近的近战敌人与敌方子弹。",
    },
    "Hexer": {
        "name": "咒术师",
        "mp_charge_style": "中速时间充能",
        "skill_name": "厄运诅咒",
        "skill_description": "标记当前血量最高的敌人，使其在持续时间内移速减半并承受更高伤害。",
    },
    "Chaos Demon": {
        "name": "混沌魔",
        "mp_charge_style": "每 5 秒随机充能 5% 到 50%",
        "skill_name": "混沌法则",
        "skill_description": "触发完全随机效果：回复 25% 最大生命、混沌惩戒(240真实伤害)、180 重击+1.5秒眩晕、全屏震荡 1.5 秒，或是释放一轮 10 发追踪混沌弹幕。",
    },
}

POKEDEX_LOCALIZATION.update(
    {
        "Swordmaster": {
            "name": "剑圣",
            "mp_charge_style": "每次普攻充能 10%",
            "skill_name": "无敌斩",
            "skill_description": "进入短暂无敌状态，在附近敌人之间高速穿梭斩击 5 次，每次造成当前普攻伤害的 120%，随后获得 5 秒的攻击速度提升。",
        },
        "Bounty Hunter": {
            "name": "赏金猎人",
            "mp_charge_style": "每次造成伤害充能 10%",
            "skill_name": "终极悬赏",
            "skill_description": "随机标记一名敌人为悬赏目标。攻击该目标会造成额外伤害并获得赏金币，每枚赏金币都会永久提升基础攻击伤害。",
        },
        "Geomancer": {
            "name": "地术师",
            "mp_charge_style": "受到伤害时充能 10%",
            "skill_name": "岩刺突袭",
            "skill_description": "在 3 名随机敌人脚下升起岩刺，造成 50 点伤害并将其定身 5 秒。",
        },
        "Bard": {
            "name": "吟游诗人",
            "mp_charge_style": "快速时间充能",
            "skill_name": "狂欢战歌",
            "skill_description": "吟唱战歌，强化 150 范围内所有友军，使其移动速度和攻击速度提升 50%，持续 6 秒（释放期间自身每秒损失最大生命值的 1%）。普通攻击有 25% 概率使目标减速 20% 持续 1 秒。",
        },
        "Shaman": {
            "name": "萨满",
            "mp_charge_style": "中速时间充能",
            "skill_name": "闪电图腾",
            "skill_description": "在脚下放置一个红色图腾。图腾拥有 30 点生命，会持续存在，并每秒向 60 范围内最远的敌人释放闪电。",
        },
        "Gladiator": {
            "name": "角斗士",
            "mp_charge_style": "受到伤害时充能 5%",
            "skill_name": "致命决斗",
            "skill_description": "将最近的敌人拉到身前并定身 3 秒，使其攻击速度翻倍，同时自身获得减伤和大幅攻击速度提升。",
        },
        "Warlock": {
            "name": "术士",
            "mp_charge_style": "每 3 秒牺牲生命值，获得 40% 法力",
            "skill_name": "灵魂虹吸",
            "skill_description": "消耗 10 点当前生命，向前方发射无限距离的宽广虚空波，造成 80 点伤害；每命中一名敌人，按损失生命值的 20% 恢复生命。",
        },
        "Tinkerer": {
            "name": "工匠",
            "mp_charge_style": "快速时间充能",
            "skill_name": "武器超频",
            "skill_description": "随机装备一把武器并使其超频 3 秒，攻击间隔减半且弹药无限，效果结束后武器消失。",
        },
        "Valkyrie": {
            "name": "女武神",
            "mp_charge_style": "受到伤害时充能",
            "skill_name": "天降重击",
            "skill_description": "升空并获得无敌与 500 点真实护盾，随后砸向敌人最密集的区域，造成范围伤害并施加短暂眩晕。落地前会重新追踪最密集的敌人，落地时掀起金色光柱冲击。",
        },
        "Dark Knight": {
            "name": "黑暗骑士",
            "mp_charge_style": "受到伤害时充能 8%",
            "skill_name": "复仇荆棘",
            "skill_description": "进入持续 5 秒的荆棘状态，将受到的 50% 伤害反弹给攻击者。",
        },
        "Psionic": {
            "name": "灵能者",
            "mp_charge_style": "极快时间充能",
            "skill_name": "念力偏转",
            "skill_description": "控制场上正在飞行的所有敌方投射物，使它们转向一名随机敌人。",
        },
    }
)

DESIGN_CHARACTER_DOC = Path(__file__).resolve().parent / "sheding" / "charactor.md"
DESIGN_JOB_DEFS, DESIGN_CHARACTER_DATA, DESIGN_POKEDEX_LOCALIZATION, DESIGN_ROLE_METADATA = load_design_roles(
    DESIGN_CHARACTER_DOC
)
JOB_DEFS.update(DESIGN_JOB_DEFS)
CHARACTER_DATA.update(DESIGN_CHARACTER_DATA)
POKEDEX_LOCALIZATION.update(DESIGN_POKEDEX_LOCALIZATION)
JOB_RESISTANCE_PROFILES.update(
    {
        job_name: {
            "physical_resistance": config.get("physical_resistance", 1.0),
            "spell_resistance": config.get("spell_resistance", 1.0),
        }
        for job_name, config in DESIGN_JOB_DEFS.items()
    }
)

HERO_JOB_NAME = "DesignRole98_hero"
SPELL_BASIC_JOBS.update(
    {
        job_name
        for job_name, metadata in DESIGN_ROLE_METADATA.items()
        if metadata.get("basic_damage_kind") == DAMAGE_KIND_SPELL
    }
)
TRUE_BASIC_JOBS.update(
    {
        job_name
        for job_name, metadata in DESIGN_ROLE_METADATA.items()
        if metadata.get("basic_damage_kind") == "true"
    }
)

BLOODWRAITH_JOB_NAME = "Bloodwraith"
JOB_DEFS[BLOODWRAITH_JOB_NAME] = {
    "shape": "slim_diamond",
    "color": (130, 18, 28),
    "max_hp": 1000.0,
    "mp_mode": "damage_taken_scaled",
    "mp_rate": 1.5,
    "attack_type": "melee",
    "attack_damage": 12.0,
    "attack_range": 46.0,
    "attack_interval": 0.68,
    "projectile_speed": 285.0,
    "move_speed": 120.0,
    "skill_id": "bloodwraith_blood_pool",
    "physical_resistance": 0.8,
    "spell_resistance": 0.8,
    "use_design_attack_speed": True,
    "use_design_attack_damage": True,
}
CHARACTER_DATA[BLOODWRAITH_JOB_NAME] = {
    "name": "Bloodwraith",
    "shape": "slim_diamond",
    "color": (130, 18, 28),
    "max_hp": 1000.0,
    "move_speed": 120.0,
    "attack_type": "melee",
    "attack_range": 46.0,
    "physical_resistance": 0.8,
    "spell_resistance": 0.8,
    "mp_charge_style": "Gain 15% MP per 10 damage taken",
    "skill_name": "Undying Grudge",
    "skill_description": "Survive a lethal hit once, cleanse all negative effects, fully restore HP, and enter a rage state with doubled move speed, tripled attack speed, and quadrupled basic attack damage while losing 8% max HP per second. The active skill grants a 25% max HP shield for 4 seconds; while it lasts, basic attacks heal for 60% of the damage dealt.",
}
POKEDEX_LOCALIZATION[BLOODWRAITH_JOB_NAME] = {
    "name": "噬血亡魂",
    "mp_charge_style": "每受到 10 点伤害充能 15%",
    "skill_name": "不屈怨念 / 血池庇护",
    "skill_description": "受到致死伤害时不会立即阵亡，会清除自身所有负面效果并恢复 100% 最大生命值。随后进入狂暴状态，移速提升 100%、攻击速度提升 200%、普攻伤害提升 300%，但每秒固定流失 8% 最大生命值。主动技能会获得等同于最大生命值 25% 的护盾，持续 4 秒；护盾存在期间，普攻造成的伤害会转化为 60% 的生命值回复。",
}
DESIGN_ROLE_METADATA[BLOODWRAITH_JOB_NAME] = {
    "role_num": 40,
    "role_cn_name": "噬血亡魂",
    "role_en_name": "Bloodwraith",
    "visual_text": "破裂血剑 / 暗红与漆黑",
    "attack_text": "狂暴斩击，物理近战，伤害 12",
    "mp_text": "受到伤害时充能 15%",
    "skill_name": "不屈怨念 / 血池庇护",
    "skill_description": "受到致死伤害时不会立即阵亡，会清除自身所有负面效果并恢复 100% 最大生命值。随后进入狂暴状态，移速提升 100%、攻击速度提升 200%、普攻伤害提升 300%，但每秒固定流失 8% 最大生命值。主动技能会获得等同于最大生命值 25% 的护盾，持续 4 秒；护盾存在期间，普攻造成的伤害会转化为 60% 的生命值回复。",
    "basic_damage_kind": "physical",
    "skill_token": "bloodwraith_blood_pool",
}
JOB_RESISTANCE_PROFILES[BLOODWRAITH_JOB_NAME] = {
    "physical_resistance": 0.8,
    "spell_resistance": 0.8,
}

PHANTOM_LANCER_JOB_NAME = "DesignRole91_phantom_lancer"
JOB_DEFS[PHANTOM_LANCER_JOB_NAME] = {
    "shape": "slim_diamond",
    "color": (86, 224, 232),
    "max_hp": 900.0,
    "mp_mode": "distance_scaled",
    "mp_rate": 1.0,
    "attack_type": "melee",
    "attack_damage": 16.0,
    "attack_range": 46.0,
    "attack_interval": 0.64,
    "projectile_speed": 285.0,
    "move_speed": 160.0,
    "skill_id": "phantom_lancer_throw",
    "physical_resistance": 0.7,
    "spell_resistance": 0.8,
    "use_design_attack_speed": True,
    "use_design_attack_damage": True,
}
CHARACTER_DATA[PHANTOM_LANCER_JOB_NAME] = {
    "name": "Phantom Lancer",
    "shape": "slim_diamond",
    "color": (86, 224, 232),
    "max_hp": 900.0,
    "move_speed": 160.0,
    "attack_type": "melee",
    "attack_range": 46.0,
    "physical_resistance": 0.7,
    "spell_resistance": 0.8,
    "mp_charge_style": "Gain 20% MP per 20 distance moved",
    "skill_name": "Wind-Touch / Lance Throw",
    "skill_description": "Attack power scales with movement speed. Picking up Cold Spear turns the next basic attack into a short dash thrust for 200% damage and 40 HP healing, and grants 30% move speed for 5 seconds. The active skill throws Cold Spear behind the current target, dealing 15 damage and leaving it on the ground for 5 seconds.",
}
POKEDEX_LOCALIZATION[PHANTOM_LANCER_JOB_NAME] = {
    "name": "绝影枪客",
    "mp_charge_style": "每移动 20 距离充能 20%",
    "skill_name": "追风之触 / 掷枪入阵",
    "skill_description": "自身移速越高，普攻伤害越高。拾取【冷锋枪】后，下一次普攻会变为短距离突刺，造成 200% 伤害并回复 40 点生命值，同时自身 5 秒内移速提升 30%。主动技能会向当前目标身后掷出【冷锋枪】，命中造成 15 点伤害并插在地面持续 5 秒。",
}
DESIGN_ROLE_METADATA[PHANTOM_LANCER_JOB_NAME] = {
    "role_num": 91,
    "role_cn_name": "绝影枪客",
    "role_en_name": "Phantom Lancer",
    "visual_text": "长锥形 / 青蓝色",
    "attack_text": "长枪挥击，物理近战，伤害 16",
    "mp_text": "移动距离充能",
    "skill_name": "追风之触 / 掷枪入阵",
    "skill_description": "自身移速越高，普攻伤害越高。拾取【冷锋枪】后，下一次普攻会变为短距离突刺，造成 200% 伤害并回复 40 点生命值，同时自身 5 秒内移速提升 30%。主动技能会向当前目标身后掷出【冷锋枪】，命中造成 15 点伤害并插在地面持续 5 秒。",
    "basic_damage_kind": "physical",
    "skill_token": "phantom_lancer_throw",
}
JOB_RESISTANCE_PROFILES[PHANTOM_LANCER_JOB_NAME] = {
    "physical_resistance": 0.7,
    "spell_resistance": 0.8,
}

TWIN_MIRROR_JOB_NAME = "DesignRole93_twin_mirror"
TWIN_MIRROR_FORM_MAX_HP = 650.0
TWIN_MIRROR_UNLOCK_RATIO = 0.4
TWIN_MIRROR_WHITE_COLOR = (244, 244, 244)
TWIN_MIRROR_BLACK_COLOR = (128, 128, 132)
TWIN_MIRROR_WHITE_SHIELD = 15.0
TWIN_MIRROR_WHITE_HEAL = 125.0
TWIN_MIRROR_WHITE_KNOCKBACK = 50.0
TWIN_MIRROR_BLACK_ATTACK_BONUS = 5.0
TWIN_MIRROR_BLACK_AOE_DAMAGE = 55.0
TWIN_MIRROR_BLACK_PULL_RADIUS = 30.0
TWIN_MIRROR_BLACK_PULL_STRENGTH = 78.0
TWIN_MIRROR_BLACK_SLOW = 0.5
TWIN_MIRROR_BLACK_SLOW_DURATION = 3.0
TWIN_MIRROR_BLACK_DURATION = 3.0

SOUL_ARBITER_JOB_NAME = "DesignRole92_soul_arbiter"
JOB_DEFS[SOUL_ARBITER_JOB_NAME] = {
    "shape": "crescent",
    "color": (118, 30, 46),
    "max_hp": 1250.0,
    "mp_mode": "damage_dealt_scaled",
    "mp_rate": 0.5,
    "attack_type": "melee",
    "attack_damage": 10.0,
    "attack_range": 72.0,
    "attack_interval": 0.56,
    "projectile_speed": 285.0,
    "move_speed": 110.0,
    "skill_id": "soul_arbiter_bond",
    "physical_resistance": 0.5,
    "spell_resistance": 1.2,
    "use_design_attack_speed": True,
    "use_design_attack_damage": True,
}
CHARACTER_DATA[SOUL_ARBITER_JOB_NAME] = {
    "name": "Soul Arbiter",
    "shape": "crescent",
    "color": (118, 30, 46),
    "max_hp": 1250.0,
    "move_speed": 110.0,
    "attack_type": "melee",
    "attack_range": 72.0,
    "physical_resistance": 0.5,
    "spell_resistance": 1.2,
    "mp_charge_style": "Gain 5% MP per 10 damage dealt",
    "skill_name": "Soul Bind / Divine Patrol",
    "skill_description": "Basic attacks create a 3-second purple soul chain instead of dealing instant damage. Every 0.5 seconds, the chain deals 10 damage; 150% of damage dealt becomes a shield, and the chain breaks if the target leaves range. If the target falls below 10% HP during the chain, it is executed through shields and turns into pink dust. The active skill deals 25 spell damage to all enemies in 60 range and enters an 8-second patrol state, increasing move speed by 30% and allowing up to 3 chained enemies. Kills during patrol summon a 10-second spirit of the fallen foe and grant 10 max HP.",
}
POKEDEX_LOCALIZATION[SOUL_ARBITER_JOB_NAME] = {
    "name": "镇灵判官",
    "mp_charge_style": "每造成 10 点伤害充能 5%",
    "skill_name": "司命之缚 / 神巫巡狩",
    "skill_description": "普攻不再是瞬间伤害，而是与目标建立持续 3 秒的紫色魂链，超出距离会拉断。期间每 0.5 秒造成 10 点伤害，并将造成伤害的 150% 转化为护盾；若目标生命值降至最大生命值 10% 以下，将直接无视护盾斩杀，目标死亡时化为粉色粉尘。主动技能对 60 范围内所有敌人造成 25 点法术伤害，并进入持续 8 秒的巡狩状态，移速提升 30%，魂链最多可同时连接 3 个敌人；巡狩期间击杀敌人会召唤对应灵魄协助作战，并使自身最大生命值提升 10。",
}
DESIGN_ROLE_METADATA[SOUL_ARBITER_JOB_NAME] = {
    "role_num": 92,
    "role_cn_name": "镇灵判官",
    "role_en_name": "Soul Arbiter",
    "visual_text": "月牙形 / 幽冥暗红",
    "attack_text": "幽冥牵引，物理近战，伤害 10",
    "mp_text": "造成伤害充能",
    "skill_name": "司命之缚 / 神巫巡狩",
    "skill_description": "普攻不再是瞬间伤害，而是与目标建立持续 3 秒的紫色魂链，超出距离会拉断。期间每 0.5 秒造成 10 点伤害，并将造成伤害的 150% 转化为护盾；若目标生命值降至最大生命值 10% 以下，将直接无视护盾斩杀，目标死亡时化为粉色粉尘。主动技能对 60 范围内所有敌人造成 25 点法术伤害，并进入持续 8 秒的巡狩状态，移速提升 30%，魂链最多可同时连接 3 个敌人；巡狩期间击杀敌人会召唤对应灵魄协助作战，并使自身最大生命值提升 10。",
    "basic_damage_kind": "physical",
    "skill_token": "soul_arbiter_bond",
}
JOB_RESISTANCE_PROFILES[SOUL_ARBITER_JOB_NAME] = {
    "physical_resistance": 0.5,
    "spell_resistance": 1.2,
}
JOB_DEFS[SUNFIRE_JOB_NAME] = {
    "shape": "slim_diamond",
    "color": SUNFIRE_WATER_COLOR,
    "max_hp": 1200.0,
    "mp_mode": "passive",
    "mp_rate": 0.0,
    "attack_type": "melee",
    "attack_damage": 10.0,
    "attack_range": 58.0,
    "attack_interval": 0.66,
    "projectile_speed": 285.0,
    "move_speed": 110.0,
    "skill_id": "sunfire_kagura",
    "physical_resistance": 0.8,
    "spell_resistance": 0.7,
    "use_design_attack_speed": True,
    "use_design_attack_damage": True,
}
CHARACTER_DATA[SUNFIRE_JOB_NAME] = {
    "name": "Sunfire Blademaster",
    "shape": "slim_diamond",
    "color": SUNFIRE_WATER_COLOR,
    "max_hp": 1200.0,
    "move_speed": 110.0,
    "attack_type": "melee",
    "attack_range": 58.0,
    "physical_resistance": 0.8,
    "spell_resistance": 0.7,
    "mp_charge_style": "Gain 10% MP per attack and 5% per hit taken",
    "skill_name": "Water-Form Flow / Sunfire Kagura",
    "skill_description": "Five-step water combo with 4% damage reduction per hit, up to 40%. The active skill clears control effects and enters Fire Form for 8 seconds, keeping the combo flow while adding true damage and +30% move speed.",
}
POKEDEX_LOCALIZATION[SUNFIRE_JOB_NAME] = {
    "name": "薪火剑士",
    "mp_charge_style": "每次攻击充能10%，受击充能5%",
    "skill_name": "生生流转 / 薪火神乐",
    "skill_description": "常态下以五段水之型循环作战；每命中一次敌人，获得4%伤害减免，最多10层。主动释放时清除自身控制，进入8秒火之形态并保持原连招节奏，所有招式追加真实伤害，移速提升30%。",
}
DESIGN_ROLE_METADATA[SUNFIRE_JOB_NAME] = {
    "role_num": 94,
    "role_cn_name": "薪火剑士",
    "role_en_name": "Sunfire Blademaster",
    "display_name": "Sunfire Blademaster",
    "visual_text": "刃形状 / 澄澈水蓝",
    "attack_text": "五段连招 / 物理近战，基础伤害 10",
    "mp_text": "造成伤害与受到伤害",
    "skill_name": "生生流转 / 薪火神乐",
    "skill_description": "常态为五段水之型连招：一式扇斩、二式突进、水车、三式三连穿梭、四式重斩减速、五式环斩回血。怒气满时释放薪火神乐，清除控制并进入8秒火之形态，保留连招节奏且所有招式追加真实伤害与移速加成。",
    "basic_damage_kind": "physical",
    "skill_token": "sunfire_kagura",
}
JOB_RESISTANCE_PROFILES[SUNFIRE_JOB_NAME] = {
    "physical_resistance": 0.8,
    "spell_resistance": 0.7,
}

JOB_DEFS[WINDSTORM_FOX_JOB_NAME] = {
    "shape": "fan",
    "color": WINDSTORM_FOX_FAN_COLOR,
    "max_hp": 700.0,
    "mp_mode": "attack_count",
    "mp_rate": 20.0,
    "attack_type": "ranged",
    "attack_damage": 10.0,
    "attack_range": 240.0,
    "attack_interval": 0.72,
    "projectile_speed": 330.0,
    "move_speed": 115.0,
    "skill_id": "windstorm_blade_roll",
    "physical_resistance": 0.8,
    "spell_resistance": 0.6,
    "use_design_attack_speed": True,
    "use_design_attack_damage": True,
}
CHARACTER_DATA[WINDSTORM_FOX_JOB_NAME] = {
    "name": "Windstorm Fox",
    "shape": "fan",
    "color": WINDSTORM_FOX_FAN_COLOR,
    "max_hp": 700.0,
    "move_speed": 115.0,
    "attack_type": "ranged",
    "attack_range": 240.0,
    "physical_resistance": 0.8,
    "spell_resistance": 0.6,
    "mp_charge_style": "Gain 20% MP per attack",
    "skill_name": "Wind Qi Gathering / Windstorm Blade Roll",
    "skill_description": "Each basic attack or skill hit grants 1 Wind Qi stack, up to 5. Each stack gives 3% move speed and 6% attack speed. At 5 stacks, basic attacks fire two wind blades at 60% damage each and can dash away from the target. If no basic attack is used for 5 seconds, Wind Qi starts fading by 1 stack every 3 seconds. The active skill fires random wind blades: R 50% for 6 blades plus a global 10-damage blade, SR 35% for 10 blades plus +0.5 physical resistance for 3 seconds, SSR 15% for 18 blades with 30% lifesteal and 40% ricochet.",
}
POKEDEX_LOCALIZATION[WINDSTORM_FOX_JOB_NAME] = {
    "name": "狂风灵狐",
    "mp_charge_style": "每次普攻充能20%",
    "skill_name": "风气聚灵 / 狂风刃卷",
    "skill_description": "每次普攻或技能命中敌人都会获得1层风气，最高5层。每层提供3%移速与6%攻速。满层后普攻变为两发风刃，每发造成60%普攻伤害，并有20%概率向后快速位移。若5秒未普攻，则每3秒失去1层风气。主动技能会随机向敌人发射风刃：R级50%发射6道并追加1道全场风刃；SR级35%发射10道并使目标物理抗性+0.5持续3秒；SSR级15%发射18道，附带30%物理吸血并有40%概率弹射最近敌人。",
}
DESIGN_ROLE_METADATA[WINDSTORM_FOX_JOB_NAME] = {
    "role_num": 95,
    "role_cn_name": "狂风灵狐",
    "role_en_name": "Windstorm Fox",
    "display_name": "Windstorm Fox",
    "visual_text": "扇形 / 灰色",
    "attack_text": "风刃，远程物理，基础伤害 10",
    "mp_text": "每次普攻充能20%",
    "skill_name": "风气聚灵 / 狂风刃卷",
    "skill_description": "每次普攻或技能命中敌人，获得1层风气，最高5层。每层提供3%移速和6%攻速。满5层后普攻变为双风刃，每发60%伤害，并有20%概率向后快速移动。5秒未普攻后，每3秒失去1层风气。主动技能按R/SR/SSR概率释放随机风刃，分别附带全场追击、物抗提升、吸血和弹射效果。",
    "basic_damage_kind": "physical",
    "skill_token": "windstorm_blade_roll",
}
JOB_RESISTANCE_PROFILES[WINDSTORM_FOX_JOB_NAME] = {
    "physical_resistance": 0.8,
    "spell_resistance": 0.6,
}

JOB_DEFS[SEA_SAGE_JOB_NAME] = {
    "shape": "hexagon",
    "color": SEA_SAGE_BLUE_COLOR,
    "max_hp": 1500.0,
    "mp_mode": "attack_count",
    "mp_rate": 5.0,
    "attack_type": "ranged",
    "attack_damage": 9.0,
    "attack_range": 260.0,
    "attack_interval": 0.74,
    "projectile_speed": 330.0,
    "move_speed": 95.0,
    "skill_id": "tide_flood",
    "physical_resistance": 0.8,
    "spell_resistance": 0.7,
    "use_design_attack_speed": True,
    "use_design_attack_damage": True,
    "basic_damage_kind": DAMAGE_KIND_SPELL,
}
CHARACTER_DATA[SEA_SAGE_JOB_NAME] = {
    "name": "Sea Sage",
    "shape": "hexagon",
    "color": SEA_SAGE_BLUE_COLOR,
    "max_hp": 1500.0,
    "move_speed": 95.0,
    "attack_type": "ranged",
    "attack_range": 260.0,
    "physical_resistance": 0.8,
    "spell_resistance": 0.7,
    "mp_charge_style": "Gain 5% MP per attack and 3% per hit taken",
    "skill_name": "Oath of Tides / Tide Flood",
    "skill_description": "Basic attacks fire water bullets. Skill casts or every 80 damage taken spawn a Water Fish. Every 6 seconds, one Water Fish is consumed to heal 30 HP, grant a 15 HP shield for 3 seconds, and add a 5% damage-reduction stack for 8 seconds, up to 4 stacks. The active skill unleashes 3 rectangular tidal waves one after another; the last wave returns to the caster, heals 30 HP on contact, and consumes all Water Fish. Wave stun durations are reduced by 50%.",
}
POKEDEX_LOCALIZATION[SEA_SAGE_JOB_NAME] = {
    "name": "沧海水翁",
    "mp_charge_style": "每次攻击充能5%，受击充能3%",
    "skill_name": "誓约水祭 / 惊涛骇浪",
    "skill_description": "水流弹普攻。每次释放技能或累计受到80点伤害，会在自身周围生成1朵水灵鱼。每6秒自动拾取1朵水灵鱼，恢复30点生命值，获得15点护盾（持续3秒），并叠加1层5%减伤（持续8秒），最多4层。主动技能朝目标方向依次释放3重矩形巨浪，最后一重会回浪，命中自身后消失并回复30点生命值，同时拾取场上全部水灵鱼；巨浪晕眩时长减少50%。",
}
DESIGN_ROLE_METADATA[SEA_SAGE_JOB_NAME] = {
    "role_num": 96,
    "role_cn_name": "沧海水翁",
    "role_en_name": "Sea Sage",
    "display_name": "Sea Sage",
    "visual_text": "六边形 / 深蓝色",
    "attack_text": "水流弹，远程法伤，基础伤害 9",
    "mp_text": "攻击充能5%，受击充能3%",
    "skill_name": "誓约水祭 / 惊涛骇浪",
    "skill_description": "普攻为水流弹。每次释放技能或累计受到80点伤害时，生成1朵水灵鱼。每6秒自动拾取1朵水灵鱼，恢复30点生命值、获得15点护盾，并叠加1层5%减伤，最多4层。主动技能依次释放3重矩形巨浪，最后一重回浪，命中自身后消失并回血，同时拾取场上全部水灵鱼；巨浪晕眩时长减少50%。",
    "basic_damage_kind": "spell",
    "skill_token": "tide_flood",
}
JOB_RESISTANCE_PROFILES[SEA_SAGE_JOB_NAME] = {
    "physical_resistance": 0.8,
    "spell_resistance": 0.7,
}

EQUILIBRIUM_JOB_NAME = "DesignRole97_equilibrium_arbiter"
JOB_DEFS[EQUILIBRIUM_JOB_NAME] = {
    "shape": "hourglass",
    "color": EQUILIBRIUM_GOLD_COLOR,
    "max_hp": 1200.0,
    "mp_mode": "attack_count",
    "mp_rate": 8.0,
    "attack_type": "melee",
    "attack_damage": 23.0,
    "attack_range": 54.0,
    "attack_interval": 0.73,
    "projectile_speed": 285.0,
    "move_speed": 100.0,
    "skill_id": "absolute_equality",
    "physical_resistance": 1.0,
    "spell_resistance": 1.0,
    "use_design_attack_speed": True,
    "use_design_attack_damage": True,
    "basic_damage_kind": DAMAGE_KIND_PHYSICAL,
}
CHARACTER_DATA[EQUILIBRIUM_JOB_NAME] = {
    "name": "Equilibrium Arbiter",
    "shape": "hourglass",
    "color": EQUILIBRIUM_GOLD_COLOR,
    "max_hp": 1200.0,
    "move_speed": 100.0,
    "attack_type": "melee",
    "attack_range": 54.0,
    "physical_resistance": 1.0,
    "spell_resistance": 1.0,
    "mp_charge_style": "Gain 8% MP per attack",
    "skill_name": "Threshold of Doom / Absolute Equality",
    "skill_description": "Whenever an enemy unit first drops below 75%, 50%, or 25% HP, a six-sided fate roll begins. Rolls of 1-3 deal 70 true damage, or 100 true damage at the 25% threshold; failed judgments leave a 4-second equilibrium mark that guarantees the next threshold trigger. If the judgment kills, all units on the field take 40 spell damage. The active skill picks the highest-HP and lowest-HP living units, equalizes their current HP to the average, and lowers both physical and spell resistance by 0.25 for 5 seconds.",
}
POKEDEX_LOCALIZATION[EQUILIBRIUM_JOB_NAME] = {
    "name": "\u5747\u8861\u5224\u5b98",
    "mp_charge_style": "Gain 8% MP per attack",
    "skill_name": "\u5384\u8fd0\u9608\u9650 / \u7edd\u5bf9\u5747\u7b49",
    "skill_description": "Random enemy units crossing 75%, 50%, or 25% HP face a d6 judgment. Rolls 1-3 deal 70 true damage, or 100 true damage at the 25% threshold; failed judgments leave a 4-second equilibrium mark that guarantees the next threshold trigger. A kill deals 40 spell damage to all units. Active: pick the highest-HP and lowest-HP living units, average their current HP, and reduce both resistances by 0.25 for 5 seconds.",
}
DESIGN_ROLE_METADATA[EQUILIBRIUM_JOB_NAME] = {
    "role_num": 97,
    "role_cn_name": "\u5747\u8861\u5224\u5b98",
    "role_en_name": "Equilibrium Arbiter",
    "display_name": "Equilibrium Arbiter",
    "visual_text": "Scale / Gold",
    "attack_text": "Mixed melee strike, 23 damage",
    "mp_text": "Gain 8% MP per attack",
    "skill_name": "Threshold of Doom / Absolute Equality",
    "skill_description": "Random enemy units crossing 75%, 50%, or 25% HP face a d6 judgment. Rolls 1-3 deal 70 true damage, or 100 true damage at the 25% threshold; failed judgments leave a 4-second equilibrium mark that guarantees the next threshold trigger. A kill deals 40 spell damage to all units. Active: pick the highest-HP and lowest-HP living units, average their current HP, and reduce both resistances by 0.25 for 5 seconds.",
    "basic_damage_kind": "physical",
    "skill_token": "absolute_equality",
}
JOB_RESISTANCE_PROFILES[EQUILIBRIUM_JOB_NAME] = {
    "physical_resistance": 1.0,
    "spell_resistance": 1.0,
}

EFFECT_CATEGORY_LOCALIZATION = {
    "positive": "正面",
    "negative": "负面",
    "neutral": "中性",
}

EFFECT_CATEGORY_COLORS = {
    "positive": (78, 172, 106),
    "negative": (214, 92, 92),
    "neutral": (96, 142, 212),
}

EFFECT_DATA = {
    "guard": {
        "name": "守护",
        "category": "positive",
        "tags": ["减伤", "回血", "持续"],
        "sources": ["骑士"],
        "description": "守护期间减少受到的非真实伤害，并持续回复生命值。结束时会根据记录的承伤触发反噬。",
    },
    "shield": {
        "name": "护盾姿态",
        "category": "positive",
        "tags": ["防御", "姿态"],
        "sources": ["骑士"],
        "description": "角色进入护盾保护状态，会显示额外护盾特效，常与守护联动出现。",
    },
    "true_shield": {
        "name": "真实护盾",
        "category": "positive",
        "tags": ["护盾", "吸收", "防御"],
        "sources": ["巨兽", "女武神"],
        "description": "先于生命值承受伤害的额外护盾值，可直接吸收同等数值的来袭伤害。",
    },
    "regeneration": {
        "name": "持续回复",
        "category": "positive",
        "tags": ["治疗", "续航", "持续"],
        "sources": ["圣骑士", "吸血鬼"],
        "description": "在一段时间内持续恢复生命值，适合拖长战斗并抵消持续伤害。",
    },
    "paladin_blessing": {
        "name": "圣光祝福",
        "category": "positive",
        "tags": ["治疗", "增益", "范围支援"],
        "sources": ["圣骑士"],
        "description": "释放治疗后进入的增益状态，会按节奏持续为自己提供额外恢复效果。",
    },
    "berserker_spin": {
        "name": "旋风",
        "category": "positive",
        "tags": ["范围伤害", "加速", "近战"],
        "sources": ["狂战士"],
        "description": "进入高速旋风状态，周期性对周围敌人造成伤害，同时提升自身移动效率。",
    },
    "ninja_dash": {
        "name": "影遁疾行",
        "category": "positive",
        "tags": ["位移", "加速", "脱战"],
        "sources": ["忍者"],
        "description": "释放分身后短时间大幅提速，迅速拉开身位或切换站位。",
    },
    "druid_form": {
        "name": "熊形态",
        "category": "positive",
        "tags": ["变身", "强化", "近战"],
        "sources": ["德鲁伊"],
        "description": "暂时切换为熊形态，获得额外生命、立即治疗并改用近战攻击，命中还会附带眩晕。",
    },
    "swordmaster_invuln": {
        "name": "无敌",
        "category": "positive",
        "tags": ["无敌", "突袭"],
        "sources": ["剑圣"],
        "description": "期间不会受到伤害，适合穿梭战场或躲避高爆发技能。",
    },
    "swordmaster_haste": {
        "name": "剑势加速",
        "category": "positive",
        "tags": ["攻速", "强化"],
        "sources": ["剑圣"],
        "description": "显著缩短攻击间隔，使剑圣在无敌斩后进入高速连击节奏。",
    },
    "windrunner_storm": {
        "name": "风暴外壳",
        "category": "positive",
        "tags": ["加速", "弹开", "防御"],
        "sources": ["风行者"],
        "description": "持续提升移动速度，并将靠近的近战敌人与飞行弹幕推离自身。",
    },
    "gladiator_duel": {
        "name": "决斗斗志",
        "category": "positive",
        "tags": ["减伤", "攻速", "单挑"],
        "sources": ["角斗士"],
        "description": "角斗士进入决斗优势状态，获得减伤与攻击速度提升，专注压制被拉近的目标。",
    },
    "overclock": {
        "name": "武器超频",
        "category": "positive",
        "tags": ["武器", "攻速", "无限弹药"],
        "sources": ["工匠"],
        "description": "随机装备的武器进入超频状态，射速更快并且在持续时间内不消耗弹药。",
    },
    "dark_reflect": {
        "name": "荆棘反伤",
        "category": "positive",
        "tags": ["反伤", "防御"],
        "sources": ["黑暗骑士"],
        "description": "持续期间会把承受的一部分非真实伤害反弹给攻击者。",
    },
    "succubus_barrage": {
        "name": "魅惑连射",
        "category": "positive",
        "tags": ["连射", "远程", "压制"],
        "sources": ["魅魔"],
        "description": "魅惑命中后短时间内的普攻会变成散射多段弹幕，形成持续压制火力。",
    },
    "vampire_channel": {
        "name": "吸血引导",
        "category": "positive",
        "tags": ["引导", "吸血", "续航"],
        "sources": ["吸血鬼"],
        "description": "锁定目标进行持续吸血，同时为自己提供后续生命回复。",
    },
    "vampire_regen": {
        "name": "鲜血回春",
        "category": "positive",
        "tags": ["治疗", "续航", "持续"],
        "sources": ["吸血鬼"],
        "description": "吸血完成后保留一段持续回复效果，帮助吸血鬼在拉扯战中稳定回满生命。",
    },
    "summon": {
        "name": "召唤物",
        "category": "neutral",
        "tags": ["召唤", "临时单位", "追击"],
        "sources": ["死灵法师"],
        "description": "生成会自动追击敌人的临时单位，用于补充战场人数和扰乱目标选择。",
    },
    "minefield": {
        "name": "地雷",
        "category": "neutral",
        "tags": ["陷阱", "范围伤害", "布置"],
        "sources": ["爆破手"],
        "description": "提前布置在地面的爆炸陷阱，敌人靠近触发后会造成范围伤害。",
    },
    "poison_field": {
        "name": "毒雾领域",
        "category": "negative",
        "tags": ["区域", "持续伤害", "中毒"],
        "sources": ["毒师"],
        "description": "持续存在的地面毒区，站在其中的敌人会不断受伤并积累中毒层数。",
    },
    "frost_comet": {
        "name": "冰霜彗星",
        "category": "negative",
        "tags": ["区域", "冻结", "爆发"],
        "sources": ["冰霜法师"],
        "description": "大型冰霜打击效果，会冻结区域内目标并追加多段伤害。",
    },
    "shield_wall": {
        "name": "能量壁垒",
        "category": "neutral",
        "tags": ["地形", "阻挡", "弹道拦截"],
        "sources": ["盾卫"],
        "description": "在战场上生成可阻挡角色移动和投射物的能量墙，改变交战路线。",
    },
    "totem": {
        "name": "闪电图腾",
        "category": "neutral",
        "tags": ["召唤", "炮台", "持续攻击"],
        "sources": ["萨满"],
        "description": "留在原地的自动攻击单位，会周期性对附近目标释放闪电。",
    },
    "weapon_equipped": {
        "name": "持有武器",
        "category": "neutral",
        "tags": ["武器", "掉落", "战术"],
        "sources": ["全职业"],
        "description": "捡起武器球后会暂时切换为对应武器攻击方式，直到弹药耗尽或效果结束。",
    },
    "sniper_charge": {
        "name": "狙击蓄力",
        "category": "neutral",
        "tags": ["蓄力", "瞄准"],
        "sources": ["狙击手"],
        "description": "激光发射前的短暂瞄准阶段，结束后会立即打出高伤害贯穿射线。",
    },
    "time_snapshot": {
        "name": "时光快照",
        "category": "neutral",
        "tags": ["时间", "记录", "回溯"],
        "sources": ["时行者"],
        "description": "周期性记录位置与生命值，供时光回溯技能恢复到较早的战斗状态。",
    },
    "clone": {
        "name": "分身",
        "category": "neutral",
        "tags": ["召唤", "分身", "限时"],
        "sources": ["幻术师"],
        "description": "制造低伤害、低生命的临时镜像单位，用于扰乱战场和分担火力。",
    },
    "decoy": {
        "name": "诱饵",
        "category": "neutral",
        "tags": ["诱敌", "召唤"],
        "sources": ["忍者"],
        "description": "在原地留下可被攻击的诱饵，吸引敌方仇恨并在被击中时反击。",
    },
    "pyro_breath": {
        "name": "龙息引导",
        "category": "neutral",
        "tags": ["引导", "扇形输出", "持续"],
        "sources": ["炎术士"],
        "description": "持续朝面前喷吐扇形火焰，在持续时间内反复灼烧前方区域。",
    },
    "smasher_leap": {
        "name": "重击跳跃",
        "category": "neutral",
        "tags": ["位移", "起跳", "落地"],
        "sources": ["重锤手"],
        "description": "先跃入空中短暂脱离地面，再于目标点落地造成范围冲击。",
    },
    "valkyrie_dive": {
        "name": "天降俯冲",
        "category": "neutral",
        "tags": ["位移", "俯冲", "落地"],
        "sources": ["女武神"],
        "description": "升空准备后锁定区域坠落，落地时结算范围伤害并附加短暂眩晕。",
    },
    "melee_gap_dash": {
        "name": "近战突进",
        "category": "neutral",
        "tags": ["位移", "追击", "AI"],
        "sources": ["多数近战职业"],
        "description": "近战单位在刚好够不到目标时会触发短距离追击突进，帮助贴身作战。",
    },
    "bounty_mark": {
        "name": "悬赏标记",
        "category": "neutral",
        "tags": ["标记", "悬赏", "锁定"],
        "sources": ["赏金猎人"],
        "description": "被标记者会成为赏金猎人的优先攻击目标，命中可为猎人带来额外收益。",
    },
    "bounty_coins": {
        "name": "赏金币",
        "category": "neutral",
        "tags": ["成长", "叠层", "强化"],
        "sources": ["赏金猎人"],
        "description": "赏金猎人命中悬赏目标后会积累赏金币，每层都会永久提升其基础攻击伤害。",
    },
    "bard_song": {
        "name": "战歌",
        "category": "neutral",
        "tags": ["范围", "攻速", "移速"],
        "sources": ["吟游诗人"],
        "description": "鼓舞 150 范围内所有友军，使其攻速与移速提升；吟游诗人的普攻也会附带音波减速。",
    },
    "slow": {
        "name": "减速",
        "category": "negative",
        "tags": ["减益", "移速", "持续"],
        "sources": ["法师", "冰霜法师", "咒术师", "重锤手"],
        "description": "降低移动速度，使目标更难追击、逃脱或完成走位。",
    },
    "stun": {
        "name": "眩晕",
        "category": "negative",
        "tags": ["控制", "硬控"],
        "sources": ["巨兽", "武僧", "女武神", "多种武器"],
        "description": "目标无法移动、攻击或施法，是最直接的硬控制效果之一。",
    },
    "freeze": {
        "name": "冻结",
        "category": "negative",
        "tags": ["控制", "冻结", "硬控"],
        "sources": ["冰霜法师"],
        "description": "冻结会附带眩晕效果，目标完全停滞并承受后续冰霜连段伤害。",
    },
    "root": {
        "name": "定身",
        "category": "negative",
        "tags": ["控制", "定身"],
        "sources": ["地术师", "角斗士"],
        "description": "目标无法移动，但仍可能继续攻击或施法，常用于限制走位。",
    },
    "charm": {
        "name": "魅惑",
        "category": "negative",
        "tags": ["控制", "魅惑"],
        "sources": ["魅魔"],
        "description": "被魅惑的目标无法攻击，并会缓慢朝魅魔移动。",
    },
    "control": {
        "name": "精神控制",
        "category": "negative",
        "tags": ["控制", "反叛"],
        "sources": ["傀儡师"],
        "description": "目标会在持续时间内倒向原队友，把攻击转移到其他单位身上。",
    },
    "doom": {
        "name": "末日",
        "category": "negative",
        "tags": ["持续伤害", "斩杀"],
        "sources": ["电磁兵"],
        "description": "持续造成真实伤害，并会在目标生命降到阈值以下时触发斩杀。",
    },
    "poison": {
        "name": "中毒",
        "category": "negative",
        "tags": ["持续伤害", "叠层"],
        "sources": ["毒师"],
        "description": "中毒可持续叠层并不断造成真实伤害，层数会随时间慢慢衰减。",
    },
    "burn": {
        "name": "自燃",
        "category": "negative",
        "tags": ["持续伤害", "自损"],
        "sources": ["法师"],
        "description": "奥术新星结束后法师会进入自燃状态，在持续时间内缓慢损失生命。",
    },
    "hell_burn": {
        "name": "灼烧",
        "category": "negative",
        "tags": ["持续伤害", "叠层"],
        "sources": ["炼狱使者"],
        "description": "炼狱使者施加的燃烧会持续叠层，每层每秒造成目标最大生命值1%伤害，持续3秒，最多5层。",
    },
    "curse": {
        "name": "厄运诅咒",
        "category": "negative",
        "tags": ["易伤", "减速"],
        "sources": ["咒术师"],
        "description": "被诅咒目标承受更高伤害，同时移动速度会受到明显压制。",
    },
    "backlash": {
        "name": "反噬",
        "category": "negative",
        "tags": ["延迟伤害", "自损"],
        "sources": ["骑士"],
        "description": "守护结束后按记录的承伤结算额外自伤，是骑士强防御的代价。",
    },
    "duel_lock": {
        "name": "决斗锁定",
        "category": "negative",
        "tags": ["定身", "单挑", "锁定"],
        "sources": ["角斗士"],
        "description": "被拖入决斗的目标会被定在近距离位置，被迫与角斗士进行正面交换。",
    },
    "duel_haste": {
        "name": "决斗亢奋",
        "category": "negative",
        "tags": ["攻速", "强制对拼"],
        "sources": ["角斗士"],
        "description": "被角斗士拉入决斗的目标会获得攻击速度提升，但也因此更难脱离贴脸换血节奏。",
    },
}

EFFECT_UI_TEXT = {
    "menu_button": "效果图鉴",
    "title": "效果图鉴",
    "return": "返回主菜单",
    "helper": "鼠标悬停左侧或右侧面板时，可使用滚轮滚动内容",
    "labels": {
        "category": "标签类别",
        "tags": "效果标签",
        "sources": "常见来源",
        "description": "效果说明",
    },
}

POKEDEX_UI_TEXT = {
    "menu_button": "图鉴",
    "title": "角色图鉴",
    "return": "返回主菜单",
    "helper": "鼠标悬停左侧或右侧面板时，可使用滚轮滚动内容",
    "labels": {
        "max_hp": "最大生命",
        "move_speed": "移动速度",
        "attack_type": "攻击类型",
        "attack_range": "攻击距离",
        "physical_resistance": "物理抵抗",
        "spell_resistance": "法术抵抗",
        "mp_charge": "充能方式",
        "skill": "技能名称",
        "passive": "专属被动",
        "passive_desc": "被动描述：",
        "skill_desc": "技能描述：",
    },
}

ATTACK_TYPE_LOCALIZATION = {
    "melee": "近战",
    "ranged": "远程",
}


def get_pokedex_data(key):
    data = CHARACTER_DATA[key]
    localized = POKEDEX_LOCALIZATION.get(key, {})
    return {
        **data,
        "job_name": key,
        "display_name": localized.get("name", data["name"]),
        "display_mp_charge_style": localized.get("mp_charge_style", data["mp_charge_style"]),
        "display_skill_name": localized.get("skill_name", data["skill_name"]),
        "display_skill_description": localized.get("skill_description", data["skill_description"]),
        "display_passive_name": localized.get("passive_name", data.get("passive_name", "")),
        "display_passive_description": localized.get("passive_description", data.get("passive_description", "")),
        "display_attack_type": ATTACK_TYPE_LOCALIZATION.get(data["attack_type"], data["attack_type"]),
        "physical_resistance": max(
            0.0,
            float(data.get("physical_resistance", JOB_RESISTANCE_PROFILES.get(key, {}).get("physical_resistance", 1.0))),
        ),
        "spell_resistance": max(
            0.0,
            float(data.get("spell_resistance", JOB_RESISTANCE_PROFILES.get(key, {}).get("spell_resistance", 1.0))),
        ),
    }


def get_effect_data(key):
    data = EFFECT_DATA[key]
    return {
        **data,
        "display_name": data["name"],
        "display_category": EFFECT_CATEGORY_LOCALIZATION.get(data["category"], data["category"]),
        "display_tags": " / ".join(data["tags"]),
        "display_sources": "、".join(data["sources"]),
        "category_color": EFFECT_CATEGORY_COLORS.get(data["category"], MENU_ACCENT),
    }


WEAPON_DEFS = {
    "Pistol": {
        "label": "PI",
        "ammo": 8,
        "fire_interval": 3.0,
        "damage": 0.6,
        "range": WEAPON_RANGE_MEDIUM,
        "spread_deg": 4.0,
        "burst_count": 1,
        "projectile_speed": 300.0,
        "projectile_color": (230, 230, 255),
        "homing": 0.0,
        "stun_duration": 1.0,
    },
    "SMG": {
        "label": "SM",
        "ammo": 30,
        "fire_interval": 0.2,
        "damage": 0.2,
        "range": WEAPON_RANGE_SHORT,
        "spread_deg": 16.0,
        "burst_count": 1,
        "projectile_speed": 320.0,
        "projectile_color": (255, 196, 92),
        "homing": 0.0,
        "stun_duration": 0.0,
    },
    "MachineGun": {
        "label": "MG",
        "ammo": 60,
        "fire_interval": 0.7,
        "damage": 0.1,
        "range": WEAPON_RANGE_MEDIUM,
        "spread_deg": 14.0,
        "burst_count": 1,
        "projectile_speed": 310.0,
        "projectile_color": (255, 108, 108),
        "homing": 0.0,
        "stun_duration": 0.0,
    },
    "Rifle": {
        "label": "RF",
        "ammo": 30,
        "fire_interval": 0.5,
        "damage": 0.3,
        "range": WEAPON_RANGE_MEDIUM,
        "spread_deg": 12.0,
        "burst_count": 1,
        "projectile_speed": 340.0,
        "projectile_color": (152, 255, 162),
        "homing": 0.0,
        "stun_duration": 0.0,
    },
    "Staff": {
        "label": "ST",
        "ammo": 1,
        "fire_interval": 1.0,
        "damage": 0.8,
        "range": WEAPON_RANGE_INFINITE,
        "spread_deg": 0.0,
        "burst_count": 3,
        "projectile_speed": 225.0,
        "projectile_color": (210, 164, 255),
        "homing": 6.5,
        "stun_duration": 0.0,
    },
    "ColdSpear": {
        "label": "CS",
        "ammo": 1,
        "fire_interval": 0.55,
        "damage": 1.0,
        "range": 72.0,
        "spread_deg": 0.0,
        "burst_count": 1,
        "projectile_speed": 0.0,
        "projectile_color": (92, 224, 236),
        "homing": 0.0,
        "stun_duration": 0.0,
        "special_kind": "spear_thrust",
    },
}

for weapon_id in FIREARM_WEAPON_IDS:
    WEAPON_DEFS[weapon_id]["fire_interval"] /= FIREARM_ATTACK_SPEED_MULTIPLIER

WEAPON_ORB_POOL = [weapon_id for weapon_id in WEAPON_DEFS.keys() if weapon_id != "ColdSpear"]


def rebalance_basic_attacks():
    for config in JOB_DEFS.values():
        if not config.get("use_design_attack_damage"):
            config["attack_damage"] = max(1, int(config["attack_damage"] * 0.5)) * 10
        if not config.get("use_design_attack_speed"):
            config["attack_interval"] = BASIC_ATTACK_COOLDOWN


rebalance_basic_attacks()


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
        if character.alive and getattr(character, "design_untargetable_timer", 0.0) <= 0:
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
    return targetables


def select_nearest_enemy(character, characters):
    nearest = None
    nearest_distance_sq = float("inf")
    for other in characters:
        if not other.alive or other.owner_id == character.owner_id:
            continue
        distance_sq = (other.pos - character.pos).length_squared()
        if distance_sq < nearest_distance_sq:
            nearest_distance_sq = distance_sq
            nearest = other
    return nearest


def select_lowest_hp_enemy(character, characters):
    enemies = [other for other in characters if other.alive and other.owner_id != character.owner_id]
    if not enemies:
        return None
    return min(enemies, key=lambda other: (other.hp, (other.pos - character.pos).length_squared()))


def select_farthest_enemy(character, characters):
    enemies = [other for other in characters if other.alive and other.owner_id != character.owner_id]
    if not enemies:
        return None
    return max(enemies, key=lambda other: (other.pos - character.pos).length_squared())


def select_highest_hp_enemy(character, characters):
    enemies = [other for other in characters if other.alive and other.owner_id != character.owner_id]
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


def spawn_damage_text(game_state, target, amount, damage_kind=None, is_true_damage=False, text=None, color=None):
    if game_state is None or target is None:
        return
    offset = pygame.Vector2(0, -getattr(target, "radius", CHARACTER_RADIUS) - 10)
    game_state["damage_texts"].append(
        DamageText(
            target.pos + offset,
            amount,
            damage_kind=damage_kind,
            is_true_damage=is_true_damage,
            text=text,
            color=color,
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


class DamageText:
    def __init__(self, pos, amount, damage_kind=None, is_true_damage=False, text=None, color=None):
        self.pos = pygame.Vector2(pos)
        self.amount = max(1, int(round(amount)))
        self.text = text if text is not None else f"-{self.amount}"
        self.color = color if color is not None else get_damage_text_color(damage_kind, is_true_damage)
        self.lifetime = DAMAGE_TEXT_DURATION
        self.alive = True

    def update(self, dt):
        self.pos.y -= 32 * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface, font):
        alpha = int(255 * clamp(self.lifetime / DAMAGE_TEXT_DURATION, 0.0, 1.0))
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
        overlay = pygame.Surface((arc_radius * 5, arc_radius * 5), pygame.SRCALPHA)
        overlay_center = (overlay.get_width() // 2, overlay.get_height() // 2)
        arc_rect = pygame.Rect(0, 0, arc_radius * 2, arc_radius * 2)
        arc_rect.center = overlay_center
        shadow_color = (*shade_color(self.color, 0.35), max(36, alpha // 2))
        glow_color = (*mix_color(self.color, (255, 255, 255), 0.34), alpha)
        core_color = (*self.color, alpha)
        pygame.draw.arc(overlay, shadow_color, arc_rect.inflate(8, 8), math.radians(205), math.radians(334), 7)
        pygame.draw.arc(overlay, glow_color, arc_rect, math.radians(210), math.radians(330), 4)
        tip_start = pygame.Vector2(overlay_center) + pygame.Vector2(arc_radius * 0.15, -arc_radius * 0.18)
        tip_end = pygame.Vector2(overlay_center) + pygame.Vector2(arc_radius * 0.78, arc_radius * 0.12)
        pygame.draw.line(overlay, core_color, tip_start, tip_end, 3)
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
                    spawn_attack_impact(game_state, target.pos, self.color, radius=max(10, int(self.radius * 2.8)))
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
            self.hp = 50
            self.max_hp = 50
            self.damage = 8
            self.speed = 155.0
            self.lifetime = DESIGN_WOLF_DURATION
            self.attack_type = "melee"
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
        pre_damage_hp = self.hp
        self.hp -= amount
        handle_equilibrium_thresholds(self, pre_damage_hp, source if hasattr(source, "on_damage_dealt") else getattr(source, "owner", None), game_state, ignore_equilibrium_thresholds=ignore_equilibrium_thresholds)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
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
        target = select_nearest_targetable(self, game_state)
        if target is None:
            return
        offset = target.pos - self.pos
        distance = offset.length()
        direction = offset.normalize() if distance > 0 else random_unit_vector()
        if self.attack_type == "melee":
            self.vel = direction * self.speed
            self.pos += self.vel * dt
            if distance <= self.attack_range + target.radius:
                target.take_damage(self.damage, source=self.owner, damage_type="design_physical_summon", game_state=game_state)
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
                self.attack_cooldown = 3.0 if self.summon_type == "drone" else 0.9
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


def spawn_attack_impact(game_state, pos, color, radius=14, thickness=3, lifetime=0.16, burst_count=6):
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


def apply_design_hit_effects(attacker, target, game_state, is_melee):
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
        if attacker.design_phoenix_same_hits >= 7:
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
        target.design_ranger_mark = min(RANGER_MARK_MAX, target.design_ranger_mark + 1)
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
    if target is None or not target.alive:
        return
    repeats = max(1, int(attacker.config.get("attack_repeat", 1)))
    damage = attacker.get_current_basic_damage() * attacker.get_target_attack_bonus(target)
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
                attacker.heal(100.0)
            else:
                attacker.heal(50.0)
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
                if role_num == 63 and target.hp > 0 and target.hp <= target.max_hp * 0.05:
                    target.take_damage(target.hp + 1.0, source=attacker, damage_type="true_design_execute", game_state=game_state)
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
                )
        attacker.design_sentinel_lock = False
    attacker.attack_cooldown = attacker.get_basic_attack_cooldown()
    attacker.on_attack_committed()


def cast_design_skill(caster, game_state, token=None):
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
    elif role_num == 95 or token == "windstorm_blade_roll":
        def windstorm_blade_roll_once():
            living_enemies = [enemy for enemy in enemies if enemy.alive]
            if not living_enemies:
                return False
            roll = random.random()
            if roll < 0.50:
                for _ in range(8):
                    chosen = random.choice(living_enemies)
                    spawn_windstorm_blade_projectile(
                        caster,
                        game_state,
                        chosen.pos - caster.pos,
                        WINDSTORM_FOX_SKILL_BLADE_DAMAGE,
                        "design_physical_windstorm_blade",
                        speed=700.0,
                        max_range=900.0,
                    )
                for enemy in living_enemies:
                    enemy.take_damage(WINDSTORM_FOX_GLOBAL_BLADE_DAMAGE, source=caster, damage_type="design_physical_windstorm_global", game_state=game_state)
            elif roll < 0.85:
                for _ in range(12):
                    chosen = random.choice(living_enemies)
                    spawn_windstorm_blade_projectile(
                        caster,
                        game_state,
                        chosen.pos - caster.pos,
                        WINDSTORM_FOX_SKILL_BLADE_DAMAGE,
                        "design_physical_windstorm_blade",
                        speed=730.0,
                        max_range=920.0,
                        apply_resist=True,
                    )
            else:
                for _ in range(20):
                    chosen = random.choice(living_enemies)
                    spawn_windstorm_blade_projectile(
                        caster,
                        game_state,
                        chosen.pos - caster.pos,
                        WINDSTORM_FOX_SKILL_BLADE_DAMAGE,
                        "design_physical_windstorm_blade",
                        speed=760.0,
                        max_range=940.0,
                        ricochet=True,
                        lifesteal_ratio=WINDSTORM_FOX_LIFESTEAL_RATIO,
                    )
            return True

        if windstorm_blade_roll_once() and random.random() < 0.30:
            windstorm_blade_roll_once()
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
            if (enemy.pos - caster.pos).length() <= DESIGN_FORTRESS_RADIUS + enemy.radius:
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
            (enemy for enemy in enemies if enemy.alive),
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
            if (enemy.pos - caster.pos).length() <= XUANWU_BULWARK_TAUNT_RADIUS + enemy.radius:
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
        living = [enemy for enemy in enemies if enemy.alive]
        if living:
            prey = max(living, key=lambda e: (e.design_susanoo_prowl, -((e.pos - caster.pos).length_squared())))
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
    elif token == "phantom_lancer_throw":
        target = select_nearest_enemy(caster, game_state["characters"])
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else pygame.Vector2(1, 0)
        if target is not None:
            offset = target.pos - caster.pos
            if offset.length_squared() > 0:
                direction = offset.normalize()
                target.take_damage(caster.get_current_basic_damage() * 2.0, source=caster, damage_type="design_physical_spear_throw", game_state=game_state)
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
        direction = caster.recent_move_dir if caster.recent_move_dir.length_squared() > 0 else random_unit_vector()
        direction = direction.normalize()
        caster.pos -= direction * 80.0
        caster.pos.x = clamp(caster.pos.x, ARENA_RECT.left + caster.radius, ARENA_RECT.right - caster.radius)
        caster.pos.y = clamp(caster.pos.y, ARENA_RECT.top + caster.radius, ARENA_RECT.bottom - caster.radius)
        caster.design_ranger_speed_timer = max(caster.design_ranger_speed_timer, RANGER_DASH_SPEED_DURATION)
        for offset in (-24, -12, 0, 12, 24):
            spawn_design_projectile(caster, game_state, direction.rotate(offset), 14.0, "design_physical_ranger", (160, 255, 180), max_range=320.0, pierce=True)
    elif token == "stone_skin":
        caster.clear_negative_states()
        caster.heal(80.0)
        caster.control_immunity_timer = 5.0
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
            target.take_damage(60.0, source=caster, damage_type="true_design_guillotine", game_state=game_state)
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
            if (enemy.pos - caster.pos).length() <= 90.0 + enemy.radius:
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
            if enemy.design_marked and enemy.design_mark_owner_id == caster.owner_id:
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
            damage += max(0.0, speed_ratio - 1.0) * 45.0
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
        return max(1.0, damage)

    def get_current_melee_stun_duration(self):
        if self.druid_form_timer > 0 and self.held_weapon is None:
            return DRUID_FORM_STUN
        if self.job_name == "DesignRole60_golem":
            return 1.2
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
        return max(0.08, multiplier)

    def get_basic_attack_cooldown(self):
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
        return healed

    def gain_mp(self, amount, reason):
        if not self.alive or amount <= 0:
            return
        self.mp = clamp(self.mp + amount, 0.0, MAX_MP)

    def apply_slow(self, amount, duration):
        if self.job_name == "DesignRole64_dreamweaver":
            return
        self.slow_timer = max(self.slow_timer, duration)
        self.slow_factor = max(self.slow_factor, amount)

    def apply_stun(self, duration):
        if self.control_immunity_timer > 0 or self.job_name == "DesignRole64_dreamweaver":
            return
        self.stun_timer = max(self.stun_timer, duration)

    def apply_root(self, duration):
        if self.control_immunity_timer > 0 or self.job_name == "DesignRole64_dreamweaver":
            return
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
        weapon_orb.alive = False
        if self.config["mp_mode"] == "weapon_pickup":
            self.gain_mp(self.config["mp_rate"], "weapon_pickup")
        return True

    def clear_weapon(self):
        self.held_weapon = None

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

        damage = amount
        is_true_damage = str(damage_type).startswith("true_")
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
                )
            )
        if self.hp <= 0:
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
                if source_character is not None and source_character.is_dragon():
                    source_character.design_dragon_awe = min(DRAGON_AWE_MAX, source_character.design_dragon_awe + 1)
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
        spawn_attack_impact(game_state, target.pos, self.get_visual_color(), radius=max(11, int(self.radius * 1.1)))
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

        skill_id = self.config["skill_id"]
        if self.is_design_role():
            if self.silence_timer > 0:
                return
            if self.stun_timer > 0 and self.design_meta.get("skill_token") not in {"phase_shift", "sunfire_kagura"}:
                return
            if cast_design_skill(self, game_state):
                self.mp = 0.0
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
                spawn_attack_impact(game_state, self.pos, (255, 90, 90), radius=72, thickness=4, lifetime=0.18, burst_count=10)

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
                self.heal(2)

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
        draw_shape_icon(surface, self.shape, draw_color, (round(center.x), round(center.y)), self.radius - 2)

    def draw_spawn_fx(self, surface):
        if self.spawn_fx_timer <= 0:
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
        if self.shield_timer > 0:
            pygame.draw.circle(surface, (120, 180, 255), center, round(self.radius + 6), 2)
        if self.berserker_spin_timer > 0:
            pygame.draw.circle(surface, (255, 90, 90), center, round(self.radius + 8), 2)
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
    job_names = list(JOB_DEFS.keys())
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

    title = title_font.render("Auto Battler Arena", True, TEXT_COLOR)
    surface.blit(title, (header_rect.left + 14, header_rect.top + 6))

    alive_characters = get_living_main_characters(game_state)
    chips = [
        ("Alive", str(len(alive_characters)), (110, 190, 140)),
        ("Orbs", str(len(game_state["weapon_orbs"])), (110, 170, 255)),
    ]
    chip_width = 88
    chip_height = 24
    chip_gap = 8
    chips_total_width = len(chips) * chip_width + max(0, len(chips) - 1) * chip_gap
    chip_x = header_rect.right - chips_total_width - 14
    chip_y = header_rect.top + 11
    for index, (label, value, accent_color) in enumerate(chips):
        chip_rect = pygame.Rect(chip_x + index * (chip_width + chip_gap), chip_y, chip_width, chip_height)
        draw_panel(surface, chip_rect, (24, 30, 40), border_color=(78, 88, 102), accent_color=accent_color, radius=10, shadow_offset=(1, 2))
        label_surface = small_font.render(label, True, (174, 186, 200))
        value_surface = small_font.render(value, True, TEXT_COLOR)
        surface.blit(label_surface, (chip_rect.left + 10, chip_rect.top + 4))
        surface.blit(value_surface, (chip_rect.right - value_surface.get_width() - 10, chip_rect.top + 4))

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
    game_state["design_effects"] = [effect for effect in game_state["design_effects"] if effect.alive]
    game_state["weapon_orbs"] = [orb for orb in game_state["weapon_orbs"] if orb.alive]
    game_state["damage_texts"] = [damage_text for damage_text in game_state["damage_texts"] if damage_text.alive]
    game_state["death_particles"] = [particle for particle in game_state["death_particles"] if particle.alive]
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
    for particle in game_state["death_particles"]:
        particle.draw(surface)
    for damage_text in game_state["damage_texts"]:
        damage_text.draw(surface, label_font)


def draw_menu(screen, title_font, subtitle_font, button_font, player_count, hover_name, disable_timed_weapon_drops):
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
    start_rect = pygame.Rect(244, 492, 312, 72)
    pokedex_rect = pygame.Rect(244, 576, 312, 60)
    effects_rect = pygame.Rect(244, 646, 312, 52)
    win_rate_rect = pygame.Rect(244, 710, 312, 44)
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
    effects_color = MENU_BUTTON_HOVER if hover_name == "effects" else MENU_BUTTON
    win_rate_color = MENU_BUTTON_HOVER if hover_name == "win_rate" else MENU_BUTTON

    if player_count <= MIN_CHARACTERS:
        minus_color = MENU_BUTTON_DISABLED
    if player_count >= MAX_CHARACTERS:
        plus_color = MENU_BUTTON_DISABLED

    draw_panel(screen, decrement_rect, minus_color, radius=12, shadow_offset=(2, 2))
    draw_panel(screen, increment_rect, plus_color, radius=12, shadow_offset=(2, 2))
    draw_panel(screen, start_rect, start_color, radius=14, shadow_offset=(3, 4), accent_color=(255, 214, 120))
    draw_panel(screen, pokedex_rect, pokedex_color, radius=12, shadow_offset=(2, 3))
    draw_panel(screen, effects_rect, effects_color, radius=12, shadow_offset=(2, 3))
    draw_panel(screen, win_rate_rect, win_rate_color, radius=12, shadow_offset=(2, 3))

    # 开始按钮 ▶ 图标 + 文案
    start_text = button_font.render("开始战斗", True, TEXT_COLOR)
    tri = [(start_rect.left + 24, start_rect.centery - 9), (start_rect.left + 24, start_rect.centery + 9), (start_rect.left + 36, start_rect.centery)]
    pygame.draw.polygon(screen, (255, 214, 120), tri)
    screen.blit(start_text, start_text.get_rect(center=(start_rect.centerx + 6, start_rect.centery)))

    # 图鉴 / 效果 / 胜率 按钮：左侧彩色圆点
    icon_dots = ((pokedex_rect, (110, 170, 255)), (effects_rect, (142, 226, 188)), (win_rate_rect, (255, 214, 120)))
    for rect, dot_color in icon_dots:
        pygame.draw.circle(screen, dot_color, (rect.left + 18, rect.centery), 6)
        pygame.draw.circle(screen, BORDER_COLOR, (rect.left + 18, rect.centery), 6, 1)

    minus_text = title_font.render("-", True, TEXT_COLOR)
    plus_text = title_font.render("+", True, TEXT_COLOR)
    pokedex_text = button_font.render(POKEDEX_UI_TEXT["menu_button"], True, TEXT_COLOR)
    effects_text = subtitle_font.render(EFFECT_UI_TEXT["menu_button"], True, TEXT_COLOR)
    win_rate_text = subtitle_font.render("胜率", True, TEXT_COLOR)
    screen.blit(minus_text, minus_text.get_rect(center=decrement_rect.center))
    screen.blit(plus_text, plus_text.get_rect(center=increment_rect.center))
    screen.blit(pokedex_text, pokedex_text.get_rect(center=(pokedex_rect.centerx + 8, pokedex_rect.centery)))
    screen.blit(effects_text, effects_text.get_rect(center=(effects_rect.centerx + 8, effects_rect.centery)))
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

    # 底部信息条
    version_text = subtitle_font.render(f"已收录 {len(JOB_DEFS)} 名角色 · 圆环斗场 v0.9 · Enter 开始战斗", True, (150, 164, 180))
    screen.blit(version_text, version_text.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10)))

    return {
        "minus": decrement_rect,
        "plus": increment_rect,
        "start": start_rect,
        "pokedex": pokedex_rect,
        "effects": effects_rect,
        "win_rate": win_rate_rect,
        "weapon_drops": weapon_drops_rect,
    }


def get_menu_button_rects():
    return {
        "minus": pygame.Rect(232, 258, 60, 60),
        "plus": pygame.Rect(508, 258, 60, 60),
        "start": pygame.Rect(244, 492, 312, 72),
        "pokedex": pygame.Rect(244, 576, 312, 60),
        "effects": pygame.Rect(244, 646, 312, 52),
        "win_rate": pygame.Rect(244, 710, 312, 44),
        "weapon_drops": pygame.Rect(244, 356, 300, 28),
    }


def draw_battle_end_button(surface, button_font, hover_active):
    button_rect = pygame.Rect(250, 610, 300, 74)
    button_color = MENU_BUTTON_HOVER if hover_active else MENU_BUTTON
    draw_panel(surface, button_rect, button_color, radius=14, shadow_offset=(3, 4))
    button_text = button_font.render("Back To Menu", True, TEXT_COLOR)
    surface.blit(button_text, button_text.get_rect(center=button_rect.center))
    return button_rect


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


BASE_ROLE_ORDER = [n for n in JOB_DEFS.keys() if not n.startswith("DesignRole") and n != "Bloodwraith"]


def get_role_display_number(job_name):
    meta = DESIGN_ROLE_METADATA.get(job_name, {})
    num = meta.get("role_num")
    if num is not None:
        return int(num)
    if job_name == "Bloodwraith":
        return 40
    if job_name in BASE_ROLE_ORDER:
        return BASE_ROLE_ORDER.index(job_name) + 1
    return None


def get_pokedex_ordered_names():
    def sort_key(name):
        num = get_role_display_number(name)
        if num is not None:
            return (0, num)
        return (1, 0)

    return sorted(CHARACTER_DATA.keys(), key=sort_key)


def get_role_attack_tag(job_name, data):
    melee = data.get("attack_type") == "melee"
    prefix = "近" if melee else "远"
    if job_name == DRAGON_JOB_NAME:
        return prefix + "混"
    kind = DESIGN_ROLE_METADATA.get(job_name, {}).get("basic_damage_kind")
    if kind == "spell":
        return prefix + "法"
    if kind == "true":
        return prefix + "真"
    if job_name.startswith("DesignRole"):
        return prefix + "物"
    return prefix


def filter_pokedex_names(ordered_names, query):
    if not query:
        return list(ordered_names)
    q = query.lower()
    out = []
    for name in ordered_names:
        data = get_pokedex_data(name)
        if q in data["display_name"].lower() or q in name.lower():
            out.append(name)
    return out


def pokedex_layout_entries(filtered_names):
    entries = []
    prev_group = None
    for name in filtered_names:
        num = get_role_display_number(name)
        group = "design" if num is not None and num > 40 else "base"
        if group != prev_group:
            entries.append(("header", "基础英雄" if group == "base" else "设计角色"))
            prev_group = group
        entries.append(("row", name))
    return entries


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


def build_win_rate_rows(body_font, stats):
    rows = []
    for job_name in CHARACTER_DATA.keys():
        data = get_pokedex_data(job_name)
        entry = stats.get(job_name, {"matches": 0, "wins": 0})
        matches = max(0, int(entry.get("matches", 0)))
        wins = max(0, min(matches, int(entry.get("wins", 0))))
        win_rate = (wins / matches * 100.0) if matches > 0 else 0.0
        rows.append(
            {
                "job_name": job_name,
                "display_name": data["display_name"],
                "matches": matches,
                "wins": wins,
                "win_rate": win_rate,
                "shape": data["shape"],
                "color": data["color"],
            }
        )
    rows.sort(key=lambda row: (-row["win_rate"], -row["wins"], -row["matches"], row["display_name"]))
    return rows


def draw_win_rate_screen(screen, title_font, subtitle_font, body_font, button_font, hover_name, scroll_offset, stats):
    screen.fill(BACKGROUND_COLOR)

    title = title_font.render("胜率", True, TEXT_COLOR)
    subtitle = subtitle_font.render("统计每个角色的场次、获胜次数与胜率", True, (180, 192, 208))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 52)))
    screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 84)))

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

        icon_center = (row_rect.left + 16, row_rect.centery)
        draw_shape_icon(screen, row["shape"], row["color"], icon_center, 9)
        name_text = truncate_text(row["display_name"], body_font, 290)
        screen.blit(body_font.render(name_text, True, TEXT_COLOR), (row_rect.left + 34, row_rect.top + 8))
        screen.blit(body_font.render(str(row["matches"]), True, TEXT_COLOR), (columns["matches"], row_rect.top + 8))
        screen.blit(body_font.render(str(row["wins"]), True, TEXT_COLOR), (columns["wins"], row_rect.top + 8))
        rate_text = f"{row['win_rate']:.1f}%"
        rate_color = MENU_ACCENT if row["matches"] > 0 else (132, 144, 160)
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
    elif character.job_name == "DesignRole90_collector":
        if character.design_collect_fervor:
            parts.append(f"狂热{character.design_collect_fervor}")
    elif character.job_name == "DesignRole53_sentinel":
        if character.design_sentinel_lock:
            parts.append("瞄准")
    return " ".join(parts)


def draw_battle_sidebar(surface, title_font, subtitle_font, body_font, game_state, active_tab, hover_tab):
    sidebar_rect = pygame.Rect(0, 0, BATTLE_SIDEBAR_WIDTH, BATTLE_WINDOW_HEIGHT)
    panel_rect = sidebar_rect.inflate(-16, -16)
    surface.fill((10, 14, 20), sidebar_rect)
    draw_panel(surface, panel_rect, (18, 24, 32), accent_color=(84, 128, 184), radius=14)
    pygame.draw.line(surface, BORDER_COLOR, (sidebar_rect.left, 0), (sidebar_rect.left, BATTLE_WINDOW_HEIGHT), 2)

    header = title_font.render("本局数据", True, TEXT_COLOR)
    surface.blit(header, header.get_rect(center=(sidebar_rect.width // 2, 28)))

    tab_y = 54
    tab_w = 128
    tab_h = 32
    tab_gap = 8
    output_rect = pygame.Rect(panel_rect.left + 6, tab_y, tab_w, tab_h)
    taken_rect = pygame.Rect(output_rect.right + tab_gap, tab_y, tab_w, tab_h)
    tab_rects = {"output": output_rect, "taken": taken_rect}
    tab_labels = {"output": "输出排行", "taken": "承伤排行"}
    for key, rect in tab_rects.items():
        is_active = active_tab == key
        is_hover = hover_tab == key
        color = MENU_ACCENT if is_active else (MENU_BUTTON_HOVER if is_hover else MENU_BUTTON)
        draw_panel(surface, rect, color, border_color=(74, 82, 92), radius=10, shadow_offset=(1, 1))
        label = subtitle_font.render(tab_labels[key], True, TEXT_COLOR)
        surface.blit(label, label.get_rect(center=rect.center))

    participants = list(game_state.get("battle_participants", game_state.get("characters", [])))
    metric = "damageDealt" if active_tab == "output" else "damageTaken"
    accent = (220, 72, 72) if active_tab == "output" else (84, 150, 255)
    bar_bg = (34, 40, 52)
    bar_inner = (72, 78, 92)
    rows = sorted(participants, key=lambda character: (-getattr(character, metric, 0.0), character.id))
    max_value = max((getattr(character, metric, 0.0) for character in rows), default=0.0)

    row_top = 100
    row_height = 50
    bar_width = 118
    name_width = 90
    for index, character in enumerate(rows):
        row_y = row_top + index * row_height
        row_rect = pygame.Rect(panel_rect.left + 6, row_y, panel_rect.width - 12, row_height - 8)
        if row_rect.bottom > panel_rect.bottom - 8:
            break
        row_bg = (26, 30, 38) if character.alive else (22, 24, 30)
        pygame.draw.rect(surface, row_bg, row_rect, border_radius=10)
        pygame.draw.rect(surface, (46, 52, 64), row_rect, 1, border_radius=10)

        icon_color = character.color if character.alive else tuple(max(0, int(channel * 0.55)) for channel in character.color)
        draw_shape_icon(surface, character.shape, icon_color, (row_rect.left + 16, row_rect.centery - 4), 10)

        name = truncate_text(get_character_display_name(character), body_font, name_width)
        name_color = TEXT_COLOR if character.alive else (160, 168, 176)
        name_surface = body_font.render(name, True, name_color)
        surface.blit(name_surface, (row_rect.left + 32, row_rect.top + 4))

        value = float(getattr(character, metric, 0.0))
        value_surface = subtitle_font.render(str(int(round(value))), True, accent)
        surface.blit(value_surface, (row_rect.right - value_surface.get_width() - 10, row_rect.top + 4))

        state_text = describe_design_state(character)
        if state_text and character.alive:
            state_surface = body_font.render(truncate_text(state_text, body_font, 150), True, (150, 180, 205))
            surface.blit(state_surface, (row_rect.left + 32, row_rect.top + 21))

        fill_width = int(bar_width * (value / max_value)) if max_value > 0 else 0
        bar_rect = pygame.Rect(row_rect.left + 32, row_rect.bottom - 12, bar_width, 8)
        pygame.draw.rect(surface, bar_bg, bar_rect, border_radius=4)
        if fill_width > 0:
            pygame.draw.rect(surface, bar_inner, bar_rect.inflate(-2, -2), border_radius=4)
            pygame.draw.rect(surface, accent, pygame.Rect(bar_rect.left + 1, bar_rect.top + 1, max(1, fill_width - 2), bar_rect.height - 2), border_radius=4)


def create_ui_font(size, bold=False):
    preferred_fonts = [
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    return pygame.font.SysFont(preferred_fonts, size, bold=bold)


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
                elif button_rects["effects"].collidepoint(mapped_pos):
                    return ("effects", None)
                elif button_rects["win_rate"].collidepoint(mapped_pos):
                    return ("win_rate", None)

        mouse_pos = map_window_pos_to_canvas(pygame.mouse.get_pos(), canvas_rect, device_pixel_ratio)
        hover_name = next((name for name, rect in button_rects.items() if mouse_pos is not None and rect.collidepoint(mouse_pos)), None)
        canvas_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        draw_menu(canvas_surface, title_font, subtitle_font, button_font, player_count, hover_name, disable_timed_weapon_drops)
        present_canvas(screen, canvas_surface, canvas_rect)
        pygame.display.flip()
        clock.tick(FPS)


_POKEDEX_LAST_SELECTED = None


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
                for name, rect in item_rects.items():
                    if rect.collidepoint(mapped_pos):
                        if selected_name != name:
                            selected_name = name
                            _POKEDEX_LAST_SELECTED = name
                            detail_scroll_offset = 0
                            _, _, detail_max_scroll = build_detail(selected_name)
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
        )
        present_canvas(screen, canvas_surface, canvas_rect)
        detail_scroll_offset = int(clamp(detail_scroll_offset, 0, detail_max_scroll))
        pygame.display.flip()
        clock.tick(FPS)


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


def battle_loop(screen, clock, title_font, small_font, button_font, player_count, timed_weapon_orb_drops_enabled=True):
    game_state = create_game_state(player_count, timed_weapon_orb_drops_enabled)
    scene_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    frame_surface = pygame.Surface((BATTLE_WINDOW_WIDTH, BATTLE_WINDOW_HEIGHT))
    sidebar_surface = pygame.Surface((BATTLE_SIDEBAR_WIDTH, BATTLE_WINDOW_HEIGHT))
    paused = False
    active_tab = "output"

    while True:
        dt = clock.tick(FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        end_button_rect = pygame.Rect(250, 610, 300, 74)
        pause_button_rects = {
            "resume": pygame.Rect(250, 320, 300, 68),
            "menu": pygame.Rect(250, 404, 300, 68),
        }
        output_tab_rect = pygame.Rect(SCREEN_WIDTH + 16, 54, 128, 32)
        taken_tab_rect = pygame.Rect(SCREEN_WIDTH + 152, 54, 128, 32)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not game_state["winner_text"]:
                paused = not paused
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if output_tab_rect.collidepoint(event.pos):
                    active_tab = "output"
                elif taken_tab_rect.collidepoint(event.pos):
                    active_tab = "taken"
                elif game_state["winner_text"] and end_button_rect.collidepoint(event.pos):
                    return "menu"
                elif paused and pause_button_rects["resume"].collidepoint(event.pos):
                    paused = False
                elif paused and pause_button_rects["menu"].collidepoint(event.pos):
                    return "menu"

        if not paused and not game_state["winner_text"]:
            game_state["elapsed_time"] += dt
            update_weapon_orbs(game_state, dt)
            living_characters = get_living_characters(game_state)
            for character in living_characters:
                character.update(dt, game_state)

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

            update_world_lists(game_state, dt)
            game_state["characters"] = [character for character in game_state["characters"] if character.alive]
            living_characters = get_living_main_characters(game_state)
            if len(living_characters) == 1:
                winner = living_characters[0]
                game_state["winner_text"] = f"Player {winner.id} ({winner.job_name}) Wins!"
                game_state["winner_character"] = winner
            elif len(living_characters) == 0:
                game_state["winner_text"] = "No Winner"
                game_state["winner_character"] = None

        if game_state["winner_text"] and not game_state["result_recorded"]:
            record_win_rate_result(game_state)
            game_state["result_recorded"] = True

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
        frame_surface.blit(scene_surface, offset)
        if game_state["winner_text"]:
            draw_battle_end_button(frame_surface, button_font, end_button_rect.collidepoint(mouse_pos))
        elif paused:
            pause_hover = next((name for name, rect in pause_button_rects.items() if rect.collidepoint(mouse_pos)), None)
            draw_pause_menu(frame_surface, title_font, small_font, button_font, pause_hover)

        sidebar_surface.fill((10, 14, 20))
        draw_battle_sidebar(
            sidebar_surface,
            title_font,
            small_font,
            small_font,
            game_state,
            active_tab,
            "output" if output_tab_rect.collidepoint(mouse_pos) else "taken" if taken_tab_rect.collidepoint(mouse_pos) else None,
        )
        frame_surface.blit(sidebar_surface, (SCREEN_WIDTH, 0))
        screen.blit(frame_surface, (0, 0))
        pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT), WINDOW_FLAGS)
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
        player_count = menu_result[1]
        timed_weapon_orb_drops_enabled = not menu_result[2] if len(menu_result) > 2 else True
        screen = pygame.display.set_mode((BATTLE_WINDOW_WIDTH, BATTLE_WINDOW_HEIGHT), BATTLE_WINDOW_FLAGS)
        result = battle_loop(screen, clock, title_font, small_font, button_font, player_count, timed_weapon_orb_drops_enabled)
        screen = pygame.display.set_mode((WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT), WINDOW_FLAGS)
        if result is None:
            break

    pygame.quit()


if __name__ == "__main__":
    sys.excepthook = handle_unhandled_exception
    try:
        main()
    finally:
        pygame.quit()
