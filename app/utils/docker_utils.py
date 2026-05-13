import os
import logging
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def is_running_in_docker() -> bool:
    return any(
        os.environ.get(name, "").lower() in ("1", "true", "yes")
        for name in ("RUNNING_IN_DOCKER", "DOCKER_CONTAINER")
    ) or os.path.exists("/.dockerenv")


def rewrite_localhost_for_docker(base_url: str | None) -> str | None:
    """
    When running inside Docker, rewrite localhost / 127.0.0.1 / ::1 in
    *base_url* to ``host.docker.internal`` so the request can reach
    services exposed on the host machine.

    Also ensures ``host.docker.internal`` is added to ``NO_PROXY`` /
    ``no_proxy`` so the request is not routed through the HTTP proxy.

    Returns the rewritten URL (or the original if no rewrite is needed).
    """
    if not base_url:
        return base_url

    if not is_running_in_docker():
        return base_url

    parsed = urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("localhost", "127.0.0.1", "::1"):
        return base_url

    replacement_netloc = "host.docker.internal"
    if parsed.port:
        replacement_netloc = f"{replacement_netloc}:{parsed.port}"

    rewritten = urlunparse(
        (
            parsed.scheme or "http",
            replacement_netloc,
            parsed.path or "",
            "",
            "",
            "",
        )
    )
    logger.info(
        "🐳 Docker环境检测：将 %s 重写为 %s "
        "(localhost在容器内指向容器自身，host.docker.internal指向宿主机)",
        base_url,
        rewritten,
    )

    _ensure_no_proxy()

    return rewritten


_NO_PROXY_PATCHED = False


def _ensure_no_proxy():
    global _NO_PROXY_PATCHED
    if _NO_PROXY_PATCHED:
        return
    target = "host.docker.internal"
    for var in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(var, "")
        if target not in current:
            os.environ[var] = f"{current},{target}" if current else target
    _NO_PROXY_PATCHED = True
    logger.info("🐳 已将 host.docker.internal 添加到 NO_PROXY，避免代理干扰内部请求")
