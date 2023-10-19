from enum import Enum
from typing import Any, Dict, Optional, Sequence, Set, Type, Union

from fastapi._compat import (  # noqa: F401
    ModelField,
    Undefined,
    field_annotation_is_scalar_sequence,
    sequence_annotation_to_type,
)
from fastapi.utils import create_cloned_field
from pydantic import BaseModel, ConfigDict, create_model
from pydantic.v1.datetime_parse import parse_date, parse_datetime  # noqa: F401
from pydantic.v1.utils import lenient_issubclass
from pydantic_settings import BaseSettings  # noqa: F401
from typing_extensions import Annotated, get_args, get_origin

from pydantic import model_validator
from pydantic.v1.typing import is_literal_type, is_none_type, is_union


class AllowExtraModelMixin(BaseModel):
    model_config = ConfigDict(extra="allow")


class ORMModelMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def create_model_by_fields(
        name: str,
        fields: Sequence[ModelField],
        *,
        set_none: bool = False,
        extra: str = "ignore",
        **kwargs,
) -> Type[BaseModel]:
    if kwargs.pop("orm_mode", False):
        kwargs.setdefault("from_attributes", True)
    __config__ = marge_model_config(AllowExtraModelMixin, {"extra": extra, **kwargs})
    __validators__ = None

    if set_none:
        __validators__ = {"root_validator_skip_blank": model_validator(mode="before")(root_validator_skip_blank)}
        for f in fields:
            f.field_info.annotation = Optional[f.field_info.annotation]
            f.field_info.default = None
    field_params = {f.name: (f.field_info.annotation, f.field_info) for f in fields}
    model: Type[BaseModel] = create_model(name, __config__=__config__, __validators__=__validators__, **field_params)
    return model


def model_fields(model: Type[BaseModel]) -> Dict[str, ModelField]:
    fields = {}
    for field_name, field in model.model_fields.items():
        fields[field_name] = ModelField(field_info=field, name=field_name)
    return fields


def marge_model_config(model: Type[BaseModel], update: Dict[str, Any]) -> Union[type, Dict[str, Any]]:
    return {**model.model_config, **update}


def annotation_outer_type(tp: Any) -> Any:
    """Get the base type of the annotation."""
    if tp is Ellipsis:
        return Any
    origin = get_origin(tp)
    if origin is None:
        return tp
    elif is_union(origin) or origin is Annotated:
        pass
    elif origin in sequence_annotation_to_type:
        return sequence_annotation_to_type[origin]
    elif origin in {Dict, dict}:
        return dict
    elif lenient_issubclass(origin, BaseModel):
        return origin
    args = get_args(tp)
    for arg in args:
        if is_literal_type(tp):
            arg = type(arg)
        if is_none_type(arg):
            continue
        return annotation_outer_type(arg)
    return tp


def scalar_sequence_inner_type(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin is None:
        return Any
    elif is_union(origin) or origin is Annotated:  # Return the type of the first element
        return scalar_sequence_inner_type(get_args(tp)[0])
    args = get_args(tp)
    return annotation_outer_type(args[0]) if args else Any


def validator_skip_blank(v, type_: type):
    if isinstance(v, str):
        if not v:
            if issubclass(type_, Enum):
                if "" not in type_._value2member_map_:
                    return None
                return ""
            if not issubclass(type_, str):
                return None
            return ""
        if issubclass(type_, int):
            v = int(v)
    elif isinstance(v, int) and issubclass(type_, str):
        v = str(v)
    return v


def root_validator_skip_blank(cls, values: Dict[str, Any]):
    fields = model_fields(cls)

    def get_field_by_alias(alias: str) -> Optional[ModelField]:
        for f in fields.values():
            if f.alias == alias:
                return f
        return None

    for k, v in values.items():
        field = get_field_by_alias(k)
        if field:
            values[k] = validator_skip_blank(v, annotation_outer_type(field.type_))
    return values


def create_model_by_model(
        model: Type[BaseModel],
        name: str,
        *,
        include: Set[str] = None,
        exclude: Set[str] = None,
        set_none: bool = False,
        **kwargs,
) -> Type[BaseModel]:
    """Create a new model by the BaseModel."""
    fields = model_fields(model)
    keys = set(fields.keys())
    if include:
        keys &= include
    if exclude:
        keys -= exclude
    fields = {name: create_cloned_field(field) for name, field in fields.items() if name in keys}
    return create_model_by_fields(name, list(fields.values()), set_none=set_none, **kwargs)
