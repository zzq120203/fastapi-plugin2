<h2 align="center">
  FastAPI-Plugin
</h2>
<p align="center">
    <em>FastAPI-Plugin 为 FastAPI 提供的基于 SQLAlchemy ORM 快速构建数据库操作的插件.</em><br/>
</p>

## 项目介绍
 - 基于 SQLAlchemy 2.0.0+ 与 FastAPI 0.100.0+

## 安装
```shell
pip3 install fastapi_plugin-<version>-py3-none-any.whl
```

## fastapi
```python
from fastapi import FastAPI

app = FastAPI()
```

## ORM模型
```python
from uuid import UUID, uuid4

from fastapi_plugin.crud import SQLModel, Field

# 继承 SQLModel
class Category(SQLModel, table=True):
    # mode 取值 c：可写 r：可读 u：可更新
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False, mode='r')
    name: str = Field(..., title='名称', max_length=100, index=True, nullable=False, mode='cr')
    description: str = Field('', title='描述', max_length=255, mode='cru')
```

## 创建连接
### AsyncDatabase
```python
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

database_url = 'sqlite+aiosqlite:///test.db'
engine: AsyncEngine = create_async_engine(database_url)
```

### Database
```python
from sqlalchemy import create_engine, Engine

database_url = 'sqlite+aiosqlite:///test.db'
engine: Engine = create_engine(database_url)
```

## 注册
```python
from fastapi_plugin.crud import SQLAlchemyCrud, get_engine_db

database = get_engine_db(engine)

cate_router = SQLAlchemyCrud(Category, database).router()

# 挂载中间件
app.add_middleware(database.asgi_middleware)
# 挂载路由
app.include_router(cate_router.create_object_router())
app.include_router(cate_router.read_object_router())
app.include_router(cate_router.update_object_router())
app.include_router(cate_router.delete_object_router())
```

## 初始化数据库
```python
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

## 离线挂载 openapi
```python
from fastapi_plugin import offline

offline.mount(app)
```

## 完整示例代码
```python
import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from fastapi_plugin import offline
from fastapi_plugin.crud import SQLAlchemyCrud, Field, SQLModel, get_engine_db

app = FastAPI()

offline.mount(app)


class Category(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False, mode='r')
    name: str = Field(..., title='名称', max_length=100, index=True, nullable=False, mode='cr')
    description: str = Field('', title='描述', max_length=255, mode='cru')


database_url = 'sqlite+aiosqlite:///test.db'
engine: AsyncEngine = create_async_engine(database_url)

database = get_engine_db(engine)

cate_router = SQLAlchemyCrud(Category, database).router()

# 挂载中间件
app.add_middleware(database.asgi_middleware)
# 挂载路由
app.include_router(cate_router.create_object_router())
app.include_router(cate_router.read_object_router())
app.include_router(cate_router.update_object_router())
app.include_router(cate_router.delete_object_router())


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

```

## 权限
```python
from fastapi import Depends, Request
from fastapi_plugin.user import Auth, AuthRouter

auth = Auth(db=database)

auth_router = AuthRouter(auth)

app.include_router(auth_router.router)

# admin 用户可以访问
@app.get("/auth/get_user", dependencies=[Depends(auth.current_user('admin'))])
def get_user(request: Request):
    return request.user
```

## 迭代计划
- [x] 增删改查
- [x] 异步接口支持
- [x] 自动关联openapi文档
- [ ] 数据库操作前后钩子
- [x] 用户权限
- [ ] 后端管理界面
- [ ] 资源隔离