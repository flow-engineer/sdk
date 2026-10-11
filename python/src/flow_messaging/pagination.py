"""Cursor pagination. Every ``list`` method returns a page; iterate it to walk every
item across pages (each next page is fetched with ``after`` = the last item's ID).

.. code-block:: python

    page = flow.conversations.list(limit=10)   # one page: page.data, page.has_more
    for conversation in flow.conversations.list():   # every conversation
        print(conversation.id)

    # async
    page = await aflow.conversations.list(limit=10)
    async for conversation in aflow.conversations.list():
        print(conversation.id)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Generator, Iterator
from typing import Any, Generic, Protocol, TypeVar


class _HasId(Protocol):
    @property
    def id(self) -> str: ...


T = TypeVar("T", bound=_HasId)

#: Fetches one page after a cursor: (items, has_more).
SyncFetch = Callable[[str | None], tuple[list[T], bool]]
AsyncFetch = Callable[[str | None], Awaitable[tuple[list[T], bool]]]


class Page(Generic[T]):
    """One page of a list. Iterating it yields every item from here to the end of the list."""

    data: list[T]
    has_more: bool

    def __init__(self, data: list[T], has_more: bool, fetch: SyncFetch[T]) -> None:
        self.data = data
        self.has_more = has_more
        self._fetch = fetch

    def next_page(self) -> Page[T] | None:
        """The following page, or None when ``has_more`` is false."""
        if not self.has_more or not self.data:
            return None
        data, more = self._fetch(self.data[-1].id)
        return Page(data, more, self._fetch)

    def iter_pages(self) -> Iterator[Page[T]]:
        page: Page[T] | None = self
        while page is not None:
            yield page
            page = page.next_page()

    def __iter__(self) -> Iterator[T]:
        for page in self.iter_pages():
            yield from page.data

    def to_list(self, limit: int | None = None) -> list[T]:
        """Every item (up to ``limit``) across pages."""
        out: list[T] = []
        for item in self:
            if limit is not None and len(out) >= limit:
                break
            out.append(item)
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}(data=[{len(self.data)} items], has_more={self.has_more})"


class Pager(Page[T]):
    """The first page of a list, fetched when it is made."""

    def __init__(self, fetch: SyncFetch[T], after: str | None = None) -> None:
        data, more = fetch(after)
        super().__init__(data, more, fetch)


class AsyncPage(Generic[T]):
    """One page of a list. ``async for`` yields every item from here to the end of the list."""

    data: list[T]
    has_more: bool

    def __init__(self, data: list[T], has_more: bool, fetch: AsyncFetch[T]) -> None:
        self.data = data
        self.has_more = has_more
        self._fetch = fetch

    async def next_page(self) -> AsyncPage[T] | None:
        if not self.has_more or not self.data:
            return None
        data, more = await self._fetch(self.data[-1].id)
        return AsyncPage(data, more, self._fetch)

    async def iter_pages(self) -> AsyncIterator[AsyncPage[T]]:
        page: AsyncPage[T] | None = self
        while page is not None:
            yield page
            page = await page.next_page()

    async def __aiter__(self) -> AsyncIterator[T]:
        async for page in self.iter_pages():
            for item in page.data:
                yield item

    async def to_list(self, limit: int | None = None) -> list[T]:
        out: list[T] = []
        async for item in self:
            if limit is not None and len(out) >= limit:
                break
            out.append(item)
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}(data=[{len(self.data)} items], has_more={self.has_more})"


class AsyncPager(Generic[T]):
    """What async ``list`` methods return: ``await`` it for the first page, or
    ``async for`` over it for every item across pages."""

    def __init__(self, fetch: AsyncFetch[T], after: str | None = None) -> None:
        self._fetch = fetch
        self._after = after

    async def _first(self) -> AsyncPage[T]:
        data, more = await self._fetch(self._after)
        return AsyncPage(data, more, self._fetch)

    def __await__(self) -> Generator[Any, None, AsyncPage[T]]:
        return self._first().__await__()

    async def __aiter__(self) -> AsyncIterator[T]:
        page = await self._first()
        async for item in page:
            yield item

    async def to_list(self, limit: int | None = None) -> list[T]:
        return await (await self._first()).to_list(limit)
