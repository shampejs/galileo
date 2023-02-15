import logging
import time

import requests

from galileo.routing import HostRouter
from galileo.routing.offloading.request import OffloadServiceRequest
from galileo.routing.router import Router

logger = logging.getLogger(__name__)


class OffloadRouter(Router):
    """
    This router implementation  is capable of offloading requests via HTTP but can also
    execute requests locally.
    """

    def __init__(self, host_router: HostRouter):
        super().__init__()
        self.host_router = host_router

    def remote_execution(self, req: OffloadServiceRequest):
        url = self.host_router._get_url(req)

        logger.debug('forwarding request %s %s', req.method, url)

        req.sent = time.time()
        print("external", req.method, url, **req.kwargs)
        response = requests.request(req.method, url, **req.kwargs)
        req.done = req.sent

        logger.debug('%s %s: %s', req.method, url, response.status_code)
        self.requests_since_last_log_update += 1
        if time.time() - self.last_log_update >= 1:
            logger.debug(f'Sent {self.requests_since_last_log_update} requests in the last second')
            self.requests_since_last_log_update = 0
            self.last_log_update = time.time()
        return response

    def local_execution(self, req: OffloadServiceRequest) -> requests.Response:
        ...

    def request(self, req: OffloadServiceRequest) -> requests.Response:
        if req.offload:
            return self.remote_execution(req)
        else:
            return self.local_execution(req)
