from datetime import datetime,timezone,timedelta
import pytest
from sqlalchemy import select
from apps.api.models import Club,Player,Manager,Source,Tenure,Membership,Job,FootballEvent
from apps.api.events import EventInput,ingest_event

NOW=datetime.now(timezone.utc)-timedelta(days=1)

def setup_entities(session):
    session.add_all([Club(id=1,code=10,name='Test A',short_name='A'),Club(id=2,code=20,name='Test B',short_name='B'),Source(id='official',url='https://club.example',official=True,permitted=True,license='test only'),Source(id='news',url='https://news.example',official=False,permitted=True,license='test only'),Manager(id=1,name='Test Manager'),Manager(id=2,name='Test Interim')]);session.flush()
    session.add(Player(id=1,code=100,name='Test Player',club_id=1,position=4,price=70,status='a'));session.commit()

def event(**updates):
    values=dict(kind='TRANSFER',status='CONFIRMED',source_id='official',source_url='https://club.example/announcement',player_id=1,from_club_id=1,to_club_id=2,effective_at=NOW,announced_at=NOW,observed_at=NOW+timedelta(hours=1))
    values.update(updates)
    return EventInput(**values)

def test_rumor_never_changes_membership(session):
    setup_entities(session)
    ingest_event(session,event(status='RUMORED',source_id='news',source_url='https://news.example/item'))
    assert session.get(Player,1).club_id==1
    assert session.scalar(select(Job)) is None

def test_confirmed_transfer_is_idempotent_and_creates_refresh(session):
    setup_entities(session)
    first=ingest_event(session,event());session.commit()
    second=ingest_event(session,event(source_url='https://club.example/another'))
    assert first.id==second.id
    assert session.get(Player,1).club_id==2
    assert len(session.scalars(select(Job)).all())==1
    assert len(session.scalars(select(Membership)).all())==1

def test_timezone_equivalent_announcements_are_the_same_event(session):
    setup_entities(session)
    first=ingest_event(session,event());session.commit()
    other=NOW.astimezone(timezone(timedelta(hours=3)))
    second=ingest_event(session,event(effective_at=other));session.commit()
    assert first.id==second.id

def test_report_can_be_confirmed(session):
    setup_entities(session)
    ingest_event(session,event(status='REPORTED',source_id='news',source_url='https://news.example/item'));session.commit()
    row=ingest_event(session,event());session.commit()
    assert row.status=='CONFIRMED'
    assert session.get(Player,1).club_id==2

def test_nonofficial_cannot_confirm(session):
    setup_entities(session)
    with pytest.raises(ValueError,match='official'): ingest_event(session,event(source_id='news',source_url='https://news.example/item'))

def test_interim_closes_previous_tenure(session):
    setup_entities(session)
    ingest_event(session,event(kind='APPOINTMENT',player_id=None,manager_id=1,from_club_id=None,to_club_id=1,effective_at=NOW-timedelta(days=30)));session.commit()
    ingest_event(session,event(kind='INTERIM',player_id=None,manager_id=2,from_club_id=None,to_club_id=1));session.commit()
    rows=session.scalars(select(Tenure).order_by(Tenure.starts_at)).all()
    assert rows[0].ends_at is not None
    assert rows[1].interim and rows[1].ends_at is None
    assert rows[0].ends_at==rows[1].starts_at

def test_conflicting_appointment_quarantined(session):
    setup_entities(session)
    ingest_event(session,event(kind='APPOINTMENT',player_id=None,manager_id=1,from_club_id=None,to_club_id=1));session.commit()
    with pytest.raises(ValueError,match='conflicting'): ingest_event(session,event(kind='INTERIM',player_id=None,manager_id=2,from_club_id=None,to_club_id=1))

def test_backdated_future_and_wrong_source_rejected(session):
    setup_entities(session)
    with pytest.raises(ValueError): ingest_event(session,event(source_url='https://spoof.example'))
    with pytest.raises(ValueError): ingest_event(session,event(effective_at=NOW+timedelta(days=10)))

def test_later_departure_confirmation_does_not_rewrite_earlier_known_manager(session):
    from apps.api.models import Evidence
    from ml.features.intelligence import context_at
    setup_entities(session)
    ev=Evidence(source_id='official',digest='1'*64,uri='https://club.example/earlier',payload={},observed_at=NOW-timedelta(days=30));session.add(ev);session.flush()
    session.add(Tenure(manager_id=1,club_id=1,starts_at=NOW-timedelta(days=30),evidence_id=ev.id));session.commit()
    ingest_event(session,event(kind='DISMISSAL',player_id=None,manager_id=1,to_club_id=None,effective_at=NOW-timedelta(days=2)));session.commit()
    earlier=context_at(session,session.get(Player,1),NOW-timedelta(days=1))
    assert 'manager_tenure_days' in earlier
    later=context_at(session,session.get(Player,1),NOW+timedelta(days=1))
    assert 'manager_tenure_days' not in later

@pytest.mark.parametrize('kind',['SIGNING','LOAN','LOAN_RETURN','DEPARTURE'])
def test_membership_events(session,kind):
    setup_entities(session)
    ingest_event(session,event(kind=kind,to_club_id=None if kind=='DEPARTURE' else 2));session.commit()
    assert session.get(Player,1).club_id==(None if kind=='DEPARTURE' else 2)
