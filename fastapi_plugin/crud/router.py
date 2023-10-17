# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : router.py
# @Time     : 2023/10/12 9:48
from typing import List, Annotated, Type

from fastapi import APIRouter, Body, Path, Depends
from fastapi.requests import Request
from pydantic import BaseModel

from .parser import RequiredPrimaryKeyListDepend, Paginator, Selector
from .utils import sqlmodel_to_selector

try:
    from ._sqlalchemy import SQLAlchemyCrud as _SQLAlchemyCrud
except ImportError:
    _SQLAlchemyCrud = object
from fastapi_plugin.responses import GenericData, DataResponse


class CrudRouter:

    def __init__(
            self,
            crud: _SQLAlchemyCrud,
    ):
        self.crud = crud

        self.Selector: Type[Selector] = sqlmodel_to_selector(crud.Model)

    def create_object_router(
            cls,
    ) -> APIRouter:
        class ItemsData(BaseModel):
            items: List[cls.crud.ReadModel]
            total: int

        router = APIRouter(prefix=f"/{cls.crud.name}", tags=[cls.crud.name])

        @router.post(
            "",
            response_model=GenericData[ItemsData],
            name=f'create {cls.crud.name}',
        )
        async def __create_object(
                request: Request,
                objs: List[cls.crud.CreateModel] = Body(...),
        ):
            objs: List[cls.crud.ReadModel] = await cls.crud.create_items(items=objs, request=request)
            return DataResponse(data=ItemsData(
                items=objs,
                total=len(objs)
            ))

        return router

    def read_object_router(
            cls,
    ) -> APIRouter:
        class ItemsData(BaseModel):
            items: List[cls.crud.ReadModel]
            total: int

        router = APIRouter(prefix=f"/{cls.crud.name}", tags=[cls.crud.name])

        @router.get(
            "",
            response_model=GenericData[ItemsData],
            name=f'get {cls.crud.name} all',
        )
        async def __get_objects(
                request: Request,
                selector: Annotated[cls.Selector, Depends(cls.Selector())],
                paginator: Annotated[Paginator, Depends(Paginator())]
        ):
            objs, total = await cls.crud.read_items(request=request, selector=selector, paginator=paginator)
            return DataResponse(data={
                "items": objs,
                "total": total
            })

        @router.get(
            f"/{{{cls.crud.pk_name}}}",
            response_model=GenericData[cls.crud.ReadModel],
            name=f'get {cls.crud.name} by primary_key({cls.crud.pk_name})'
        )
        async def __get_object(
                request: Request,
                primary_key: cls.crud.pk_field.annotation = Path(..., alias=cls.crud.pk_name)
        ):
            obj = await cls.crud.read_item_by_primary_key(primary_key=primary_key, request=request)
            return DataResponse(data=obj)

        return router

    def update_object_router(
            cls,
    ) -> APIRouter:

        router = APIRouter(prefix=f"/{cls.crud.name}", tags=[cls.crud.name])

        @router.patch(
            f"/{{{cls.crud.pk_name}}}",
            response_model=GenericData[cls.crud.ReadModel],
            name=f'update {cls.crud.name} by primary_key({cls.crud.pk_name})',
        )
        async def __update_object(
                request: Request,
                primary_key: cls.crud.pk_field.annotation = Path(..., alias=cls.crud.pk_name),
                obj_update: cls.crud.UpdateModel = Body(...),
        ):
            obj = await cls.crud.update_items(primary_keys=[primary_key], item=obj_update, request=request)
            return DataResponse(data=obj)

        @router.patch(
            "",
            response_model=GenericData[cls.crud.ReadModel],
            name=f'update {cls.crud.name}s by primary_keys({cls.crud.pk_name})',
        )
        async def __update_object(
                request: Request,
                primary_key: RequiredPrimaryKeyListDepend,
                obj_update: cls.crud.UpdateModel = Body(...),
        ):
            obj = await cls.crud.update_items(primary_key=primary_key, item=obj_update, request=request)
            return DataResponse(data=obj)

        return router

    def delete_object_router(
            cls,
    ) -> APIRouter:

        router = APIRouter(prefix=f"/{cls.crud.name}", tags=[cls.crud.name])

        @router.delete(
            f"/{{{cls.crud.pk_name}}}",
            response_model=GenericData[cls.crud.ReadModel],
            name=f'delete {cls.crud.name} by primary_key({cls.crud.pk_name})',
        )
        async def __delete_object(
                request: Request,
                primary_key: cls.crud.pk_field.annotation = Path(..., alias=cls.crud.pk_name),
        ):
            objs = await cls.crud.delete_items(request, primary_key=[primary_key])
            return DataResponse(data=objs)

        @router.delete(
            "",
            response_model=GenericData[cls.crud.ReadModel],
            name=f'delete {cls.crud.name}s by primary_keys({cls.crud.pk_name})',
        )
        async def __delete_object(
                request: Request,
                primary_key: RequiredPrimaryKeyListDepend,
        ):
            objs = await cls.crud.delete_items(request, primary_key=primary_key)
            return DataResponse(data=objs)

        return router
