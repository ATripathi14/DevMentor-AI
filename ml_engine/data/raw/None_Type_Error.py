# None_type_Error - A NoneType error occurs when code attempts to access an attribute, call a method, or perform an operation on a variable that evaluates to None instead of an active object. (e.g. a function that forgot a return)



def get_user_data(user_id):
    users = {1: {"name": "Alice"}, 2: {"name": "Bob"}}
    if user_id in users:
        user = users[user_id]
        # forgot: return user
        # Forgetting a return isn't itself an error. Python functions default to returning None if there's no explicit return statement.
    # implicitly returns None here

def print_user_name(user_id):
    user = get_user_data(user_id)
    print(user["name"])  # crashes here — user is None
    # the traceback points at the line where it breaks, not the line where it actually went wrong (the missing return). That's exactly the "root cause vs crash site" gap that devmentor AI is trying to fill.

print_user_name(1)