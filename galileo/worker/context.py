import atexit
import logging
import os
import random
import time
from socket import gethostname
from typing import MutableMapping, List, Dict

import redis
import requests
from examples.basic.podfactory import BasicExamplePodFactory
from faas.system import Clock, LoggingLogger
from galileodb import ExperimentDatabase
from galileodb.factory import create_experiment_database_from_env
from galileodb.trace import TraceLogger, TraceWriter, FileTraceWriter, RedisTopicTraceWriter, DatabaseTraceWriter
from galileofaas.connections import RedisClient
from galileofaas.context.daemon import GalileoFaasContextDaemon
from galileofaas.context.model import GalileoFaasContext
from galileofaas.context.platform.deployment.factory import create_deployment_service
from galileofaas.context.platform.network.factory import create_network_service
from galileofaas.context.platform.node.factory import create_node_service
from galileofaas.context.platform.replica.factory import KubernetesFunctionReplicaFactory, create_replica_service
from galileofaas.context.platform.telemetry.factory import create_telemetry_service
from galileofaas.context.platform.trace.factory import create_trace_service
from galileofaas.context.platform.zone.factory import create_zone_service
from galileofaas.system.core import GalileoFaasMetrics
from galileofaas.system.metrics import GalileoLogger
from kubernetes import config, client
from telemc import TelemetryController

from galileo.apps.loader import AppClientLoader, AppClientDirectoryLoader, AppRepositoryFallbackLoader
from galileo.apps.repository import RepositoryClient
from galileo.controller.ping import PingController
from galileo.controller.wifi import WifiController
from galileo.routing import Router, ServiceRequest, ServiceRouter, HostRouter, StaticRouter, RedisRoutingTable, \
    ReadOnlyListeningRedisRoutingTable, WeightedRoundRobinBalancer
from galileo.routing.offloading.ai import AIOffloadRouter
from galileo.routing.offloading.simulated import SimulatedOffloadRouter

logger = logging.getLogger(__name__)


class Context:
    """
    Factory for various worker services. Below are the environment variables that can be set:

    - Logging
        - galileo_log_level (DEBUG|INFO|WARN| ... )

    - Redis connection:
        - galileo_redis_host (localhost)
        - galileo_redis_port (6379)
        - galileo_redis_password (None)

    - Trace logging:
        - galileo_trace_logging: file|redis|sql
        - mysql:
            - galileo_expdb_driver: sqlite|mysql
            - sqlite:
                - galileo_expdb_sqlite_path ('/tmp/galileo_sqlite')
            - mysql:
                - galileo_expdb_mysql_host (localhost)
                - galileo_expdb_mysql_port (3307)
                - galileo_expdb_mysql_user
                - galileo_expdb_mysql_password
                - galileo_expdb_mysql_db

    - Request router
        - galileo_router_type: SymmetryServiceRouter|SymmetryHostRouter|StaticRouter|DebugRouter
            - StaticRouter:
                - galileo_router_static_host (http://localhost)

    - Client app loader:
        - galileo_apps_dir ('./apps')
        - galileo_apps_repository ('http://localhost:5001')
    """

    def __init__(self, env: MutableMapping = os.environ) -> None:
        super().__init__()
        self.env = env
        self.daemon: GalileoFaasContextDaemon = None

    def getenv(self, *args, **kwargs):
        return self.env.get(*args, **kwargs)

    def keys(self, prefix: str = 'galileo_') -> List[str]:
        if prefix is None:
            return list(self.env.keys())
        else:
            return list(filter(lambda x: x.startswith('galileo_'), self.env.keys()))

    def items(self, prefix: str = 'galileo_') -> Dict[str, str]:
        if prefix is None:
            return dict(self.env.values())
        else:
            values = {}
            keys = self.keys(prefix)
            for key in keys:
                value = self.getenv(key)
                values[key] = value
        return values

    @property
    def worker_name(self):
        return self.env.get('galileo_worker_name', gethostname())

    def create_trace_writer(self) -> TraceWriter:
        trace_logging = self.env.get('galileo_trace_logging')
        logger.debug('trace logging: %s', trace_logging or 'None')

        if not trace_logging:
            return None
        elif trace_logging == 'file':
            return FileTraceWriter(self.worker_name)
        elif trace_logging == 'redis':
            return RedisTopicTraceWriter(self.create_redis())
        elif trace_logging == 'sql':
            return DatabaseTraceWriter(self.create_exp_db())
        else:
            raise ValueError('Unknown trace logging type %s' % trace_logging)

    def create_trace_logger(self, trace_queue, start=True) -> TraceLogger:
        writer = self.create_trace_writer()
        return TraceLogger(trace_queue, writer, start)

    def create_router(self, router_type=None):
        if router_type is None:
            router_type = self.env.get('galileo_router_type', 'CachingSymmetryHostRouter')
        router_type = 'CachingSymmetryHostRouter'
        print("Router_type:", router_type)
        if router_type == 'SymmetryServiceRouter':
            rtable = RedisRoutingTable(self.create_redis())
            balancer = WeightedRoundRobinBalancer(rtable)
            return ServiceRouter(balancer)
        elif router_type == 'CachingSymmetryServiceRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(self.create_redis())
            rtable.start()
            atexit.register(rtable.stop, timeout=2)
            balancer = WeightedRoundRobinBalancer(rtable)
            return ServiceRouter(balancer)
        elif router_type == 'SymmetryHostRouter':
            rtable = RedisRoutingTable(self.create_redis())
            balancer = WeightedRoundRobinBalancer(rtable)
            return HostRouter(balancer)
        elif router_type == 'CachingSymmetryHostRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(self.create_redis())
            rtable.start()
            atexit.register(rtable.stop, timeout=2)
            balancer = WeightedRoundRobinBalancer(rtable)
            return HostRouter(balancer)
        elif router_type == 'StaticRouter':
            host = self.env.get('galileo_router_static_host', 'http://localhost')
            return StaticRouter(host)
        elif router_type == 'DebugRouter':
            return DebugRouter()
        elif router_type == 'AIOffloadRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(self.create_redis())
            rtable.start()
            atexit.register(rtable.stop, timeout=2)
            balancer = WeightedRoundRobinBalancer(rtable)
            host_router = HostRouter(balancer)
            return AIOffloadRouter(host_router)
        elif router_type == 'SimulatedOffloadRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(self.create_redis())
            rtable.start()
            atexit.register(rtable.stop, timeout=2)
            balancer = WeightedRoundRobinBalancer(rtable)
            host_router = HostRouter(balancer)
            return SimulatedOffloadRouter(host_router)

        raise ValueError('Unknown router type %s' % router_type)

    def create_app_loader(self) -> AppClientLoader:
        loader = AppClientDirectoryLoader(self.env.get('galileo_apps_dir', os.path.abspath('./apps')))
        repo = RepositoryClient(self.env.get('galileo_apps_repository', 'http://localhost:5001'))

        return AppRepositoryFallbackLoader(loader, repo)

    def create_redis(self) -> redis.Redis:
        host = self.env.get('galileo_redis_host', 'localhost')

        if host.startswith('file://'):
            import redislite
            f_path = host.replace('file://', '')
            return redislite.Redis(dbfilename=f_path, decode_responses=True)

        params = {
            'host': host,
            'port': int(self.env.get('galileo_redis_port', '6379')),
            'decode_responses': True,
        }

        if self.env.get('galileo_redis_password', None) is not None:
            params['password'] = self.env['galileo_redis_password']

        logger.debug("establishing redis connection with params %s", params)

        return redis.Redis(**params)

    def setup_metrics(self, clock: Clock = None, rds: RedisClient = None):
        if rds is not None:
            metric_logger = GalileoLogger(rds, clock)
        else:
            log_fn = lambda x: logger.info(f'[log] {x}')
            metric_logger = LoggingLogger(log_fn, clock)
        return GalileoFaasMetrics(metric_logger)

    def create_exp_db(self) -> ExperimentDatabase:
        return create_experiment_database_from_env(self.env)

    def create_galileo_context(self):
        if self.daemon is not None:
            return self.daemon.context
        else:
            rds = RedisClient.from_env()
            metrics = self.setup_metrics()
            container_metrics = []
            node_metrics = ['signal', 'ping_avg', 'cpu']
            daemon = self.setup_daemon(rds, metrics, container_metrics, node_metrics)
            daemon.start()
            self.daemon = daemon
            return daemon.context

    def setup_daemon(self, rds: RedisClient, metrics: GalileoFaasMetrics, container_metrics,
                     node_metrics) -> GalileoFaasContextDaemon:
        deployment_service = create_deployment_service(metrics)

        telemc = TelemetryController(rds.conn())
        node_service = create_node_service(telemc)

        # latency in ms
        min_latency = 1
        max_latency = 1000
        latency_map = {}
        nodes = node_service.get_nodes()
        for node_1 in nodes:
            for node_2 in nodes:
                if node_1 == node_2:
                    # same node has 0.5 ms latency
                    latency_map[(node_1.name, node_2.name)] = 0.5
                else:
                    # else make random for demonstration purposes
                    # TODO this has to be updated for the specific testbed (or use Ether to model the topology)
                    latency_map[(node_1.name, node_2.name)] = random.randint(1, 100)
        network_service = create_network_service(min_latency, max_latency, latency_map)

        pod_factory = BasicExamplePodFactory()
        config.load_kube_config()
        core_v1_api = client.CoreV1Api()
        replica_factory = KubernetesFunctionReplicaFactory()
        replica_service = create_replica_service(node_service, rds, deployment_service, core_v1_api, pod_factory,
                                                 replica_factory, metrics)

        # window size to store, in seconds
        window_size = 3 * 60
        telemetry_service = create_telemetry_service(window_size, rds, node_service, container_metrics, node_metrics)

        trace_service = create_trace_service(window_size, rds, replica_service, network_service, node_service)

        zones = node_service.get_zones()
        zone_service = create_zone_service(zones)

        context = GalileoFaasContext(
            deployment_service,
            network_service,
            node_service,
            replica_service,
            telemetry_service,
            trace_service,
            zone_service,
            KubernetesFunctionReplicaFactory(),
            rds,
            telemc
        )
        return GalileoFaasContextDaemon(context)

    def stop_daemon(self):
        if self.daemon:
            self.daemon.stop()

    def create_wifi_ctrl(self):
        context = self.create_galileo_context()
        telemetry_service = context.telemetry_service
        return WifiController(telemetry_service)

    def create_ping_ctrl(self):
        context = self.create_galileo_context()
        telemetry_service = context.telemetry_service
        return PingController(telemetry_service)


class DebugRouter(Router):

    def request(self, req: ServiceRequest) -> requests.Response:
        logger.debug('DebugRouter received service request %s', req)

        response = requests.Response()
        response.status_code = 200
        response.url = self._get_url(req)
        req.sent = time.time()

        return response

    def _get_url(self, req: ServiceRequest) -> str:
        return 'http://debughost' + req.path
