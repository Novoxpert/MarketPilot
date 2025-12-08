"""
API Retry Handler Utility
Shared retry logic and error handling for all adapters
"""


from typing import Dict, Any, Optional, Tuple
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
    Handles API requests with retry logic, validation, and error handling
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

    def validate_response(self, response_data: Any, status_code: int) -> Tuple[bool, Optional[str]]:
        """
        Validate API response structure
        
        This method handles:
        - Null responses
        - Type validation (must be dict)
        - Error detection (explicit error fields)
        - Success flag validation
        - Data field requirement
        - Empty results (valid!)
        
        Returns:
            Tuple[is_valid, error_message]
            - is_valid: True if response is valid (including empty data)
            - error_message: Error description if invalid, None otherwise
        """
        # Null response
        if response_data is None:
            return False, f"Null response with status {status_code}"
        
        # Must be a dictionary
        if not isinstance(response_data, dict):
            return False, f"Expected dict, got {type(response_data).__name__}"
        
        # Check for explicit error field at root level
        if "error" in response_data:
            error_detail = response_data.get("error")
            if isinstance(error_detail, dict):
                error_msg = error_detail.get("message", str(error_detail))
            else:
                error_msg = str(error_detail)
            return False, f"API error: {error_msg}"
        
        # Check for nested error in 'detail' field
        if "detail" in response_data:
            detail = response_data["detail"]
            if isinstance(detail, dict) and "error" in detail:
                error_info = detail["error"]
                if isinstance(error_info, dict):
                    error_msg = error_info.get("message", str(error_info))
                else:
                    error_msg = str(error_info)
                return False, f"API error: {error_msg}"
        
        # If success flag exists, respect it
        if "success" in response_data:
            if response_data["success"] is False:
                # Get error message if available
                error_msg = response_data.get("error", "API returned success=false")
                return False, str(error_msg)
            # success=true, continue validation
        
        # Must have 'data' field for valid response
        if "data" not in response_data:
            # Special case: if response has pagination/metadata but no data field
            # This might indicate an API structure issue
            if "pagination" in response_data or "metadata" in response_data:
                log_event(
                    stage="ingestion",
                    block="api_retry",
                    level="WARNING",
                    msg="Response has pagination/metadata but no data field",
                    extra={
                        "adapter_id": self.adapter_id,
                        "response_keys": list(response_data.keys()),
                    },
                )
            return False, "Missing 'data' field in response"
        
        # Valid response
        # Note: data can be empty list [] or empty dict {} - that's perfectly valid!
        return True, None

    async def fetch_with_retry(
        self,
        url: str,
        symbol: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Fetch data from API with retry logic, validation, and exponential backoff

        Args:
            url: API endpoint URL
            symbol: Symbol being fetched (for logging)
            method: HTTP method (GET, POST, etc.)
            headers: Optional HTTP headers
            data: Optional request body for POST requests
            validate: Whether to validate response structure (default: True)

        Returns:
            tuple: (status_code, response_data)
                - status_code: HTTP status code (0 if all retries failed)
                - response_data: Parsed JSON response or None if invalid/failed
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
                        msg=f"Retry {retry_count}/{self.config.max_retries} after {delay:.1f}s",
                        extra={
                            "adapter_id": self.adapter_id,
                            "symbol": symbol,
                            "retry_count": retry_count,
                            "delay_seconds": delay,
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

                        # Success case (200)
                        if status == 200:
                            try:
                                response_data = await response.json()
                                
                                # Validate response structure if requested
                                if validate:
                                    is_valid, error_msg = self.validate_response(response_data, status)
                                    if not is_valid:
                                        log_event(
                                            stage="ingestion",
                                            block="api_retry",
                                            level="ERROR",
                                            msg=f"Invalid response structure: {error_msg}",
                                            extra={
                                                "adapter_id": self.adapter_id,
                                                "symbol": symbol,
                                                "error": error_msg,
                                                "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else None,
                                            },
                                        )
                                        # Return 200 with None to indicate validation failure
                                        # Adapter will treat this as an error
                                        return (status, None)
                                
                                log_event(
                                    stage="ingestion",
                                    block="api_retry",
                                    level="DEBUG",
                                    msg="Request successful",
                                    extra={
                                        "adapter_id": self.adapter_id,
                                        "symbol": symbol,
                                        "attempt": retry_count + 1,
                                    },
                                )
                                return (status, response_data)
                            
                            except (aiohttp.ContentTypeError, ValueError) as json_error:
                                log_event(
                                    stage="ingestion",
                                    block="api_retry",
                                    level="ERROR",
                                    msg=f"Failed to parse JSON response: {str(json_error)}",
                                    extra={
                                        "adapter_id": self.adapter_id,
                                        "symbol": symbol,
                                        "error_type": type(json_error).__name__,
                                    },
                                )
                                return (status, None)

                        # Handle HTTP errors (non-200 status codes)
                        error_handling = await self._handle_http_error(
                            status, response, symbol
                        )

                        if error_handling["should_retry"]:
                            last_error = error_handling["error_message"]
                            retry_count += 1

                            # For rate limits, add extra delay before continuing
                            if status == 429 and retry_count <= self.config.max_retries:
                                extra_delay = 5.0
                                log_event(
                                    stage="ingestion",
                                    block="api_retry",
                                    level="WARNING",
                                    msg=f"Rate limited - adding {extra_delay}s extra delay",
                                    extra={
                                        "adapter_id": self.adapter_id,
                                        "symbol": symbol,
                                    },
                                )
                                await asyncio.sleep(extra_delay)
                            continue
                        else:
                            # Don't retry - return error status immediately
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
                # For unexpected errors, don't retry
                return (0, None)

        # All retries exhausted
        log_event(
            stage="ingestion",
            block="api_retry",
            level="ERROR",
            msg=f"All {self.config.max_retries} retries exhausted",
            extra={
                "adapter_id": self.adapter_id,
                "symbol": symbol,
                "last_error": last_error,
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
            Dict with:
                - 'should_retry': bool - whether to retry this request
                - 'error_message': str - description of the error
        """
        # Get response text for logging (limit to 200 chars)
        try:
            text = await response.text()
            response_preview = text[:200] if text else ""
        except Exception:
            response_preview = "<unable to read response>"

        # 5xx Server Errors - Always retry
        if status in [500, 502, 503, 504]:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="WARNING",
                msg=f"Server error ({status}) - will retry",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                    "response": response_preview,
                },
            )
            return {
                "should_retry": True,
                "error_message": f"Server error ({status})",
            }

        # 429 Rate Limited - Retry with extra delay
        elif status == 429:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="WARNING",
                msg="Rate limited (429) - will retry with extra delay",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                },
            )
            return {
                "should_retry": True,
                "error_message": "Rate limited (429)",
            }

        # 4xx Client Errors - Don't retry (except 429)
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
                    "response": response_preview,
                },
            )
            return {
                "should_retry": False,
                "error_message": f"Client error ({status})",
            }

        # Other unexpected status codes - Retry cautiously
        else:
            log_event(
                stage="ingestion",
                block="api_retry",
                level="WARNING",
                msg=f"Unexpected status code ({status}) - will retry",
                extra={
                    "adapter_id": self.adapter_id,
                    "symbol": symbol,
                    "status": status,
                    "response": response_preview,
                },
            )
            return {
                "should_retry": True,
                "error_message": f"Unexpected status ({status})",
            }

    def _calculate_delay(self, retry_count: int) -> float:
        """
        Calculate delay for exponential backoff

        Formula: delay = retry_delay * (backoff_factor ^ (retry_count - 1))
        
        Examples with default config (retry_delay=2.0, backoff_factor=2.0):
        - retry 1: 2.0 * (2.0 ^ 0) = 2.0 seconds
        - retry 2: 2.0 * (2.0 ^ 1) = 4.0 seconds
        - retry 3: 2.0 * (2.0 ^ 2) = 8.0 seconds

        Args:
            retry_count: Current retry attempt number (1-indexed)

        Returns:
            Delay in seconds (float)
        """
        return self.config.retry_delay * (
            self.config.backoff_factor ** (retry_count - 1)
        )


def create_retry_handler(
    adapter_id: str,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    backoff_factor: float = 2.0,
    timeout: int = 30,
) -> APIRetryHandler:
    """
    Create a configured retry handler (convenience function)

    Args:
        adapter_id: Identifier for the adapter
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 2.0)
        backoff_factor: Exponential backoff multiplier (default: 2.0)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Configured APIRetryHandler instance

    Example:
        >>> handler = create_retry_handler("news_adapter_001", max_retries=5)
        >>> status, data = await handler.fetch_with_retry(url, "BTCUSDT")
    """
    config = APIRetryConfig(
        max_retries=max_retries,
        retry_delay=retry_delay,
        backoff_factor=backoff_factor,
        timeout=timeout,
    )
    return APIRetryHandler(adapter_id, config)