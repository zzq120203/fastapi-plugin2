# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : _sqlalchemy.py.py
# @Time     : 2023/10/11 16:11
from typing import List, Dict, Any, Generic, TypeVar, Optional, Type, Tuple

from fastapi.requests import Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import object_session

from .parser import get_modelfield_by_alias, Selector, Paginator
from .router import CrudRouter
from .sqlmodel import SQLModel, select, Session
from .utils import SqlalchemyDatabase, get_engine_db, sqlmodel_to_crud

TableModel = TypeVar('TableModel', bound=SQLModel)


class SQLAlchemyCrud(Generic[TableModel]):

    def __init__(
            self,
            model: Type[TableModel],
            engine: SqlalchemyDatabase,
    ):
        self.engine = engine
        assert self.engine, "engine is None"
        self.db = get_engine_db(self.engine)

        self.Model = model
        self.name = model.__name__
        self.CreateModel: Type[BaseModel] = sqlmodel_to_crud(model, 'Create')
        self.ReadModel: Type[BaseModel] = sqlmodel_to_crud(model, 'Read')
        self.UpdateModel: Type[BaseModel] = sqlmodel_to_crud(model, 'Update')
        self.DeleteModel: Type[BaseModel] = sqlmodel_to_crud(model, 'Delete')

        self.pk_name, self.pk_field = [(name, info) for name, info in model.model_fields.items() if info.primary_key][0]
        self.pk = getattr(self.Model, self.pk_name)

    async def on_after_create(
            self, objects: List[TableModel], request: Optional[Request] = None
    ) -> None:
        return  # pragma: no cover

    async def on_after_update(
            self,
            old_obj: TableModel,
            new_obj: TableModel,
            request: Optional[Request] = None,
    ) -> None:
        return  # pragma: no cover

    async def on_before_delete(
            self, obj: TableModel, request: Optional[Request] = None
    ) -> None:
        return  # pragma: no cover

    async def on_after_delete(
            self, obj: TableModel, request: Optional[Request] = None
    ) -> None:
        return  # pragma: no cover

    def _fetch_item_scalars(self, session: Session, query=None) -> List[TableModel]:
        sel = select(self.Model).filter(query) if query is not None else select(self.Model)
        return session.scalars(sel).all()

    def create_item(self, item: TableModel) -> TableModel:
        return self.Model(**item.model_dump(by_alias=True))

    def read_item(self, obj: TableModel) -> TableModel:
        return self.ReadModel.model_validate(obj, from_attributes=True)

    def update_item(self, obj: TableModel, values: Dict[str, Any]) -> None:
        for k, v in values.items():
            field = get_modelfield_by_alias(self.Model, k)
            if not field and not hasattr(obj, k):
                continue
            name = field.name if field else k
            if isinstance(v, dict):
                # Relational attributes, nested;such as: setattr(article.content, "body", "new body")
                sub = getattr(obj, name)
                if not isinstance(sub, dict):  # Ensure that the attribute is an object.
                    self.update_item(sub, v)
                    continue
            setattr(obj, name, v)

    def delete_item(self, obj: TableModel) -> None:
        object_session(obj).delete(obj)

    def _create_items(self, session: Session, items: List[TableModel]) -> List[TableModel]:
        if not items:
            return []
        objs = [self.create_item(item) for item in items]
        session.add_all(objs)
        session.flush()
        return objs

    async def create_items(self, request: Request, items: List[TableModel]) -> List[TableModel]:
        objs = await self.db.async_run_sync(self._create_items, items)
        results = [self.ReadModel.model_validate(obj, from_attributes=True) for obj in objs]
        await self.on_after_create(results, request=request)
        return results

    def _read_items(self, session: Session, query=None) -> List[TableModel]:
        items = self._fetch_item_scalars(session, query)
        return [self.read_item(obj) for obj in items]

    async def read_item_by_primary_key(self, request: Request, primary_key: Any) -> TableModel:
        query = self.pk == primary_key
        items = await self.db.async_run_sync(self._read_items, query)
        return self.ReadModel.model_validate(items[0], from_attributes=True)

    async def read_items(
            self, request: Request, selector: Selector, paginator: Paginator
    ) -> Tuple[List[TableModel], int]:
        sel = select(self.Model)
        selector = selector.calc_filter_clause()
        if selector:
            sel = sel.filter(*selector)
        if paginator.show_total:
            total = await self.db.async_scalar(
                select(func.count("*")).select_from(sel.with_only_columns(self.pk).subquery())
            )
        else:
            total = -1
        order_by = paginator.calc_ordering()
        if order_by:
            sel = sel.order_by(*order_by)
        sel = sel.limit(paginator.page_size).offset((paginator.page - 1) * paginator.page_size)
        results = await self.db.async_execute(sel)
        results = results.unique().scalars().all()
        return results, total

    def _update_items(
            self, session: Session, primary_key: List[Any], values: Dict[str, Any], query=None
    ) -> List[TableModel]:
        query = query or self.pk.in_(primary_key)
        items = self._fetch_item_scalars(session, query)
        [self.update_item(item, values) for item in items]
        return items

    async def update_items(self, request: Request, primary_key: List[Any], item: TableModel) -> List[TableModel]:
        return await self.db.async_run_sync(self._update_items, primary_key, item.model_dump(by_alias=True))

    def _delete_items(self, session: Session, primary_key: List[Any]) -> List[TableModel]:
        query = self.pk.in_(primary_key)
        items = self._fetch_item_scalars(session, query)
        for item in items:
            self.delete_item(item)
        return items

    async def delete_items(self, request: Request, primary_key: List[Any]) -> List[TableModel]:
        return await self.db.async_run_sync(self._delete_items, primary_key)

    def router(self) -> CrudRouter:
        return CrudRouter(self)
