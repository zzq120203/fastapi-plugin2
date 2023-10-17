# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : parser.py
# @Time     : 2023/10/11 16:29
import re
from re import Pattern
from typing import Optional, Type, Union, List, Annotated, Any, Callable, Tuple, Dict

from fastapi import Depends, Query
from sqlalchemy import desc, and_

from .sqlmodel import SQLModel
from .sqlmodel.main import FieldInfo

sql_operator_pattern: Pattern = re.compile(r"^\[(=|<=|<|>|>=|!|!=|<>|\*|!\*|~|!~|-)]")
sql_operator_map: Dict[str, str] = {
    "=": "__eq__",
    "<=": "__le__",
    "<": "__lt__",
    ">": "__gt__",
    ">=": "__ge__",
    "!": "__ne__",
    "!=": "__ne__",
    "<>": "__ne__",
    "*": "in_",
    "!*": "not_in",
    "~": "like",
    "!~": "not_like",
    "-": "between",
}


def get_modelfield_by_alias(table_model: Type[SQLModel], alias: str) -> Optional[FieldInfo]:
    fields = table_model.model_fields.values()
    for field in fields:
        if field.alias == alias:
            return field
    return None


def required_parser_str_set_list(primary_key: Union[int, str]) -> List[str]:
    if isinstance(primary_key, int):
        return [str(primary_key)]
    elif not isinstance(primary_key, str):
        return []
    return list(set(primary_key.split(",")))


RequiredPrimaryKeyListDepend = Annotated[List[str], Depends(required_parser_str_set_list)]


def parser_ob_str_set_list(order_by: Optional[str] = None) -> List[str]:
    return required_parser_str_set_list(order_by)


OrderByListDepend = Annotated[List[str], Depends(parser_ob_str_set_list)]


class Selector:
    Model: Type[SQLModel]

    def __call__(self, *args, **kwargs):
        pass

    @staticmethod
    def _parser_query_value(
            value: Any, operator: str = "__eq__", python_type_parse: Callable = str
    ) -> Tuple[Optional[str], Union[tuple, None]]:
        if isinstance(value, str):
            if not value:
                return None, None
            match = sql_operator_pattern.match(value)
            if match:
                op_key = match.group(1)
                operator = sql_operator_map.get(op_key)
                value = value.replace(f"[{op_key}]", "")
                if not value:
                    return None, None
                if operator in ["like", "not_like"] and value.find("%") == -1:
                    return operator, (f"%{value}%",)
                elif operator in ["in_", "not_in"]:
                    return operator, (list(map(python_type_parse, set(value.split(",")))),)
                elif operator == "between":
                    value = value.split(",")[:2]
                    if len(value) < 2:
                        return None, None
                    return operator, tuple(map(python_type_parse, value))
        return operator, (python_type_parse(value),)

    def calc_filter_clause(self):
        query = []
        for name, value in self.__dict__.items():
            if value:
                operator, val = self._parser_query_value(value)
                if operator:
                    query.append(getattr(getattr(self.Model, name), operator)(*val))
        return query


class Paginator:

    def __init__(self, page_size_max: int = None, page_size_default: int = 10):
        self.page_size_max = page_size_max
        self.page_size_default = page_size_default

    def __call__(
            self,
            page: Union[int] = Query(1),
            page_size: Union[int] = Query(None),
            show_total: bool = Query(True),
            order_by: OrderByListDepend = None,

    ):
        self.page = page if page and page > 0 else self.page_size_default
        self.page_size = page_size if page_size and page_size > 0 else self.page_size_default
        if self.page_size_default:
            self.page_size = min(self.page_size, self.page_size_default)
        self.show_total = show_total
        self.order_by = order_by
        return self

    def calc_ordering(self):
        order = []
        for ob in self.order_by:
            if isinstance(ob, str) and ob.startswith("-"):
                order.append(desc(ob[1:]))
            else:
                order.append(ob)

        return order
