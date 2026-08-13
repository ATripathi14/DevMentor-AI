# this script also serves as a unit test for devmentor AI with respect to Nonetype errors
def find_config(settings, key):
    for k, v in settings.items():
        if k == key:
            match = v
            # forgot: return match
    # falls through, returns None

def load_setting(settings, key):
    result = find_config(settings, key)
    return result.upper()  # AttributeError: 'NoneType' object has no attribute 'upper'

load_setting({"mode": "debug"}, "mode")