# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : jwt.py
# @Time     : 2023/10/12 9:48
from datetime import datetime, timedelta
from typing import Optional, Union

from jose import JWTError, jwt

from .base import BaseTokenStore, TokenDataSchemaT


class JwtTokenStore(BaseTokenStore):
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        expire_seconds: Optional[int] = 60 * 60 * 24 * 3,
        TokenDataSchema: TokenDataSchemaT = None,
    ):
        super().__init__(expire_seconds, TokenDataSchema)
        self.secret_key = secret_key
        self.algorithm = algorithm

    async def read_token(self, token: str) -> Optional[TokenDataSchemaT]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=self.algorithm)
            return self.TokenDataSchema.model_validate(payload)
        except JWTError:
            return None

    async def write_token(self, token_data: Union[TokenDataSchemaT, dict]) -> str:
        obj = self.TokenDataSchema.model_validate(token_data) if isinstance(token_data, dict) else token_data
        data = obj.dict()
        expire = datetime.now() + timedelta(seconds=self.expire_seconds)
        data.update({"exp": expire})
        return jwt.encode(data, self.secret_key, algorithm=self.algorithm)

    async def destroy_token(self, token: str) -> None:
        raise NotImplementedError
