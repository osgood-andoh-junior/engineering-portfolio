import os
import pytest
from apps.api.cache import Cache

@pytest.mark.skipif(not os.getenv('TEST_REDIS_URL'),reason='A real isolated Redis test service is required')
def test_redis_version_and_lock_isolation():
    from redis import Redis
    redis=Redis.from_url(os.environ['TEST_REDIS_URL'],decode_responses=True)
    a,b=Cache(redis),Cache(redis)
    import uuid
    key='test:'+uuid.uuid4().hex
    a.set(key,{'value':1},ttl=30)
    assert b.get(key)=={'value':1}
    with a.lock(key) as owner:
        assert owner
        with b.lock(key) as contender: assert not contender
    b.invalidate()
    assert a.get(key) is None
