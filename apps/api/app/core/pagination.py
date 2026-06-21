"""Pagination helpers used by all list endpoints."""

from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    limit: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def page_params(
    page: int = Query(1, ge=1, description="Trang (bắt đầu từ 1)"),
    limit: int = Query(20, ge=1, le=200, description="Số bản ghi mỗi trang"),
) -> PageParams:
    return PageParams(page=page, limit=limit)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int


def paginate(db: Session, stmt: Select, params: PageParams) -> tuple[list, int]:
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.offset(params.offset).limit(params.limit)).scalars().all()
    return list(rows), int(total)


def build_page(items: list, total: int, params: PageParams) -> dict:
    pages = (total + params.limit - 1) // params.limit if params.limit else 0
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "limit": params.limit,
        "pages": pages,
    }
