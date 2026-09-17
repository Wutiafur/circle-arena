import re
from pathlib import Path


ATTACK_SPEED_INTERVALS = {
    "极快": 0.42,
    "很快": 0.56,
    "快": 0.72,
    "慢": 1.02,
    "很慢": 1.28,
    "极慢": 1.55,
}

VISUAL_SHAPE_MAP = {
    "交叉十字": "cross_x",
    "极长矩形": "wide",
    "虚线圆": "ring",
    "椭圆": "oval",
    "三角形": "triangle",
    "星月形": "star5",
    "宽矩形": "wide",
    "宽棱状": "slim_diamond",
    "厚重棱状": "hexagon",
    "锐棱状": "triangle",
    "长弧状": "slim_diamond",
    "船锚形": "cross",
    "十字": "cross",
    "四色方块": "square",
    "问号形": "ring",
    "墓碑状": "wide",
    "细长三角": "triangle",
    "连菱形": "diamond",
    "粗六边形": "hexagon",
    "眼睛形": "oval",
    "扑克形": "square",
    "扭曲波纹": "ring",
    "燕尾形": "triangle_down",
    "不规则块": "shards",
    "新月形": "half_circle",
    "六芒星": "star6",
    "斧刃半圆": "half_circle",
    "螺旋形": "ring",
    "齿轮形": "gear",
    "泪滴形": "triangle_down",
    "八卦形": "ring",
    "多足圆": "circle",
    "厚重正方": "square",
    "水滴形": "triangle_down",
    "菱形长剑": "slim_diamond",
    "漩涡形": "ring",
    "太阳形": "star6",
    "船舵形": "gear",
    "星云状": "shards",
    "莲花形": "star6",
    "细长半月": "half_circle",
    "火焰形": "triangle",
    "弹壳形": "wide",
    "缺角沙漏": "hourglass",
    "立方体": "square",
    "狼牙形": "shards",
    "波纹形": "ring",
    "蜂巢形": "hexagon",
    "剑柄形": "cross",
    "锁链": "cross_x",
    "巨大六边": "hexagon",
    "矮胖圆柱": "wide",
    "扩音器": "triangle",
    "宝箱形": "wide",
}

COLOR_MAP = {
    "墨蓝色": (48, 74, 126),
    "银蓝色": (156, 192, 220),
    "浅灰色": (206, 212, 220),
    "动物棕": (146, 102, 74),
    "毒绿色": (118, 190, 74),
    "宇宙深蓝": (62, 86, 146),
    "铁灰色": (118, 124, 136),
    "海蓝色": (74, 152, 214),
    "猩红色": (196, 52, 74),
    "混色": (166, 148, 224),
    "纯白色": (244, 244, 244),
    "阴暗灰": (112, 112, 120),
    "荧光蓝": (104, 228, 255),
    "撞色红蓝": (210, 96, 146),
    "金色": (240, 196, 100),
    "军绿色": (112, 136, 86),
    "亮金色": (238, 212, 108),
    "黑红相间": (146, 64, 72),
    "暗紫色": (96, 72, 146),
    "翠绿色": (90, 196, 110),
    "灰黑色": (86, 90, 96),
    "深灰色": (88, 90, 106),
    "幽蓝色": (102, 156, 232),
    "血红色": (206, 56, 56),
    "梦幻紫": (174, 122, 226),
    "亮银色": (212, 218, 228),
    "黑白相间": (196, 196, 196),
    "暗紫绿": (106, 134, 92),
    "生铁色": (126, 132, 118),
    "蔚蓝色": (92, 172, 236),
    "魔力紫": (170, 92, 220),
    "暗夜黑": (28, 30, 38),
    "纯白金": (252, 246, 204),
    "幽灵青": (112, 214, 214),
    "星空紫": (152, 118, 210),
    "深黑紫": (58, 48, 78),
    "暗红色": (182, 68, 52),
    "黄铜色": (194, 152, 88),
    "亮蓝色": (88, 178, 255),
    "亮白光": (242, 244, 248),
    "极光色": (136, 222, 212),
    "暗黄绿": (136, 152, 84),
    "空灵白": (240, 244, 252),
    "暗金色": (180, 152, 92),
    "玄黑": (36, 38, 42),
    "银白色": (222, 228, 238),
    "青碧色": (64, 190, 178),
    "冰蓝色": (138, 206, 255),
    "火药黑": (56, 54, 54),
    "震荡白": (232, 238, 244),
    "珠光宝气": (224, 190, 122),
}

ROLE_CONFIG_OVERRIDES = {
    98: {"skill_token": "hero_triple"},
    41: {"skill_token": "trap", "mp_mode": "passive", "mp_rate": 12.0},
    42: {"skill_token": "charge_dash", "mp_mode": "distance_scaled", "mp_rate": 1.0},
    43: {"skill_token": "phase_shift", "basic_damage_kind": "spell", "mp_mode": "damage_taken_scaled", "mp_rate": 1.0},
    44: {"skill_token": "summon_wolf", "attack_status": ("bleed", 0.6), "mp_mode": "damage_dealt_scaled", "mp_rate": 1.5},
    45: {"skill_token": "plague_mark", "basic_damage_kind": "spell", "attack_status": ("poison", 0.2), "mp_mode": "passive", "mp_rate": 10.0},
    46: {"skill_token": "meteor_storm", "basic_damage_kind": "spell", "mp_mode": "passive", "mp_rate": 8.0},
    47: {"skill_token": "fortress", "mp_mode": "damage_taken_scaled", "mp_rate": 1.2, "radius_scale": 1.16},
    48: {"skill_token": "cannon_support", "shotgun_pellets": 12, "shotgun_damage": 3.0, "shotgun_spread": 40.0, "shotgun_range": 180.0, "mp_mode": "timed_random", "mp_rate": 0.0, "mp_interval": 3.0, "mp_random_range": (5.0, 25.0)},
    49: {"skill_token": "blood_ritual", "mp_mode": "passive", "mp_rate": 16.0},
    50: {"skill_token": "element_switch", "basic_damage_kind": "spell", "mp_mode": "passive", "mp_rate": 12.0},
    51: {"skill_token": "mimic", "basic_damage_kind": "spell", "mp_mode": "passive", "mp_rate": 33.0},
    52: {"skill_token": "grave_swamp", "mp_mode": "death_count", "mp_rate": 40.0, "radius_scale": 1.12},
    53: {"skill_token": "eagle_eye", "mp_mode": "stationary", "mp_rate": 25.0, "attack_range": 420.0},
    54: {"skill_token": "joker_box", "mp_mode": "passive", "mp_rate": 5.0},
    55: {"skill_token": "mortar_barrage", "attack_aoe_radius": 20.0, "mp_mode": "damage_dealt_scaled", "mp_rate": 0.5},
    56: {"skill_token": "fate_link", "basic_damage_kind": "spell", "basic_beam_interval": 0.5, "attack_range": 280.0, "mp_mode": "passive", "mp_rate": 8.0},
    57: {"skill_token": "dice_roll", "attack_random_values": [5, 20, 50, 100], "mp_mode": "attack_count", "mp_rate": 20.0},
    58: {"skill_token": "black_hole", "basic_damage_kind": "true", "mp_mode": "passive", "mp_rate": 12.0},
    59: {"skill_token": "arrow_rain", "mp_mode": "distance_scaled", "mp_rate": 0.75},
    60: {"skill_token": "stone_skin", "attack_stun_duration": 0.12, "mp_mode": "damage_taken_scaled", "mp_rate": 1.0, "radius_scale": 1.24},
    61: {"skill_token": "swallow_return", "mp_mode": "attack_count", "mp_rate": 25.0},
    62: {"skill_token": "frost_burst", "basic_damage_kind": "spell", "attack_status": ("cold", 0.1), "mp_mode": "passive", "mp_rate": 8.0},
    63: {"skill_token": "guillotine", "mp_mode": "damage_dealt_scaled", "mp_rate": 1.5, "radius_scale": 1.1},
    64: {"skill_token": "deep_sleep", "basic_damage_kind": "spell", "attack_status": ("sleep", 0.01), "mp_mode": "passive", "mp_rate": 10.0},
    65: {"skill_token": "drone", "mp_mode": "passive", "mp_rate": 20.0},
    66: {"skill_token": "blood_contract", "mp_mode": "damage_taken_scaled", "mp_rate": 1.5},
    67: {"skill_token": "one_inch_punch", "mp_mode": "attack_count", "mp_rate": 20.0},
    68: {"skill_token": "web_bind", "basic_damage_kind": "spell", "attack_status": ("poison", 0.2), "mp_mode": "passive", "mp_rate": 12.0},
    69: {"skill_token": "taunt_roar", "mp_mode": "damage_taken_scaled", "mp_rate": 0.8, "radius_scale": 1.18},
    70: {"skill_token": "monsoon", "basic_damage_kind": "spell", "mp_mode": "passive", "mp_rate": 8.0},
    71: {"skill_token": "arc_blade", "basic_damage_kind": "spell", "mp_mode": "attack_count", "mp_rate": 10.0},
    72: {"skill_token": "soul_feast", "basic_damage_kind": "true", "mp_mode": "damage_event_any", "mp_rate": 2.0},
    73: {"skill_token": "holy_pillar", "basic_damage_kind": "spell", "mp_mode": "passive", "mp_rate": 10.0},
    74: {"skill_token": "broadside", "mp_mode": "damage_dealt_scaled", "mp_rate": 1.2},
    75: {"skill_token": "gravity_field", "basic_damage_kind": "spell", "beam_basic": True, "attack_range": 9999.0, "mp_mode": "passive", "mp_rate": 8.0},
    76: {"skill_token": "flying_swords", "mp_mode": "passive", "mp_rate": 10.0},
    77: {"skill_token": "shadow_step", "attack_repeat": 2, "mp_mode": "distance_scaled", "mp_rate": 0.5},
    78: {"skill_token": "hell_charge", "basic_damage_kind": "spell", "attack_status": ("hell_burn", 0.2), "mp_mode": "damage_taken_scaled", "mp_rate": 1.2},
    79: {"skill_token": "bullet_storm", "attack_repeat": 2, "mp_mode": "attack_count", "mp_rate": 10.0},
    80: {"skill_token": "time_stop", "mp_mode": "damage_dealt_scaled", "mp_rate": 2.0},
    81: {"skill_token": "matrix_collapse", "basic_damage_kind": "spell", "mp_mode": "passive", "mp_rate": 10.0, "radius_scale": 1.08},
    82: {"skill_token": "rend", "mp_mode": "passive", "mp_rate": 20.0},
    83: {"skill_token": "aurora_wall", "basic_damage_kind": "spell", "mp_mode": "passive", "mp_rate": 12.0},
    84: {"skill_token": "swarm_storm", "basic_damage_kind": "spell", "mp_mode": "damage_taken_scaled", "mp_rate": 1.5},
    85: {"skill_token": "sword_dash", "mp_mode": "damage_dealt_scaled", "mp_rate": 2.0},
    86: {"skill_token": "chain_net", "mp_mode": "passive", "mp_rate": 8.0},
    87: {"skill_token": "glacier_shock", "basic_damage_kind": "spell", "mp_mode": "damage_taken_scaled", "mp_rate": 0.8, "radius_scale": 1.22},
    88: {"skill_token": "powder_blast", "mp_mode": "passive", "mp_rate": 12.0, "radius_scale": 1.16},
    89: {"skill_token": "infrasound", "basic_damage_kind": "spell", "mp_mode": "damage_dealt_scaled", "mp_rate": 1.5},
    90: {"skill_token": "throw_arsenal", "mp_mode": "weapon_pickup", "mp_rate": 50.0},
    93: {"skill_token": "twin_mirror_pulse", "color": (244, 244, 244), "attack_range": 320.0, "projectile_speed": 430.0},
    99: {"skill_token": "phoenix_wrath", "basic_damage_kind": "spell", "attack_interval": 0.5},
    100: {"skill_token": "xuanwu_bulwark", "attack_interval": 0.6},
    101: {"skill_token": "tiger_roar", "mp_mode": "death_count", "mp_rate": 50.0, "attack_interval": 1.8},
    102: {"skill_token": "dragon_sweep", "mp_mode": "death_count", "mp_rate": 25.0, "attack_interval": 1.0},
}


def slugify_name(name):
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "role"


def parse_header(header):
    match = re.match(r"(\d+)\.\s*([^\(\n]+?)(?:\s*\(([^)]+)\))?\s*$", header)
    if not match:
        raise ValueError(f"Unable to parse role header: {header}")
    return int(match.group(1)), match.group(2).strip(), (match.group(3) or "").strip()


def parse_body_line(prefix, lines):
    for line in lines:
        if prefix in line:
            return line.split("：", 1)[1].strip()
    return ""


def parse_skill_lines(lines):
    skill_lines = []
    capture = False
    for line in lines:
        if "技能描述" in line:
            capture = True
            _, remainder = line.split("：", 1)
            if remainder.strip():
                skill_lines.append(remainder.strip())
            continue
        if capture:
            skill_lines.append(line.lstrip("- ").strip())
    return skill_lines


def parse_attack_profile(text):
    damage_match = re.search(r"伤害\s*([0-9]+(?:\s*\*\s*[0-9]+)?)", text)
    damage = 10.0
    if damage_match:
        damage_text = damage_match.group(1).replace(" ", "")
        if "*" in damage_text:
            left, _right = damage_text.split("*", 1)
            damage = float(left)
        else:
            damage = float(damage_text)
    attack_type = "melee" if "近战" in text else "ranged"
    interval = 0.85
    for label, value in ATTACK_SPEED_INTERVALS.items():
        if label in text:
            interval = value
            break
    attack_range = 44.0 if attack_type == "melee" else 285.0
    if "超远程" in text:
        attack_range = 420.0
    elif "远程" in text and "扇形" in text:
        attack_range = 210.0
    elif attack_type == "ranged" and "无限长" in text:
        attack_range = 9999.0
    elif attack_type == "ranged" and "慢" in text:
        attack_range = 300.0
    elif attack_type == "ranged" and "快" in text:
        attack_range = 275.0
    return damage, attack_type, interval, attack_range


def parse_mp_profile(text):
    count_match = re.search(r"每受到([0-9.]+)次伤害充能([0-9.]+)%", text)
    if count_match:
        count = max(1.0, float(count_match.group(1)))
        amount = float(count_match.group(2))
        return "damage_event_any", amount / count
    if "随时间" in text:
        every_match = re.search(r"每([0-9.]+)秒充能([0-9.]+)%", text)
        if every_match:
            seconds = float(every_match.group(1))
            amount = float(every_match.group(2))
            return "passive", amount / max(0.1, seconds)
        return "passive", 10.0
    if "受到伤害" in text:
        per_match = re.search(r"每受([0-9.]+)点伤害充能([0-9.]+)%", text)
        if per_match:
            damage = float(per_match.group(1))
            amount = float(per_match.group(2))
            return "damage_taken_scaled", amount / max(1.0, damage)
        return "damage_taken_scaled", 1.0
    if "造成伤害" in text:
        per_match = re.search(r"每造成([0-9.]+)点?伤害充能([0-9.]+)%", text)
        if per_match:
            damage = float(per_match.group(1))
            amount = float(per_match.group(2))
            return "damage_dealt_scaled", amount / max(1.0, damage)
        return "damage_dealt_scaled", 1.0
    if "移动" in text:
        per_match = re.search(r"每移动([0-9.]+)距离充能([0-9.]+)%", text)
        if per_match:
            distance = float(per_match.group(1))
            amount = float(per_match.group(2))
            return "distance_scaled", amount / max(1.0, distance)
        return "distance_scaled", 0.5
    if "每次普攻充能" in text or "每次攻击" in text:
        amount_match = re.search(r"充能([0-9.]+)%", text)
        return "attack_count", float(amount_match.group(1)) if amount_match else 15.0
    if "静止" in text:
        return "stationary", 25.0
    if "随机充能" in text:
        return "timed_random", 0.0
    if "角色阵亡" in text:
        amount_match = re.search(r"充能([0-9.]+)%", text)
        return "death_count", float(amount_match.group(1)) if amount_match else 50.0
    if "角色受伤" in text:
        return "damage_event_any", 2.0
    if "拾取武器" in text:
        return "weapon_pickup", 50.0
    return "passive", 10.0


def parse_skill_block(text):
    skill_names = re.findall(r"\*\*([^*]+)\*\*", text)
    skill_name = skill_names[-1].strip() if skill_names else "技能"
    description = re.sub(r"\*\*([^*]+)\*\*：?", r"\1：", text).strip()
    description = re.sub(r"^\-\s*", "", description)
    return skill_name, description


def load_design_roles(doc_path):
    text = Path(doc_path).read_text(encoding="utf-8")
    blocks = []
    current_header = None
    current_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            if current_header:
                blocks.append((current_header, current_lines))
            current_header = line[4:].strip()
            current_lines = []
        elif current_header:
            current_lines.append(line)
    if current_header:
        blocks.append((current_header, current_lines))

    job_defs = {}
    character_data = {}
    localization = {}
    metadata = {}
    for header, lines in blocks:
        role_num, role_cn_name, role_en_name = parse_header(header)
        visual_text = parse_body_line("视觉设定", lines)
        stats_text = parse_body_line("基础属性", lines)
        attack_text = parse_body_line("普攻设定", lines)
        mp_text = parse_body_line("充能方式", lines)
        skill_lines = parse_skill_lines(lines)
        skill_text = "\n".join(skill_lines)
        skill_name, skill_description = parse_skill_block(skill_text)

        stats_match = re.search(
            r"HP\s*([0-9.]+)\s*\|\s*物理抗性\s*([0-9.]+)\s*\|\s*法术抗性\s*([0-9.]+)\s*\|\s*移速\s*([0-9.]+)",
            stats_text,
        )
        if not stats_match:
            continue
        damage, attack_type, attack_interval, attack_range = parse_attack_profile(attack_text)
        mp_mode, mp_rate = parse_mp_profile(mp_text)
        role_key = f"DesignRole{role_num}_{slugify_name(role_en_name or role_cn_name)}"
        visual_shape = VISUAL_SHAPE_MAP.get(visual_text.split("/", 1)[0].strip(), "circle")
        color_key = visual_text.split("/", 1)[1].strip() if "/" in visual_text else visual_text.strip()
        color = COLOR_MAP.get(color_key, (180, 180, 180))
        override = ROLE_CONFIG_OVERRIDES.get(role_num, {})
        physical_resistance = float(stats_match.group(2))
        spell_resistance = float(stats_match.group(3))
        move_speed = float(stats_match.group(4)) * 100.0
        config = {
            "shape": override.get("shape", visual_shape),
            "color": override.get("color", color),
            "max_hp": float(stats_match.group(1)),
            "mp_mode": override.get("mp_mode", mp_mode),
            "mp_rate": override.get("mp_rate", mp_rate),
            "attack_type": override.get("attack_type", attack_type),
            "attack_damage": override.get("attack_damage", damage),
            "attack_range": override.get("attack_range", attack_range),
            "attack_interval": override.get("attack_interval", attack_interval),
            "projectile_speed": override.get("projectile_speed", 310.0 if attack_type == "ranged" else 285.0),
            "move_speed": override.get("move_speed", move_speed),
            "skill_id": f"design_{role_num}",
            "physical_resistance": physical_resistance,
            "spell_resistance": spell_resistance,
            "use_design_attack_speed": True,
            "use_design_attack_damage": True,
        }
        for key, value in override.items():
            if key not in config:
                config[key] = value

        job_defs[role_key] = config
        character_data[role_key] = {
            "name": role_en_name or role_cn_name,
            "shape": config["shape"],
            "color": config["color"],
            "max_hp": config["max_hp"],
            "move_speed": config["move_speed"],
            "attack_type": config["attack_type"],
            "attack_range": config["attack_range"],
            "physical_resistance": physical_resistance,
            "spell_resistance": spell_resistance,
            "mp_charge_style": mp_text,
            "skill_name": skill_name,
            "skill_description": skill_description,
        }
        localization[role_key] = {
            "name": role_cn_name,
            "mp_charge_style": mp_text,
            "skill_name": skill_name,
            "skill_description": skill_description,
        }
        metadata[role_key] = {
            "role_num": role_num,
            "role_cn_name": role_cn_name,
            "role_en_name": role_en_name,
            "visual_text": visual_text,
            "attack_text": attack_text,
            "mp_text": mp_text,
            "skill_name": skill_name,
            "skill_description": skill_description,
            "basic_damage_kind": override.get("basic_damage_kind", "physical"),
            "skill_token": override.get("skill_token", f"design_{role_num}"),
        }
        if "mp_interval" in override:
            metadata[role_key]["mp_interval"] = override["mp_interval"]
        if "mp_random_range" in override:
            metadata[role_key]["mp_random_range"] = override["mp_random_range"]
    return job_defs, character_data, localization, metadata
