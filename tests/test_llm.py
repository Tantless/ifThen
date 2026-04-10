from __future__ import annotations

import httpx
import pytest

from if_then_mvp.llm import LLMClientError, OpenAICompatibleTransport


class _FakeResponse:
    def __init__(self, *, json_payload=None, text_payload: str = '', status_code: int = 200):
        self._json_payload = json_payload
        self.text = text_payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('boom', request=None, response=None)

    def json(self):
        if self._json_payload is None:
            raise ValueError('no json')
        return self._json_payload


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse], calls: list[dict]):
        self._responses = responses
        self._calls = calls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, *, json, headers):
        self._calls.append({'url': url, 'json': json, 'headers': headers})
        return self._responses.pop(0)


def test_transport_falls_back_to_stream_when_nonstream_response_omits_content(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []
    responses = [
        _FakeResponse(
            json_payload={
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                        }
                    }
                ]
            }
        ),
        _FakeResponse(
            text_payload='\n'.join(
                [
                    'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}',
                    'data: {"choices":[{"delta":{"content":"pong"},"finish_reason":null}]}',
                    'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}]}',
                    'data: [DONE]',
                ]
            )
        ),
    ]

    monkeypatch.setattr(
        httpx,
        'Client',
        lambda timeout: _FakeClient(responses=responses, calls=calls),
    )

    transport = OpenAICompatibleTransport(timeout_seconds=1)

    content = transport.post_chat_completion(
        base_url='https://example.test/v1',
        api_key='sk-test',
        payload={
            'model': 'gpt-test',
            'messages': [
                {'role': 'system', 'content': 'You are a helper.'},
                {'role': 'user', 'content': 'say pong'},
            ],
        },
    )

    assert content == 'pong'
    assert len(calls) == 2
    assert calls[0]['json'].get('stream') is None
    assert calls[1]['json']['stream'] is True


def test_transport_raises_when_stream_fallback_still_has_no_content(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _FakeResponse(
            json_payload={
                'choices': [
                    {
                        'message': {
                            'role': 'assistant',
                        }
                    }
                ]
            }
        ),
        _FakeResponse(text_payload='data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":"stop"}]}\ndata: [DONE]'),
    ]

    monkeypatch.setattr(httpx, 'Client', lambda timeout: _FakeClient(responses=responses, calls=[]))

    transport = OpenAICompatibleTransport(timeout_seconds=1)

    with pytest.raises(LLMClientError, match='Chat completion message content must be a string'):
        transport.post_chat_completion(
            base_url='https://example.test/v1',
            api_key='sk-test',
            payload={'model': 'gpt-test', 'messages': []},
        )
