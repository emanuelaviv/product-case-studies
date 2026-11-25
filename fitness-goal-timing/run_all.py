"""Rebuild and validate with outbound networking disabled in this process."""

import socket


def blocked(*args, **kwargs):
    raise RuntimeError("Outbound networking is disabled for this offline portfolio build")


socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked

from analysis import run
from render import render
from validate import validate

run()
render()
validate()
print("Offline build completed with outbound network calls blocked.")
