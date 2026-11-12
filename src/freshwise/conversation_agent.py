"""Lan's Gemini conversation integration. Forecast and calculations remain app-owned.

Entry point: PreparationAgent(context, client=GeminiClient(key)).send(message).
Use choose_weight(label) to preview; confirm() alone changes the active plan.
"""
import json
import os
import re
import ssl
import urllib.request
from urllib.error import HTTPError, URLError

import certifi
from .application_tools import invoke, _number

WEIGHTS = {'Small change': .25, 'Meet halfway': .5, 'Use my estimate': 1.0}
CENTRAL = 'central_preparation_recommendation'
ADJUSTED = 'manager_adjusted_central_recommendation'


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
        tls = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request, timeout=60, context=tls) as response:
            return json.load(response)


def declaration(name, description, properties):
    language = {'type': 'STRING', 'enum': ['en', 'it'],
                'description': 'Language of the manager’s conversation, not the tool name.'}
    return {'name': name, 'description': description,
            'parameters': {'type': 'OBJECT', 'properties': {**properties, 'reply_language': language},
                           'required': list(properties)}}


class PreparationAgent:
    def __init__(self, context, client):
        self.context, self.client = context, client
        self.stock = self.estimate = self.active_plan = self.pending_plan = None
        self.trace = []
        self.history = []
        self.language = 'en'

    def say(self, english, italian):
        return italian if self.language == 'it' else english

    def send(self, message):
        """Collect stock or an estimate. Returns display data; failures preserve active plan."""
        if isinstance(message, str):
            if re.search(r'\b(ciao|buongiorno|buonasera|porzioni|ordini|quante|italiano)\b', message, re.I):
                self.language = 'it'
            elif re.search(r'\b(hello|hi|english|portions|orders)\b', message, re.I):
                self.language = 'en'
            if re.search(r"\b(cosa ne pensi|che ne pensi|cosa consigli|che mi consigli|what do you think|what would you do|what do you recommend)\b", message, re.I):
                if re.search(r"\b(cosa|che)\b", message, re.I):
                    self.language = 'it'
                return self.suggest_adjustment()
        return self._turn(message)

    def suggest_adjustment(self):
        if self.stock is None:
            return self._reply(self.say("How many portions do you already have ready?", "Quante porzioni hai già pronte?"))
        if self.estimate is None:
            return self._reply(self.say("How many orders do you expect, roughly?", "Quanti ordini ti aspetti, più o meno?"))

        args = {"usable_stock": self.stock, "manager_estimate": self.estimate,
                "opinion_weight": WEIGHTS["Small change"]}
        output = invoke(ADJUSTED, args, context=self.context)
        if output["status"] != "success":
            return self._reply(self.say("I couldn’t preview the change.", "Non sono riuscita a calcolare l’anteprima."), "error")
        original = output["result"]["original_plan"]["new_portions_to_prepare"]
        adjusted = output["result"]["adjusted_plan"]["new_portions_to_prepare"]
        self.trace.append({"name": ADJUSTED, "arguments": args, "output": output})
        return self._reply(self.say(
            f"If the event numbers are still uncertain, I’d start with Small change. "
            f"That would move the plan from {original} to {adjusted} new portions. "
            "If you have firm bookings, your estimate can carry more weight. Want to preview Small change?",
            f"Se i numeri dell’evento sono ancora incerti, partirei da Piccola modifica. "
            f"Il piano passerebbe da {original} a {adjusted} nuove porzioni. "
            "Se hai prenotazioni confermate, darei più peso alla tua stima. Vuoi vedere l’anteprima?"))

    def choose_weight(self, label):
        if label not in WEIGHTS:
            raise ValueError('Choose one of the three displayed adjustment options.')
        if self.stock is None:
            return self._reply(self.say('How many portions do you have ready? Zero is fine.', 'Quante porzioni hai già pronte? Va bene anche zero.'))
        if self.estimate is None:
            return self._reply(self.say('About how many orders do you expect?', 'Quanti ordini ti aspetti, più o meno?'))
        return self._turn(f'I choose {label}. Preview the adjustment; do not apply it.', WEIGHTS[label])

    def confirm(self):
        if self.pending_plan is None:
            return self._reply('There is no pending plan to apply.')
        self.active_plan, self.pending_plan = self.pending_plan, None
        if self.active_plan["manager_adjustment_applied"]:
            self.estimate = None
        quantity = self.active_plan['new_portions_to_prepare']
        return self._reply(self.say(
            f"Plan confirmed. Use the {self.stock} ready portions first, then make {quantity} more.",
            f"Piano confermato. Usa prima le {self.stock} porzioni pronte, poi preparane altre {quantity}."))

    def _reply(self, text, status='ok'):
        return {'status': status, 'answer': text, 'active_plan': self.active_plan,
                'pending_plan': self.pending_plan,
                'weight_choices': list(WEIGHTS) if self.estimate is not None and self.pending_plan is None else []}

    def _turn(self, message, weight=None):
        if not isinstance(message, str) or not message.strip():
            return self._reply('Please enter a message.')
        if len(message) > 4000:
            return self._reply('Please shorten the message.', 'needs_input')
        number = {'type': 'NUMBER'}
        if weight is None:
            functions = [
                declaration(CENTRAL, 'Calculate preparation using manager-provided ready stock. Do not invent missing stock.',
                            {'usable_stock': {'type': 'INTEGER'}}),
                declaration('record_manager_estimate', 'Record the manager\'s explicitly stated expected orders. This does not calculate or apply a plan.',
                            {'manager_estimate': number}),
                declaration('suggest_adjustment', 'Help the manager choose an adjustment when asked for advice. No numeric arguments.', {})]
        else:
            functions = [declaration(ADJUSTED,
                'Preview adjustment using the application-owned stock, estimate and chosen weight. No arguments needed.', {})]
        system = (
            'You are FreshWise for the dish selected by the application. Never change dish or invent inputs. '
            'Call the preparation tool for a preparation question if stock is explicitly provided. '
            'If stock is missing ask how many portions are ready to use; accept 0. '
            'Sound like a friendly, professional kitchen colleague. Ask one short, simple question at a time. '
            f'Use the manager’s language throughout, including greetings. Current language: {self.language}. '
            'For a short answer such as a number, keep the established language. Set reply_language on tool calls. '
            'If an event is mentioned without an order estimate, ask how many orders the manager expects. '
            'If an estimate is explicitly provided, record it; application will ask the influence weight. '
            'If the manager asks which adjustment you recommend or asks what you think of the adjustment, call suggest_adjustment. '
            'Never calculate quantities yourself. Never promise zero waste/shortages, or predict next-week waste. '
            'For waste questions say only labelled simulation results can support a comparison; this test has no verified impact table. '
            'Confirmation and application are handled by a separate button. '
            f'Current ready stock: {self.stock!r}. Current manager estimate: {self.estimate!r}. '
            'Prior messages are context only; do not reuse old values as new inputs.')
        history = self.history[-12:]
        while history and (
            history[0]['role'] != 'user' or 'text' not in history[0]['parts'][0]
        ):
            history = history[1:]
        contents = history + [{'role': 'user', 'parts': [{'text': message}]}]
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
                self.history = contents + [content]
                return self._reply(text)
            if len(calls) != 1:
                raise ValueError('Please provide stock and event estimates in separate messages.')
            call = calls[0]
            name, args = call['name'], call.get('args', {})
            if not isinstance(args, dict):
                raise ValueError('Invalid tool arguments.')
            args = dict(args)
            language = args.pop('reply_language', None)
            if weight is None and language in ('en', 'it'):
                self.language = language
            if name == 'suggest_adjustment' and weight is None and not args:
                reply = self.suggest_adjustment()
                output = {'status': reply['status'], 'recommendation': reply['answer']}
                answer = reply['answer']
            elif name == 'record_manager_estimate' and weight is None:
                if set(args) != {'manager_estimate'}:
                    raise ValueError('Unexpected estimate arguments.')
                estimate = _number(args['manager_estimate'], 'Manager estimate')
                self.estimate, self.pending_plan = estimate, None
                output = {'manager_estimate': estimate, 'status': 'recorded_not_applied'}
                answer = self.suggest_adjustment()['answer']
            elif name == CENTRAL and weight is None:
                output = invoke(name, args, context=self.context)
                if output['status'] != 'success':
                    return self._reply(output['answer'], 'needs_input')
                stock = output['result']['usable_stock']
                self.stock, self.pending_plan = stock, output['result']
                quantity = self.pending_plan['new_portions_to_prepare']
                answer = self.say(
                    f"Use the {stock} ready portions first and make {quantity} more. Does that plan work for you?",
                    f"Usa prima le {stock} porzioni pronte e preparane altre {quantity}. Ti va bene questo piano?")
            elif name == ADJUSTED and weight is not None:
                if args:
                    raise ValueError('Adjustment inputs must come from application state.')
                args = {'usable_stock': self.stock, 'manager_estimate': self.estimate, 'opinion_weight': weight}
                output = invoke(name, args, context=self.context)
                original, adjusted = output['result']['original_plan'], output['result']['adjusted_plan']
                self.pending_plan = adjusted
                before, after = original['new_portions_to_prepare'], adjusted['new_portions_to_prepare']
                answer = self.say(
                    f"With your update, I’d make {after} new portions. The previous plan called for {before}. Does that work for you?",
                    f"Con il tuo aggiornamento, preparerei {after} nuove porzioni. Il piano precedente ne prevedeva {before}. Ti va bene?")
            else:
                raise ValueError('Tool call is not allowed at this step.')
            self.trace.append({'name': name, 'arguments': args, 'output': output})
            # Template uses exact returned numbers; no second model call or invented arithmetic.
            tool_response = {'name': name, 'response': output}
            if 'id' in call:
                tool_response['id'] = call['id']
            self.history = contents + [content, {'role': 'user', 'parts': [{'functionResponse': tool_response}]},
                                       {'role': 'model', 'parts': [{'text': answer}]}]
            return self._reply(answer)
        except HTTPError as exc:
            if exc.code in (401, 403):
                return self._reply('Gemini refused access. Check that the API key and project have access to this model.', 'error')
            if exc.code == 429:
                return self._reply('Gemini has reached its request limit. Try again shortly.', 'error')
            if exc.code == 404:
                return self._reply('The configured Gemini model is unavailable for this project.', 'error')
            return self._reply(f'Gemini rejected the request (HTTP {exc.code}). Your active plan has not changed.', 'error')
        except (URLError, TimeoutError):
            return self._reply('FreshWise could not connect to Gemini. Your active plan has not changed.', 'error')
        except Exception:
            # Never echo HTTP request headers, keys, or provider error bodies into the UI.
            return self._reply('The request could not be completed. Your active plan has not changed. Please try again.', 'error')
