import asyncio
import atexit
import concurrent.futures
import threading
from typing import Any, Dict, Optional

try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

SERVER_BACKENDS = [
    "llama-cpp-server",
]

DEFAULT_MAX_NEW_TOKENS = 4096
DEFAULT_BATCH_SIZE = 8


def require_openai():
    if not HAS_OPENAI:
        raise ImportError(
            "The 'openai' package is required for GenAI inference. "
            "Install it with: pip install openai"
        )


class GenAIConfig:
    def __init__(
        self,
        backend: str = "llama-cpp-server",
        server_url: Optional[str] = None,
        max_concurrency: int = 200,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
        temperature: float = 0.0,
        top_p: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
        skip_special_tokens: bool = True,
        min_pixels: Optional[int] = None,
        max_pixels: Optional[int] = None,
    ):
        if backend in SERVER_BACKENDS and server_url is None:
            raise ValueError(f"`server_url` must not be None for the {backend} backend.")
        self.backend = backend
        self.server_url = server_url
        self.max_concurrency = max_concurrency
        self.model_name = model_name
        self.api_key = api_key or "null"
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty
        self.skip_special_tokens = skip_special_tokens
        self.min_pixels = min_pixels
        self.max_pixels = max_pixels


class _AsyncThreadManager:
    def __init__(self):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.stopped = False
        self._event_start = threading.Event()
        self._event_cleanup_done = threading.Event()
        self._shutting_down = False

    def start(self):
        if self.is_running():
            return
        self._shutting_down = False
        self.stopped = False
        self._event_start.clear()
        self._event_cleanup_done.clear()

        def _run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self._event_start.set()
            try:
                self.loop.run_forever()
            finally:
                self._cleanup_loop_internal()
                self._event_cleanup_done.set()
                self.stopped = True

        self.thread = threading.Thread(target=_run_loop, daemon=True)
        self.thread.start()
        self._event_start.wait()

    def _cleanup_loop_internal(self):
        if self.loop is None:
            return
        try:
            pending = asyncio.all_tasks(self.loop)
            if pending:
                for task in pending:
                    task.cancel()
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            if hasattr(self.loop, "shutdown_default_executor"):
                self.loop.run_until_complete(self.loop.shutdown_default_executor())
        except Exception:
            pass
        finally:
            self.loop.close()

    def stop(self, timeout: float = 5.0):
        if not self.is_running():
            return
        self._shutting_down = True

        async def _graceful_shutdown():
            current_task = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks(self.loop) if t is not current_task and not t.done()]
            if not pending:
                return
            done, still_pending = await asyncio.wait(pending, timeout=timeout, return_when=asyncio.ALL_COMPLETED)
            for task in still_pending:
                task.cancel()
            await asyncio.gather(*still_pending, return_exceptions=True)

        try:
            future = asyncio.run_coroutine_threadsafe(_graceful_shutdown(), self.loop)
            future.result(timeout=timeout + 2.0)
        except Exception:
            pass

        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except RuntimeError:
            pass

        self._event_cleanup_done.wait(timeout=5.0)
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        self.loop = None
        self.thread = None

    def run_async(self, coro):
        if not self.is_running():
            raise RuntimeError("Event loop is not running")
        if self._shutting_down:
            raise RuntimeError("Event loop is shutting down")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def is_running(self):
        return self.loop is not None and not self.loop.is_closed() and not self.stopped


_async_thread_manager: Optional[_AsyncThreadManager] = None


def get_async_manager() -> _AsyncThreadManager:
    global _async_thread_manager
    if _async_thread_manager is None:
        _async_thread_manager = _AsyncThreadManager()
    return _async_thread_manager


def start_aio_loop():
    manager = get_async_manager()
    if not manager.is_running():
        manager.start()
        atexit.register(manager.stop)


def close_aio_loop(timeout: float = 5.0):
    manager = get_async_manager()
    if manager.is_running():
        manager.stop(timeout=timeout)


def run_async(coro, return_future=False, timeout=None):
    manager = get_async_manager()
    if not manager.is_running():
        start_aio_loop()
    if not manager.is_running():
        raise RuntimeError("Failed to start event loop")
    if manager._shutting_down:
        raise RuntimeError("Event loop is shutting down")
    future = manager.run_async(coro)
    if return_future:
        return future
    return future.result(timeout=timeout)


class GenAIClient:
    def __init__(
        self,
        backend: str,
        base_url: str,
        max_concurrency: int = 200,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        require_openai()
        super().__init__()
        self.backend = backend
        self._max_concurrency = max_concurrency
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "null",
        )
        if model_name is None:
            model_name = run_async(self._get_model_name(), timeout=10)
        self._model_name = model_name
        self._semaphore = asyncio.Semaphore(self._max_concurrency)

    @property
    def model_name(self) -> str:
        return self._model_name

    def create_chat_completion(self, messages, *, return_future=False, **kwargs):
        async def _create():
            async with self._semaphore:
                return await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    **kwargs,
                )

        return run_async(_create(), return_future=return_future)

    def close(self):
        run_async(self._client.close(), timeout=5)

    async def _get_model_name(self):
        try:
            models = await self._client.models.list()
        except Exception as e:
            raise RuntimeError(f"Failed to get model list: {e}") from e
        return models.data[0].id
