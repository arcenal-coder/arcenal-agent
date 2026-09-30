"""Fondations typées communes aux contrats ARC Core."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


Permission = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*\.[a-z][a-z0-9_-]*$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
