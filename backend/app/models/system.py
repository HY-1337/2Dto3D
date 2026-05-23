from pydantic import BaseModel


class SystemCheck(BaseModel):
    python: bool
    gpu: bool
    cuda: bool
    local_model: bool
    bambu_studio: bool
    bambu_path: str | None = None

