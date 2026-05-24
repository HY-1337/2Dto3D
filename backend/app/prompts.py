"""
Prompt 工程 — 运行时强制「潮玩切题」。

无论用户输入什么，最终 prompt 都必须落在：
  设计师玩具 / 盲盒手办 / 可收藏 Q 版公仔 / 可 3D 打印的潮玩造型
"""

from __future__ import annotations

import re
from enum import Enum


class StylePreset(str, Enum):
    CHAOPLAY = "chaoplay"   # 盲盒/Q版 vinyl 潮玩（默认，比赛主推）
    PERLER = "perler"       # 拼豆风格潮玩（色块化、像素化公仔）
    MINIMAL = "minimal"     # 极简可打印潮玩（块面公仔）


# ── 切题核心锚点：所有风格都必须带上，不可关闭 ──────────────────────────
CHAOWAN_CORE = (
    "standalone 3D vinyl art toy figurine, game asset style collectible object, "
    "humanoid designer toy character with head torso arms and legs, "
    "Q-version chibi mascot figure, single isolated figurine, "
    "3D model render game asset, no background no base no stand"
)

CHAOWAN_SUFFIX = (
    "isolated asset floating in vacuum, die-cut sticker style with transparent-look background, "
    "alpha channel placeholder, orthographic projection, front t-pose view, "
    "standalone figurine object no studio backdrop, no base no stage, "
    "game asset render, high resolution texture, sharp clean edges, "
    "zero shadows, zero ground reflection, pure isolated essence, "
    "no frame, no border, no container, no background plane"
)

# 全局负向词：压制「泛化生图」倾向
GLOBAL_NEGATIVE = (
    "realistic photo, photorealistic, live action, real human person, portrait photography, "
    "landscape, scenery, architecture, interior design, poster, illustration only, concept art sheet, "
    "multiple characters, crowd, complex background, cluttered scene, "
    "anime screenshot, manga panel, game UI, "
    "flat 2d drawing without volume, sketch, line art only, "
    "non-humanoid object, vehicle, car, building, furniture, utensil, weapon only, "
    "pure animal without human traits, creature without human body plan, amorphous blob, "
    "robot that is not humanoid, abstract geometric shape without character form, "
    "missing limbs, missing head, missing torso, faceless figure, "
    "white frame, square border, square background, background box, solid block background, "
    "outline container, portrait frame, card background, "
    "shadows, floor shadow, ground shadow, drop shadow, cast shadow, "
    "floor, ground plane, stage, pedestal, base, platform, "
    "studio backdrop, photo background, environment scene, scenery background, "
    "text, caption, logo, watermark, signature, "
    "blurry, low quality, deformed, extra limbs, fused fingers"
)

# 用户输入若命中以下词，判定为跑题，直接拒绝
OFF_TOPIC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"风景|山水|海景|日落|星空|森林|草原|城市天际线|建筑外观|室内装修|房间设计", re.I), "风景/建筑类描述"),
    (re.compile(r"写实照片|真实照片|证件照|写真|人像摄影|自拍|模特", re.I), "写实人像/摄影类描述"),
    (re.compile(r"海报|banner|封面设计|宣传图|广告图|logo|标志设计|UI界面|网页", re.I), "平面设计/UI 类描述"),
    (re.compile(r"地图|图表|信息图|流程图|思维导图|表格", re.I), "信息图表类描述"),
    (re.compile(r"汽车|飞机|火车|轮船|坦克|枪|刀剑|武器|家具|桌子|椅子|沙发|灯具|建筑|房子|桥梁", re.I), "非人形物品/载具/武器/家具/建筑类描述"),
    (re.compile(r"^(一只|一条|一头)?\s*(猫|狗|鱼|鸟|马|老虎|狮子|兔子|蛇|龙|恐龙|鲨鱼|鲸鱼)$", re.I), "纯动物、未体现人形特征"),
    (re.compile(r"^\s*(画|生成|做)?\s*(一张|一幅)?\s*(图|照片|图片)\s*$", re.I), "过于空泛、未描述潮玩主体"),
    (re.compile(r"landscape|scenery|realistic photo|portrait photo|poster design|logo design|infographic", re.I), "off-topic English prompt"),
    (re.compile(r"\b(car|vehicle|airplane|tank|gun|weapon|furniture|building|bridge|house)\b", re.I), "off-topic non-humanoid object"),
    (re.compile(r"^\s*(a|an)?\s*(cat|dog|bird|fish|horse|tiger|lion|rabbit|snake|dragon)\s*$", re.I), "pure animal without humanoid traits"),
]

# 若用户已明确提到「玩具/公仔/手办/潮玩未/play-toy」等，则不再二次包装
TOY_SUBJECT_HINT = re.compile(
    r"潮玩|手办|公仔|玩偶|盲盒|figurine|figure|toy|collectible|designer toy|vinyl|mascot|chibi|"
    r"人形|人物|角色|卡通人物|小人|娃娃|动漫人物|Q版|character|person|humanoid|anthropomorphic|cartoon",
    re.I,
)


STYLE_TEMPLATES: dict[str, dict[str, str]] = {
    "chaoplay": {
        "style_anchor": (
            "POP MART style vinyl toy, cute cartoon character designer art toy, "
            "smooth matte vinyl material, oversized head small body chibi human ratio, "
            "clear human-like body with head torso arms and legs"
        ),
        "style_suffix": (
            "isolated collectible display figure, standing character pose, "
            "sharp clean edges, high resolution toy texture, zero background"
        ),
        "style_negative": (
            "realistic animal without human traits, realistic human photo, animal photography, "
            "plush doll fabric texture, action figure with visible joints, model kit parts, gunpla, "
            "non-humanoid robot, quadruped creature, packaging box, display case, base stand"
        ),
    },
    "perler": {
        "style_anchor": (
            "perler bead fuse bead humanoid art toy pattern, pixel-block cartoon character designer toy figurine, "
            "limited color palette perler bead style human-shaped collectible"
        ),
        "style_suffix": (
            "flat color blocks with clear bead grid edges, cute simplified humanoid toy silhouette with distinct body parts, "
            "perler bead craft aesthetic applied to a human-shaped cartoon designer toy figure, "
            "isolated floating asset, no canvas background"
        ),
        "style_negative": (
            "photorealistic, smooth gradient, too many colors, realistic texture, "
            "cross-stitch, embroidery, knitting, non-humanoid silhouette, animal shape, object shape, "
            "background canvas, craft mat, table surface, grid board"
        ),
    },
    "minimal": {
        "style_anchor": (
            "minimalist 3D printable humanoid designer toy figurine, low-poly cartoon character collectible toy, "
            "geometric simplified human-shaped art toy for 3D printing and digital human rigging, "
            "game asset style 3D model render, orthographic projection"
        ),
        "style_suffix": (
            "simple solid geometric humanoid volumes with clear head torso arms and legs, "
            "no hair strands, no thin wings, no overhangs, "
            "print-friendly humanoid toy design, blocky cute cartoon character figure, "
            "t-pose friendly stance, isolated asset floating in vacuum"
        ),
        "style_negative": (
            "highly detailed sculpt, thin wires, lace, fur texture, complex drapery, "
            "realistic anatomy, fine mesh details, non-humanoid shape, abstract blob, "
            "missing body parts, asymmetrical limbs, quadruped, serpentine form, "
            "print bed, support structures, raft, build plate"
        ),
    },
}


class OffTopicError(ValueError):
    """用户描述偏离「潮玩」赛道。"""


def validate_user_prompt(user_prompt: str) -> None:
    text = user_prompt.strip()
    if len(text) < 2:
        raise OffTopicError("请描述你想要的人形潮玩造型（有头、躯干、四肢），例如：「一个戴耳机的蓝色小猫公仔，人形站立姿态」")

    for pattern, reason in OFF_TOPIC_PATTERNS:
        if pattern.search(text):
            raise OffTopicError(
                f"输入疑似「{reason}」，与本项目「AI 人形潮玩设计/打印」主题不符。"
                f"请改为描述一个人形卡通潮玩公仔（有头、躯干、四肢），例如：「一个赛博朋克风格的人形机器人潮玩公仔，透明头盔，站立姿态」"
            )


def normalize_subject(user_prompt: str) -> str:
    """把用户描述强制包装成「人形潮玩公仔主体」。"""
    text = user_prompt.strip()
    if TOY_SUBJECT_HINT.search(text):
        return f"a humanoid cartoon designer toy character of {text}, with head torso arms and legs, standing pose"
    return f"a humanoid cartoon designer toy figurine of {text}, with clear human-like body proportions, head torso arms and legs, standing upright"


def build_prompt(
    user_prompt: str,
    style: StylePreset = StylePreset.CHAOPLAY,
    extra_suffix: str = "",
) -> dict[str, str | list[str]]:
    """
    组装最终 prompt。切题策略：
    1. 校验用户输入是否跑题
    2. 主体包装为 designer toy figurine
    3. 注入 CHAOWAN_CORE + 风格锚点 + CHAOWAN_SUFFIX（三层锁死）
    4. 负向词叠加 GLOBAL_NEGATIVE + 风格负向词
    """
    validate_user_prompt(user_prompt)

    template = STYLE_TEMPLATES[style.value]
    subject = normalize_subject(user_prompt)

    prompt_parts = [
        CHAOWAN_CORE,
        template["style_anchor"],
        subject,
        template["style_suffix"],
        CHAOWAN_SUFFIX,
        extra_suffix.strip(),
    ]
    prompt = ", ".join(p for p in prompt_parts if p)

    negative_parts = [GLOBAL_NEGATIVE, template["style_negative"]]
    negative_prompt = ", ".join(p for p in negative_parts if p)

    enforced_rules = [
        "强制人形潮玩锚点 (humanoid CHAOWAN_CORE)",
        f"风格锚点 ({style.value})",
        "主体包装为 humanoid cartoon designer toy figurine" if not TOY_SUBJECT_HINT.search(user_prompt) else "用户已含人形/玩具语义，补强人形结构描述",
        "全局反泛化负向词（含非人形过滤）",
    ]

    return {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "style": style.value,
        "user_prompt": user_prompt,
        "normalized_subject": subject,
        "enforced_rules": enforced_rules,
        "topic": "chaowan",
    }
