from datetime import timedelta
import numpy as np
from sqlalchemy import select,and_,or_
from apps.api.models import Tenure, TacticalObservation, TacticalRegime, FootballEvent, Player, HistoricalStat, Identity, Membership, Evidence,Fixture

def context_at(session, player, cutoff):
    tenures = session.scalars(select(Tenure).where(Tenure.club_id == player.club_id, Tenure.starts_at < cutoff)).all()
    from apps.api.models import Evidence
    tenure_times=dict(session.execute(select(Evidence.id,Evidence.observed_at).where(Evidence.id.in_({t.evidence_id for t in tenures}))).all())
    def known_closed(t):
        return t.ends_at is not None and t.ends_observed_at is not None and t.ends_at.replace(tzinfo=cutoff.tzinfo)<=cutoff and t.ends_observed_at.replace(tzinfo=cutoff.tzinfo)<cutoff
    valid = [t for t in tenures if not known_closed(t) and tenure_times[t.evidence_id].replace(tzinfo=cutoff.tzinfo) < cutoff]
    result = {}
    if valid:
        tenure = max(valid, key=lambda t: t.starts_at)
        result['manager_tenure_days'] = (cutoff - tenure.starts_at.replace(tzinfo=cutoff.tzinfo)).days
        ids = session.execute(select(Identity.season_id, Identity.fpl_id).where(Identity.player_id == player.id)).all()
        rows = []
        for season, pid in ids:
            rows += session.scalars(select(HistoricalStat).join(Fixture,and_(Fixture.season_id==HistoricalStat.season,Fixture.provider_id==HistoricalStat.fixture)).where(HistoricalStat.season == season, HistoricalStat.fpl_id == pid, HistoricalStat.kickoff >= tenure.starts_at, HistoricalStat.kickoff < cutoff - timedelta(hours=3), HistoricalStat.observed_at < cutoff,or_(and_(HistoricalStat.home.is_(True),Fixture.home_id==player.club_id),and_(HistoricalStat.home.is_(False),Fixture.away_id==player.club_id)))).all()
        result['manager_matches'] = len(rows)
        # Regularized estimates use the player's wider available history, never another club's raw rate.
        if rows:
            result['manager_60_rate'] = (sum(r.minutes >= 60 for r in rows) + 2) / (len(rows) + 4)
            result['manager_minutes'] = (sum(r.minutes for r in rows) + 4 * 45) / (len(rows) + 4)
    tactical = session.scalars(select(TacticalObservation).where(TacticalObservation.club_id == player.club_id, TacticalObservation.match_at < cutoff - timedelta(hours=3), TacticalObservation.observed_at < cutoff).order_by(TacticalObservation.match_at.desc()).limit(5)).all()
    possession = [t.possession for t in tactical if t.possession is not None and not t.inferred]
    if possession:
        result['possession_5'] = float(np.mean(possession))
    formations = [t.formation for t in reversed(tactical) if t.formation]
    if len(formations) >= 2:
        result['formation_changes'] = sum(a != b for a,b in zip(formations, formations[1:]))
    result['arrivals_30'] = len(session.scalars(select(FootballEvent).where(FootballEvent.to_club_id == player.club_id, FootballEvent.status == 'CONFIRMED', FootballEvent.effective_at < cutoff, FootballEvent.effective_at >= cutoff - timedelta(days=30), FootballEvent.observed_at < cutoff)).all())
    memberships = session.scalars(select(Membership).where(Membership.club_id == player.club_id, Membership.starts_at < cutoff)).all()
    membership_times=dict(session.execute(select(Evidence.id,Evidence.observed_at).where(Evidence.id.in_({m.evidence_id for m in memberships}))).all())
    known = [m for m in memberships if not known_closed(m) and membership_times[m.evidence_id].replace(tzinfo=cutoff.tzinfo)<cutoff]
    # Historical positions are not reconstructed from today's player position.
    if known:
        peers=session.scalars(select(Player).where(Player.id.in_([m.player_id for m in known]),Player.position==player.position,Player.updated_at<cutoff)).all()
        # A current position that was updated after a historical cutoff is excluded.
        result['competition'] = max(0,len(peers)-int(any(p.id==player.id for p in peers)))
    return result

def enrich_history(session, frame):
    """Join context only where identity, club membership and observation time are established."""
    from types import SimpleNamespace
    import pandas as pd
    identities = {(i.season_id,i.fpl_id):i.player_id for i in session.scalars(select(Identity).where(Identity.player_id.is_not(None)))}
    memberships = session.scalars(select(Membership)).all()
    if not memberships:
        return frame
    first=min(pd.Timestamp(m.starts_at).tz_localize('UTC') if m.starts_at.tzinfo is None else pd.Timestamp(m.starts_at) for m in memberships)
    if pd.to_datetime(frame.get('deadline',frame.kickoff),utc=True).max()<first:return frame
    by_player={}
    for member in memberships:by_player.setdefault(member.player_id,[]).append(member)
    evidence_times=dict(session.execute(select(Evidence.id,Evidence.observed_at)).all())
    output=[]
    for row in frame.to_dict('records'):
        cutoff=pd.Timestamp(row.get('deadline',row['kickoff'])).to_pydatetime()
        if cutoff.tzinfo is None:
            from datetime import timezone
            cutoff=cutoff.replace(tzinfo=timezone.utc)
        pid=identities.get((row['season'],row['fpl_id']))
        valid=[m for m in by_player.get(pid,[]) if m.starts_at.replace(tzinfo=cutoff.tzinfo)<cutoff and not (m.ends_at is not None and m.ends_observed_at is not None and m.ends_at.replace(tzinfo=cutoff.tzinfo)<=cutoff and m.ends_observed_at.replace(tzinfo=cutoff.tzinfo)<cutoff) and evidence_times[m.evidence_id].replace(tzinfo=cutoff.tzinfo)<cutoff]
        if valid:
            member=max(valid,key=lambda m:m.starts_at)
            row.update(context_at(session,SimpleNamespace(id=pid,club_id=member.club_id,position=row.get('position')),cutoff))
            row['context_observed_at']=cutoff-timedelta(microseconds=1)
        output.append(row)
    return pd.DataFrame(output)

def sustained_change(before, after, min_matches=6):
    """Welch test with minimum effect size; exploratory detector, not a validated causal claim."""
    from scipy.stats import ttest_ind
    a, b = np.asarray(before, float), np.asarray(after, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < min_matches or len(b) < min_matches or np.std(np.r_[a,b]) == 0:
        return {'detected': False, 'reason': 'insufficient evidence'}
    test = ttest_ind(a,b,equal_var=False)
    effect = abs(float(b.mean()-a.mean())) / max(float(a.std()), 1e-6)
    return {'detected': bool(test.pvalue < .01 and effect > 1), 'p_value': float(test.pvalue), 'standardized_shift': effect, 'matches': [len(a),len(b)], 'status': 'exploratory; provider-specific validation required'}
