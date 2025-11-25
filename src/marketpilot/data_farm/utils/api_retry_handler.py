"""
API Retry Handler Utility
Shared retry logic and error handling for all adapters
"""

from typing import Dict, Any, Optional
import aiohttp
import asyncio
from marketpilot.utils.logger import log_event


class APIRetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        backoff_factor: float = 2.0,
        timeout: int = 30,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.timeout = timeout


class APIRetryHandler:
    """
    Handles API requests with retry logic and error handling
    Can be used by all adapters (price, news, fundamental, etc.)
    """

    def __init__(self, adapter_id: str, config: Optional[APIRetryConfig] = None):
        """
        Initialize retry handler

        Args:
            adapter_id: Identifier for the adapter using this handler
            config: Retry configuration (uses defaults if not provided)
        """
        self.adapter_id = adapter_id
        self.config = config or APIRetryConfig()

    async def fetch_with_retry(
        self,
        url: str,
        symbol: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        """
        Fetch data from API with retry logic and exponential backoff

        Args:
            url: API endpoint URL
            symbol: Symbol being fetched (for logging)
            method: HTTP method (GET, POST, etc.)
            headers: Optional HTTP headers
            data: Optional request body for POST requests

        Returns:
            tuple: (status_code, response_data)
                - status_code: HTTP status code (0 if all retries failed)
                - response_data: Parsed JSON response or None
        """
        retry_count = 0
        last_error = None

        while retry_count <= self.config.max_retries:
            try:
                # Calculate delay for this attempt (skip for first attempt)
                if retry_count > 0:
                    delay = self._calculate_delay(retry_count)
                    log_event(
                        stage="ingestion",
                        block="api_retry",
                        level="INFO",
                        msg=f"Retry attempt {retry_count}/{self.config.max_retries} after {delay:.1f}s delay",
                        extra={
                            "adapter_id": self.adapter_id,
                            "symbol": symbol,
                            "retry_count": retry_count,
                            "delay_seconds": delay,
                            "url": url,
                        },
                    )
                    await asyncio.sleep(delay)

                # Make HTTP request
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    ) as response:
                        status = response.status

                        # Success case
                        if status == 200:
                            try:
                                response_data = await response.json()
                                log_event(
                                    stage="ingestion",
                                    block="api_retry",
                                    level="DEBUG",
                                    msg="Request successful (200)",
                                    extra={
                                        "adapter_id": self.adapter_id,
                                        "symbol": symbol,
                                        "attempt": retry_count + 1,
                                    },
                                )
                                return (status, response_data)
                            except Exception as json_error:
                                log_event(
                                    stage="ingestion",
                                    block="api_retry",
                                    level="ERROR",
                                    msg=f"Failed to parse JSON response: {str(json_error)}",
                                    extra={
                                        "adapter_id": self.adapter_id,
                                        "symbol": symbol,
                                    },
                                )
                                return (status, None)

                        # Handle different error codes
                        error_handling = self._handle_http_error(
                            status, response, symbol
                        )

                        if error_handling["should_retry"]:
                            last_error = error_handling["error_message"]
                            retry_count += 1

                            # For rate limits, add extra delay
                            if status == 429 and retry_count <= self.config.max_retries:
                                extra_delay = 5  # Extra 5 seconds for rate limits
                                log_event(
                                    stage="ingestion",
                                    block="api_retry",
                                    level="WARNING",
                                    msg=f"Rate limited - adding extra {extra_delay}s delay",
                                    extra={
                                        "adapter_id": self.adapter_id,
                                        "symbol": symbol,
                                    },
                                )
                                await asyncio.sleep(extra_delay)
                            continue
                        else:
                            # Don't retry - return error immediately
                            return (status, None)

            except aiohttp.ClientError as e:
                log_event(
                    stage="ingestion",
                    block="api_retry",
                    level="WARNING",
                    msg="Network error - will retry",
                    extra={
                        "adapter_id": self.adapter_id,
                        "symbol": symbol,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "attempt": retry_count + 1,
                    },
                )
                last_error = f"Network error: {str(e)}"
                retry_count += 1
                continue

            except asyncio.TimeoutError:
                log_event(
                    stage="ingestion",
                    block="api_retry",
                    level="WARNING",
                    msg=f"Request timeout ({self.config.timeout}s) - will retry",
                    extra={
                        "adapter_id": self.adapter_id,
                        "symbol": symbol,
                        "timeout": self.config.timeout,
                        "attempt": retry_count + 1,
                    },
                )
                last_error = f"Request timeout ({self.config.timeout}s)"
                retry_count += 1
                continue

            except Exception as e:
                log_event(
                    stage="ingestion",
                    block="api_retry",
                    level="ERROR",
                    msg=f"Unexpected error: {str(e)}",
                    extra={
                        "adapter_id": self.adapter_id,
                        "symbol": symbol,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                return (0, None)

        # All retries exhausted
        log_event(
            stage="ingestion",
            block="api_retry",
            level="ERROR",
            msg=f"All {self.config.max_retries} retry attempts exhausted",
            extra={
                "adapter_id": self.adapter_id,
                "symbol": symbol,
                "last_error": last_error,
                "url": url,
            },
        )
        return (0, None)

    async def _handle_http_error(
        self, status: int, response: aiohttp.ClientResponse, symbol: str
    ) -> Dict[str, Any]:
        """
        Handle different HTTP error codes and determine retry strategy

        Args:
            status: HTTP status code
            response: Response object
            symbol: Symbol being fetched

        Returns:
            Dict with 'should_retry' and 'error_message'
        """
        text = await response.text()

        # 503 Service Unavailable - Retry
        if status == 503:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="WARNING",
                msg="Service unavailable (503) - will retry",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                    "response": text[:200],
                },
            )
            return {
                "should_retry": True,
                "error_message": "Service unavailable (503)",
            }

        # 429 Rate Limited - Retry with extra delay
        elif status == 429:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="WARNING",
                msg="Rate limited (429) - will retry",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                },
            )
            return {"should_retry": True, "error_message": "Rate limited (429)"}

        # 500, 502, 504 Server Errors - Retry
        elif status in [500, 502, 504]:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="WARNING",
                msg=f"Server error ({status}) - will retry",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                    "response": text[:200],
                },
            )
            return {
                "should_retry": True,
                "error_message": f"Server error ({status})",
            }

        # 400, 401, 403, 404 Client Errors - Don't retry
        elif status in [400, 401, 403, 404]:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="ERROR",
                msg=f"Client error ({status}) - not retrying",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                    "response": text[:200],
                },
            )
            return {
                "should_retry": False,
                "error_message": f"Client error ({status})",
            }

        # Other errors - Retry cautiously
        else:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="WARNING",
                msg=f"Unexpected status ({status}) - will retry",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                    "response": text[:200],
                },
            )
            return {
                "should_retry": True,
                "error_message": f"Unexpected status ({status})",
            }

    def _calculate_delay(self, retry_count: int) -> float:
        """
        Calculate delay for exponential backoff

        Args:
            retry_count: Current retry attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        return self.config.retry_delay * (
            self.config.backoff_factor ** (retry_count - 1)
        )


# Convenience function for creating retry handler
def create_retry_handler(
    adapter_id: str,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    backoff_factor: float = 2.0,
    timeout: int = 30,
) -> APIRetryHandler:
    """
    Create a configured retry handler

    Args:
        adapter_id: Identifier for the adapter
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (seconds)
        backoff_factor: Exponential backoff multiplier
        timeout: Request timeout (seconds)

    Returns:
        Configured APIRetryHandler instance
    """
    config = APIRetryConfig(
        max_retries=max_retries,
        retry_delay=retry_delay,
        backoff_factor=backoff_factor,
        timeout=timeout,
    )
    return APIRetryHandler(adapter_id, config)