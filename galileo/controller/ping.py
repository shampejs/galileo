from galileofaas.context.platform.telemetry.rds import RedisTelemetryService


class PingController:

    def __init__(self, telemetry_service: RedisTelemetryService):
        self.telemetry_service = telemetry_service

    def get_ping(self):
        raise NotImplementedError()
