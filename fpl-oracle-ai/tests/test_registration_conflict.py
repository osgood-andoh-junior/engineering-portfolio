import asyncio
import httpx
from datetime import datetime,timezone,timedelta
from apps.api.models import Club,Player,Source
from apps.api.events import EventInput,ingest_event
from ml.ingestion.fpl import FPLClient,sync_fpl

def test_lagging_fpl_record_cannot_reverse_a_confirmed_transfer(session):
    session.add_all([Club(id=1,code=10,name='Old club',short_name='OLD'),Club(id=2,code=20,name='New club',short_name='NEW'),Source(id='official',url='https://club.example',official=True,permitted=True,license='test only')]);session.flush()
    session.add(Player(id=1,code=123,name='Test Player',club_id=1,position=3,price=60,status='a',registration_state='verified'));session.commit()
    now=datetime.now(timezone.utc)-timedelta(days=1)
    ingest_event(session,EventInput(kind='TRANSFER',status='CONFIRMED',source_id='official',source_url='https://club.example/transfer',player_id=1,from_club_id=1,to_club_id=2,effective_at=now,announced_at=now,observed_at=now));session.commit()
    def respond(request):
        payload={'elements':[{'id':1,'code':123,'team':1,'web_name':'Test Player','element_type':3,'now_cost':60,'status':'a'}],'teams':[{'id':1,'code':10,'name':'Old club','short_name':'OLD'},{'id':2,'code':20,'name':'New club','short_name':'NEW'}],'events':[{'id':1,'deadline_time':'2026-08-21T17:30:00Z'}]}
        return httpx.Response(200,json=[] if request.url.path.endswith('/fixtures/') else payload)
    asyncio.run(sync_fpl(session,FPLClient(httpx.MockTransport(respond))))
    player=session.get(Player,1)
    assert player.club_id==2 and player.registration_state=='conflict'
