import os
from runtests import TESTDIR

FIXTURE = 'default'

class MockResponse(object):
    def __init__(self):
        self.status = 200
        self.headers = {
            'location': '/foobar',
            'set-cookie': 'cookie',
        }
        self.fixture = ''
    
    def getheader(self, header_name, default=None):
        return self.headers.get(header_name)
    get = getheader

    def read(self):
        path = os.path.join(TESTDIR, "fixtures/%s.html" % FIXTURE)
        return open(path).read()

class MockHttplib2Response(MockResponse):
    def __init__(self, info):
        self.status = info.status
        self.headers = info.headers
        self.fixture = ''
    
    def has_key(self, key):
        return self.__contains__(key)
        
    def __iter__(self):
        return iter(self.headers.keys())
        
    def __contains__(self, item):
        return item in self.headers
        
    def __getitem__(self, item):
        item = self.headers.get(item)
        if not item:
            raise KeyError(item)
        
    def __setitem__(self, key, value):
        self.headers[key] = value
