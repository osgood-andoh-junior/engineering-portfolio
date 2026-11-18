import pandas as pd
import pytest
from ml.ingestion.historical import validate_history

def test_only_identical_duplicates_can_be_collapsed():
    row={'element':1,'fixture':1,'kickoff_time':'2025-08-01','total_points':3,'minutes':90}
    clean,removed=validate_history(pd.DataFrame([row,row]),'test')
    assert len(clean)==1 and removed==1
    with pytest.raises(ValueError,match='conflicting'):
        validate_history(pd.DataFrame([row,{**row,'total_points':9}]),'test')
