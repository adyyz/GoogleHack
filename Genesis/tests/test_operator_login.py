from contextlib import nullcontext
from dataclasses import replace
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from backend.config import Settings
from backend import api
from backend.repository import Repository

PASSWORD = 'TEST_ONLY_PASSWORD_NEVER_RETURN'
CREDENTIALS = {'email': 'operator@example.test', 'password': PASSWORD, 'uid': 'test-operator'}


@pytest.fixture
def cloud_settings(monkeypatch):
    def init(self, settings, dataset_id=None):
        self.settings, self.dataset_id, self.db = settings, dataset_id, None
    monkeypatch.setattr(Repository, '__init__', init)
    return replace(Settings.load(), mode='cloud', project_id='test-genesis', firestore_host=None, auth_host=None,
        operator_uids=frozenset({'test-operator'}), admin_uids=frozenset({'test-operator'}),
        firebase_web_api_key='TEST_ONLY_PUBLIC_CONFIG', operator_demo_login=json.dumps(CREDENTIALS),
        operator_demo_login_enabled=True)


def test_secret_shape_and_local_rejection(cloud_settings):
    assert PASSWORD not in repr(cloud_settings)
    for value in ['not-json', '[]', '{}', json.dumps({**CREDENTIALS, 'password': ''})]:
        with pytest.raises(ValueError): replace(cloud_settings, operator_demo_login=value).operator_demo_credentials()
    with pytest.raises(ValueError): replace(cloud_settings, mode='local').operator_demo_credentials()


@pytest.mark.parametrize('mode,secret,enabled', [('local', '', False), ('cloud', '', True), ('cloud', json.dumps(CREDENTIALS), False)])
def test_disabled_shortcut_is_absent(cloud_settings, monkeypatch, mode, secret, enabled):
    monkeypatch.setattr(api, 'urlopen', lambda *args, **kwargs: pytest.fail('Disabled shortcut attempted HTTP'))
    settings = replace(cloud_settings, mode=mode, operator_demo_login=secret, operator_demo_login_enabled=enabled,
        auth_host='127.0.0.1:9099' if mode == 'local' else None)
    with TestClient(api.create_app(settings)) as client:
        assert client.post('/api/operator/demo-login').status_code == 404
        config = client.get('/api/config').json()
        assert 'operator_demo_email' not in config and 'operator_password' not in config


def test_success_verifies_identity_and_returns_only_token(cloud_settings, monkeypatch):
    requests = []
    def transport(request, timeout):
        assert request.full_url.startswith('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?')
        assert timeout == 10
        assert json.loads(request.data) == {'email': CREDENTIALS['email'], 'password': PASSWORD, 'returnSecureToken': True}
        requests.append(request)
        return nullcontext(SimpleNamespace(read=lambda _size: json.dumps({'idToken': 'TEST_ONLY_TOKEN', 'localId': 'test-operator', 'refreshToken': 'TEST_ONLY_NOT_RETURNED'}).encode()))
    monkeypatch.setattr(api, 'urlopen', transport)
    def verify(token, *, app, check_revoked):
        assert token == 'TEST_ONLY_TOKEN' and check_revoked
        return {'uid': 'test-operator'}
    monkeypatch.setattr(api.auth, 'verify_id_token', verify)
    with TestClient(api.create_app(cloud_settings)) as client:
        config = client.get('/api/config')
        assert config.json()['operator_demo_email'] == CREDENTIALS['email'] and PASSWORD not in config.text
        response = client.post('/api/operator/demo-login')
        assert response.status_code == 200 and response.json() == {'idToken': 'TEST_ONLY_TOKEN'}
        assert response.headers['cache-control'] == 'no-store' and PASSWORD not in response.text
        assert len(requests) == 1


def test_both_allowlists_are_required(cloud_settings, monkeypatch):
    monkeypatch.setattr(api, 'urlopen', lambda *args, **kwargs: pytest.fail('Unapproved identity attempted HTTP'))
    for field in ['operator_uids', 'admin_uids']:
        with TestClient(api.create_app(replace(cloud_settings, **{field: frozenset()}))) as client:
            assert client.post('/api/operator/demo-login').status_code == 403
            assert 'operator_demo_email' not in client.get('/api/config').json()


@pytest.mark.parametrize('fault', ['uid', 'claims', 'upstream', 'missing-token'])
def test_failures_never_disclose_transport_details(cloud_settings, monkeypatch, caplog, fault):
    def transport(*_args, **_kwargs):
        if fault == 'upstream': raise TimeoutError(PASSWORD)
        body = {'idToken': 'TEST_ONLY_TOKEN', 'localId': 'wrong' if fault == 'uid' else 'test-operator'}
        if fault == 'missing-token': del body['idToken']
        return nullcontext(SimpleNamespace(read=lambda _size: json.dumps(body).encode()))
    monkeypatch.setattr(api, 'urlopen', transport)
    monkeypatch.setattr(api.auth, 'verify_id_token', lambda *args, **kwargs: {'uid': 'wrong' if fault == 'claims' else 'test-operator'})
    with TestClient(api.create_app(cloud_settings)) as client:
        response = client.post('/api/operator/demo-login')
        assert response.status_code == 502 and PASSWORD not in response.text and PASSWORD not in caplog.text
