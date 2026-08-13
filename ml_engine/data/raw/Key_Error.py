# key_error — accessing a missing dict key, ideally nested keys

dict1 = [
    {"a": 1 , "b": 2}, 
    {"c": 3, "d": 4}
]

# print(dict1[1]["e"]) # KeyError
print(dict1[1]["d"])
# print(dict1[0]["d"]) # KeyError
