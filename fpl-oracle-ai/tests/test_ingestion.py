import asyncio
import httpx
import pytest
from sqlalchemy import select,func
from ml.ingestion.fpl import FPLClient,sync_fpl
from apps.api.models import Player,Identity

def payload(code=123):
    return {'elements':[dict(id=1,code=code,team=1,web_name='Test',element_type=3,now_cost=60,status='a')],'teams':[dict(id=1,code=10,name='Test A',short_name='A')],'events':[dict(id=1,deadline_time='2025-08-15T18:00:00Z',is_current=True)]}

def test_sync_is_idempotent_and_detects_upstream_season(session):
    def respond(request):return httpx.Response(200,json=[] if request.url.path.endswith('/fixtures/') else payload())
    result=asyncio.run(sync_fpl(session,FPLClient(httpx.MockTransport(respond))))
    asyncio.run(sync_fpl(session,FPLClient(httpx.MockTransport(respond))))
    assert result['season']=='2025-26'
    assert session.scalar(select(func.count()).select_from(Player))==1
    assert session.scalar(select(func.count()).select_from(Identity))==1

def test_upstream_failure_propagates():
    def respond(request):return httpx.Response(403)
    with pytest.raises(httpx.HTTPStatusError):asyncio.run(FPLClient(httpx.MockTransport(respond)).get('/bootstrap-static/'))

def test_pooled_client_reuses_transport_preserves_rate_limit_and_closes():
    observed=[]
    def respond(request):
        observed.append(asyncio.get_running_loop().time())
        return httpx.Response(200,json={'test_only':True})
    async def run():
        async with FPLClient(httpx.MockTransport(respond)) as client:
            transport=client.http
            await client.get('/test-only/one/')
            await client.get('/test-only/two/')
            assert client.http is transport and not transport.is_closed
        assert transport.is_closed and client.http is None
    asyncio.run(run())
    assert len(observed)==2 and observed[1]-observed[0]>=.9
