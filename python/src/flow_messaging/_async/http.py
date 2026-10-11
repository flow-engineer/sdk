"""Requests: auth, Flow-Version, idempotency keys on POSTs (reused across retries), and
retries for connection errors, timeouts, 429 rate_limited and 5xx, honouring
retry_after. The sync client is generated from this file."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeVar

import httpx

from .._base import (
    Options,
    Query,
    async_sleep,
    backoff,
    encode_query,
    error_from_response,
    idempotency_key,
    retryable,
)
from .._constants import MAX_RETRY_WAIT
from ..errors import APIConnectionError, APITimeoutError
from ..pagination import AsyncPager

T = TypeVar("T")


class AsyncHTTPClient:
    def __init__(self, options: Options, client: httpx.AsyncClient | None = None) -> None:
        self.options = options
        self._own_client = client is None
        self.client = client or httpx.AsyncClient(timeout=options.timeout)
        self._sleep = async_sleep

    async def aclose(self) -> None:
        if self._own_client:
            await self.client.aclose()

    async def send(
        self,
        method: str,
        path: str,
        *,
        query: Query | None = None,
        json: Any = None,
        files: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        auth: bool = True,
        idempotency: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """One request with retries; returns a successful response or raises a typed error."""
        opts = self.options
        h = opts.headers(headers, auth=auth)
        # The keyless endpoints take no Idempotency-Key: there is no key to scope it to.
        if method == "POST" and auth:
            h["Idempotency-Key"] = idempotency or idempotency_key()
        retries = opts.max_retries if max_retries is None else max_retries
        t = opts.timeout if timeout is None else timeout
        url = opts.url(path)
        params = encode_query(query)
        attempt = 0
        while True:
            try:
                response = await self.client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    files=files,
                    data=data,
                    headers=h,
                    timeout=t,
                )
            except httpx.TimeoutException as e:
                if attempt < retries:
                    await self._sleep(backoff(attempt))
                    attempt += 1
                    continue
                raise APITimeoutError(f"Request timed out after {t} s.", type="timeout") from e
            except httpx.TransportError as e:
                if attempt < retries:
                    await self._sleep(backoff(attempt))
                    attempt += 1
                    continue
                raise APIConnectionError(f"Could not reach {opts.base_url}: {e}", type="connection_error") from e
            if response.is_success or response.is_redirect:
                return response
            err = error_from_response(response)
            if attempt < retries and retryable(response.status_code, err):
                wait = float(err.retry_after) if err.retry_after is not None else backoff(attempt)
                if wait <= MAX_RETRY_WAIT:
                    await self._sleep(wait)
                    attempt += 1
                    continue
            raise err

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """A request whose answer is JSON (None for 204)."""
        response = await self.send(method, path, **kwargs)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def list(
        self,
        path: str,
        query: Query,
        item: Callable[[Any], T],
    ) -> AsyncPager[Any]:
        """A paged list: ``after`` in ``query`` is where it starts; later pages follow the last item."""
        rest = {k: v for k, v in query.items() if k != "after"}

        async def fetch(after: str | None) -> tuple[list[Any], bool]:
            res = await self.request("GET", path, query={**rest, "after": after})
            return [item(x) for x in res["data"]], bool(res.get("has_more"))

        return AsyncPager(fetch, query.get("after"))
