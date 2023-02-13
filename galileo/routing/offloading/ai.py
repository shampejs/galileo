import logging

import requests

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
        # TODO implement
        raise NotImplementedError()

    def invoke_model(self, req: OffloadServiceRequest):
        # TODO invoke model
        raise NotImplementedError()

    def local_execution(self, req: OffloadServiceRequest) -> requests.Response:
        return self.invoke_model(req)
