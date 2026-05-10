"""
Python client for Rust llama-manager service.
Manages llama-server lifecycle from the Python side.
"""

import os
import socket
import time
from typing import Any, Dict, List, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

DEFAULT_MANAGER_PORT = 8081
DEFAULT_SERVER_PORT = 8080


class LlamaManagerClient:
    def __init__(
        self,
        manager_url: Optional[str] = None,
        manager_port: int = DEFAULT_MANAGER_PORT,
        timeout: float = 10.0,
    ):
        if not HAS_REQUESTS:
            raise ImportError("requests library is required. Install with: pip install requests")
        if manager_url is None:
            manager_url = f"http://127.0.0.1:{manager_port}"
        self.base_url = manager_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, **kwargs) -> requests.Response:
        return requests.get(
            f"{self.base_url}{path}",
            timeout=kwargs.get("timeout", self.timeout),
            **kwargs,
        )

    def _post(self, path: str, **kwargs) -> requests.Response:
        return requests.post(
            f"{self.base_url}{path}",
            timeout=kwargs.get("timeout", self.timeout),
            **kwargs,
        )

    def health(self) -> bool:
        try:
            resp = self._get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def get_manager_url(self) -> str:
        resp = self._get("/manager_url")
        resp.raise_for_status()
        return resp.json()["url"]

    def get_status(self) -> Dict[str, Any]:
        resp = self._get("/status")
        resp.raise_for_status()
        return resp.json()

    def is_server_running(self) -> bool:
        status = self.get_status()
        return status.get("running", False)

    def get_server_url(self) -> Optional[str]:
        status = self.get_status()
        if status.get("running"):
            return status.get("server_url")
        return None

    def get_available_port(self, start: int = 8080, end: int = 9999) -> int:
        for port in range(start, end + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(("127.0.0.1", port))
                continue
            except (socket.error, OSError):
                return port
        raise RuntimeError("No available port found")

    def list_models(self) -> List[Dict[str, Any]]:
        resp = self._get("/models")
        resp.raise_for_status()
        return resp.json().get("models", [])

    def start_server(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        mmproj_path: Optional[str] = None,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        ctx_size: int = 8192,
        n_gpu_layers: Optional[int] = None,
        n_threads: Optional[int] = None,
        batch_size: Optional[int] = None,
        flash_attention: bool = True,
        additional_args: Optional[str] = None,
        wait_ready: bool = True,
        wait_timeout: float = 60.0,
    ) -> str:
        params: Dict[str, Any] = {
            "host": host,
            "ctx_size": ctx_size,
            "flash_attention": flash_attention,
        }

        if model_path:
            params["model_path"] = model_path
        elif model_name:
            params["model_name"] = model_name
        else:
            raise ValueError("Either model_path or model_name must be provided")

        if mmproj_path:
            params["mmproj_path"] = mmproj_path

        if port is None:
            port = self.get_available_port()

        params["port"] = port

        if n_gpu_layers is not None:
            params["n_gpu_layers"] = n_gpu_layers
        if n_threads is not None:
            params["n_threads"] = n_threads
        if batch_size is not None:
            params["batch_size"] = batch_size
        if additional_args:
            params["additional_args"] = additional_args

        resp = self._post("/start", params=params, timeout=wait_timeout)
        resp.raise_for_status()
        url = resp.json()["url"]

        if wait_ready:
            start_time = time.time()
            while time.time() - start_time < wait_timeout:
                try:
                    health_resp = requests.get(f"{url}/health", timeout=5.0)
                    if health_resp.status_code == 200:
                        return url
                except Exception:
                    pass
                time.sleep(1.0)
            raise TimeoutError(
                f"llama-server started at {url} but failed to become ready within {wait_timeout}s"
            )

        return url

    def stop_server(self) -> None:
        resp = self._post("/stop", timeout=30.0)
        resp.raise_for_status()

    def restart_server(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ) -> str:
        if self.is_server_running():
            self.stop_server()
            time.sleep(1.0)
        return self.start_server(model_path=model_path, model_name=model_name, **kwargs)


def find_free_port(start: int = 8080, end: int = 9999) -> int:
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
    raise RuntimeError("No available port found in range")


def get_default_models_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = os.environ.get("APPDATA", "C:/Users/Public")
        return os.path.join(base, "PaddleOCR-Desktop", "models", "llama")
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return os.path.join(xdg, "PaddleOCR-Desktop", "models", "llama")
        home = os.path.expanduser("~")
        return os.path.join(home, ".local", "share", "PaddleOCR-Desktop", "models", "llama")
