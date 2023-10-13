# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : utils.py.py
# @Time     : 2023/10/11 16:11
from typing import Union, Type, Literal

from pydantic import BaseModel, create_model, ConfigDict
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy_database import AsyncDatabase, Database

from .sqlmodel import SQLModel

SqlalchemyDatabase = Union[Engine, AsyncEngine, Database, AsyncDatabase]


def get_engine_db(engine: SqlalchemyDatabase) -> Union[Database, AsyncDatabase]:
    if isinstance(engine, (Database, AsyncDatabase)):
        return engine
    if isinstance(engine, Engine):
        return Database(engine)
    if isinstance(engine, AsyncEngine):
        return AsyncDatabase(engine)
    raise TypeError(f"Unknown engine type: {type(engine)}")


def sqlmodel_to_crud(
        base_model: Type[SQLModel],
        action: Literal['Create', 'Read', 'Update', 'Delete'] = "Create"
) -> Type[BaseModel]:
    fields = {name: (field_info.annotation, field_info) for name, field_info in base_model.model_fields.items() if
              action[0].lower() in field_info.mode.lower()}
    model: Type[BaseModel] = create_model(
        f"{base_model.__name__}{action}", __config__=ConfigDict(extra='ignore'), **fields)
    return model
