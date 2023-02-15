import logging
import time
import requests
import docker

from galileo.routing import HostRouter
from galileo.routing.offloading import OffloadRouter
from galileo.routing.offloading.request import OffloadServiceRequest

logger = logging.getLogger(__name__)


class AIOffloadRouter(OffloadRouter):
    """
    This router implementation loads a model at startup and is capable of offloading requests via HTTP but can also
    execute requests locally invoking the loaded model.
    """

    def __init__(self, host_router: HostRouter):
        super().__init__(host_router)
        self.model = self.load_model()

    def load_model(self):
        # TODO implement - fürs erste mal lassen später ergänzen
        pass

    def invoke_model(self, req: OffloadServiceRequest):
        url = 'http://localhost:8080'

        logger.debug('forwarding request %s %s', req.method, url)

        req.sent = time.time()
        response = requests.request(req.method, 'http://localhost:8080', **req.kwargs)
        req.done = req.sent

        logger.debug('%s %s: %s', req.method, url, response.status_code)
        self.requests_since_last_log_update += 1
        if time.time() - self.last_log_update >= 1:
            logger.debug(f'Sent {self.requests_since_last_log_update} requests in the last second')
            self.requests_since_last_log_update = 0
            self.last_log_update = time.time()
        return response

    def local_execution(self, req: OffloadServiceRequest) -> requests.Response:
        return self.invoke_model(req)
