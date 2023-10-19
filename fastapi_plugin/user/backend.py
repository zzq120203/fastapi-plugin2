# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : backend.py
# @Time     : 2023/10/12 9:48
from typing import Generic, TypeVar

from fastapi import Response, status

from fastapi_plugin.user.strategy.base import BaseTokenStore, BaseTokenStoreNotSupportedError, TokenDataSchemaT
from fastapi_plugin.user.schemas import BaseTokenData
from fastapi_plugin.user.transport.base import Transport, TransportLogoutNotSupportedError


class AuthBackend(Generic[TokenDataSchemaT]):
    """
    Combination of an authentication transport and strategy.

    Together, they provide a full authentication method logic.

    :param strategy: Name of the backend.
    :param transport: Authentication transport instance.
    an authentication strategy instance.
    """

    transport: Transport

    def __init__(
        self,
        transport: Transport,
        strategy: BaseTokenStore[TokenDataSchemaT],
    ):
        self.transport = transport
        self.strategy = strategy

    async def login(
        self, token_data: BaseTokenData
    ) -> Response:
        token = await self.strategy.write_token(token_data)
        return await self.transport.get_login_response(token)

    async def logout(
        self, token: str
    ) -> Response:
        try:
            await self.strategy.destroy_token(token)
        except BaseTokenStoreNotSupportedError:
            pass

        try:
            response = await self.transport.get_logout_response()
        except TransportLogoutNotSupportedError:
            response = Response(status_code=status.HTTP_204_NO_CONTENT)

        return response
