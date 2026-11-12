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

    def test_missing_estimate_and_missing_stock(self):
        a = self.make()
        reply = a.send('There is an event')
        self.assertIn('About how many', reply['answer'])
        self.assertEqual(a.trace, [])
        self.assertIsNone(a.estimate)
        self.assertIn('ready', a.choose_weight('Small change')['answer'])

    def test_event_as_first_message_needs_no_provider(self):
        a = self.make()
        response = a.send('There’s a local event.')
        self.assertEqual(response['status'], 'needs_input')
        self.assertIn('About how many orders', response['answer'])
        self.assertIsNone(a.stock)
        self.assertIsNone(a.estimate)
        self.assertEqual(a.trace, [])

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
        a = self.make()
        reply = a.send('Guarantee zero waste')
        self.assertEqual(reply['status'], 'scope_limit')
        self.assertIn('cannot guarantee', reply['answer'])
        self.assertIsNone(a.active_plan)
        self.assertEqual(a.trace, [])

    def test_waste_prediction_does_not_call_provider(self):
        a = self.make()
        reply = a.send('How much waste will we have next week?')
        self.assertEqual(reply['status'], 'scope_limit')
        self.assertEqual(a.trace, [])

    def test_discard_adjustment_keeps_confirmed_plan(self):
        a = self.make(call(CENTRAL, usable_stock=20), call('record_manager_estimate', manager_estimate=140), call(ADJUSTED))
        a.send('20 ready'); a.confirm(); a.send('140 orders'); a.choose_weight('Small change')
        a.cancel_preview()
        self.assertIsNone(a.pending_plan)
        self.assertEqual(a.active_plan['new_portions_to_prepare'], 80)

    def test_http_failure_reports_code_without_secrets(self):
        from urllib.error import HTTPError
        a = self.make(HTTPError('secret-url', 503, 'secret-body', {}, None))
        reply = a.send('20 ready')
        self.assertEqual(reply['error_code'], 'HTTP 503')
        self.assertNotIn('secret', reply['answer'])

    def test_other_weights_match_manual_tool(self):
        for label, weight in [('Meet halfway', .5), ('Use my estimate', 1.)]:
            with self.subTest(label=label):
                a = self.make(call(ADJUSTED))
                a.stock, a.estimate = 20, 140
                a.choose_weight(label)
                manual = invoke(ADJUSTED, {'usable_stock':20, 'manager_estimate':140,
                                          'opinion_weight':weight}, context=a.context)
                self.assertEqual(a.pending_plan, manual['result']['adjusted_plan'])
                self.assertIsNone(a.active_plan)

    def test_missing_stock_never_defaults_to_zero(self):
        a = self.make(call(CENTRAL))
        result = a.send('How much should I prepare?')
        self.assertEqual(result['status'], 'needs_input')
        self.assertIsNone(a.stock)
        self.assertIsNone(a.pending_plan)
        self.assertEqual(a.trace, [])


if __name__ == '__main__':
    unittest.main()
