try:
    from settings_local import *
except ImportError:
    raise Exception('Error importing settings_local.py  Did you create it from the template?')


# Provide defaults
MAX_DIMEN    = locals().get('MAX_DIMEN', 4000)
CONVERT_CMD  = locals().get('CONVERT_CMD', 'convert')
STRIP_PREFIX = locals().get('STRIP_PREFIX', '')
STR404       = locals().get('STR404',
                            '<html><head><title>404 - Not Found</title></head><body><h1>404 - Not Found</h1></body></html>')


if STRIP_PREFIX[0:1] != '/':
    STRIP_PREFIX = '/' + STRIP_PREFIX
