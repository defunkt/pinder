"""
Handles the Campfire room.
"""
from datetime import datetime
import re
import time
import urlparse

from BeautifulSoup import BeautifulSoup

class Room(object):
    "A Campfire room."
    def __init__(self, campfire, id, name=None):
        self._campfire = campfire
        self._verify_response = campfire._verify_response
        self._post = campfire._post
        self._get = campfire._get
        self._room = None

        self.membership_key = self.user_id = None
        self.last_cache_id = self.timestamp = None
        self.idle_since = datetime.now()

        #: The room id.
        self.id = id
        #: The name of the room.
        self.name = name
        #: The U{urlparsed<http://docs.python.org/lib/module-urlparse.html#l2h-4268>} URI of the room.
        self.uri = urlparse.urlparse("%s/room/%s" % (urlparse.urlunparse(self._campfire.uri), self.id))

    def __repr__(self):
        return "<Room: %s>" % self.name

    def __eq__(self, other):
        return self.id == other.id

    def join(self, force=False):
        """Joins the room; if 'force' is True join even if already joined.

        Returns True if successfully joined, False otherwise. """
        if not self._room or force:
            self._room = self._get("room/%s" % self.id)
            if not self._verify_response(self._room, success=True):
                self._room = None
                return False
            self._get_room_data()
        self.ping()
        return True

    def leave(self):
        """Leaves the room.

        Returns True if successfully left, False otherwise."""
        has_left = self._verify_response(
            self._post('room/%s/leave' % self.id), redirect=True)
        self._room = self.membership_key = self.user_id = None
        self.last_cache_id = self.timestamp = self.idle_since = None
        return has_left

    def toggle_guest_access(self):
        """Toggles guest access on and off.

        Returns True if successfully toggled, False otherwise."""
        response_result = self._verify_response(
            self._post(
                'room/%s/toggle_guest_access' % self.id), success=True)

        # go back inside to toggle the guest access
        return response_result and self.join(True)

    def guest_access_enabled(self):
        """Checks if the guest access is enabled.

        Returns True if the guest access is enabled, False otherwise."""
        return self.guest_url() is not None

    def guest_url(self):
        """Gets the URL for guest access.

        Returns None if the guest access is not enabled."""
        self.join()
        soup = BeautifulSoup(self._room.body)
        try:
            return soup.find('div', {'id': 'guest_access_control'}).h4.string
        except AttributeError:
            return None

    def guest_invite_code(self):
        """Gets the invite code for guest access.

        Returns None if the guest access is not enabled."""
        url = self.guest_url()
        if url:
            return re.search(r'\/(\w*)$', url).groups(0)[0]

    def change_name(self, name):
        """Changes the name of the room.

        Returns the new name if successfully changed, None otherwise."""
        response = self._post('account/edit/room/%s' % self.id,
            {'room[name]': name}, ajax=True)
        if self._verify_response(response, success=True):
            self.name = name
            return self.name
    rename = change_name

    def change_topic(self, topic):
        """Changes the topic of the room.

        Returns the new topic if successfully changed, None otherwise."""
        response = self._post('room/%s/change_topic' % self.id,
            {'room[topic]': topic}, ajax=True)
        if self._verify_response(response, success=True):
            return topic

    def topic(self):
        """Gets the current topic, if any."""
        self.join()
        soup = BeautifulSoup(self._room.body)
        h = soup.find(attrs={'id': 'topic'})
        if h:
            def _is_navigable_string(tag):
                return not hasattr(tag, 'attrs')
            topic = filter(_is_navigable_string, h.contents)
            return repr("".join(topic).strip())

    def lock(self):
        """Locks the room to prevent new users from entering.

        Returns True if successfully locked, False otherwise."""
        return self._verify_response(self._post(
            'room/%s/lock' % self.id, {}, ajax=True), success=True)

    def unlock(self):
        """Unlocks the room.

        Returns True if successfully unlocked, False otherwise."""
        return self._verify_response(self._post(
            'room/%s/unlock' % self.id, {}, ajax=True), success=True)

    def ping(self, force=False):
        """Pings the server updating the last time we have been seen there.

        Returns True if successfully pinged, False otherwise."""
        now = datetime.now()
        delta = now - self.idle_since
        if delta.seconds < 60 or force:
            self.idle_since = datetime.now()
            return self._verify_response(self._post(
                'room/%s/tabs' % self.id, {}, ajax=True), success=True)
        return False

    def destroy(self):
        """Destroys the room.

        Returns True if successfully destroyed, False otherwise."""
        return self._verify_response(self._post(
            'account/delete/room/%s' % self.id), success=True)

    def users(self):
        """Lists the users chatting in the room.

        Returns a set of the users."""
        return self._campfire.users(self.name)

    def speak(self, message):
        """Send a message to the room.

        Returns the message if successfully sent it, None otherwise."""
        self.join()
        return self._send(message)

    def paste(self, message):
        """Paste a message to the room.

        Returns the message if successfully pasted it, None otherwise."""
        self.join()
        return self._send(message, {'paste': True})

    def messages(self):
        """Gets new messages.

        Returns a list of message data:
         * id: the id of the message
         * person: the name of the person who wrote the message if any
         * user_id: the user id of the person if any
         * message: the message itself if any"""
        data = dict(l=self.last_cache_id, m=self.membership_key,
                    s=self.timestamp, t=int(time.time()))
        response = self._post("poll.fcgi", data, ajax=True)

        cache_match = re.search(r'lastCacheID = (\d+)', response.body)
        if cache_match:
            self.last_cache_id = cache_match.groups(0)[0]

        messages = []

        for line in response.body.split("\r\n"):
            if 'timestamp_message' in line:
                continue

            id_match = re.search(r'message_(\d+)', line)
            if not id_match:
                continue

            try:
                messages.append(dict(
                    id = id_match.groups(0)[0],
                    user_id = re.search(r'user_(\d+)', line).groups(0)[0],
                    person = re.search(r'\\u003Ctd class=\\"person\\"\\u003E(?:\\u003Cspan\\u003E)?(.+?)(?:\\u003C\/span\\u003E)?\\u003C\/td\\u003E', line).groups(0)[0],
                    message = re.search(r'\\u003Ctd class=\\"body\\"\\u003E\\u003Cdiv\\u003E(.+?)\\u003C\/div\\u003E\\u003C\/td\\u003E', line).groups(0)[0]
                    ))
            except AttributeError:
                continue

        return messages

    def transcripts(self):
        """Gets the dates of transcripts of the room.

        Returns a list of dates."""
        return self._campfire.transcripts(self.id)

    def transcript(self, date):
        """Get the transcript for the given date (a datetime.date instance).

        Returns a list of message data:
         * id: the id of the message
         * person: the name of the person who wrote the message if any
         * user_id: the user id of the person if any
         * message: the message itself if any"""
        uri = 'room/%s/transcript/%s' % (self.id, date.strftime('%Y/%m/%d'))

        soup = BeautifulSoup(self._get(uri).body)

        def _filter_messages(tag):
            return tag.has_key('class') and 'message' in tag['class'].split()
        messages = soup.findAll(_filter_messages)

        all_transcript = []
        for message in messages:
            t = {}

            person = message.find(True, attrs={'class': 'person'})
            try:
                t['person'] = person.span.string
            except AttributeError:
                try:
                    t['person'] = person.string
                except AttributeError:
                    t['person'] = None

            body = message.find('td', attrs={'class': 'body'})
            try:
                t['message'] = body.div.string
            except AttributeError:
                t['message'] = None

            t['id'] = re.search(r'message_(\d+)', message['id']).groups()[0]
            match = re.search(r'user_(\d+)', message['class'])
            if match:
                t['user_id'] = match.groups()[0]
            else:
                t['user_id'] = None

            all_transcript.append(t)

        return all_transcript

    def _send(self, message, options={}):
        data = {'message': message, 't': int(time.time())}
        data.update(options)
        response = self._post('room/%s/speak' % self.id, data, ajax=True)
        if self._verify_response(response, success=True):
            return message

    def _get_room_data(self):
        self.membership_key = re.search(r'\"membershipKey\": \"([a-z0-9]+)\"',
            self._room.body).groups(0)[0]
        self.user_id = re.search(r'\"userID\": (\d+)',
            self._room.body).groups(0)[0]
        self.last_cache_id = re.search(r'\"lastCacheID\": (\d+)',
            self._room.body).groups(0)[0]
        self.timestamp = re.search(r'\"timestamp\": (\d+)',
            self._room.body).groups(0)[0]



__all__ = ['Room']
