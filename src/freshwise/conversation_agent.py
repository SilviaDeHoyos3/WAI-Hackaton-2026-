"""Lan's Gemini conversation integration. Forecast and calculations remain app-owned.

Entry point: PreparationAgent(context, client=GeminiClient(key)).send(message).
Use choose_weight(label) to preview; confirm() alone changes the active plan.
"""
import json
import os
import re
import socket
import urllib.error
import urllib.request
from .application_tools import invoke, _number

WEIGHTS = {'Small change': .25, 'Meet halfway': .5, 'Use my estimate': 1.0}
CENTRAL = 'central_preparation_recommendation'
ADJUSTED = 'manager_adjusted_central_recommendation'
CODE_REVISION = 'event-start-fix-1'


class GeminiClient:
    def __init__(self, key=None, model=None):
        self.key = key or os.environ.get('GEMINI_API_KEY', '')
        self.model = model or os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
        if not self.key:
            raise ValueError('Configure GEMINI_API_KEY or enter a key in the test screen.')
        if not self.model or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-.' for c in self.model):
            raise ValueError('Invalid model identifier.')

    def generate(self, payload):
        request = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': self.key}, method='POST')
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)


def declaration(name, description, properties):
    result = {'name': name, 'description': description}
    if properties:
        result['parameters'] = {'type': 'OBJECT', 'properties': properties, 'required': list(properties)}
    return result


class PreparationAgent:
    def __init__(self, context, client):
        self.context, self.client = context, client
        self.stock = self.estimate = self.active_plan = self.pending_plan = None
        self.trace = []
        self.history = []
        self.last_error = None
        self.revision = CODE_REVISION

    def send(self, message):
        """Collect stock or an estimate. Returns display data; failures preserve active plan."""
        normalized = message.strip().lower().replace('’', "'") if isinstance(message, str) else ''
        if re.fullmatch(r"there(?: is|'s) (?:a |an )?(?:local )?(?:event|festival|holiday|promotion)[.!]?", normalized):
            answer = 'About how many orders do you expect for this dish next week?'
            self.history += [{'role': 'user', 'parts': [{'text': message}]},
                             {'role': 'model', 'parts': [{'text': answer}]}]
            return self._reply(answer, 'needs_input')
        return self._turn(message)

    def choose_weight(self, label):
        if label not in WEIGHTS:
            raise ValueError('Choose one of the three displayed adjustment options.')
        if self.stock is None:
            return self._reply('How many portions do you already have ready to use? 0 is valid.')
        if self.estimate is None:
            return self._reply('About how many orders do you expect for this dish next week?')
        return self._turn(f'I choose {label}. Preview the adjustment; do not apply it.', WEIGHTS[label])

    def confirm(self):
        if self.pending_plan is None:
            return self._reply('There is no pending plan to apply.')
        self.active_plan, self.pending_plan = self.pending_plan, None
        return self._reply(f"Plan applied in this demo: use {self.active_plan['usable_stock']} ready portions first, then prepare "
                           f"{self.active_plan['new_portions_to_prepare']} new portions.")

    def cancel_preview(self):
        self.pending_plan = None
        return self._reply('Preview discarded. Your active plan has not changed.')

    def _reply(self, text, status='ok'):
        return {'status': status, 'answer': text, 'active_plan': self.active_plan,
                'pending_plan': self.pending_plan, 'error_code': self.last_error if status == 'error' else None,
                'weight_choices': list(WEIGHTS) if self.estimate is not None and self.pending_plan is None else []}

    def _turn(self, message, weight=None):
        if not isinstance(message, str) or not message.strip():
            return self._reply('Please enter a message.')
        if len(message) > 4000:
            return self._reply('Please shorten the message.', 'needs_input')
        self.last_error = None
        # These scope boundaries must not depend on the model following a prompt.
        lower = message.lower()
        if weight is None and re.search(r'\b(waste|shortage|unmet|carbon|emission|guarantee|promise)\b|浪费|缺货|碳排|保证', lower):
            if re.search(r'guarantee|promise|zero|保证|零', lower):
                answer = 'I cannot guarantee both zero waste and zero unmet orders. Demand is uncertain. I can calculate a preparation plan using stated inputs.'
            else:
                answer = ('This tool recommends preparation; it does not predict next-week waste, shortages or carbon savings. '
                          'Use the labelled simulation results in the Impact screen for historical comparisons; demo-meal and all-meal results differ.')
            self.history += [{'role': 'user', 'parts': [{'text': message}]},
                             {'role': 'model', 'parts': [{'text': answer}]}]
            return self._reply(answer, 'scope_limit')
        number = {'type': 'NUMBER'}
        if weight is None:
            functions = [
                declaration(CENTRAL, 'Calculate preparation using manager-provided ready stock. Do not invent missing stock.',
                            {'usable_stock': {'type': 'INTEGER'}}),
                declaration('record_manager_estimate', 'Record the manager\'s explicitly stated expected orders. This does not calculate or apply a plan.',
                            {'manager_estimate': number})]
        else:
            functions = [declaration(ADJUSTED,
                'Preview adjustment using the application-owned stock, estimate and chosen weight. No arguments needed.', {})]
        system = (
            'You are FreshWise for the dish selected by the application. Never change dish or invent inputs. '
            'Call the preparation tool for a preparation question if stock is explicitly provided. '
            'If stock is missing ask how many portions are ready to use; accept 0. '
            'If an event is mentioned without an order estimate, ask exactly: '
            'About how many orders do you expect for this dish next week? '
            'If an estimate is explicitly provided, record it; application will ask the influence weight. '
            'Never calculate quantities yourself. Never promise zero waste/shortages, or predict next-week waste. '
            'For waste questions say only labelled simulation results can support a comparison; this test has no verified impact table. '
            'Confirmation and application are handled by a separate button. '
            f'Current ready stock: {self.stock!r}. Current manager estimate: {self.estimate!r}. '
            'Prior messages are context only; do not reuse old values as new inputs.')
        tail = self.history[-12:]
        # Never send a truncated history starting with an orphan function response.
        while tail and not (tail[0].get('role') == 'user' and
                            any('text' in part for part in tail[0].get('parts', []))):
            tail = tail[1:]
        contents = tail + [{'role': 'user', 'parts': [{'text': message}]}]
        payload = {'systemInstruction': {'parts': [{'text': system}]}, 'contents': contents,
                   'tools': [{'functionDeclarations': functions}]}
        if weight is not None:
            payload['toolConfig'] = {'functionCallingConfig': {'mode': 'ANY', 'allowedFunctionNames': [ADJUSTED]}}
        try:
            response = self.client.generate(payload)
            content = response['candidates'][0]['content']
            calls = [p['functionCall'] for p in content.get('parts', []) if 'functionCall' in p]
            if not calls:
                if weight is not None:
                    raise ValueError('No adjustment tool call returned.')
                text = ' '.join(p.get('text', '') for p in content.get('parts', []) if not p.get('thought'))
                if not text.strip():
                    raise ValueError('No reply returned.')
                if re.search(r'[1-9]', text):
                    text = ('No planning tool was executed for this message. Please state your ready-to-use stock '
                            'or the expected orders for the event; preparation quantities must come from the tools.')
                    content = {'role': 'model', 'parts': [{'text': text}]}
                self.history = contents + [content]
                return self._reply(text)
            if len(calls) != 1:
                raise ValueError('Please provide stock and event estimates in separate messages.')
            call = calls[0]
            name, args = call['name'], call.get('args', {})
            if not isinstance(args, dict):
                raise ValueError('Invalid tool arguments.')
            if name == 'record_manager_estimate' and weight is None:
                if set(args) != {'manager_estimate'}:
                    raise ValueError('Unexpected estimate arguments.')
                estimate = _number(args['manager_estimate'], 'Manager estimate')
                self.estimate, self.pending_plan = estimate, None
                output = {'manager_estimate': estimate, 'status': 'recorded_not_applied'}
                answer = ('About how much should we move toward your estimate? '
                          'Choose Small change (25%), Meet halfway (50%), or Use my estimate (100%).')
            elif name == CENTRAL and weight is None:
                output = invoke(name, args, context=self.context)
                if output['status'] != 'success':
                    return self._reply(output['answer'], 'needs_input')
                stock = output['result']['usable_stock']
                self.stock, self.pending_plan = stock, output['result']
                answer = (f"Use {stock} ready portions first, then prepare "
                          f"{self.pending_plan['new_portions_to_prepare']} new portions. Review and confirm to apply.")
            elif name == ADJUSTED and weight is not None:
                if args:
                    raise ValueError('Adjustment inputs must come from application state.')
                args = {'usable_stock': self.stock, 'manager_estimate': self.estimate, 'opinion_weight': weight}
                output = invoke(name, args, context=self.context)
                original, adjusted = output['result']['original_plan'], output['result']['adjusted_plan']
                self.pending_plan = adjusted
                answer = (f"New preparation: {original['new_portions_to_prepare']} → "
                          f"{adjusted['new_portions_to_prepare']} portions. We moved the forecast "
                          f"{weight:.0%} toward your {self.estimate:g}-order estimate, keeping "
                          f"{self.stock} ready portions. Review and confirm to apply.")
            else:
                raise ValueError('Tool call is not allowed at this step.')
            self.trace.append({'name': name, 'arguments': args, 'output': output,
                               'provider_model': getattr(self.client, 'model', 'offline-test-double'),
                               'preview_only': True})
            # Template uses exact returned numbers; no second model call or invented arithmetic.
            tool_response = {'name': name, 'response': output}
            if 'id' in call:
                tool_response['id'] = call['id']
            self.history = contents + [content, {'role': 'user', 'parts': [{'functionResponse': tool_response}]},
                                       {'role': 'model', 'parts': [{'text': answer}]}]
            return self._reply(answer)
        except Exception as error:
            # Never echo HTTP request headers, keys, or provider error bodies into the UI.
            if isinstance(error, urllib.error.HTTPError):
                self.last_error = f'HTTP {error.code}'
                reason = {403: 'The provider denied access.', 429: 'The provider rate limit was reached.',
                          503: 'The provider is temporarily busy.'}.get(error.code, 'The provider request failed.')
            elif isinstance(error, (TimeoutError, socket.timeout, urllib.error.URLError)):
                self.last_error, reason = 'NETWORK_OR_TIMEOUT', 'The provider connection failed or timed out.'
            else:
                self.last_error, reason = 'INVALID_TOOL_RESPONSE', 'The reply or tool inputs could not be validated.'
            return self._reply(reason + ' Your active plan has not changed. Please try again.', 'error')
