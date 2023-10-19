from __future__ import annotations

import ipaddress
import sys
import types
import uuid
import weakref
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import (
    AbstractSet,
    Any,
    Callable,
    ClassVar,
    Dict,
    ForwardRef,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import pydantic
from annotated_types import MaxLen
from pydantic import BaseModel, EmailStr, ImportString, NameEmail
from pydantic._internal._fields import PydanticGeneralMetadata
from pydantic._internal._model_construction import ModelMetaclass
from pydantic._internal._repr import Representation
from pydantic.fields import FieldInfo as PydanticFieldInfo
from pydantic_core import PydanticUndefined, PydanticUndefinedType
from sqlalchemy import Boolean, Column, Date, DateTime
from sqlalchemy import Enum as sa_Enum
from sqlalchemy import Float, ForeignKey, Integer, Interval, Numeric, inspect
from sqlalchemy.orm import RelationshipProperty, declared_attr, registry, relationship
from sqlalchemy.orm.attributes import set_attribute
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm.instrumentation import is_instrumented
from sqlalchemy.orm.properties import MappedColumn
from sqlalchemy.sql import false, true
from sqlalchemy.sql.schema import DefaultClause, MetaData
from sqlalchemy.sql.sqltypes import LargeBinary, Time

from .sql.sqltypes import GUID, AutoString
from .typing import SQLModelConfig

if sys.version_info >= (3, 8):
    from typing import get_args, get_origin
else:
    from typing_extensions import get_args, get_origin

from typing_extensions import Annotated, _AnnotatedAlias

_T = TypeVar("_T")
NoArgAnyCallable = Callable[[], Any]
NoneType = type(None)


def __dataclass_transform__(
    *,
    eq_default: bool = True,
    order_default: bool = False,
    kw_only_default: bool = False,
    field_descriptors: Tuple[Union[type, Callable[..., Any]], ...] = (()),
) -> Callable[[_T], _T]:
    return lambda a: a


class FieldInfo(PydanticFieldInfo):
    nullable: Union[bool, PydanticUndefinedType]

    def __init__(self, default: Any = PydanticUndefined, **kwargs: Any) -> None:
        primary_key = kwargs.pop("primary_key", False)
        nullable = kwargs.pop("nullable", PydanticUndefined)
        foreign_key = kwargs.pop("foreign_key", PydanticUndefined)
        unique = kwargs.pop("unique", False)
        index = kwargs.pop("index", PydanticUndefined)
        sa_column = kwargs.pop("sa_column", PydanticUndefined)
        sa_column_args = kwargs.pop("sa_column_args", PydanticUndefined)
        sa_column_kwargs = kwargs.pop("sa_column_kwargs", PydanticUndefined)
        mode = kwargs.pop("mode", "crud")
        if sa_column is not PydanticUndefined:
            if sa_column_args is not PydanticUndefined:
                raise RuntimeError(
                    "Passing sa_column_args is not supported when "
                    "also passing a sa_column"
                )
            if sa_column_kwargs is not PydanticUndefined:
                raise RuntimeError(
                    "Passing sa_column_kwargs is not supported when "
                    "also passing a sa_column"
                )
        super().__init__(default=default, **kwargs)
        self.primary_key = primary_key
        self.nullable = nullable
        self.foreign_key = foreign_key
        self.unique = unique
        self.index = index
        self.sa_column = sa_column
        self.sa_column_args = sa_column_args
        self.sa_column_kwargs = sa_column_kwargs
        self.mode = mode


class RelationshipInfo(Representation):
    def __init__(
        self,
        *,
        back_populates: Optional[str] = None,
        link_model: Optional[Any] = None,
        sa_relationship: Optional[RelationshipProperty] = None,  # type: ignore
        sa_relationship_args: Optional[Sequence[Any]] = None,
        sa_relationship_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if sa_relationship is not None:
            if sa_relationship_args is not None:
                raise RuntimeError(
                    "Passing sa_relationship_args is not supported when "
                    "also passing a sa_relationship"
                )
            if sa_relationship_kwargs is not None:
                raise RuntimeError(
                    "Passing sa_relationship_kwargs is not supported when "
                    "also passing a sa_relationship"
                )
        self.back_populates = back_populates
        self.link_model = link_model
        self.sa_relationship = sa_relationship
        self.sa_relationship_args = sa_relationship_args
        self.sa_relationship_kwargs = sa_relationship_kwargs


def Field(
    default: Any = PydanticUndefined,
    *,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    include: Union[
        AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], Any
    ] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_mutation: bool = True,
    regex: Optional[str] = None,
    primary_key: bool = False,
    foreign_key: Optional[Any] = None,
    unique: bool = False,
    nullable: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    index: Union[bool, PydanticUndefinedType] = PydanticUndefined,
    sa_column: Union[Column, PydanticUndefinedType, Callable[[], Column]] = PydanticUndefined,  # type: ignore
    sa_column_args: Union[Sequence[Any], PydanticUndefinedType] = PydanticUndefined,
    sa_column_kwargs: Union[
        Mapping[str, Any], PydanticUndefinedType
    ] = PydanticUndefined,
    mode: Optional[str] = "crud",
    schema_extra: Optional[Dict[str, Any]] = None,
) -> Any:
    current_schema_extra = schema_extra or {}
    if isinstance(default, Callable):
        default_factory = default
        default = PydanticUndefined
    if default is PydanticUndefined:
        if isinstance(sa_column, types.FunctionType):  # lambda
            sa_column_ = sa_column()
        else:
            sa_column_ = sa_column

        # server_default -> default
        if isinstance(sa_column_, Column) and isinstance(
            sa_column_.server_default, DefaultClause
        ):
            default_value = sa_column_.server_default.arg
            if issubclass(type(sa_column_.type), Integer) and isinstance(
                default_value, str
            ):
                default = int(default_value)
            elif issubclass(type(sa_column_.type), Boolean):
                if default_value is false():
                    default = False
                elif default_value is true():
                    default = True
                elif isinstance(default_value, str):
                    if default_value == "1":
                        default = True
                    elif default_value == "0":
                        default = False

    field_info = FieldInfo(
        default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        exclude=exclude,
        include=include,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_items=min_items,
        max_items=max_items,
        min_length=min_length,
        max_length=max_length,
        allow_mutation=allow_mutation,
        regex=regex,
        primary_key=primary_key,
        foreign_key=foreign_key,
        unique=unique,
        nullable=nullable,
        index=index,
        sa_column=sa_column,
        sa_column_args=sa_column_args,
        sa_column_kwargs=sa_column_kwargs,
        mode=mode,
        **current_schema_extra,
    )
    return field_info


def Relationship(
    *,
    back_populates: Optional[str] = None,
    link_model: Optional[Any] = None,
    sa_relationship: Optional[RelationshipProperty[Any]] = None,
    sa_relationship_args: Optional[Sequence[Any]] = None,
    sa_relationship_kwargs: Optional[Mapping[str, Any]] = None,
) -> Any:
    relationship_info = RelationshipInfo(
        back_populates=back_populates,
        link_model=link_model,
        sa_relationship=sa_relationship,
        sa_relationship_args=sa_relationship_args,
        sa_relationship_kwargs=sa_relationship_kwargs,
    )
    return relationship_info


@__dataclass_transform__(kw_only_default=True, field_descriptors=(Field, FieldInfo))
class SQLModelMetaclass(ModelMetaclass, DeclarativeMeta):
    __sqlmodel_relationships__: Dict[str, RelationshipInfo]
    model_config: SQLModelConfig
    model_fields: Dict[str, FieldInfo]

    # Replicate SQLAlchemy
    def __setattr__(cls, name: str, value: Any) -> None:
        if cls.model_config.get("table", False):
            DeclarativeMeta.__setattr__(cls, name, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(cls, name: str) -> None:
        if cls.model_config.get("table", False):
            DeclarativeMeta.__delattr__(cls, name)
        else:
            super().__delattr__(name)

    # From Pydantic
    def __new__(
        cls,
        name: str,
        bases: Tuple[Type[Any], ...],
        class_dict: Dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        relationships: Dict[str, RelationshipInfo] = {}
        dict_for_pydantic = {}
        original_annotations = class_dict.get("__annotations__", {})
        pydantic_annotations = {}
        relationship_annotations = {}
        for k, v in class_dict.items():
            if isinstance(v, RelationshipInfo):
                relationships[k] = v
            else:
                dict_for_pydantic[k] = v
        for k, v in original_annotations.items():
            if k in relationships:
                relationship_annotations[k] = v
            else:
                pydantic_annotations[k] = v
        dict_used = {
            **dict_for_pydantic,
            "__weakref__": None,
            "__sqlmodel_relationships__": relationships,
            "__annotations__": pydantic_annotations,
        }
        # Duplicate logic from Pydantic to filter config kwargs because if they are
        # passed directly including the registry Pydantic will pass them over to the
        # superclass causing an error
        allowed_config_kwargs: Set[str] = {
            key
            for key in dir(SQLModelConfig)
            if not (
                key.startswith("__") and key.endswith("__")
            )  # skip dunder methods and attributes
        }
        pydantic_kwargs = kwargs.copy()
        config_kwargs = {
            key: pydantic_kwargs.pop(key)
            for key in pydantic_kwargs.keys() & allowed_config_kwargs
        }
        config_table = getattr(
            class_dict.get("Config", object()), "table", False
        ) or kwargs.get("table", False)
        # If we have a table, we need to have defaults for all fields
        # Pydantic v2 sets a __pydantic_core_schema__ which is very hard to change. Changing the fields does not do anything
        if config_table is True:
            for key in pydantic_annotations.keys():
                value = dict_used.get(key, PydanticUndefined)
                if value is PydanticUndefined:
                    dict_used[key] = None
                elif isinstance(value, FieldInfo):
                    if (
                        value.default in (PydanticUndefined, Ellipsis)
                    ) and value.default_factory is None:
                        value.original_default = (
                            value.default
                        )  # So we can check for nullable
                        value.default = None

        new_cls: Type["SQLModelMetaclass"] = super().__new__(
            cls, name, bases, dict_used, **config_kwargs
        )
        new_cls.__annotations__ = {
            **relationship_annotations,
            **pydantic_annotations,
            **new_cls.__annotations__,
        }

        def get_config(name: str) -> Any:
            config_class_value = new_cls.model_config.get(name, PydanticUndefined)
            if config_class_value is not PydanticUndefined:
                return config_class_value
            kwarg_value = kwargs.get(name, PydanticUndefined)
            if kwarg_value is not PydanticUndefined:
                return kwarg_value
            return PydanticUndefined

        config_table = get_config("table")
        if config_table is True:
            # If it was passed by kwargs, ensure it's also set in config
            new_cls.model_config["table"] = config_table
            for k, v in new_cls.model_fields.items():
                col = get_column_from_field(v)
                setattr(new_cls, k, col)
            # Set a config flag to tell FastAPI that this should be read with a field
            # in orm_mode instead of preemptively converting it to a dict.
            # This could be done by reading new_cls.model_config['table'] in FastAPI, but
            # that's very specific about SQLModel, so let's have another config that
            # other future tools based on Pydantic can use.
            new_cls.model_config["read_from_attributes"] = True

        config_registry = get_config("registry")
        if config_registry is not PydanticUndefined:
            config_registry = cast(registry, config_registry)
            # If it was passed by kwargs, ensure it's also set in config
            new_cls.model_config["registry"] = config_table
            setattr(new_cls, "_sa_registry", config_registry)
            setattr(new_cls, "metadata", config_registry.metadata)
            setattr(new_cls, "__abstract__", True)
        return new_cls

    # Override SQLAlchemy, allow both SQLAlchemy and plain Pydantic models
    def __init__(
        cls, classname: str, bases: Tuple[type, ...], dict_: Dict[str, Any], **kw: Any
    ) -> None:
        # Only one of the base classes (or the current one) should be a table model
        # this allows FastAPI cloning a SQLModel for the response_model without
        # trying to create a new SQLAlchemy, for a new table, with the same name, that
        # triggers an error
        base_is_table = False
        for base in bases:
            config = getattr(base, "model_config")
            if config and getattr(config, "table", False):
                base_is_table = True
                break
        if cls.model_config.get("table", False) and not base_is_table:
            dict_used = dict_.copy()
            for field_name, field_value in cls.model_fields.items():
                col = getattr(cls, field_name)
                dict_used[field_name] = get_column_from_field(field_value) if col is None else col
            for rel_name, rel_info in cls.__sqlmodel_relationships__.items():
                if rel_info.sa_relationship:
                    # There's a SQLAlchemy relationship declared, that takes precedence
                    # over anything else, use that and continue with the next attribute
                    dict_used[rel_name] = rel_info.sa_relationship
                    continue
                ann = cls.__annotations__[rel_name]
                relationship_to = get_origin(ann)
                # Direct relationships (e.g. 'Team' or Team) have None as an origin
                if relationship_to is None:
                    relationship_to = ann
                # If Union (e.g. Optional), get the real field
                elif relationship_to is Union:
                    relationship_to = get_args(ann)[0]
                # If a list, then also get the real field
                elif relationship_to is list:
                    relationship_to = get_args(ann)[0]
                if isinstance(relationship_to, ForwardRef):
                    relationship_to = relationship_to.__forward_arg__
                rel_kwargs: Dict[str, Any] = {}
                if rel_info.back_populates:
                    rel_kwargs["back_populates"] = rel_info.back_populates
                if rel_info.link_model:
                    ins = inspect(rel_info.link_model)
                    local_table = getattr(ins, "local_table")
                    if local_table is None:
                        raise RuntimeError(
                            "Couldn't find the secondary table for "
                            f"model {rel_info.link_model}"
                        )
                    rel_kwargs["secondary"] = local_table
                rel_args: List[Any] = []
                if rel_info.sa_relationship_args:
                    rel_args.extend(rel_info.sa_relationship_args)
                if rel_info.sa_relationship_kwargs:
                    rel_kwargs.update(rel_info.sa_relationship_kwargs)
                rel_value: RelationshipProperty[Any] = relationship(
                    relationship_to, *rel_args, **rel_kwargs
                )
                dict_used[rel_name] = rel_value
                setattr(cls, rel_name, rel_value)  # Fix #315
            DeclarativeMeta.__init__(cls, classname, bases, dict_used, **kw)
        else:
            ModelMetaclass.__init__(cls, classname, bases, dict_, **kw)


def _is_optional_or_union(type_: Optional[type]) -> bool:
    if sys.version_info >= (3, 10):
        return get_origin(type_) in (types.UnionType, Union)
    else:
        return get_origin(type_) is Union


def get_sqlalchemy_type(field: FieldInfo) -> Any:
    type_: Optional[type] | _AnnotatedAlias = field.annotation

    # Resolve Optional/Union fields

    if type_ is not None and _is_optional_or_union(type_):
        bases = get_args(type_)
        if len(bases) > 2:
            raise RuntimeError(
                "Cannot have a (non-optional) union as a SQL alchemy field"
            )
        type_ = bases[0]
    # Resolve Annoted fields,
    # like typing.Annotated[pydantic_core._pydantic_core.Url,
    # UrlConstraints(max_length=512,
    # allowed_schemes=['smb', 'ftp', 'file']) ]
    if type_ is pydantic.AnyUrl:
        if field.metadata:
            meta = field.metadata[0]
            return AutoString(length=meta.max_length)
        else:
            return AutoString

    org_type = get_origin(type_)
    if org_type is Annotated:
        type2 = get_args(type_)[0]
        if type2 is pydantic.AnyUrl:
            meta = get_args(type_)[1]
            return AutoString(length=meta.max_length)
    elif org_type is pydantic.AnyUrl and type(type_) is _AnnotatedAlias:
        return AutoString(type_.__metadata__[0].max_length)

    # The 3rd is PydanticGeneralMetadata
    metadata = _get_field_metadata(field)
    if type_ is None:
        raise ValueError("Missing field type")
    if issubclass(type_, str) or type_ in (EmailStr, NameEmail, ImportString):
        max_length = getattr(metadata, "max_length", None)
        if max_length:
            return AutoString(length=max_length)
        return AutoString
    if issubclass(type_, float):
        return Float
    if issubclass(type_, bool):
        return Boolean
    if issubclass(type_, int):
        return Integer
    if issubclass(type_, datetime):
        return DateTime
    if issubclass(type_, date):
        return Date
    if issubclass(type_, timedelta):
        return Interval
    if issubclass(type_, time):
        return Time
    if issubclass(type_, Enum):
        return sa_Enum(type_)
    if issubclass(type_, bytes):
        return LargeBinary
    if issubclass(type_, Decimal):
        return Numeric(
            precision=getattr(metadata, "max_digits", None),
            scale=getattr(metadata, "decimal_places", None),
        )
    if issubclass(type_, ipaddress.IPv4Address):
        return AutoString
    if issubclass(type_, ipaddress.IPv4Network):
        return AutoString
    if issubclass(type_, ipaddress.IPv6Address):
        return AutoString
    if issubclass(type_, ipaddress.IPv6Network):
        return AutoString
    if issubclass(type_, Path):
        return AutoString
    if issubclass(type_, uuid.UUID):
        return GUID
    raise ValueError(f"The field {field.title} has no matching SQLAlchemy type")


def get_column_from_field(field: FieldInfo) -> Column:  # type: ignore
    """
    sa_column > field attributes > annotation info
    """
    sa_column = getattr(field, "sa_column", PydanticUndefined)
    if isinstance(sa_column, Column):
        return sa_column
    if isinstance(sa_column, MappedColumn):
        return sa_column.column
    if isinstance(sa_column, types.FunctionType):
        col = sa_column()
        assert isinstance(col, Column)
        return col
    sa_type = get_sqlalchemy_type(field)
    primary_key = getattr(field, "primary_key", False)
    index = getattr(field, "index", PydanticUndefined)
    if index is PydanticUndefined:
        index = False
    nullable = not primary_key and _is_field_noneable(field)
    # Override derived nullability if the nullable property is set explicitly
    # on the field
    if hasattr(field, "nullable"):
        field_nullable = getattr(field, "nullable")
        if field_nullable != PydanticUndefined:
            nullable = field_nullable
    args = []
    foreign_key = getattr(field, "foreign_key", None)
    unique = getattr(field, "unique", False)
    if foreign_key:
        args.append(ForeignKey(foreign_key))
    kwargs = {
        "primary_key": primary_key,
        "nullable": nullable,
        "index": index,
        "unique": unique,
    }
    sa_default: Union[PydanticUndefinedType, Callable[[], Any]] = PydanticUndefined
    if field.default_factory:
        sa_default = field.default_factory
    elif field.default is not PydanticUndefined:
        sa_default = field.default
    if sa_default is not PydanticUndefined:
        kwargs["default"] = sa_default
    sa_column_args = getattr(field, "sa_column_args", PydanticUndefined)
    if sa_column_args is not PydanticUndefined:
        args.extend(list(cast(Sequence[Any], sa_column_args)))
    sa_column_kwargs = getattr(field, "sa_column_kwargs", PydanticUndefined)
    if sa_column_kwargs is not PydanticUndefined:
        kwargs.update(cast(Dict[Any, Any], sa_column_kwargs))
    return Column(sa_type, *args, **kwargs)  # type: ignore


class_registry = weakref.WeakValueDictionary()  # type: ignore

default_registry = registry()
_TSQLModel = TypeVar("_TSQLModel", bound="SQLModel")


class SQLModel(BaseModel, metaclass=SQLModelMetaclass, registry=default_registry):
    # SQLAlchemy needs to set weakref(s), Pydantic will set the other slots values
    __slots__ = ("__weakref__",)
    __tablename__: ClassVar[Union[str, Callable[..., str]]]
    __sqlmodel_relationships__: ClassVar[Dict[str, RelationshipProperty[Any]]]
    __name__: ClassVar[str]
    metadata: ClassVar[MetaData]
    __allow_unmapped__ = True  # https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-20-step-six
    model_config = SQLModelConfig(from_attributes=True)

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        new_object = super().__new__(cls)
        # SQLAlchemy doesn't call __init__ on the base class
        # Ref: https://docs.sqlalchemy.org/en/14/orm/constructors.html
        # Set __fields_set__ here, that would have been set when calling __init__
        # in the Pydantic model so that when SQLAlchemy sets attributes that are
        # added (e.g. when querying from DB) to the __fields_set__, this already exists
        object.__setattr__(new_object, "__pydantic_fields_set__", set())
        if not hasattr(new_object, "__pydantic_extra__"):
            object.__setattr__(new_object, "__pydantic_extra__", None)
        if not hasattr(new_object, "__pydantic_private__"):
            object.__setattr__(new_object, "__pydantic_private__", None)
        return new_object

    def __init__(__pydantic_self__, **data: Any) -> None:
        old_dict = __pydantic_self__.__dict__.copy()
        super().__init__(**data)
        __pydantic_self__.__dict__ = {**old_dict, **__pydantic_self__.__dict__}
        non_pydantic_keys = data.keys() - __pydantic_self__.model_fields
        for key in non_pydantic_keys:
            if key in __pydantic_self__.__sqlmodel_relationships__:
                setattr(__pydantic_self__, key, data[key])

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_sa_instance_state"}:
            self.__dict__[name] = value
            return
        else:
            # Set in SQLAlchemy, before Pydantic to trigger events and updates
            if self.model_config.get("table", False) and is_instrumented(self, name):  # type: ignore
                set_attribute(self, name, value)
            # Set in Pydantic model to trigger possible validation changes, only for
            # non relationship values
            if name not in self.__sqlmodel_relationships__:
                super(SQLModel, self).__setattr__(name, value)

    def __repr_args__(self) -> Sequence[Tuple[Optional[str], Any]]:
        # Don't show SQLAlchemy private attributes
        return [(k, v) for k, v in self.__dict__.items() if not k.startswith("_sa_")]

    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def model_validate(
        cls: Type[_TSQLModel],
        obj: Any,
        *,
        strict: Optional[bool] = None,
        from_attributes: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> _TSQLModel:
        # Somehow model validate doesn't call __init__ so it would remove our init logic
        validated = super().model_validate(
            obj, strict=strict, from_attributes=from_attributes, context=context
        )

        # remove defaults so they don't get validated
        data = {}
        for key, value in validated:
            field = cls.model_fields.get(key)

            if field is None:
                continue

            if (
                hasattr(field, "default")
                and field.default is not PydanticUndefined
                and value == field.default
            ):
                continue

            data[key] = value

        return cls(**data)


def _is_field_noneable(field: FieldInfo) -> bool:
    if hasattr(field, "nullable") and not isinstance(
        field.nullable, PydanticUndefinedType
    ):
        return field.nullable
    if not field.is_required():
        default = getattr(field, "original_default", field.default)
        if default is PydanticUndefined:
            return False
        if field.annotation is None or field.annotation is NoneType:
            return True
        if _is_optional_or_union(field.annotation):
            for base in get_args(field.annotation):
                if base is NoneType:
                    return True

        return False
    return False


def _get_field_metadata(field: FieldInfo) -> object:
    for meta in field.metadata:
        if isinstance(meta, PydanticGeneralMetadata):
            return meta
        if isinstance(meta, MaxLen):
            return meta
    return object()
