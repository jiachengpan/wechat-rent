from google.appengine.api import memcache
import pickle

def store(key, value, chunksize=950000):
  serialized = pickle.dumps(value, 2)
  values = {}
  for i in xrange(0, len(serialized), chunksize):
    values['%s.%s' % (key, i//chunksize)] = serialized[i : i+chunksize]
  return memcache.set_multi(values)

def retrieve(key):
  result = memcache.get_multi(['%s.%s' % (key, i) for i in xrange(32)])
  serialized = ''.join([v for k, v in sorted(result.items()) if v is not None])
  return pickle.loads(serialized)

