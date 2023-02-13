import logging

import requests

from galileo.routing import HostRouter
from galileo.routing.offloading import OffloadRouter
from galileo.routing.offloading.request import OffloadServiceRequest

logger = logging.getLogger(__name__)


class SimulatedOffloadRouter(OffloadRouter):
    """
    This router implementation is capable of offloading requests via HTTP but can also
    execute requests locally by sleeping for a specified duration.
    """

    def __init__(self, host_router: HostRouter):
        super().__init__(host_router)


    def local_execution(self, req: OffloadServiceRequest) -> requests.Response:
        raise NotImplementedError()
