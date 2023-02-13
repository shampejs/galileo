import pandas as pd
from galileofaas.context.platform.telemetry.rds import RedisTelemetryService


class WifiController:

    def __init__(self, telemetry_service: RedisTelemetryService):
        self.telemetry_service = telemetry_service

    def get_wifi_quality(self):
        node = ''
        metric = 'signal'
        signals: pd.DataFrame = self.telemetry_service.get_node_resource(node, metric)
        return signals['value'].mean()

    def switch_wifi(self):
        raise NotImplementedError()
