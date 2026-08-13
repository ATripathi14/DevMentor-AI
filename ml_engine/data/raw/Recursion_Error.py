# Recursion error - function calls itself with no condition prersent - infinite recursion happens and code fails when python reaches its maximum recursion depth
def blow_stack():
    return blow_stack()

blow_stack()