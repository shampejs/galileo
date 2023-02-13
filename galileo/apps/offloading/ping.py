from galileo.apps.app import OffloadAppClient
from galileo.controller.ping import PingController


class PingAppClient(OffloadAppClient):

    def __init__(self, ping_ctrl: PingController, parameters=None):
        self.ping_ctrl = ping_ctrl
        if parameters:
            method = parameters.get('method', 'get')
            path = parameters.get('path', '/')
            kwargs = parameters.get('kwargs')
        else:
            method = 'get'
            path = '/'
            kwargs = None

        client = PingOffloadClient(ping_ctrl, method, path, kwargs)

        super().__init__('http', None, client)

class PingOffloadClient:

    def __init__(self, ping_ctrl: PingController, method='get', path='/', parameters=None) -> None:
        super().__init__()
        self.ping_ctrl = ping_ctrl
        self.method = method
        self.path = path
        self.parameters = parameters or {}

    def next_request(self):
        # TODO: decide to offload or not
        ping = self.ping_ctrl.get_ping()
        if ping < 30:
            offload = True
        else:
            offload = False

        return self.method, self.path, offload, self.parameters
