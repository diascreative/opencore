# todo: copy the general guts of openhcd.view.people to here to have that view call into this for most of its logic.

PROFILE_THUMB_SIZE = (75, 100)

_MIN_PW_LENGTH = None

def min_pw_length():
    global _MIN_PW_LENGTH
    if _MIN_PW_LENGTH is None:
        _MIN_PW_LENGTH = get_setting(None, 'min_pw_length', 8)
    return _MIN_PW_LENGTH