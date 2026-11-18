from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.db import session_dependency
from apps.api.cache import Cache

def test_api_empty_states_and_internal_security(session):
    app.dependency_overrides[session_dependency]=lambda:session
    with TestClient(app) as client:
        assert client.get('/api/v1/health').status_code==200
        assert client.get('/api/v1/players').json()['items']==[]
        assert client.get('/api/v1/predictions').json()['items']==[]
        assert client.get('/api/v1/players/123').status_code==404
        assert client.post('/api/v1/internal/managers',json={'name':'Test'}).status_code==401
        assert client.post('/api/v1/optimizer/squad',json={}).status_code==409
        response=client.get('/api/v1/players?limit=10000')
        assert response.status_code==422
        assert response.headers.get('X-Request-ID')
    app.dependency_overrides.clear()

def test_cache_version_invalidates_previous_values():
    cache=Cache();cache.set('predictions',{'items':[1]})
    assert cache.get('predictions')=={'items':[1]}
    cache.invalidate()
    assert cache.get('predictions') is None

def test_fresh_and_stale_envelopes_and_single_flight(monkeypatch):
    current=[1000.0]
    monkeypatch.setattr('apps.api.cache.time.time',lambda:current[0])
    cache=Cache();cache.set('public',{'items':[1]},ttl=2,stale_ttl=10)
    assert cache.read('public')[1]=='fresh'
    current[0]=1003
    assert cache.read('public')[1]=='stale'
    assert cache.get('public') is None
    assert cache.get('public',allow_stale=True)=={'items':[1]}
    with cache.lock('one') as first:
        assert first
        with cache.lock('one') as second:assert not second
    current[0]=1013
    assert cache.read('public')[1]=='miss'
