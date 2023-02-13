import time

from galileo.routing import ServiceRequest


class OffloadServiceRequest(ServiceRequest):
    service: str
    path: str
    method: str
    kwargs: dict
    "if offload == True -> offload request (i.e., via HTTP), if !offload -> process request locally"
    offload: bool

    created: float
    sent: float
    done: float

    def __init__(self, service, path='/', method='get', offload=True, **kwargs) -> None:
        super().__init__(service, path, method, **kwargs)
        self.service = service
        self.path = path
        self.method = method
        self.offload = offload
        self.kwargs = kwargs

        self.created = time.time()
