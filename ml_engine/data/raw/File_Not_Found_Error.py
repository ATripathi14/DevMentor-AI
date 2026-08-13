# file_not_found - opening a file path that doesn't exist

file = open("non_existent_file.txt", "r")
print(file.read())
file.close()