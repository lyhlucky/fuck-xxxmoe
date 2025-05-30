import threading
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, before
import logging


logger = logging.getLogger('CurlX')

try:
    import curl_cffi
    from curl_cffi import requests as core_requests
    from curl_cffi.requests.exceptions import RequestException as CurlRequestException, SSLError as CurlSSLError
    import requests
    from requests.utils import cookiejar_from_dict
    CoreRequestExceptions = (requests.RequestException, CurlRequestException, CurlSSLError)
    USE_CURL_CFFI = True
except ImportError:
    logger.info('import curl_cffi failed, try import httpx...')
    import httpx as core_requests
    from httpx import HTTPError, RequestError
    CoreRequestExceptions = (HTTPError, RequestError)
    USE_CURL_CFFI = False
    
    
class CurlX:
    def __init__(
        self,
        headers=None,
        cookies=None,
        proxies=None,
        timeout=10,
        verify=True,
        retries=3,
        retry_wait=1
    ):
        self.headers = headers or {}
        self.proxies = proxies
        self.timeout = timeout
        self.verify = verify
        self.retries = retries
        self.retry_wait = retry_wait
        self.cookies = self._normalize_cookies(cookies)

        self._retry_local = threading.local()

        if USE_CURL_CFFI:
            self.session = core_requests.Session()
            self.session.headers.update(self.headers)
            self.session.verify = self.verify
            if isinstance(self.cookies, dict):
                jar = cookiejar_from_dict(self.cookies, overwrite=True)
                self.session.cookies.update(jar)
        else:
            self._create_httpx_client(verify=self.verify, proxy=self.proxies)
            
    def _normalize_cookies(self, cookies):
        if isinstance(cookies, str):
            return self._parse_cookie_string(cookies)
        elif isinstance(cookies, dict):
            return cookies
        return {}

    def _create_httpx_client(self, verify=True, proxy=None):
        client_args = {
            "headers": self.headers,
            "timeout": self.timeout,
            "verify": verify,
            "cookies": self.cookies,
        }
        if proxy:
            if isinstance(proxy, dict):
                proxy = proxy.get("https") or proxy.get("http")
            client_args["proxy"] = proxy

        self.session = core_requests.Client(**client_args)

    def update_headers(self, headers):
        self.headers = self._merge_headers_case_insensitive(self.headers, headers)
        self.session.headers.update(headers)

    def update_cookies(self, cookies):
        cookies = self._normalize_cookies(cookies)
        self.cookies.update(cookies)
        if USE_CURL_CFFI:
            jar = cookiejar_from_dict(cookies, overwrite=True)
            self.session.cookies.update(jar)
        else:
            self.session.cookies.update(cookies)

    def _before_retry(self, retry_state):
        attempt = retry_state.attempt_number
        self._retry_local.count = attempt
        if attempt > 1:
            logger.info(f"Retry attempt {attempt}...")

    def _get_retry_decorator(self):
        return retry(
            reraise=True,
            stop=stop_after_attempt(self.retries),
            wait=wait_fixed(self.retry_wait),
            retry=retry_if_exception_type(CoreRequestExceptions),
            before=self._before_retry,
        )

    def _make_request(self, method, url, **kwargs):
        headers = kwargs.pop("headers", {})
        headers = self._merge_headers_case_insensitive(self.headers, headers)
        timeout = kwargs.pop("timeout", self.timeout)
        cookies = kwargs.pop("cookies", None)
        data = kwargs.pop("data", None)
        json_data = kwargs.pop("json", None)
        params = kwargs.pop("params", None)
        proxy_override = kwargs.pop("proxies", self.proxies)
        stream = kwargs.pop("stream", False)

        # 第3次重试关闭证书验证
        retry_count = getattr(self._retry_local, "count", 1)
        should_disable_verify = retry_count == 3

        if USE_CURL_CFFI:
            if should_disable_verify:
                logger.info("Disabling SSL verification on 3rd attempt.")
                self.session.verify = False
            request_args = {
                "headers": headers,
                "timeout": timeout,
                "cookies": cookies,
                "data": data,
                "json": json_data,
                "params": params,
                "verify": self.session.verify,
                "proxies": proxy_override,
                "stream": stream
            }
            return self.session.request(method, url, **request_args)
        else:
            if should_disable_verify:
                logger.info("Disabling SSL verification on 3rd attempt.")
                self._create_httpx_client(verify=False, proxy=proxy_override)

            request_args = {
                "headers": headers,
                "timeout": timeout,
                "cookies": cookies,
                "data": data,
                "json": json_data,
                "params": params,
            }
            if stream:
                request_args["stream"] = True
            return self.session.request(method, url, **request_args)
       
    def _parse_cookie_string(self, cookie_str):
        cookies = {}
        for part in cookie_str.split(';'):
            if '=' in part:
                key, value = part.strip().split('=', 1)
                cookies[key] = value
        return cookies
    
    def _merge_headers_case_insensitive(self, base, override):
        lower_keys = {k.lower(): k for k in base}
        result = base.copy()
        for k, v in override.items():
            orig_key = lower_keys.get(k.lower(), k)
            result[orig_key] = v
        return result

    def request(self, method, url, **kwargs):
        retry_wrapper = self._get_retry_decorator()
        return retry_wrapper(self._make_request)(method, url, **kwargs)

    def get(self, url, **kwargs): return self.request("GET", url, **kwargs)
    def post(self, url, **kwargs): return self.request("POST", url, **kwargs)
    def put(self, url, **kwargs): return self.request("PUT", url, **kwargs)
    def delete(self, url, **kwargs): return self.request("DELETE", url, **kwargs)
    def close(self): self.session.close()
