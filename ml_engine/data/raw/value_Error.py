# value_error — e.g. int("abc"), or unpacking mismatch

def get_age_from_input(age_str):
    age = int(age_str)  # crashes if age_str isn't a valid number
    return age

user_input = "twenty-five"
age = get_age_from_input(user_input)
print("Age:", age)