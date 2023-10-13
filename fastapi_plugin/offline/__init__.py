# !/usr/bin/env Python3
# -*- coding: utf-8 -*-
# @Author   : zhangzhanqi
# @FILE     : __init__.py.py
# @Time     : 2023/9/4 10:10
from pathlib import Path

from fastapi import FastAPI, openapi, applications
from fastapi.staticfiles import StaticFiles

__BASE_DIR = Path(__file__).resolve().parent


def mount(
        app: FastAPI,
        static_url='/static/offline',
):
    """
    加载离线文件

    """
    # 1. local static files
    app.mount(static_url,
              StaticFiles(directory=__BASE_DIR / 'static'), static_url.replace('/', '-'))

    # 2.配置 Swagger UI
    def custom_swagger_ui_html(*args, **kw):
        kw.update({
            'swagger_js_url': f'{static_url}/openapi/swagger-ui-bundle.js',
            'swagger_css_url': f'{static_url}/openapi/swagger-ui.css',
            'swagger_favicon_url': f'{static_url}/icon.ico',
        })
        return openapi.docs.get_swagger_ui_html(*args, **kw)

    applications.get_swagger_ui_html = custom_swagger_ui_html

    # 3.配置 redoc UI
    def custom_redoc_html(*args, **kw):
        kw.update({
            'redoc_js_url': f'{static_url}/openapi/redoc.standalone.js',
            'redoc_favicon_url': f'{static_url}/icon.ico',
        })
        return openapi.docs.get_redoc_html(*args, **kw)

    applications.get_redoc_html = custom_redoc_html
