# encoding: utf-8

from __future__ import unicode_literals

import gc
import mock
import tempfile
import unittest

import spotify


class SessionCallbacksTest(unittest.TestCase):
    def setUp(self):
        self.callbacks = spotify.SessionCallbacks()
        self.sp_session = spotify.ffi.NULL
        spotify.session_instance = mock.sentinel.session
        self.sp_error = 1

    def tearDown(self):
        spotify.session_instance = None

    def test_no_callbacks_if_session_instance_is_none(self):
        spotify.session_instance = None
        self.callbacks.logged_in = mock.Mock()

        self.callbacks._logged_in(self.sp_session, self.sp_error)

        self.assertEqual(self.callbacks.logged_in.call_count, 0)

    def test_logged_in_callback(self):
        self.callbacks.logged_in = mock.Mock()

        self.callbacks._logged_in(self.sp_session, self.sp_error)

        self.callbacks.logged_in.assert_called_once_with(
            spotify.session_instance, spotify.Error(self.sp_error))

    def test_logged_in_without_session(self):
        spotify.session_instance = None
        self.callbacks.logged_in = mock.Mock()

        self.callbacks._logged_in(self.sp_session, self.sp_error)

        self.assertEqual(self.callbacks.logged_in.call_count, 0)

    def test_logged_out_callback(self):
        self.callbacks.logged_out = mock.Mock()

        self.callbacks._logged_out(self.sp_session)

        self.callbacks.logged_out.assert_called_once_with(
            spotify.session_instance)

    def test_logged_out_without_session(self):
        spotify.session_instance = None
        self.callbacks.logged_out = mock.Mock()

        self.callbacks._logged_out(self.sp_session)

        self.assertEqual(self.callbacks.logged_out.call_count, 0)

    def test_metadata_updated_callback(self):
        self.callbacks.metadata_updated = mock.Mock()

        self.callbacks._metadata_updated(self.sp_session)

        self.callbacks.metadata_updated.assert_called_once_with(
            spotify.session_instance)

    def test_metadata_updated_without_session(self):
        spotify.session_instance = None
        self.callbacks.metadata_updated = mock.Mock()

        self.callbacks._metadata_updated(self.sp_session)

        self.assertEqual(self.callbacks.metadata_updated.call_count, 0)

    def test_connection_error_callback(self):
        self.callbacks.connection_error = mock.Mock()

        self.callbacks._connection_error(self.sp_session, self.sp_error)

        self.callbacks.connection_error.assert_called_once_with(
            spotify.session_instance, spotify.Error(self.sp_error))

    def test_connection_error_without_session(self):
        spotify.session_instance = None
        self.callbacks.connection_error = mock.Mock()

        self.callbacks._connection_error(self.sp_session, self.sp_error)

        self.assertEqual(self.callbacks.connection_error.call_count, 0)

    def test_message_to_user_callback(self):
        self.callbacks.message_to_user = mock.Mock()
        data = spotify.ffi.new('char[]', b'a log message\n')

        self.callbacks._message_to_user(self.sp_session, data)

        self.callbacks.message_to_user.assert_called_once_with(
            spotify.session_instance, u'a log message')

    def test_message_to_user_without_session(self):
        spotify.session_instance = None
        self.callbacks.message_to_user = mock.Mock()
        data = spotify.ffi.new('char[]', b'a log message\n')

        self.callbacks._message_to_user(self.sp_session, data)

        self.assertEqual(self.callbacks.message_to_user.call_count, 0)

    def test_notify_main_thread_callback(self):
        self.callbacks.notify_main_thread = mock.Mock()

        self.callbacks._notify_main_thread(self.sp_session)

        self.callbacks.notify_main_thread.assert_called_once_with(
            spotify.session_instance)

    def test_notify_main_thread_without_session(self):
        spotify.session_instance = None
        self.callbacks.notify_main_thread = mock.Mock()

        self.callbacks._notify_main_thread(self.sp_session)

        self.assertEqual(self.callbacks.notify_main_thread.call_count, 0)

    def test_music_delivery_callback(self):
        sp_audioformat = spotify.ffi.new('sp_audioformat *')
        sp_audioformat.channels = 2
        audio_format = spotify.AudioFormat(sp_audioformat)

        num_frames = 10
        frames_size = audio_format.frame_size() * num_frames
        frames = spotify.ffi.new('char[]', frames_size)
        frames[0:3] = [b'a', b'b', b'c']
        frames_void_ptr = spotify.ffi.cast('void *', frames)

        self.callbacks.music_delivery = mock.Mock()
        self.callbacks.music_delivery.return_value = num_frames

        result = self.callbacks._music_delivery(
            self.sp_session, sp_audioformat, frames_void_ptr, num_frames)

        self.callbacks.music_delivery.assert_called_once_with(
            spotify.session_instance, mock.ANY, mock.ANY, num_frames)
        self.assertEqual(
            self.callbacks.music_delivery.call_args[0][1].sp_audioformat,
            sp_audioformat)
        self.assertEqual(
            self.callbacks.music_delivery.call_args[0][2][:5], b'abc\x00\x00')
        self.assertEqual(result, num_frames)

    def test_music_delivery_without_session(self):
        spotify.session_instance = None
        self.callbacks.music_delivery = mock.Mock()

        sp_audioformat = spotify.ffi.new('sp_audioformat *')
        num_frames = 10
        frames = spotify.ffi.new('char[]', 0)
        frames_void_ptr = spotify.ffi.cast('void *', frames)

        self.callbacks._music_delivery(
            self.sp_session, sp_audioformat, frames_void_ptr, num_frames)

        self.assertEqual(self.callbacks.music_delivery.call_count, 0)

    def test_music_delivery_without_callback_does_not_consume(self):
        self.callbacks.music_delivery = None

        sp_audioformat = spotify.ffi.new('sp_audioformat *')
        num_frames = 10
        frames = spotify.ffi.new('char[]', 0)
        frames_void_ptr = spotify.ffi.cast('void *', frames)

        result = self.callbacks._music_delivery(
            self.sp_session, sp_audioformat, frames_void_ptr, num_frames)

        self.assertEqual(result, 0)

    def test_play_token_lost_callback(self):
        self.callbacks.play_token_lost = mock.Mock()

        self.callbacks._play_token_lost(self.sp_session)

        self.callbacks.play_token_lost.assert_called_once_with(
            spotify.session_instance)

    def test_play_token_lost_without_session(self):
        spotify.session_instance = None
        self.callbacks.play_token_lost = mock.Mock()

        self.callbacks._play_token_lost(self.sp_session)

        self.assertEqual(self.callbacks.play_token_lost.call_count, 0)

    def test_log_message_callback(self):
        self.callbacks.log_message = mock.Mock()
        data = spotify.ffi.new('char[]', b'a log message\n')

        self.callbacks._log_message(self.sp_session, data)

        self.callbacks.log_message.assert_called_once_with(
            spotify.session_instance, u'a log message')

    def test_log_message_without_session(self):
        spotify.session_instance = None
        self.callbacks.log_message = mock.Mock()
        data = spotify.ffi.new('char[]', b'a log message\n')

        self.callbacks._log_message(self.sp_session, data)

        self.assertEqual(self.callbacks.log_message.call_count, 0)

    def test_end_of_track_callback(self):
        self.callbacks.end_of_track = mock.Mock()

        self.callbacks._end_of_track(self.sp_session)

        self.callbacks.end_of_track.assert_called_once_with(
            spotify.session_instance)

    def test_end_of_track_without_session(self):
        spotify.session_instance = None
        self.callbacks.end_of_track = mock.Mock()

        self.callbacks._end_of_track(self.sp_session)

        self.assertEqual(self.callbacks.end_of_track.call_count, 0)

    def test_streaming_error_callback(self):
        self.callbacks.streaming_error = mock.Mock()

        self.callbacks._streaming_error(self.sp_session, self.sp_error)

        self.callbacks.streaming_error.assert_called_once_with(
            spotify.session_instance, spotify.Error(self.sp_error))

    def test_streaming_error_without_session(self):
        spotify.session_instance = None
        self.callbacks.streaming_error = mock.Mock()

        self.callbacks._streaming_error(self.sp_session, self.sp_error)

        self.assertEqual(self.callbacks.streaming_error.call_count, 0)

    def test_user_info_updated_callback(self):
        self.callbacks.user_info_updated = mock.Mock()

        self.callbacks._user_info_updated(self.sp_session)

        self.callbacks.user_info_updated.assert_called_once_with(
            spotify.session_instance)

    def test_user_info_updated_without_session(self):
        spotify.session_instance = None
        self.callbacks.user_info_updated = mock.Mock()

        self.callbacks._user_info_updated(self.sp_session)

        self.assertEqual(self.callbacks.user_info_updated.call_count, 0)

    def test_start_playback_callback(self):
        self.callbacks.start_playback = mock.Mock()

        self.callbacks._start_playback(self.sp_session)

        self.callbacks.start_playback.assert_called_once_with(
            spotify.session_instance)

    def test_start_playback_without_session(self):
        spotify.session_instance = None
        self.callbacks.start_playback = mock.Mock()

        self.callbacks._start_playback(self.sp_session)

        self.assertEqual(self.callbacks.start_playback.call_count, 0)

    def test_offline_status_updated_callback(self):
        self.callbacks.offline_status_updated = mock.Mock()

        self.callbacks._offline_status_updated(self.sp_session)

        self.callbacks.offline_status_updated.assert_called_once_with(
            spotify.session_instance)

    def test_offline_status_updated_without_session(self):
        spotify.session_instance = None
        self.callbacks.offline_status_updated = mock.Mock()

        self.callbacks._offline_status_updated(self.sp_session)

        self.assertEqual(self.callbacks.offline_status_updated.call_count, 0)

    def test_credentials_blob_updated_callback(self):
        self.callbacks.credentials_blob_updated = mock.Mock()
        data = spotify.ffi.new('char[]', b'a credentials blob')

        self.callbacks._credentials_blob_updated(self.sp_session, data)

        self.callbacks.credentials_blob_updated.assert_called_once_with(
            spotify.session_instance, b'a credentials blob')

    def test_credentials_blob_updated_without_session(self):
        spotify.session_instance = None
        self.callbacks.credentials_blob_updated = mock.Mock()
        data = spotify.ffi.new('char[]', b'a credentials blob')

        self.callbacks._credentials_blob_updated(self.sp_session, data)

        self.assertEqual(self.callbacks.credentials_blob_updated.call_count, 0)

    def test_connection_state_updated_callback(self):
        self.callbacks.connection_state_updated = mock.Mock()

        self.callbacks._connection_state_updated(self.sp_session)

        self.callbacks.connection_state_updated.assert_called_once_with(
            spotify.session_instance)

    def test_connection_state_updated_without_session(self):
        spotify.session_instance = None
        self.callbacks.connection_state_updated = mock.Mock()

        self.callbacks._connection_state_updated(self.sp_session)

        self.assertEqual(self.callbacks.connection_state_updated.call_count, 0)

    def test_scrobble_error_callback(self):
        self.callbacks.scrobble_error = mock.Mock()

        self.callbacks._scrobble_error(self.sp_session, self.sp_error)

        self.callbacks.scrobble_error.assert_called_once_with(
            spotify.session_instance, spotify.Error(self.sp_error))

    def test_scrobble_error_without_session(self):
        spotify.session_instance = None
        self.callbacks.scrobble_error = mock.Mock()

        self.callbacks._scrobble_error(self.sp_session, self.sp_error)

        self.assertEqual(self.callbacks.scrobble_error.call_count, 0)

    def test_private_session_mode_changed_callback(self):
        self.callbacks.private_session_mode_changed = mock.Mock()

        self.callbacks._private_session_mode_changed(
            self.sp_session, 1)

        self.callbacks.private_session_mode_changed.assert_called_once_with(
            spotify.session_instance, True)

    def test_private_session_mode_changed_without_session(self):
        spotify.session_instance = None
        self.callbacks.private_session_mode_changed = mock.Mock()

        self.callbacks._private_session_mode_changed(
            self.sp_session, 1)

        self.assertEqual(
            self.callbacks.private_session_mode_changed.call_count, 0)


class SessionConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = spotify.SessionConfig()

    def test_api_version_defaults_to_current_lib_version(self):
        self.assertEqual(
            self.config.api_version, spotify.lib.SPOTIFY_API_VERSION)

    def test_cache_location_defaults_to_tmp_in_cwd(self):
        self.assertEqual(self.config.cache_location, b'tmp')

    def test_settings_location_defaults_to_tmp_in_cwd(self):
        self.assertEqual(self.config.settings_location, b'tmp')

    def test_application_key_is_unknown(self):
        self.assertIsNone(self.config.application_key)

    def test_application_key_filename_defaults_to_a_file_in_cwd(self):
        self.assertEqual(
            self.config.application_key_filename, b'spotify_appkey.key')

    def test_user_agent_defaults_to_pyspotify(self):
        self.assertEqual(self.config.user_agent, 'pyspotify')

    def test_callbacks_defaults_to_none(self):
        self.assertIsNone(self.config.callbacks)

    def test_compress_playlists_defaults_to_false(self):
        self.assertFalse(self.config.compress_playlists)

    def test_dont_save_metadata_for_playlists_defaults_to_false(self):
        self.assertFalse(self.config.dont_save_metadata_for_playlists)

    def test_initially_unload_playlists_defaults_to_false(self):
        self.assertFalse(self.config.initially_unload_playlists)

    def test_device_id_defaults_to_none(self):
        self.assertIsNone(self.config.device_id)

    def test_proxy_defaults_to_none(self):
        self.assertIsNone(self.config.proxy)

    def test_proxy_username_defaults_to_none(self):
        self.assertIsNone(self.config.proxy_username)

    def test_proxy_password_defaults_to_none(self):
        self.assertIsNone(self.config.proxy_password)

    def test_ca_certs_filename_defaults_none(self):
        self.assertIsNone(self.config.ca_certs_filename)

    def test_tracefile_defaults_to_none(self):
        self.assertIsNone(self.config.tracefile)

    def test_get_application_key_prefers_the_key_attr(self):
        self.config.application_key = b'secret key from attr'

        self.assertEqual(
            self.config.get_application_key(), b'secret key from attr')

    def test_get_application_key_can_load_key_from_file(self):
        self.config.application_key = None
        self.config.application_key_filename = tempfile.mkstemp()[1]

        with open(self.config.application_key_filename, 'wb') as f:
            f.write(b'secret key from file')

        self.assertEqual(
            self.config.get_application_key(), b'secret key from file')

    def test_get_application_key_fails_if_no_key_found(self):
        self.config.application_key_filename = '/nonexistant'

        self.assertRaises(EnvironmentError, self.config.get_application_key)

    def test_get_callbacks_prefers_the_key_attr(self):
        self.config.callbacks = mock.sentinel.my_callbacks

        self.assertEqual(
            self.config.get_callbacks(), mock.sentinel.my_callbacks)

    @mock.patch(
        'spotify.session.SessionCallbacks', spec=spotify.SessionCallbacks)
    def test_get_callbacks_creates_new_callbacks_object_if_needed(self, mock):
        self.config.callbacks = None

        self.config.get_callbacks()

        mock.assert_called_once_with()

    def test_make_sp_session_config_returns_a_c_object(self):
        self.config.application_key = b''

        self.assertIsInstance(
            self.config.make_sp_session_config(), spotify.ffi.CData)

    def test_application_key_size_is_calculated_correctly(self):
        self.config.application_key = b'123'

        sp_session_config = self.config.make_sp_session_config()

        self.assertEqual(sp_session_config.application_key_size, 3)

    def test_make_sp_session_config_encodes_unicode_as_utf8(self):
        self.config.application_key = b''
        self.config.device_id = 'æ device_id'
        self.config.proxy = 'æ proxy'
        self.config.proxy_username = 'æ proxy_username'
        self.config.proxy_password = 'æ proxy_password'
        self.config.ca_certs_filename = 'æ ca_certs_filename'
        self.config.tracefile = 'æ tracefile'

        sp_session_config = self.config.make_sp_session_config()

        self.assertEqual(
            spotify.ffi.string(sp_session_config.device_id),
            b'\xc3\xa6 device_id')
        self.assertEqual(
            spotify.ffi.string(sp_session_config.proxy),
            b'\xc3\xa6 proxy')
        self.assertEqual(
            spotify.ffi.string(sp_session_config.proxy_username),
            b'\xc3\xa6 proxy_username')
        self.assertEqual(
            spotify.ffi.string(sp_session_config.proxy_password),
            b'\xc3\xa6 proxy_password')
        self.assertEqual(
            spotify.ffi.string(sp_session_config.ca_certs_filename),
            b'\xc3\xa6 ca_certs_filename')
        self.assertEqual(
            spotify.ffi.string(sp_session_config.tracefile),
            b'\xc3\xa6 tracefile')

    def test_weak_key_dict_keeps_struct_parts_alive(self):
        self.config.application_key = b''

        sp_session_config = self.config.make_sp_session_config()

        self.assertIn(sp_session_config, spotify.weak_key_dict)
        self.assertEqual(len(spotify.weak_key_dict[sp_session_config]), 11)


@mock.patch('spotify.session.lib', spec=spotify.lib)
class SessionTest(unittest.TestCase):

    def create_session(self, lib_mock):
        lib_mock.sp_session_create.return_value = spotify.ErrorType.OK
        config = spotify.SessionConfig()
        config.application_key = b'secret'
        return spotify.Session(config=config)

    def tearDown(self):
        spotify.session_instance = None

    def test_raises_error_if_a_session_already_exists(self, lib_mock):
        self.create_session(lib_mock)

        self.assertRaises(RuntimeError, self.create_session, lib_mock)

    @mock.patch('spotify.session.SessionConfig', spec=spotify.SessionConfig)
    def test_creates_config_if_none_provided(self, config_cls_mock, lib_mock):
        lib_mock.sp_session_create.return_value = spotify.ErrorType.OK

        spotify.Session()

        config_cls_mock.assert_called_once_with()
        config_obj_mock = config_cls_mock.return_value
        config_obj_mock.make_sp_session_config.assert_called_once_with()

    def test_adds_callbacks_to_config_if_provided(self, lib_mock):
        lib_mock.sp_session_create.return_value = spotify.ErrorType.OK
        config = spotify.SessionConfig()
        config.application_key = b'secret'
        callbacks = spotify.SessionCallbacks()

        self.assertIsNone(config.callbacks)

        spotify.Session(config=config, callbacks=callbacks)

        self.assertEqual(config.callbacks, callbacks)

    def test_raises_error_if_not_ok(self, lib_mock):
        lib_mock.sp_session_create.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        config = spotify.SessionConfig()
        config.application_key = b'secret'

        self.assertRaises(spotify.Error, spotify.Session, config=config)

    def test_releases_sp_session_when_session_dies(self, lib_mock):
        sp_session = spotify.ffi.NULL

        def func(sp_session_config, sp_session_ptr):
            sp_session_ptr[0] = sp_session
            return spotify.ErrorType.OK

        lib_mock.sp_session_create.side_effect = func
        config = spotify.SessionConfig()
        config.application_key = b'secret'

        session = spotify.Session(config=config)
        session = None  # noqa
        spotify.session_instance = None
        gc.collect()  # Needed for PyPy

        lib_mock.sp_session_release.assert_called_with(sp_session)

    def test_weak_key_dict_keeps_config_alive(self, lib_mock):
        session = self.create_session(lib_mock)

        self.assertIn(session.sp_session, spotify.weak_key_dict)
        self.assertEqual(len(spotify.weak_key_dict[session.sp_session]), 1)

    def test_login_raises_error_if_no_password_and_no_blob(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        self.assertRaises(AttributeError, session.login, 'alice')

    def test_login_with_password(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.login('alice', 'secret')

        lib_mock.sp_session_login.assert_called_once_with(
            session.sp_session, mock.ANY, mock.ANY,
            False, spotify.ffi.NULL)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][1]),
            b'alice')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][2]),
            b'secret')

    def test_login_with_blob(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.login('alice', blob='secret blob')

        lib_mock.sp_session_login.assert_called_once_with(
            session.sp_session, mock.ANY, spotify.ffi.NULL,
            False, mock.ANY)
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][1]),
            b'alice')
        self.assertEqual(
            spotify.ffi.string(lib_mock.sp_session_login.call_args[0][4]),
            b'secret blob')

    def test_login_with_remember_me_flag(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.login('alice', 'secret', remember_me='anything truish')

        lib_mock.sp_session_login.assert_called_once_with(
            session.sp_session, mock.ANY, mock.ANY,
            True, spotify.ffi.NULL)

    def test_login_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_login.return_value = spotify.ErrorType.NO_SUCH_USER
        session = self.create_session(lib_mock)

        self.assertRaises(spotify.Error, session.login, 'alice', 'secret')

    def test_relogin(self, lib_mock):
        lib_mock.sp_session_relogin.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.relogin()

        lib_mock.sp_session_relogin.assert_called_once_with(session.sp_session)

    def test_relogin_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_relogin.return_value = (
            spotify.ErrorType.NO_CREDENTIALS)
        session = self.create_session(lib_mock)

        self.assertRaises(spotify.Error, session.relogin)

    def test_remembered_user_grows_buffer_to_fit_username(self, lib_mock):
        username = 'alice' * 100

        def func(sp_session, buffer_, buffer_size):
            # -1 to keep a char free for \0 terminating the string
            length = min(len(username), buffer_size - 1)
            # Due to Python 3 treating bytes as an array of ints, we have to
            # encode and copy chars one by one.
            for i in range(length):
                buffer_[i] = username[i].encode('utf-8')
            return len(username)

        lib_mock.sp_session_remembered_user.side_effect = func
        session = self.create_session(lib_mock)

        result = session.remembered_user

        lib_mock.sp_session_remembered_user.assert_called_with(
            session.sp_session, mock.ANY, mock.ANY)
        self.assertEqual(result, username)

    def test_remembered_user_is_none_if_not_remembered(self, lib_mock):
        lib_mock.sp_session_remembered_user.return_value = -1
        session = self.create_session(lib_mock)

        result = session.remembered_user

        lib_mock.sp_session_remembered_user.assert_called_with(
            session.sp_session, mock.ANY, mock.ANY)
        self.assertIsNone(result)

    def test_user_name(self, lib_mock):
        lib_mock.sp_session_user_name.return_value = spotify.ffi.new(
            'char[]', b'alice')
        session = self.create_session(lib_mock)

        result = session.user_name

        lib_mock.sp_session_user_name.assert_called_with(session.sp_session)
        self.assertEqual(result, 'alice')

    def test_forget_me(self, lib_mock):
        lib_mock.sp_session_forget_me.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.forget_me()

        lib_mock.sp_session_forget_me.assert_called_with(session.sp_session)

    def test_forget_me_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_forget_me.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = self.create_session(lib_mock)

        self.assertRaises(spotify.Error, session.forget_me)

    @mock.patch('spotify.user.lib', spec=spotify.lib)
    def test_user(self, user_lib_mock, lib_mock):
        lib_mock.sp_session_user.return_value = (
            spotify.ffi.new('sp_user **'))
        session = self.create_session(lib_mock)

        result = session.user

        lib_mock.sp_session_user.assert_called_with(session.sp_session)
        self.assertIsInstance(result, spotify.User)

    def test_user_if_not_logged_in(self, lib_mock):
        lib_mock.sp_session_user.return_value = spotify.ffi.NULL
        session = self.create_session(lib_mock)

        result = session.user

        lib_mock.sp_session_user.assert_called_with(session.sp_session)
        self.assertIsNone(result)

    def test_logout(self, lib_mock):
        lib_mock.sp_session_logout.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.logout()

        lib_mock.sp_session_logout.assert_called_once_with(session.sp_session)

    def test_logout_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_login.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = self.create_session(lib_mock)

        self.assertRaises(spotify.Error, session.logout)

    def test_process_events_returns_ms_to_next_timeout(self, lib_mock):
        def func(sp_session, int_ptr):
            int_ptr[0] = 5500
            return spotify.ErrorType.OK

        lib_mock.sp_session_process_events.side_effect = func

        session = self.create_session(lib_mock)

        timeout = session.process_events()

        self.assertEqual(timeout, 5500)

    def test_process_events_fail_raises_error(self, lib_mock):
        lib_mock.sp_session_process_events.return_value = (
            spotify.ErrorType.BAD_API_VERSION)
        session = self.create_session(lib_mock)

        self.assertRaises(spotify.Error, session.process_events)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_player_load(self, track_lib_mock, lib_mock):
        lib_mock.sp_session_player_load.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)
        sp_track = spotify.ffi.new('int *')
        track = spotify.Track(sp_track)

        session.player_load(track)

        lib_mock.sp_session_player_load.assert_called_once_with(
            session.sp_session, sp_track)

    @mock.patch('spotify.track.lib', spec=spotify.lib)
    def test_player_load_fail_raises_error(self, track_lib_mock, lib_mock):
        lib_mock.sp_session_player_load.return_value = (
            spotify.ErrorType.TRACK_NOT_PLAYABLE)
        session = self.create_session(lib_mock)
        sp_track = spotify.ffi.new('int *')
        track = spotify.Track(sp_track)

        self.assertRaises(spotify.Error, session.player_load, track)

    def test_player_play(self, lib_mock):
        lib_mock.sp_session_player_play.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.player_play(True)

        lib_mock.sp_session_player_play.assert_called_once_with(
            session.sp_session, 1)

    def test_player_play_with_false_to_pause(self, lib_mock):
        lib_mock.sp_session_player_play.return_value = spotify.ErrorType.OK
        session = self.create_session(lib_mock)

        session.player_play(False)

        lib_mock.sp_session_player_play.assert_called_once_with(
            session.sp_session, 0)
