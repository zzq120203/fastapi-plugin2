# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : auth.py
# @Time     : 2023/10/12 9:48
from typing import Callable, Optional, Tuple, cast, Union, Type, TypeVar, Annotated, Sequence

from fastapi import Depends, HTTPException, status, Form
from fastapi.requests import Request
from fastapi.security import SecurityScopes, OAuth2PasswordRequestForm
from passlib.context import CryptContext

from fastapi_plugin.crud.sqlalchemy_database import Database, AsyncDatabase
from fastapi_plugin.crud.sqlmodel import Session, select
from fastapi_plugin.user.backend import AuthBackend
from fastapi_plugin.user.models import User, Role, UserRoleLink, BaseUser
from fastapi_plugin.user.strategy.base import BaseTokenStore, TokenDataSchemaT
from fastapi_plugin.user.strategy.db import DbTokenStore
from fastapi_plugin.user.transport import Transport

UserModelT = TypeVar("UserModelT", bound=BaseUser)


class _AuthInit:
    db: Union[AsyncDatabase, Database] = None

    def __init__(
            self,
            db: Union[AsyncDatabase, Database],
            user_model: Type[UserModelT] = User,
            pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto"),
    ):
        self.db = db
        self.user_model = user_model
        self.pwd_context = pwd_context

    def _create_role_user_sync(self, session: Session, role_key: str = "admin") -> User:
        # create admin role
        role = session.scalar(select(Role).where(Role.key == role_key))
        if not role:
            role = Role(key=role_key, name=f"{role_key} role")
            session.add(role)
            session.flush()

        # create admin user
        user = session.scalar(
            select(self.user_model)
            .join(UserRoleLink, UserRoleLink.user_id == self.user_model.id)
            .where(UserRoleLink.role_id == role.id)
        )
        if not user:
            user = self.user_model(
                username=role_key,
                password=self.pwd_context.hash(role_key),
                email=f"{role_key}@amis.work",  # type:ignore
                roles=[role],
            )
            session.add(user)
            session.flush()
        return user

    async def create_role_user(self, role_key: str = "admin", commit: bool = True) -> User:
        user = await self.db.async_run_sync(self._create_role_user_sync, role_key)
        if commit:
            await self.db.async_commit()
        return user


class Auth(_AuthInit):

    def __init__(
            self,
            db: Union[AsyncDatabase, Database],
            strategy: BaseTokenStore[TokenDataSchemaT] = None,
            transport: Transport = None,
            user_model: Type[UserModelT] = User,
            pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto"),
    ):
        super().__init__(db, user_model, pwd_context)
        self.transport = transport
        self.strategy = strategy or DbTokenStore(db)
        self.backend = AuthBackend(self.transport, self.strategy)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key == 'transport' and value:
            self.backend.transport = value

    def current_token(
            self,
            roles: Union[str, Sequence[str]] = None,
            groups: Union[str, Sequence[str]] = None,
            permissions: Union[str, Sequence[str]] = None,
    ):
        async def current_token_dependency(
                request: Request,
                security_scopes: SecurityScopes,
                token=Depends(cast(Callable, self.transport.scheme)),
        ):
            _, token = await self._authenticate(
                request=request,
                security_scopes=security_scopes,
                token=token,
                roles=roles,
                groups=groups,
                permissions=permissions,
            )
            return token

        return current_token_dependency

    def current_user(
            self,
            roles: Union[str, Sequence[str]] = None,
            groups: Union[str, Sequence[str]] = None,
            permissions: Union[str, Sequence[str]] = None,
    ):
        async def current_user_dependency(
                request: Request,
                security_scopes: SecurityScopes,
                token=Depends(cast(Callable, self.transport.scheme)),
        ):
            user, _ = await self._authenticate(
                request=request,
                security_scopes=security_scopes,
                token=token,
                roles=roles,
                groups=groups,
                permissions=permissions,
            )
            return user

        return current_user_dependency

    async def _authenticate(
            self,
            request: Request,
            security_scopes: SecurityScopes,
            token: Optional[str],
            roles: Union[str, Sequence[str]] = None,
            groups: Union[str, Sequence[str]] = None,
            permissions: Union[str, Sequence[str]] = None,
    ) -> Tuple[Optional[TokenDataSchemaT], Optional[str]]:
        async def has_requires(_user: UserModelT) -> bool:
            return _user and await self.db.async_run_sync(_user.has_requires, roles=roles, groups=groups,
                                                          permissions=permissions)

        user: Optional[TokenDataSchemaT] = None
        if token is not None:
            user = await self.strategy.read_token(token)

        status_code = status.HTTP_401_UNAUTHORIZED
        if user:
            if not await has_requires(user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions",
                )

            if not user.is_active:
                status_code = status.HTTP_401_UNAUTHORIZED
                user = None
        if not user:
            raise HTTPException(status_code=status_code)
        request.scope["user"] = user
        return user, token


class UserOAuth2PasswordRequestForm(OAuth2PasswordRequestForm):
    def __init__(self, *, username: Annotated[str, Form()], password: Annotated[str, Form()]):
        super().__init__(username=username, password=password)
