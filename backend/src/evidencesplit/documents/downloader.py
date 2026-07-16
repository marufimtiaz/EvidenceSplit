import asyncio
import ipaddress
import logging
import socket
import tempfile
from urllib.parse import urljoin, urlparse

import httpx

from evidencesplit.config import settings
from evidencesplit.shared.http_errors import ProviderHTTPError

logger = logging.getLogger(__name__)


class SafePDFDownloader:
    redirect_statuses = {301, 302, 303, 307, 308}

    @staticmethod
    async def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Unsafe remote PDF URL.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            parsed.hostname,
            port,
            type=socket.SOCK_STREAM,
        )
        if not addresses:
            raise ValueError("Remote PDF host could not be resolved.")
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0].split("%")[0])
            if not ip.is_global:
                raise ValueError("Remote PDF host resolves to a private or local address.")

    async def download(self, url: str) -> str:
        max_bytes = settings.MAX_REMOTE_PDF_SIZE_MB * 1024 * 1024
        current_url = url
        logger.info("external_request provider=remote_pdf operation=download host=%s", urlparse(url).hostname)
        async with httpx.AsyncClient(
            timeout=settings.REMOTE_DOWNLOAD_TIMEOUT_SECONDS,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            for _ in range(4):
                await self._validate_url(current_url)
                async with client.stream("GET", current_url, headers={"Accept": "application/pdf"}) as response:
                    if response.status_code in self.redirect_statuses:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("Remote PDF redirect had no destination.")
                        current_url = urljoin(current_url, location)
                        logger.info(
                            "external_redirect provider=remote_pdf operation=download host=%s",
                            urlparse(current_url).hostname,
                        )
                        continue
                    if response.is_error:
                        await response.aread()
                        error = ProviderHTTPError.from_response("remote_pdf", "download", response)
                        logger.error(
                            "external_failure provider=%s operation=%s status=%s host=%s detail=%s",
                            error.provider,
                            error.operation,
                            error.status_code,
                            urlparse(current_url).hostname,
                            error.detail,
                        )
                        raise error
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > max_bytes:
                        raise ValueError("Remote PDF exceeds the download size limit.")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > max_bytes:
                            raise ValueError("Remote PDF exceeds the download size limit.")
                    content_type = response.headers.get("content-type", "").lower()
                    has_pdf_signature = bytes(content[:4]) == b"%PDF"
                    if "application/pdf" not in content_type and not has_pdf_signature:
                        raise ValueError("Remote response is not a PDF.")
                    if not has_pdf_signature:
                        raise ValueError("Remote file has an invalid PDF signature.")
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    try:
                        temp_file.write(content)
                        logger.info(
                            "external_success provider=remote_pdf operation=download host=%s bytes=%s",
                            urlparse(current_url).hostname,
                            len(content),
                        )
                        return temp_file.name
                    finally:
                        temp_file.close()
        raise ValueError("Remote PDF exceeded the redirect limit.")
