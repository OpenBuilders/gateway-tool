from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from core.dtos.base import BaseThresholdFilterDTO


class BaseFDO(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class BaseExceptionFDO(BaseModel):
    detail: str


class BaseThresholdFilterPO(BaseThresholdFilterDTO):
    ...
