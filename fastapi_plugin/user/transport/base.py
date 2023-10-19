# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : base.py
# @Time     : 2023/10/12 9:48
from typing import Protocol

from fastapi import Response
from fastapi.security.base import SecurityBase

from fastapi_plugin.common.typing import OpenAPIResponseType


class TransportLogoutNotSupportedError(Exception):
    pass


class Transport(Protocol):
    scheme: SecurityBase

    async def get_login_response(self, token: str) -> Response:
        ...  # pragma: no cover

    async def get_logout_response(self) -> Response:
        ...  # pragma: no cover

    @staticmethod
    def get_openapi_login_responses_success() -> OpenAPIResponseType:
        """Return a dictionary to use for the openapi responses route parameter."""
        ...  # pragma: no cover

    @staticmethod
    def get_openapi_logout_responses_success() -> OpenAPIResponseType:
        """Return a dictionary to use for the openapi responses route parameter."""
        ...  # pragma: no cover
