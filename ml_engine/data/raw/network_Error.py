# Network Error — failed requests.get() call (timeout, connection refused, bad URL)


import requests

# Triggers a real network error (DNS Lookup Failure)
# Fails immediately with a refused connection
requests.get("http://127.0.0.1:1")