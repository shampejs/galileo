from galileo.apps.app import OffloadAppClient
from galileo.controller.wifi import WifiController


class WifiAppClient(OffloadAppClient):

    def __init__(self, wifi_ctrl: WifiController, parameters=None):
        self.wifi_ctrl = wifi_ctrl
        if parameters:
            method = parameters.get('method', 'get')
            path = parameters.get('path', '/')
            kwargs = parameters.get('kwargs')
        else:
            method = 'get'
            path = '/'
            kwargs = None

        client = WifiOffloadClient(method, path, kwargs)

        super().__init__('http', None, client)

class WifiOffloadClient:

    def __init__(self, wifi_ctrl: WifiController, method='get', path='/', parameters=None) -> None:
        super().__init__()
        self.wifi_ctrl = wifi_ctrl
        self.method = method
        self.path = path
        self.parameters = parameters or {}

    def next_request(self):
        # TODO: decide to offload or not
        wifi_quality = self.wifi_ctrl.get_wifi_quality()
        if wifi_quality < 30:
            offload = True
        else:
            offload = False

        return self.method, self.path, offload, self.parameters
