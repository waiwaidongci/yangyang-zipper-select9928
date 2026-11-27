from pydantic import BaseModel, ConfigDict, Field, constr
from typing import Annotated


class DatasetImport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Annotated[str, constr(strip_whitespace=True, min_length=2, max_length=140)]
    csv: str = Field(min_length=5, max_length=600_000)


class DatasetInfo(BaseModel):
    id: int
    name: str
    checksum: str
    count: int
