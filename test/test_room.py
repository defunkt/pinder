from httplib import HTTPConnection
import unittest

from pinder import Campfire, Room
import utils


class RoomTest(unittest.TestCase):
    def setUp(self):
        self.response = utils.MockResponse()
        self.campfire = Campfire('foobar')
        self.room = Room(self.campfire, 12345, 'Room 1')
        self.campfire = Campfire('foobar')
        response = self.response
        HTTPConnection.request = lambda self, m, l, b, h: None
        HTTPConnection.getresponse = lambda self: response
        
    def test_join(self):
        utils.FIXTURE = 'room_info'
        self.assertEqual(True, self.room.join())
        self.assertEqual(True, self.room.join(force=True))

    def test_guest_url_no_guest_url(self):
        utils.FIXTURE = 'no_guest_url'
        self.assert_(self.room.guest_url() is None)
        
    def test_guest_url(self):
        utils.FIXTURE = 'guest_url'
        self.assertEqual('http://sample.campfirenow.com/99d14',
            self.room.guest_url())
            
    def test_guest_invite_code_no_guest_url(self):
        utils.FIXTURE = 'no_guest_url'
        self.assert_(self.room.guest_invite_code() is None)
        
    def test_guest_invite_code(self):
        utils.FIXTURE = 'guest_url'
        self.assertEqual('99d14', self.room.guest_invite_code())
        
    def test_transcripts(self):
        utils.FIXTURE = 'transcripts'
        transcripts = self.room.transcripts()
        self.assertEqual(1, len(transcripts))
        

if __name__ == '__main__':
    unittest.main()
