from typing import List

from galileo.experiment.model import Experiment, Telemetry, ServiceRequestTrace, Instructions
from tests.api import ResourceTest


class TestExperimentResource(ResourceTest):

    def test_get(self):
        exp = Experiment('id1', 'name1', 'creator1', 123, 456, 789, 'FINISH')
        self.db_resource.db.save_experiment(exp)
        result = self.simulate_get(f'/api/experiments/id1')

        self.assertIsNotNone(result.json)
        self.assertEqual(result.json, exp.__dict__)

    def test_delete(self):
        exp_id = 'id1'
        exp = Experiment(exp_id, 'name1', 'creator1', 1, 20, 7, 'FINISH')
        telemetry: List[Telemetry] = [Telemetry(1, 'metric1', 'node1', 1, exp_id),
                                      Telemetry(2, 'metric2', 'node2', 2, exp_id)]
        traces: List[ServiceRequestTrace] = [ServiceRequestTrace('client1', 'service1', 'host1', 2, 2, 3),
                                             ServiceRequestTrace('client2', 'service2', 'host2', 6, 5, 4)]
        instructions: Instructions = Instructions(exp_id, 'instructions')
        db = self.db_resource.db
        db.save_experiment(exp)
        db.save_instructions(instructions)
        db.save_telemetry(telemetry)
        db.save_traces(traces)
        db.touch_traces(exp)

        self.simulate_delete('/api/experiments/id1')

        self.assertEqual(len(db.find_all()), 0)
        self.assertEqual(db.get_instructions(exp_id), None)

        traces_fetched = db.db.fetchall('SELECT * FROM traces')
        telemetry_fetched = db.db.fetchall('SELECT * FROM telemetry')
        self.assertEqual(len(traces_fetched), 0)
        self.assertEqual(len(telemetry_fetched), 0)
        pass
