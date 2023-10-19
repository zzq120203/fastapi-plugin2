# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : router.py
# @Time     : 2023/10/12 9:48
from typing import Type, Tuple, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import SecretStr
from starlette import status

from fastapi_plugin.common.pydantic import create_model_by_model
from fastapi_plugin.crud import SQLAlchemyCrud, SQLModel
from fastapi_plugin.crud.router import CrudRouter
from fastapi_plugin.crud.sqlmodel import select
from fastapi_plugin.user import Auth
from fastapi_plugin.user.auth import UserOAuth2PasswordRequestForm, UserModelT
from fastapi_plugin.user.models import User
from fastapi_plugin.user.schemas import UserLoginOut
from fastapi_plugin.user.transport.bearer import BearerTransport


class AuthRouter(CrudRouter):
    schema_user_info: Type[SQLModel] = None
    schema_user_login_out: Type[UserLoginOut] = UserLoginOut
    router_prefix = "/auth"

    def __init__(self, auth: Auth):
        self.auth = auth
        assert self.auth, "auth is None"

        self.schema_user_info = self.schema_user_info or create_model_by_model(
            User, "UserInfo", exclude={"password"}
        )
        super().__init__(SQLAlchemyCrud(User, auth.db))

        self.auth.transport = self.auth.transport or BearerTransport(f'{self.router_prefix}/login')

    @property
    def router(cls):
        router = APIRouter(prefix=f"{cls.router_prefix}")
        get_current_token = cls.auth.current_token()

        @router.post(
            "/login",
        )
        async def login(
                request: Request,
                credentials: UserOAuth2PasswordRequestForm = Depends(),
        ):
            user = await cls.authenticate(credentials)
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LOGIN_BAD_CREDENTIALS",
                )
            response = await cls.auth.backend.login(user.model_dump())
            return response

        @router.post(
            "/logout",
        )
        async def logout(
                token: Tuple[User, str] = Depends(get_current_token),
        ):
            return await cls.auth.backend.logout(token)

        return router

    async def authenticate_user(self, username: str, password: Union[str, SecretStr]) -> Optional[UserModelT]:
        user = await self.crud.db.async_scalar(select(self.crud.Model).where(self.crud.Model.username == username))
        if user:
            pwd = password.get_secret_value() if isinstance(password, SecretStr) else password
            pwd2 = user.password.get_secret_value() if isinstance(user.password, SecretStr) else user.password
            if self.auth.pwd_context.verify(pwd, pwd2):  # 用户存在 且 密码验证通过
                return user
        return None

    async def authenticate(
            self, credentials: OAuth2PasswordRequestForm
    ) -> Optional[User]:
        return await self.authenticate_user(credentials.username, credentials.password)
