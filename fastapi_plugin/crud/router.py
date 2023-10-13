# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : router.py
# @Time     : 2023/10/12 9:48
from typing import List

from fastapi import APIRouter, Body, Path
from fastapi.requests import Request
from pydantic import BaseModel

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
        self.name = crud.name
        self.crud = crud

    def create_object_router(
            cls,
    ) -> APIRouter:
        class ItemsData(BaseModel):
            items: List[cls.crud.ReadModel]
            total: int

        router = APIRouter(prefix=f"/{cls.name}")

        @router.post(
            "",
            response_model=GenericData[ItemsData],
            name=f'create {cls.name}',
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

    def get_object_router(
            cls,
    ) -> APIRouter:
        class ItemsData(BaseModel):
            items: List[cls.crud.ReadModel]
            total: int

        router = APIRouter(
            prefix=f"/{cls.name}",
        )

        @router.get(
            "",
            response_model=GenericData[ItemsData],
            name=f'get {cls.name} all',
        )
        async def __get_objects(
                request: Request,
        ):
            objs = await cls.crud.read_items(request=request)
            return DataResponse(data={
                "items": objs,
                "total": len(objs)
            })

        @router.get(
            "/{primary_key}",
            response_model=GenericData[cls.crud.ReadModel],
            name=f'get {cls.name} by primary_key({cls.crud.pk_name})'
        )
        async def __get_object(
                request: Request,
                primary_key: cls.crud.pk.annotation = Path(..., alias=cls.crud.pk_name)
        ):
            obj = await cls.crud.read_item_by_primary_key(primary_key=primary_key, request=request)
            return DataResponse(data=obj)

        return router
