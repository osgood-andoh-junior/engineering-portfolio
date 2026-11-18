import json
import time
import secrets
import threading
from contextlib import contextmanager
from redis import Redis
from redis.exceptions import RedisError
from apps.api.config import settings

class Cache:
    def __init__(self, redis=None):
        self.redis = redis or (Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2) if settings.redis_url else None)
        self.local = {}
        self.local_locks={}
        self.hits = self.misses = 0
        self.stale_hits=0

    def version(self):
        if self.redis:
            try:
                return self.redis.get('oracle:version') or '0'
            except RedisError:
                pass
        return str(self.local.get('_version', 0))

    def read(self,key):
        key = f'oracle:v2:{self.version()}:{key}'
        entry=None
        if self.redis:
            try:
                value = self.redis.get(key)
                if value:
                    entry=json.loads(value)
            except RedisError:
                pass
        if entry is None:entry=self.local.get(key)
        if entry and entry['stale_until']>time.time():
            if entry['fresh_until']>time.time():
                self.hits+=1
                return entry['value'],'fresh'
            self.stale_hits+=1
            return entry['value'],'stale'
        self.misses += 1
        return None,'miss'

    def get(self,key,allow_stale=False):
        value,state=self.read(key)
        return value if state=='fresh' or state=='stale' and allow_stale else None

    def set(self, key, value, ttl=300,stale_ttl=0):
        if ttl<=0 or stale_ttl<0:raise ValueError('Invalid cache TTL')
        key = f'oracle:v2:{self.version()}:{key}'
        entry={'value':value,'fresh_until':time.time()+ttl,'stale_until':time.time()+ttl+stale_ttl}
        if self.redis:
            try:
                self.redis.set(key, json.dumps(entry), ex=ttl+stale_ttl)
                return
            except RedisError:
                pass
        self.local[key] = entry

    def invalidate(self):
        if self.redis:
            # Failure propagates so durable refresh retries rather than silently skipping invalidation.
            self.redis.incr('oracle:version')
        self.local.clear()
        self.local['_version'] = time.time_ns()

    @contextmanager
    def lock(self, key, ttl=120):
        if not self.redis:
            local_lock=self.local_locks.setdefault(key,threading.Lock())
            acquired=local_lock.acquire(blocking=False)
            try:yield acquired
            finally:
                if acquired:local_lock.release()
            return
        token = secrets.token_hex(16)
        acquired = self.redis.set('lock:' + key, token, nx=True, ex=ttl)
        try:
            yield bool(acquired)
        finally:
            if acquired:
                self.redis.eval("if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end", 1, 'lock:' + key, token)

cache = Cache()
