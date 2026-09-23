# 圆环斗场 · 会话交接上下文（SESSION CONTEXT）

> 用法：新会话中把本文件路径发给新助手（"先读 C:\Users\76009\Desktop\myselfgame\circle\SESSION_CONTEXT.md"），即可无缝续接本项目工作。

## 一、项目概要
- **项目**：中文 Pygame 自动对战竞技场「圆环斗场」
- **路径**：`C:\Users\76009\Desktop\myselfgame\circle`
- **核心文件**：已模块化 —— 入口薄壳 `main.py`(21 行) + `game/` 包；设计角色源 `sheding/charactor.md`；生成器 `design_characters.py`
- **运行**：`python main.py`（Pygame 2.6.1 / Python 3.12）
- **角色数**：`len(JOB_DEFS)` = 120（40 基础 + 80 设计/特殊）
- **回归测试**：`python tests/regress.py`（headless 数据完整性 + 死斗模拟 + 渲染冒烟；默认 20 人 2400 帧）

## 二、剧情与沟通风格
- 助手 persona：**CETACEA_LOLI（鲸鱼娘）**，称用户"主人"，**只讲中文**，回复末尾带 🐋
- 用户风格：每个改动先「诊断 + 方案表」由主人多选（推荐组合标注 ✅）；会追加自定义需求；攒批 commit

## 三、游戏模式
- **死斗战**（主菜单"死斗战"按钮）：大逃杀 20 人混战（原"开始战斗"，已改名；倍速键 1/2/4，Esc 暂停）
- **擂台赛**（主菜单"擂台模式"）：红蓝队团战 1~8 人，选人 → 战前布阵（红左蓝右拖拽摆位）→ 单挑；含再战/结算
- **图鉴 / 效果 / 胜率 / 设置 / 禁用角色 / 入场押注**（押注界面显示历史胜率）

## 四、数值与机制关键位置（已模块化到 game/ 包）
- `game/data.py`：`JOB_DEFS` / `CHARACTER_DATA` / `JOB_RESISTANCE_PROFILES`（设计角色由 md 解析，手写角色硬编码块）+ 图鉴/胜率访问 + 角色显示辅助
- `game/character.py`：`Character` 角色类（约 4650 行；底部 `from game.engine import *` 解 character↔engine 环）
- `game/engine.py`：战斗核心 —— 目标选择/特效实体/`cast_design_skill` 技能分派/`apply_design_hit_effects`/`fire_design_basic_attack`（顶部 `from game.character import Character`）
- `game/ui.py` / `game/loops.py` / `game/world.py`：界面绘制 / 流程循环 + main() / 刷怪·场景·状态
- `game/utils.py` / `game/drawing.py`：纯工具（颜色/几何/文本）/ 绘制辅助（形状图标/图鉴详情）
- `game/runtime.py`：跨模块共享可变全局（`_LIVE_GAME_STATE`/`_LIVE_SPEED_MULTIPLIER`/`_DISABLED_ROLE_KEYS`）
- `game/paths.py`：`PROJECT_ROOT` 项目根锚点（拆包后 `__file__` 已不可用于定位项目根）
- `ROLE_CONFIG_OVERRIDES`（design_characters.py）：`attack_interval/attack_damage/mp_mode/mp_rate/skill_token` 等覆盖
- 攻速档位（design_characters.py `ATTACK_SPEED_INTERVALS`）：极快 0.5 / 很快 0.75 / 中速 1.5 / 快 1.0 / 慢 2.0 / 很慢 3.0 / 极慢 4.0（注意匹配顺序，长词优先）
- **防线铁律**：凡遍历 `get_targetables()` 且访问 `design_*` 属性，必须 `isinstance(x, Character)` 过滤或 getattr 兜底（get_targetables 含 Banner/图腾/召唤物等非角色）
- `create_game_state` 完整结构（banners/design_effects/projectiles/spawn_fx 等键）

## 五、最近已完成并 commit 的工作（git 历史尾部）
1. **main.py 模块化拆分**（15471 行 → 21 行薄壳 + game/ 包 12 文件）：阶段A data/runtime/paths → 阶段B engine → 阶段C ui/loops → 阶段D character/engine(战斗核心)/utils/drawing/world；character↔engine 用底部导入解环；新增 tests/regress.py 回归测试
2. **崩溃修复**：①冷锋枪(spear_thrust) clear_weapon 后访问 held_weapon→None（约1/4概率）；②get_targetables(含Banner/图腾/召唤物) 派生列表 7 处直接调 apply_* 角色专属方法→AttributeError（补 isinstance 守卫）
3. 擂台红蓝团战 1~8 人 + 战前布阵（拖拽摆位/半场限制/防重叠）
2. 新角色 104~121：幽灵祭司/炎舞姬/深渊观测者/夺心者/裂空者/魂缚剑匣(109 剑灵)/噬魂蝶母(110 蝶魄变身)/铁轨狂徒(111 列车V2)/战旗守护者(112)/灵魂药剂师(113)/指挥官(114)/虚空放逐者(115 放逐)/雀影(116 腐血)/雷切剑豪(117 三段雷斩)/涓灵(118 涓流)/血裔狂徒(119 吸血盛宴)/白狐武士(120 藏势反击)
3. 大量平衡调整：巨石魔削弱、攻速档位重定义、行刑官/幻影枪骑/游侠优化、凤凰/圣骑士/水翁平衡
4. 战斗界面优化：侧边栏滚动/三 tab/状态折叠、伤害数字合并、header 精简、跟随面板、伤害开关
5. 特效增强：弧月斩残影、暴击金字、拖尾分级、命中分级震屏、大招聚气、治疗飘字、击杀闪耀、放逐特效
6. 崩溃修复：bet_loop 缺参、Summon design_* 属性、larva attack_interval 等（归档 bug/finish/）

## 六、测试惯例（重要）
- 临时脚本 `_xxx_check.py`：设 `SDL_VIDEODRIVER=dummy`、`PYGAME_HIDE_SUPPORT_PROMPT=1`、`sys.stdout.reconfigure(encoding="utf-8")`、`pygame.font.init()`，离屏渲染 + 断言，跑完删除
- 陷阱：开场定格（`spawn_fx_timer=0` 或 `elapsed_time>1.5` 才测战斗逻辑）；远程弹丸需飞行模拟命中；物/法抗折伤断言要用真伤或比值；角色 key 需查 `JOB_DEFS`（如手写角色 DesignRole47_role 等）
- 新角色落地标准流程：md 条目 + design_characters override + main.py（常量/JOB_DEFS/属性/技能分支/update/绘制/describe）+ `_xxx_check.py` 测试 + commit

## 七、git 仓库
- 身份：`Wutiafur <760093@qq.com>`；`.gitignore` 已含 `__pycache__/`、`*.pyc`、`bug/crash_*.txt`、`settings.json`、`_scan.py` 等
- 常做小步 commit，消息中文概括改动

## 八、待办/可继续方向
- 低胜率角色优化候选：混沌魔/极光（7 场 0 胜）、刺客/巧匠基础角色等（win_rate_stats.json 可查）
- 方案已提未做：军乐司令（擂台增益 A 方案）、座敷童子（已有草稿）、龙珏（被拒，勿重新启用）
- 可选：README 补 104-121 记录、模块化拆分、云备份

## 九、当前 git 状态
- 最近 commit（模块化拆分完成）：`490d763`（阶段D 细拆 engine.py）→ 后续若有未提交改动以实际 git log 为准