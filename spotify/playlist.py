from __future__ import unicode_literals

import collections
import pprint
import re

import spotify
from spotify import ffi, lib, utils


__all__ = [
    'Playlist',
    'PlaylistContainer',
    'PlaylistFolder',
    'PlaylistOfflineStatus',
    'PlaylistTrack',
    'PlaylistType',
    'PlaylistUnseenTracks',
]


class Playlist(object):
    """A Spotify playlist.

    You can get playlists from the :attr:`~Session.playlist_container`,
    :attr:`~Session.inbox`, :attr:`~Session.starred`,
    :meth:`~Session.starred_for_user`, :meth:`~Session.search`, etc., or you
    can create a playlist yourself from a Spotify URI::

        >>> playlist = spotify.Playlist(
        ...     'spotify:user:fiat500c:playlist:54k50VZdvtnIPt4d8RBCmZ')
        >>> playlist.load().name
        u'500C feelgood playlist'
    """

    def __init__(self, uri=None, sp_playlist=None, add_ref=True):
        assert uri or sp_playlist, 'uri or sp_playlist is required'
        if uri is not None:
            playlist = spotify.Link(uri).as_playlist()
            if playlist is None:
                raise spotify.Error(
                    'Failed to get playlist from Spotify URI: %r' % uri)
            sp_playlist = playlist._sp_playlist
            add_ref = True
        if add_ref:
            lib.sp_playlist_add_ref(sp_playlist)
        self._sp_playlist = ffi.gc(sp_playlist, lib.sp_playlist_release)

    def __repr__(self):
        if not self.is_loaded:
            return 'Playlist(<not loaded>)'
        try:
            return 'Playlist(%r)' % self.link.uri
        except spotify.Error as exc:
            return 'Playlist(<error: %s>)' % exc

    @property
    def is_loaded(self):
        """Whether the playlist's data is loaded."""
        return bool(lib.sp_playlist_is_loaded(self._sp_playlist))

    def load(self, timeout=None):
        """Block until the playlist's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self, timeout=timeout)

    # TODO add_callbacks()
    # TODO remove_callbacks()

    @property
    def tracks(self):
        """The playlist's tracks.

        Will always return an empty list if the search isn't loaded.
        """
        if not self.is_loaded:
            return []

        def get_track(sp_playlist, key):
            return spotify.Track(
                sp_track=lib.sp_playlist_track(sp_playlist, key))

        return utils.Sequence(
            sp_obj=self._sp_playlist,
            add_ref_func=lib.sp_playlist_add_ref,
            release_func=lib.sp_playlist_release,
            len_func=lib.sp_playlist_num_tracks,
            getitem_func=get_track)

    @property
    def tracks_with_metadata(self):
        """The playlist's tracks, with metadata specific to the playlist as a
        a list of :class:`~spotify.PlaylistTrack` objects.

        Will always return an empty list if the search isn't loaded.
        """
        if not self.is_loaded:
            return []

        return utils.Sequence(
            sp_obj=self._sp_playlist,
            add_ref_func=lib.sp_playlist_add_ref,
            release_func=lib.sp_playlist_release,
            len_func=lib.sp_playlist_num_tracks,
            getitem_func=PlaylistTrack)

    @property
    def name(self):
        """The playlist's name.

        Assigning to :attr:`name` will rename the playlist.

        Will always return :class:`None` if the track isn't loaded.
        """
        name = utils.to_unicode(lib.sp_playlist_name(self._sp_playlist))
        return name if name else None

    @name.setter
    def name(self, new_name):
        self.rename(new_name)

    def rename(self, new_name):
        """Rename the playlist."""
        new_name = ffi.new('char[]', utils.to_bytes(new_name))
        spotify.Error.maybe_raise(
            lib.sp_playlist_rename(self._sp_playlist, new_name))

    @property
    def owner(self):
        """The :class:`User` object for the owner of the playlist."""
        return spotify.User(sp_user=lib.sp_playlist_owner(self._sp_playlist))

    def is_collaborative(self):
        return bool(lib.sp_playlist_is_collaborative(self._sp_playlist))

    def set_collaborative(self, value):
        spotify.Error.maybe_raise(
            lib.sp_playlist_set_collaborative(self._sp_playlist, int(value)))

    collaborative = property(is_collaborative, set_collaborative)
    """Whether the playlist can be modified by all users or not."""

    def set_autolink_tracks(self, link=True):
        """If a playlist is autolinked, unplayable tracks will be made playable
        by linking them to other Spotify tracks, where possible."""
        # TODO Add a global default setting for if playlists just be autolinked
        # or not. pyspotify 1.x defaults to always autolinking, and doesn't
        # give the user any choice.
        spotify.Error.maybe_raise(
            lib.sp_playlist_set_autolink_tracks(self._sp_playlist, int(link)))

    @property
    def description(self):
        """The playlist's description.

        Will return :class:`None` if the description is unset.
        """
        description = lib.sp_playlist_get_description(self._sp_playlist)
        if description == ffi.NULL:
            return None
        return utils.to_unicode(description)

    @property
    def image(self):
        """The playlist's :class:`Image`.

        Will always return :class:`None` if the playlist isn't loaded or the
        playlist has no image.
        """
        image_id = ffi.new('char[20]')
        has_image = bool(
            lib.sp_playlist_get_image(self._sp_playlist, image_id))
        if not has_image:
            return None
        sp_image = lib.sp_image_create(
            spotify.session_instance._sp_session, image_id)
        return spotify.Image(sp_image=sp_image, add_ref=False)

    @property
    def has_pending_changes(self):
        """Check if the playlist has local changes that has not been
        acknowledged by the server yet.
        """
        return bool(lib.sp_playlist_has_pending_changes(self._sp_playlist))

    def add_tracks(self, tracks, position=None):
        """Add the given tracks to playlist at the given position.

        ``tracks`` can either be a single :class:`~spotify.Track` or a list of
        :class:`~spotify.Track` objects. If ``position`` isn't specified, the
        tracks are added to the end of the playlist.
        """
        if isinstance(tracks, spotify.Track):
            tracks = [tracks]
        if position is None:
            position = len(self.tracks)
        lib.sp_playlist_add_tracks(
            self._sp_playlist, [t._sp_track for t in tracks], len(tracks),
            position, spotify.session_instance._sp_session)

    def remove_tracks(self, tracks):
        """Remove the given tracks from the playlist.

        ``tracks`` can be a single :class:`~spotify.Track` or a list of
        :class:`~spotify.Track` objects.
        """
        if isinstance(tracks, spotify.Track):
            tracks = [tracks]
        tracks = list(set(tracks))  # Remove duplicates
        spotify.Error.maybe_raise(lib.sp_playlist_remove_tracks(
            self._sp_playlist, [t._sp_track for t in tracks], len(tracks)))

    def reorder_tracks(self, tracks, new_position):
        """Move the given ``tracks`` to a ``new_position`` in the playlist.

        ``tracks`` can be a single :class:`~spotify.Track` or a list of
        :class:`~spotify.Track` objects.

        ``new_position`` must be equal to or lower than the current playlist
        length.
        """
        if isinstance(tracks, spotify.Track):
            tracks = [tracks]
        tracks = list(set(tracks))  # Remove duplicates
        spotify.Error.maybe_raise(lib.sp_playlist_reorder_tracks(
            self._sp_playlist, [t._sp_track for t in tracks], len(tracks),
            new_position))

    @property
    def num_subscribers(self):
        """The number of subscribers to the playlist.

        The number can be higher than the length of the :attr:`subscribers`
        collection, especially if the playlist got many subscribers.

        May be zero until you call :meth:`update_subscribers` and the
        ``subscribers_changed`` callback is called.
        """
        # TODO Link subscribers_changed in docstring to callback docs
        return lib.sp_playlist_num_subscribers(self._sp_playlist)

    @property
    def subscribers(self):
        """The canonical usernames of up to 500 of the subscribers of the
        playlist.

        May be empty until you call :meth:`update_subscribers` and the
        ``subscribers_changed`` callback is called.
        """
        # TODO Link subscribers_changed in docstring to callback docs
        sp_subscribers = ffi.gc(
            lib.sp_playlist_subscribers(self._sp_playlist),
            lib.sp_playlist_subscribers_free)
        # The ``subscribers`` field is ``char *[1]`` according to the struct,
        # so we must cast it to ``char **`` to be able to access more than the
        # first subscriber.
        subscribers = ffi.cast('char **', sp_subscribers.subscribers)
        usernames = []
        for i in range(sp_subscribers.count):
            usernames.append(utils.to_unicode(subscribers[i]))
        return usernames

    def update_subscribers(self):
        """Request an update of :attr:`num_subscribers` and the
        :attr:`subscribers` collection.

        The ``subscribers_changed`` callback will be called when the subscriber
        data has been updated.
        """
        # TODO Link subscribers_changed in docstring to callback docs
        spotify.Error.maybe_raise(lib.sp_playlist_update_subscribers(
            spotify.session_instance._sp_session, self._sp_playlist))

    def is_in_ram(self):
        return bool(lib.sp_playlist_is_in_ram(
            spotify.session_instance._sp_session, self._sp_playlist))

    def set_in_ram(self, value):
        spotify.Error.maybe_raise(lib.sp_playlist_set_in_ram(
            spotify.session_instance._sp_session, self._sp_playlist,
            int(value)))

    in_ram = property(is_in_ram, set_in_ram)
    """Whether the playlist is in RAM, and not only on disk.

    A playlist must *currently be* in RAM for tracks to be available. A
    playlist must *have been* in RAM for other metadata to be available.

    By default, playlists are kept in RAM unless
    :attr:`~spotify.SessionConfig.initially_unload_playlists` is set to
    :class:`True` before creating the :class:`~spotify.Session`. If the
    playlists are initially unloaded, set :attr:`in_ram` to :class:`True` to
    have a playlist loaded into RAM.
    """

    def set_offline_mode(self, offline=True):
        """Mark the playlist to be synchronized for offline playback.

        The playlist must be in the current user's playlist container.
        """
        spotify.Error.maybe_raise(lib.sp_playlist_set_offline_mode(
            spotify.session_instance._sp_session, self._sp_playlist,
            int(offline)))

    @property
    def offline_status(self):
        """The playlist's :class:`PlaylistOfflineStatus`."""
        return PlaylistOfflineStatus(lib.sp_playlist_get_offline_status(
            spotify.session_instance._sp_session, self._sp_playlist))

    @property
    def offline_download_completed(self):
        """The download progress for an offline playlist.

        A number in the range 0-100. Always :class:`None` if
        :attr:`offline_status` isn't :attr:`PlaylistOfflineStatus.DOWNLOADING`.
        """
        if self.offline_status != PlaylistOfflineStatus.DOWNLOADING:
            return None
        return int(lib.sp_playlist_get_offline_download_completed(
            spotify.session_instance._sp_session, self._sp_playlist))

    @property
    def link(self):
        """A :class:`Link` to the playlist."""
        if not self.is_loaded:
            raise spotify.Error('The playlist must be loaded to create a link')
        sp_link = lib.sp_link_create_from_playlist(self._sp_playlist)
        if sp_link == ffi.NULL:
            if not self.in_ram:
                raise spotify.Error(
                    'The playlist must have been in RAM to create a link')
            # TODO Figure out why we can still get NULL here even if
            # the playlist is both loaded and in RAM.
            raise spotify.Error('Failed to get link from Spotify playlist')
        return spotify.Link(sp_link=sp_link, add_ref=False)


class PlaylistContainer(collections.MutableSequence):
    """A Spotify playlist container.

    The playlist container can be accessed as a regular Python collection to
    work with the playlists::

        >>> import spotify
        >>> session = spotify.Session()
        # Login, etc.
        >>> container = session.playlist_container
        >>> container.is_loaded
        False
        >>> container.load()
        [Playlist(u'spotify:user:jodal:playlist:6xkJysqhkj9uwufFbUb8sP'),
         Playlist(u'spotify:user:jodal:playlist:0agJjPcOhHnstLIQunJHxo'),
         PlaylistFolder(id=8027491506140518932L, name=u'Shared playlists',
            type=<PlaylistType.START_FOLDER: 1>),
         Playlist(u'spotify:user:p3.no:playlist:7DkMndS2KNVQuf2fOpMt10'),
         PlaylistFolder(id=8027491506140518932L, name=u'',
            type=<PlaylistType.END_FOLDER: 2>)]
        >>> container[0]
        Playlist(u'spotify:user:jodal:playlist:6xkJysqhkj9uwufFbUb8sP')

    As you can see, a playlist container can contain a mix of
    :class:`~spotify.Playlist` and :class:`~spotify.PlaylistFolder` objects.

    The container supports operations that changes the container as well.

    To add a playlist you can use :meth:`append` or :meth:`insert` with either
    the name of a new playlist or an existing playlist object. For example::

        >>> playlist = spotify.Playlist(
        ...     'spotify:user:fiat500c:playlist:54k50VZdvtnIPt4d8RBCmZ')
        >>> container.insert(3, playlist)
        >>> container.append('New empty playlist')

    To remove a playlist or folder you can use :meth:`remove_playlist`, or::

        >>> del container[0]

    To replace an existing playlist or folder with a new empty playlist with
    the given name you can use :meth:`remove_playlist` and
    :meth:`add_new_playlist`, or::

        >>> container[0] = 'My other new empty playlist'

    To replace an existing playlist or folder with an existing playlist you can
    :use :meth:`remove_playlist` and :meth:`add_playlist`, or::

        >>> container[0] = playlist
    """

    def __init__(self, sp_playlistcontainer, add_ref=True):
        if add_ref:
            lib.sp_playlistcontainer_add_ref(sp_playlistcontainer)
        self._sp_playlistcontainer = ffi.gc(
            sp_playlistcontainer, lib.sp_playlistcontainer_release)

    def __repr__(self):
        return '<spotify.PlaylistContainer owned by %s: %s>' % (
            self.owner.link.uri, pprint.pformat(list(self)))

    @property
    def is_loaded(self):
        """Whether the playlist container's data is loaded."""
        return bool(lib.sp_playlistcontainer_is_loaded(
            self._sp_playlistcontainer))

    def load(self, timeout=None):
        """Block until the playlist container's data is loaded.

        After ``timeout`` seconds with no results :exc:`~spotify.Timeout` is
        raised. If ``timeout`` is :class:`None` the default timeout is used.

        The method returns ``self`` to allow for chaining of calls.
        """
        return utils.load(self, timeout=timeout)

    # TODO add_callbacks()
    # TODO remove_callbacks()

    def __len__(self):
        # Required by collections.Sequence

        length = lib.sp_playlistcontainer_num_playlists(
            self._sp_playlistcontainer)
        if length == -1:
            return 0
        return length

    def __getitem__(self, key):
        # Required by collections.Sequence

        if isinstance(key, slice):
            return list(self).__getitem__(key)
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')

        playlist_type = PlaylistType(lib.sp_playlistcontainer_playlist_type(
            self._sp_playlistcontainer, key))

        if playlist_type is PlaylistType.PLAYLIST:
            sp_playlist = lib.sp_playlistcontainer_playlist(
                self._sp_playlistcontainer, key)
            return Playlist(sp_playlist=sp_playlist, add_ref=True)
        elif playlist_type in (
                PlaylistType.START_FOLDER, PlaylistType.END_FOLDER):
            return PlaylistFolder(
                id=lib.sp_playlistcontainer_playlist_folder_id(
                    self._sp_playlistcontainer, key),
                name=utils.get_with_fixed_buffer(
                    100,
                    lib.sp_playlistcontainer_playlist_folder_name,
                    self._sp_playlistcontainer, key),
                type=playlist_type)
        else:
            raise spotify.Error('Unknown playlist type: %r' % playlist_type)

    def __setitem__(self, key, value):
        # Required by collections.MutableSequence

        if not isinstance(key, (int, slice)):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if isinstance(key, slice):
            if not isinstance(value, collections.Iterable):
                raise TypeError('can only assign an iterable')
        if isinstance(key, int):
            if not 0 <= key < self.__len__():
                raise IndexError('list index out of range')
            key = slice(key, key + 1)
            value = [value]

        # In case playlist creation fails, we create before we remove any
        # playlists.
        for i, val in enumerate(value, key.start):
            if isinstance(val, Playlist):
                self.add_playlist(val, index=i)
            else:
                self.add_new_playlist(val, index=i)

        # Adjust for the new playlist at position key.start.
        key = slice(key.start + len(value), key.stop + len(value), key.step)
        del self[key]

    def __delitem__(self, key):
        # Required by collections.MutableSequence

        if isinstance(key, slice):
            start, stop, step = key.indices(self.__len__())
            indexes = range(start, stop, step)
            for i in reversed(sorted(indexes)):
                self.remove_playlist(i)
            return
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')
        self.remove_playlist(key)

    def add_new_playlist(self, name, index=None):
        """Add an empty playlist with ``name`` at the given ``index``.

        The playlist name must not be space-only or longer than 255 chars.

        If the ``index`` isn't specified, the new playlist is added at the end
        of the container.

        Returns the new playlist.
        """
        self._validate_name(name)
        name = ffi.new('char[]', utils.to_bytes(name))
        sp_playlist = lib.sp_playlistcontainer_add_new_playlist(
            self._sp_playlistcontainer, name)
        if sp_playlist == ffi.NULL:
            raise spotify.Error('Playlist creation failed')
        playlist = Playlist(sp_playlist=sp_playlist, add_ref=True)
        if index is not None:
            self.move_playlist(self.__len__() - 1, index)
        return playlist

    def add_playlist(self, playlist, index=None):
        """Add an existing ``playlist`` to the playlist container at the given
        ``index``.

        The playlist can either be a :class:`~spotify.Playlist`, or a
        :class:`~spotify.Link` linking to a playlist.

        If the ``index`` isn't specified, the playlist is added at the end of
        the container.

        Returns the added playlist, or :class:`None` if the playlist already
        existed in the container. If the playlist already exists, it will not
        be moved to the given ``index``.
        """
        if isinstance(playlist, spotify.Link):
            link = playlist
        elif isinstance(playlist, spotify.Playlist):
            link = playlist.link
        else:
            raise TypeError(
                'Argument must be Link or Playlist, got %s' % type(playlist))
        sp_playlist = lib.sp_playlistcontainer_add_playlist(
            self._sp_playlistcontainer, link._sp_link)
        if sp_playlist == ffi.NULL:
            return None
        playlist = Playlist(sp_playlist=sp_playlist, add_ref=True)
        if index is not None:
            self.move_playlist(self.__len__() - 1, index)
        return playlist

    def add_folder(self, name, index=None):
        """Add a playlist folder with ``name`` at the given ``index``.

        The playlist folder name must not be space-only or longer than 255
        chars.

        If the ``index`` isn't specified, the folder is added at the end of the
        container.
        """
        self._validate_name(name)
        if index is None:
            index = self.__len__()
        name = ffi.new('char[]', utils.to_bytes(name))
        spotify.Error.maybe_raise(lib.sp_playlistcontainer_add_folder(
            self._sp_playlistcontainer, index, name))

    def _validate_name(self, name):
        if len(name) > 255:
            raise ValueError('Playlist name cannot be longer than 255 chars')
        if len(re.sub('\s+', '', name)) == 0:
            raise ValueError('Playlist name cannot be space-only')

    def remove_playlist(self, index, recursive=False):
        """Remove playlist at the given index from the container.

        If the item at the given ``index`` is the start or the end of a
        playlist folder, and the other end of the folder is found, it is also
        removed. The folder content is kept, but is moved one level up the
        folder hierarchy. If ``recursive`` is :class:`True`, the folder content
        is removed as well.

        Using ``del playlist_container[3]`` is equivalent to
        ``playlist_container.remove_playlist(3)``. Similarly, ``del
        playlist_container[0:2]`` is equivalent to calling this method with
        indexes ``1`` and ``0``.
        """
        item = self[index]
        if isinstance(item, PlaylistFolder):
            indexes = self._find_folder_indexes(self, item.id, recursive)
        else:
            indexes = [index]
        for i in reversed(sorted(indexes)):
            spotify.Error.maybe_raise(
                lib.sp_playlistcontainer_remove_playlist(
                    self._sp_playlistcontainer, i))

    @staticmethod
    def _find_folder_indexes(container, folder_id, recursive):
        indexes = []
        for i, item in enumerate(container):
            if isinstance(item, PlaylistFolder) and item.id == folder_id:
                indexes.append(i)
        assert len(indexes) <= 2, (
            'Found more than 2 items with the same playlist folder ID')
        if recursive and len(indexes) == 2:
            start, end = indexes
            indexes = list(range(start, end + 1))
        return indexes

    def move_playlist(self, from_index, to_index, dry_run=False):
        """Move playlist at ``from_index`` to ``to_index``.

        If ``dry_run`` is :class:`True` the move isn't actually done. It is
        only checked if the move is possible.
        """
        spotify.Error.maybe_raise(lib.sp_playlistcontainer_move_playlist(
            self._sp_playlistcontainer, from_index, to_index, int(dry_run)))

    @property
    def owner(self):
        """The :class:`User` object for the owner of the playlist container."""
        sp_user = lib.sp_playlistcontainer_owner(self._sp_playlistcontainer)
        return spotify.User(sp_user=sp_user)

    def get_unseen_tracks(self, playlist):
        """Get a list of unseen tracks in the given ``playlist``.

        The list is a :class:`PlaylistUnseenTracks` instance.

        The tracks will remain "unseen" until :meth:`clear_unseen_tracks` is
        called on the playlist.
        """
        return PlaylistUnseenTracks(
            self._sp_playlistcontainer, playlist._sp_playlist)

    def clear_unseen_tracks(self, playlist):
        """Clears unseen tracks from the given ``playlist``."""
        result = lib.sp_playlistcontainer_clear_unseen_tracks(
            self._sp_playlistcontainer, playlist._sp_playlist)
        if result == -1:
            raise spotify.Error('Failed clearing unseen tracks')

    def insert(self, index, value):
        # Required by collections.MutableSequence

        self[index:index] = [value]


class PlaylistFolder(collections.namedtuple(
        'PlaylistFolder', ['id', 'name', 'type'])):
    """A playlist folder."""
    pass


@utils.make_enum('SP_PLAYLIST_OFFLINE_STATUS_')
class PlaylistOfflineStatus(utils.IntEnum):
    pass


class PlaylistTrack(object):
    """A playlist track with metadata specific to the playlist.

    Use :attr:`~spotify.Playlist.tracks_with_metadata` to get a list of
    :class:`PlaylistTrack`.
    """

    def __init__(self, sp_playlist, index):
        lib.sp_playlist_add_ref(sp_playlist)
        self._sp_playlist = ffi.gc(sp_playlist, lib.sp_playlist_release)
        self._index = index

    # TODO Add useful __repr__

    @property
    def track(self):
        """The :class:`~spotify.Track`."""
        return spotify.Track(
            sp_track=lib.sp_playlist_track(self._sp_playlist, self._index))

    @property
    def create_time(self):
        """When the track was added to the playlist, as seconds since Unix
        epoch.
        """
        return lib.sp_playlist_track_create_time(
            self._sp_playlist, self._index)

    @property
    def creator(self):
        """The :class:`~spotify.User` that added the track to the playlist."""
        return spotify.User(sp_user=lib.sp_playlist_track_creator(
            self._sp_playlist, self._index))

    def is_seen(self):
        return bool(lib.sp_playlist_track_seen(self._sp_playlist, self._index))

    def set_seen(self, value):
        spotify.Error.maybe_raise(lib.sp_playlist_track_set_seen(
            self._sp_playlist, self._index, int(value)))

    seen = property(is_seen, set_seen)
    """Whether the track is marked as seen or not."""

    @property
    def message(self):
        """A message attached to the track. Typically used in the inbox."""
        message = lib.sp_playlist_track_message(self._sp_playlist, self._index)
        if message == ffi.NULL:
            return None
        return utils.to_unicode(message)


@utils.make_enum('SP_PLAYLIST_TYPE_')
class PlaylistType(utils.IntEnum):
    pass


class PlaylistUnseenTracks(collections.Sequence):
    """A list of unseen tracks in a playlist.

    The list may contain items that are :class:`None`.

    Returned by :meth:`PlaylistContainer.get_unseen_tracks`.
    """

    BATCH_SIZE = 100

    def __init__(self, sp_playlistcontainer, sp_playlist):
        lib.sp_playlistcontainer_add_ref(sp_playlistcontainer)
        self._sp_playlistcontainer = ffi.gc(
            sp_playlistcontainer, lib.sp_playlistcontainer_release)

        lib.sp_playlist_add_ref(sp_playlist)
        self._sp_playlist = ffi.gc(sp_playlist, lib.sp_playlist_release)

        self._num_tracks = 0
        self._sp_tracks_len = 0
        self._get_more_tracks()

    def _get_more_tracks(self):
        self._sp_tracks_len = min(
            self._num_tracks, self._sp_tracks_len + self.BATCH_SIZE)
        self._sp_tracks = ffi.new('sp_track *[]', self._sp_tracks_len)
        self._num_tracks = lib.sp_playlistcontainer_get_unseen_tracks(
            self._sp_playlistcontainer, self._sp_playlist,
            self._sp_tracks, self._sp_tracks_len)

        if self._num_tracks < 0:
            raise spotify.Error('Failed to get unseen tracks for playlist')

    def __len__(self):
        return self._num_tracks

    def __getitem__(self, key):
        if isinstance(key, slice):
            return list(self).__getitem__(key)
        if not isinstance(key, int):
            raise TypeError(
                'list indices must be int or slice, not %s' %
                key.__class__.__name__)
        if not 0 <= key < self.__len__():
            raise IndexError('list index out of range')
        while key >= self._sp_tracks_len:
            self._get_more_tracks()
        sp_track = self._sp_tracks[key]
        if sp_track == ffi.NULL:
            return None
        return spotify.Track(sp_track=sp_track, add_ref=True)

    def __repr__(self):
        return pprint.pformat(list(self))
