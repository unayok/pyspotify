from __future__ import unicode_literals

import sys

from spotify import ffi, lib


PY2 = sys.version_info[0] == 2

if PY2:  # pragma: no branch
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes


def enum(lib_prefix, enum_prefix=''):
    def wrapper(obj):
        for attr in dir(lib):
            if attr.startswith(lib_prefix):
                name = attr.replace(lib_prefix, enum_prefix)
                setattr(obj, name, getattr(lib, attr))
        return obj
    return wrapper


def get_with_growing_buffer(func, obj):
    actual_length = 10
    buffer_length = actual_length
    while actual_length >= buffer_length:
        buffer_length = actual_length + 1
        buffer_ = ffi.new('char[%d]' % buffer_length)
        actual_length = func(obj, buffer_, buffer_length)
    if actual_length == -1:
        return None
    return to_unicode(buffer_)


def to_bytes(value):
    if isinstance(value, text_type):
        return value.encode('utf-8')
    elif isinstance(value, binary_type):
        return value
    else:
        raise ValueError('Value must be text or bytes')


def to_unicode(value):
    if isinstance(value, ffi.CData):
        return ffi.string(value).decode('utf-8')
    elif isinstance(value, binary_type):
        return value.decode('utf-8')
    elif isinstance(value, text_type):
        return value
    else:
        raise ValueError('Value must be text, bytes, or char[]')


def to_country(code):
    return to_unicode(chr(code >> 8) + chr(code & 0xff))


def to_country_code(country):
    country = to_unicode(country)
    if len(country) != 2:
        raise ValueError('Must be exactly two chars')
    first, second = (ord(char) for char in country)
    if (not (ord('A') <= first <= ord('Z')) or
            not (ord('A') <= second <= ord('Z'))):
        raise ValueError('Chars must be in range A-Z')
    return first << 8 | second
