import functools
import logging
import os
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

from .constants import USER_AGENT
from .filesystem import overwrite

logger = logging.getLogger(__name__)


class SourceAddressAdapter(HTTPAdapter):
    def __init__(self, address: str, **kwargs):
        self.source_address = (address, 0)
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["source_address"] = self.source_address
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs["source_address"] = self.source_address
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def create_requests_session() -> requests.Session:
    s = requests.Session()
    # hardcode 1min timeout for connect & read for now
    # https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
    # A hack to overwrite get() method
    s.get_orig, s.get = s.get, functools.partial(s.get, timeout=(60, 60))  # type: ignore
    retries = Retry(total=3, backoff_factor=0.1)
    bind_address = os.environ.get("BIND_ADDRESS")
    for scheme in ("http://", "https://"):
        adapter = (
            SourceAddressAdapter(bind_address, max_retries=retries)
            if bind_address
            else HTTPAdapter(max_retries=retries)
        )
        s.mount(scheme, adapter)
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def download(
    session: requests.Session, url: str, dest: Path
) -> tuple[bool, requests.Response | None]:
    try:
        resp = session.get(url, allow_redirects=True)
    except requests.RequestException:
        logger.warning("download %s failed with exception", exc_info=True)
        return False, None
    if resp.status_code >= 400:
        logger.warning(
            "download %s failed with status %s, skipping this package",
            url,
            resp.status_code,
        )
        return False, resp
    with overwrite(dest, "wb") as f:
        f.write(resp.content)
    return True, resp
