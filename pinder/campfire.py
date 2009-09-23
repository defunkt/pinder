"""
Handles Campfire online chat.
"""
import datetime
import re
import time
import urllib
import urlparse

from BeautifulSoup import BeautifulSoup
import httplib2

try:
    set # python 2.3 does not have the set data type
except NameError:
    from sets import Set as set

from __init__ import __version__
from room import Room

class Campfire(object):
    """Creates a connection to the Campfire account with the given subdomain.
    Accepts a boolean indicating whether the connection should be made using
    SSL or not (default: false)."""
    def __init__(self, subdomain, ssl=False):
        #: The Campfire's subdomain.
        self.subdomain = subdomain
        #: True if the user is logged in Campfire, False otherwise.
        self.logged_in = False
        #: Contains the connection cookie.
        self.cookie = None

        # Schema for the Campfire URI
        schema = 'http'
        if ssl: schema += 's'

        #: The U{urlparsed<http://docs.python.org/lib/module-urlparse.html#l2h-4268>} URI of the Campfire account.
        self.uri = urlparse.urlparse("%s://%s.campfirenow.com" % (schema, self.subdomain))
        self._location = None
        self._room_re = re.compile(r'room\/(\d*)')
        self._http_client = httplib2.Http(timeout=5)
        self._http_client.force_exception_to_status_code = False

    def login(self, email, password):
        """Logs into Campfire with the given email and password.

        Returns True if logged in, False otherwise."""
        response = self._post("login",
            dict(email_address=email, password=password))
        self.logged_in = self._verify_response(response,
            redirect_to=self._uri_for())
        return self.logged_in

    def logout(self):
        """Logs out from Campfire.

        Returns True if logged out, False otherwise."""
        retval = self._verify_response(self._get("logout"), redirect=True)
        self.logged_in = not retval
        return retval

    def create_room(self, name, topic=''):
        """Creates a Campfire room with the given name and an optional topic.

        Returns None if the room has not been created."""
        room_data = {
            'room[name]': name,
            'room[topic]': topic
        }
        response = self._post('account/create/room?from=lobby', room_data,
            ajax=True)
        if self._verify_response(response, success=True):
            return self.find_room_by_name(name)

    def find_room_by_name(self, name):
        """Finds a Campfire room with the given name.

        Returns a Room instance if found, None otherwise."""
        rooms = self._get_rooms_markup()

        for room in rooms:
            try:
                room_name = room.h2.a.string
            except AttributeError: # the chat is full
                room_name = room.h2.string.strip()

            if room_name.lower() == name.lower():
                try:
                    room_uri = room.h2.a['href']
                except AttributeError: # no uri available (!?)
                    return None

                room_id = self._room_id_from_uri(room_uri)
                return Room(self, room_id, name)

    def find_or_create_room_by_name(self, name):
        """Finds a Campfire room with the given name.
        If the room is not present it will be created.

        Returns a Room instance."""
        return self.find_room_by_name(name) or self.create_room(name)

    def users(self, *room_names):
        """Lists the users chatting in any room or in the given room(s).

        Returns a set of the users."""
        rooms = self._get_rooms_markup()

        all_users = []
        for room in rooms:
            try:
                room_name = room.h2.a.string
            except AttributeError: # the chat is full
                room_name = room.h2.string.strip()
            if not room_names or room_name in room_names:
                room_users_list = room.find('ul')
                if not room_users_list:
                    break
                room_users = room_users_list.findAll('span')
                for user in room_users:
                    all_users.append(user.string)
        return set(all_users)

    def rooms_names(self):
        """Lists the names of the rooms available in the Campfire subdomain.

        Returns a list of the names of the rooms."""
        rooms = self._get_rooms_markup()

        rooms_names_list = []
        for room in rooms:
            try:
                rooms_names_list.append(room.h2.a.string)
            except AttributeError:
                rooms_names_list.append(room.h2.string.strip())
        rooms_names_list.sort()
        return rooms_names_list

    def rooms(self):
        """Lists the available rooms.

        Returns a list of Room objects."""
        names = self.rooms_names()
        return [self.find_room_by_name(name) for name in names]

    def transcripts(self, room_id=None):
        """Gets the dates of the transcripts by room filtered by the given id
        if any.

        Returns a dictionary of all the dates by room.
        """
        uri = 'files%2Btranscripts'
        if room_id:
            uri = '%s?room_id=%s' % (uri, str(room_id))

        soup = BeautifulSoup(self._get(uri).body)

        def _filter_transcripts(tag):
            return tag.has_key('class') and 'transcript' in tag['class'].split()
        transcripts_markup = soup.findAll(_filter_transcripts)

        result = {}
        for tag in transcripts_markup:
            link = tag.a['href']
            found_room_id = self._room_id_from_uri(link)
            date = re.search(
                r'/transcript/(\d{4}/\d{2}/\d{2})', link).groups()[0]
            try:
                result[found_room_id]
            except KeyError:
                result[found_room_id] = []
            result[found_room_id].append(self._parse_transcript_date(date))

        if room_id:
            return result[str(room_id)]
        return result

    def _parse_transcript_date(self, date):
        return datetime.date.fromtimestamp(time.mktime(
            time.strptime(date, '%Y/%m/%d')))

    def _filter_rooms_markup(self, tag):
        return tag.name == 'div' and tag.has_key('id') and tag['id'].startswith('room_')

    def _get_rooms_markup(self):
        body = self._get().body
        soup = BeautifulSoup(body)
        return soup.findAll(self._filter_rooms_markup)

    def _uri_for(self, path=''):
        return "%s/%s" % (urlparse.urlunparse(self.uri), path)

    def _room_id_from_uri(self, uri):
        try:
            return self._room_re.split(uri)[1]
        except IndexError:
            pass

    def _prepare_request(self, **options):
        headers = {}

        headers['User-Agent'] = 'Pinder/%s' % __version__

        if self.cookie:
            headers['cookie'] = self.cookie
        if 'ajax' in options:
            headers['X-Requested-With'] = 'XMLHttpRequest'
            headers['X-Prototype-Version'] = '1.5.1.1'
        return headers

    def _perform_request(self, method, path, data={}, **options):
        headers = self._prepare_request(**options)
        if method == 'POST':
            headers.update({"Content-type": "application/x-www-form-urlencoded"})
            location = self._uri_for(path)
        elif method == 'GET':
            if self._location:
                location = self._location
            else:
                location = self._uri_for(path)
            self._location = None
        else:
            raise Exception, 'Unsupported HTTP method'

        response, content = self._http_client.request(location, method,
            urllib.urlencode(data), headers)
        response.body = content

        if response.get('set-cookie'):
            self.cookie = response.get('set-cookie')

        return response

    def _post(self, path, data={}, **options):
        return self._perform_request('POST', path, data, **options)

    def _get(self, path=''):
        return self._perform_request('GET', path)

    def _verify_response(self, response, **options):
        if 'success' in options:
            return response.status == 200
        elif 'redirect' in options:
            return response.status in xrange(300, 400)
        elif 'redirect_to' in options:
            location = response.get('location')
            return self._verify_response(
                response, redirect=True) and location == options['redirect_to']
        else:
            return False


__all__ = ['Campfire']
