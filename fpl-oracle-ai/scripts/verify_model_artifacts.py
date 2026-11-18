"""Validate trusted local fitted artifacts; this does not rerun accuracy evaluation."""
import gc
import json
import pickle
from pathlib import Path
from sqlalchemy import select
from sklearn.utils.validation import check_is_fitted
from apps.api.config import settings
from apps.api.db import Session
from apps.api.models import ModelVersion


def main():
    root=settings.artifact_dir.resolve()
    results=[]
    with Session() as session:
        versions=session.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all()
    for version in versions:
        path=Path(version.artifact).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Artifact outside the trusted local training directory')
        bundle=pickle.loads(path.read_bytes())
        model=bundle['model']
        if bundle['kind'] in ('lstm','gru'):
            from ml.models.recurrent import RecurrentRegressor
            restored=RecurrentRegressor(model['input_size'],bundle['kind'])
            restored.load_state_dict(model['state'],strict=True)
            if not model['state'] or not bundle['residuals']:
                raise ValueError('Empty learned state or calibration residuals')
            del restored
        elif bundle['kind']=='baseline':
            if not model.get('position_prior'):
                raise ValueError('Baseline fitted priors missing')
        else:
            check_is_fitted(model)
        results.append({'id':version.id,'kind':bundle['kind'],'sequence_length':bundle.get('length'),'fitted_artifact_valid':True})
        del bundle,model
        gc.collect()
    (settings.data_dir/'model-artifact-verification.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({'validated_fitted_artifacts':len(results),'families':sorted({r['kind'] for r in results}),'sequence_lengths':sorted({r['sequence_length'] for r in results if r['kind'] in ('lstm','gru')}),'accuracy_re_evaluated':False},indent=2))


if __name__=='__main__':
    main()
