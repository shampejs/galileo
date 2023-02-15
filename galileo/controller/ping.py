import pandas as pd
import logging
from galileofaas.context.platform.telemetry.rds import RedisTelemetryService
logger = logging.getLogger(__name__)

class PingController:

    def __init__(self, telemetry_service: RedisTelemetryService):
        self.telemetry_service = telemetry_service

    def get_ping(self):
        node = 'localhost.localdomain'
        metric = 'ping_avg'
        ping: pd.DataFrame = self.telemetry_service.get_node_resource(node, metric)
        if ping is None or ping.size == 0:
            return 0

        return ping['value'][-3:].mean()