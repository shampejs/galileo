"""
Module to start webapp from WSGI context.


"""
import os

import falcon
import pymq
import redis
from pymq.provider.redis import RedisConfig

from galileo.apps.repository import Repository
from galileo.controller import ExperimentController
from galileo.experiment.db.factory import create_experiment_database_from_env
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.webapp.app import AppContext, CORSComponent, setup


def create_context() -> AppContext:
    context = AppContext()

    context.rds = redis.Redis(
        host=os.getenv('galileo_redis_host', 'localhost'),
        port=int(os.getenv('galileo_redis_port', 6379)),
        decode_responses=True
    )
    pymq.init(RedisConfig(context.rds))

    context.ectrl = ExperimentController(context.rds)
    context.exp_db = create_experiment_database_from_env()
    context.exp_service = SimpleExperimentService(context.exp_db)
    context.repository = Repository(os.getenv('galileo_apps_repo_dir', os.path.abspath('./apps-repo')))

    return context


api = falcon.API(middleware=[CORSComponent()])
setup(api, create_context())
