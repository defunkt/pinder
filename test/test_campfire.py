from httplib import HTTPConnection
import unittest
from urlparse import urlparse

import httplib2

from pinder import Campfire
import utils

class CampfireTest(unittest.TestCase):
    def setUp(self):
        self.response = utils.MockResponse()
        self.campfire = Campfire('foobar')
        response = self.response
        HTTPConnection.request = lambda self, m, l, b, h: None
        HTTPConnection.getresponse = lambda self: response
        httplib2.Response = utils.MockHttplib2Response
        
    def test_creation(self):
        self.assertEqual('foobar', self.campfire.subdomain)
        self.assertEqual(False, self.campfire.logged_in)
        self.assertEqual(None, self.campfire.cookie)
        uri = 'http://foobar.campfirenow.com'
        self.assertEqual(urlparse(uri), self.campfire.uri)
        self.assertEqual(self.campfire._uri_for(), '%s/' % uri)

    def test_ssl(self):
        campfire = Campfire('foobar', True)
        uri = 'https://foobar.campfirenow.com'
        self.assertEqual(urlparse(uri), campfire.uri)

    def test_verify_response_success(self):
        self.response.status = 200
        self.assertEqual(True, self.campfire._verify_response(self.response,
            success=True))

    def test_verify_response_redirect_true(self):
        self.response.status = 302
        self.assertEqual(True, self.campfire._verify_response(self.response,
            redirect=True))

    def test_verify_response_redirect_false(self):
        self.response.status = 200
        self.assertEqual(False, self.campfire._verify_response(self.response,
            redirect=True))

    def test_verify_response_redirect_to(self):
        self.response.status = 304
        self.assertEqual(True, self.campfire._verify_response(self.response,
            redirect_to='/foobar'))

    def test_verify_response_redirect_to_without_redirect(self):
        self.response.status = 200
        self.assertEqual(False, self.campfire._verify_response(self.response,
            redirect_to='/foobar'))

    def test_verify_response_redirect_to_wrong_path(self):
        response = utils.MockResponse()
        response.headers['location'] = '/baz'
        response.status = 304
        self.assertEqual(False, self.campfire._verify_response(response,
            redirect_to='/foobar'))

    def test_prepare_request(self):
        headers = self.campfire._prepare_request()
        self.assert_('User-Agent' in headers)
        self.assert_(headers['User-Agent'].startswith('Pinder/'))
        headers = self.campfire._prepare_request(ajax=True)
        self.assert_('X-Requested-With' in headers)
        self.campfire.cookie = 'cookie'
        headers = self.campfire._prepare_request()
        self.assertEqual(headers['cookie'], self.campfire.cookie)
    
    def test_perform_request(self):
        response = self.campfire._perform_request('GET', '')
        self.assertEqual(self.campfire.cookie, response.getheader('set-cookie'))
    
    def test_login(self):
        utils.FIXTURE = 'default'
        self.response.headers['location'] = self.campfire._uri_for()
        self.response.status = 302
        self.assertEqual(True, self.campfire.login('foo', 'foopass'))
        
    def test_find_room_by_name(self):
        utils.FIXTURE = 'rooms_names'
        room = self.campfire.find_room_by_name('Room A')
        self.assert_(room is not None)
        self.assert_(self.campfire.find_room_by_name('No Room') is None)
    
    def test_find_room_by_name_no_rooms(self):
        utils.FIXTURE = 'no_rooms'
        self.assert_(self.campfire.find_room_by_name('Room A') is None)
    
    def test_create_room(self):
        utils.FIXTURE = 'rooms_names'
        name = 'New Room'
        self.assert_(self.campfire.find_room_by_name(name) is None)
        new_room_markup = self.response.read().splitlines()
        new_room_markup.append("""
        <div id="room_1234" class="room available shaded"><h2>
        <a href="http://sample.campfirenow.com/room/1234">%s</a>
        </h2>
        </div>""" % name)
        self.response.read = lambda: '\n'.join(new_room_markup)
        self.assert_(self.campfire.find_room_by_name(name) is not None)
    
    def test_users_rooms_empty(self):
        utils.FIXTURE = 'chat_rooms_empty'
        self.assert_(not self.campfire.users())

    def test_users_rooms_one_empty(self):
        utils.FIXTURE = 'chat_rooms_one_empty'
        self.assert_('Tom Jones' in self.campfire.users('Room A'))
        self.assert_(not self.campfire.users('Room B'))

    def test_users_rooms_not_empty(self):
        utils.FIXTURE = 'chat_rooms_not_empty'
        users = self.campfire.users()
        self.assertEqual(['Tom Jones', 'Gloria Estefan'], list(users))
        
    def test_rooms_names(self):
        utils.FIXTURE = 'rooms_names'
        self.assertEqual(['Room A', 'Room B'], self.campfire.rooms_names())

    def test_rooms(self):
        utils.FIXTURE = 'rooms_names'
        from pinder import Room
        self.assert_(isinstance(self.campfire.rooms()[0], Room))
        
    def test_find_or_create_room_by_name(self):
        utils.FIXTURE = 'chat_rooms_empty'
        room = self.campfire.find_room_by_name('Room A')
        self.assertEqual(room, self.campfire.find_or_create_room_by_name(
            'Room A'))
    
    def test_room_id_from_url(self):
        self.assertEqual(None, self.campfire._room_id_from_uri(
            'http://www.google.com'))
        self.assertEqual('1234', self.campfire._room_id_from_uri(
            'http://foo.campfirenow.com/room/1234/foo/bar'))
            
    def test_transcripts(self):
        utils.FIXTURE = 'transcripts'
        transcripts = self.campfire.transcripts()
        self.assertEqual(2, len(transcripts.keys()))
        self.assert_('12345' in transcripts.keys())
        self.assertEqual(2001, transcripts['12345'][0].year)

    def test_transcripts_empty(self):
        utils.FIXTURE = 'no_transcripts'
        transcripts = self.campfire.transcripts()
        self.assertEqual({}, transcripts)


if __name__ == '__main__':
    unittest.main()
