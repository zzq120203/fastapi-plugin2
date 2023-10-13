# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : responses.py
# @Time     : 2023/7/31 13:14
from typing import Any, Dict, Optional, Generic, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

Data = TypeVar('Data')


class GenericData(BaseModel, Generic[Data]):
    request_id: Optional[str] = None
    code: int = 200
    message: Optional[str] = ''
    data: Optional[Data] = None


class DataResponse(JSONResponse):

    def __init__(self, content=None, *, status_code: int = 200,
                 headers: Optional[dict] = None,
                 media_type: Optional[str] = None,
                 background=None, **kwargs):
        if content is None:
            content = kwargs or None
        if content.get("code", None) is not None:
            status_code = content.get("code")
        self.exclude_none = True

        super().__init__(status_code=status_code, headers=headers, media_type=media_type, background=background,
                         content=content)

    def render(self, content: Any) -> bytes:
        if isinstance(content, Dict):
            content.update({"code": self.status_code})
            return GenericData(**content).model_dump_json(
                exclude_none=self.exclude_none,
                by_alias=True,
            ).encode("utf-8")
        elif isinstance(content, GenericData):
            content.code = self.status_code
            return content.model_dump_json(
                exclude_none=self.exclude_none,
                by_alias=True,
            ).encode("utf-8")
        else:
            return GenericData(code=self.status_code, data=content).model_dump_json(
                exclude_none=self.exclude_none,
                by_alias=True,
            ).encode('utf-8')
