# 保留 fastapi.requests 的原有导出，并按本项目的应用类型将 Request.app 收窄为 FastAPI。
from fastapi.applications import FastAPI
from starlette.requests import HTTPConnection as HTTPConnection
from starlette.requests import Request as _Request

class Request(_Request):
    @property
    def app(self) -> FastAPI: ...
