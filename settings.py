try:
    from settings_local import *
except ImportError:
    raise Exception('Error importing settings_local.py  Did you create it from the template?')


# Provide defaults
MAX_DIMEN         = locals().get('MAX_DIMEN',        4000)
CONVERT_CMD       = locals().get('CONVERT_CMD',      'convert')
STRIP_PREFIX      = locals().get('STRIP_PREFIX',     '')
STR404            = locals().get('STR404',
                                 '<html><head><title>404 - Not Found</title></head><body><h1>404 - Not Found</h1></body></html>')
VERBOSE           = locals().get('VERBOSE',          False)
ENABLE_HASH_PATH  = locals().get('ENABLE_HASH_PATH', False)
HASH_PATH_LENGTH  = locals().get('HASH_PATH_LENGTH', 10)
SECRET_HASH_KEY   = locals().get('SECRET_HASH_KEY',  None)


# Check that hash key is long enough
if ENABLE_HASH_PATH:
    if not isinstance(SECRET_HASH_KEY, basestring) or len(SECRET_HASH_KEY) < 10:
        raise Exception('ENABLE_HASH_PATH is True, so SECRET_HASH_KEY must be ' +
                        'a string of length at least 10 but it is %s' % repr(SECRET_HASH_KEY))


# Ensure that STRIP_PREFIX begins with a /
if STRIP_PREFIX[0:1] != '/':
    STRIP_PREFIX = '/' + STRIP_PREFIX
