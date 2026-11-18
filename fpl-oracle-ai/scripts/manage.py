import argparse
import asyncio
import json
from apps.api.db import Session

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['sync','history','train','train-minutes','predict','worker-once','backtest','matches','managers'])
    parser.add_argument('--limit',type=int,default=50)
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--epochs',type=int,default=5)
    parser.add_argument('--max-rows',type=int)
    parser.add_argument('--kinds',default='baseline,catboost,lightgbm,lstm,gru')
    parser.add_argument('--strict-point-in-time',action='store_true')
    args=parser.parse_args()
    with Session() as session:
        if args.command=='sync':
            from ml.ingestion.fpl import sync_fpl
            result=asyncio.run(sync_fpl(session))
        elif args.command=='managers':
            from ml.ingestion.managers import import_reviewed_directory,refresh_manager_match_facts
            result=import_reviewed_directory(session)
            result['match_records']=refresh_manager_match_facts(session)
        elif args.command=='matches':
            from ml.ingestion.current_matches import sync_player_matches
            result=asyncio.run(sync_player_matches(session,limit=args.limit,offset=args.offset))
        elif args.command=='history':
            from ml.ingestion.historical import sync_history
            result=asyncio.run(sync_history(session))
        elif args.command=='train-minutes':
            from ml.training.minutes import train_minutes
            result=train_minutes(session)
        elif args.command=='train':
            from ml.training.train import train
            result=train(session,kinds=tuple(args.kinds.split(',')),epochs=args.epochs,max_rows=args.max_rows,strict_point_in_time=args.strict_point_in_time)
        elif args.command=='backtest':
            from ml.training.train import load_frame
            from ml.features.intelligence import enrich_history
            from ml.features.point_in_time import build_features
            from ml.evaluation.backtest import rolling_backtest
            from apps.api.config import settings
            frame=build_features(enrich_history(session,load_frame(session)))
            result=rolling_backtest(frame)
            settings.artifact_dir.mkdir(exist_ok=True)
            (settings.artifact_dir/'backtest.json').write_text(json.dumps(result,indent=2,default=str))
        elif args.command=='predict':
            from ml.inference.predict import refresh_predictions
            from apps.api.cache import cache
            result=refresh_predictions(session); session.commit(); cache.invalidate()
        else:
            from workers.run import run_once
            result=asyncio.run(run_once())
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
