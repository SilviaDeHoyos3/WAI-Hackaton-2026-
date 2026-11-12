import unittest
from freshwise.application_tools import PlanningContext, invoke
from freshwise.conversation_agent import PreparationAgent, CENTRAL, ADJUSTED


class QueueClient:
    def __init__(self, *items):
        self.items = list(items)
    def generate(self, payload):
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return {'candidates': [{'content': {'role': 'model', 'parts': [item]}}]}


def call(name, **args):
    return {'functionCall': {'name': name, 'args': args, 'id': 'test-call'}, 'thoughtSignature': 'test'}


class ConversationTests(unittest.TestCase):
    def make(self, *items):
        return PreparationAgent(PlanningContext('synthetic', 100, 'synthetic test only'), QueueClient(*items))

    def test_confirm_and_adjustment_matches_manual_controls(self):
        a = self.make(call(CENTRAL, usable_stock=20), call('record_manager_estimate', manager_estimate=140), call(ADJUSTED))
        a.send('I have 20 ready portions')
        self.assertEqual(a.pending_plan['new_portions_to_prepare'], 80)
        self.assertIsNone(a.active_plan)
        a.confirm()
        a.send('I expect 140 orders')
        self.assertEqual(a.active_plan['new_portions_to_prepare'], 80)
        a.choose_weight('Small change')
        manual = invoke(ADJUSTED, {'usable_stock': 20, 'manager_estimate': 140, 'opinion_weight': .25}, context=a.context)
        self.assertEqual(a.pending_plan, manual['result']['adjusted_plan'])
        self.assertEqual(a.pending_plan['new_portions_to_prepare'], 90)
        self.assertEqual(a.active_plan['new_portions_to_prepare'], 80)
        a.confirm()
        self.assertEqual(a.active_plan['new_portions_to_prepare'], 90)

    def test_zero_and_sufficient_stock(self):
        for stock, expected in [(0, 100), (120, 0)]:
            a = self.make(call(CENTRAL, usable_stock=stock))
            a.send(f'{stock} ready')
            self.assertEqual(a.pending_plan['new_portions_to_prepare'], expected)

    def test_advice_calculates_a_small_change_without_applying_it(self):
        a = self.make(call(CENTRAL, usable_stock=20), call('record_manager_estimate', manager_estimate=140))
        a.send('20 ready portions')
        a.confirm()
        a.send('I expect 140 orders')
        answer = a.send('what do you think')['answer']
        self.assertIn('Small change', answer)
        self.assertIn('80 to 90', answer)
        self.assertIsNone(a.pending_plan)
        self.assertEqual(a.active_plan['new_portions_to_prepare'], 80)

    def test_missing_estimate_and_missing_stock(self):
        a = self.make({'text': 'About how many orders do you expect for this dish next week?'})
        reply = a.send('There is an event')
        self.assertIn('About how many', reply['answer'])
        self.assertEqual(a.trace, [])
        self.assertIsNone(a.estimate)
        self.assertIn('ready', a.choose_weight('Small change')['answer'])

    def test_model_cannot_supply_forecast_or_adjustment_weight(self):
        a = self.make(call(CENTRAL, usable_stock=20, forecast=999))
        self.assertEqual(a.send('20 ready')['status'], 'error')
        self.assertIsNone(a.pending_plan)
        a = self.make(call(ADJUSTED, opinion_weight=1))
        a.stock, a.estimate = 20, 140
        self.assertEqual(a.choose_weight('Small change')['status'], 'error')
        self.assertEqual(a.trace, [])

    def test_provider_failure_preserves_active_plan(self):
        a = self.make(call(CENTRAL, usable_stock=20), RuntimeError('secret provider error'))
        a.send('20 ready'); a.confirm()
        response = a.send('event')
        self.assertEqual(response['status'], 'error')
        self.assertEqual(a.active_plan['new_portions_to_prepare'], 80)
        self.assertNotIn('secret', response['answer'])

    def test_guarantee_text_does_not_apply_plan(self):
        a = self.make({'text': 'I cannot guarantee zero waste or zero unmet orders.'})
        a.send('Guarantee zero waste')
        self.assertIsNone(a.active_plan)
        self.assertEqual(a.trace, [])


if __name__ == '__main__':
    unittest.main()
