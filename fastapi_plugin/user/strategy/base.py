# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : base.py
# @Time     : 2023/10/12 9:48
from typing import Generic, Optional, TypeVar, Union

from ..models import User

TokenDataSchemaT = TypeVar("TokenDataSchemaT", bound=User)


class BaseTokenStoreNotSupportedError(Exception):
    pass


class BaseTokenStore(Generic[TokenDataSchemaT]):
    TokenDataSchema: TokenDataSchemaT

    def __init__(self, expire_seconds: Optional[int] = 60 * 60 * 24 * 3,
                 TokenDataSchema: TokenDataSchemaT = None) -> None:
        self.TokenDataSchema = TokenDataSchema or User
        self.expire_seconds = expire_seconds

    async def read_token(self, token: Optional[str]) -> Optional[TokenDataSchemaT]:
        raise NotImplementedError

    async def write_token(self, token_data: Union[TokenDataSchemaT, dict]) -> str:
        raise NotImplementedError

    async def destroy_token(self, token: str) -> None:
        raise NotImplementedError
