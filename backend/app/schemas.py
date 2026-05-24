from enum import Enum

from pydantic import BaseModel, Field


class StylePreset(str, Enum):
    chaoplay = "chaoplay"
    perler = "perler"
    minimal = "minimal"


class GenerateRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="潮玩主体描述，如：一只戴耳机的蓝色小猫公仔",
        examples=["一只戴耳机的蓝色小猫公仔", "赛博朋克机器人潮玩，透明头盔"],
    )
    style: StylePreset = Field(default=StylePreset.chaoplay, description="潮玩风格预设")
    width: int | None = Field(default=None, ge=256, le=2048)
    height: int | None = Field(default=None, ge=256, le=2048)
    extra_suffix: str = Field(default="", max_length=500, description="额外后缀（仍会在潮玩锚点内生效）")


class GenerateResponse(BaseModel):
    task_id: str
    image_url: str
    local_path: str
    prompt: str
    negative_prompt: str
    style: str
    provider: str
    topic: str = "chaowan"
    normalized_subject: str
    enforced_rules: list[str]


class HealthResponse(BaseModel):
    status: str
    provider: str
    topic: str = "chaowan"
