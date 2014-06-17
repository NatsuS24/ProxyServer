from scoket import socket

class StubClient(object):
	def __init__(self):
		self.conn = socket(socket.AF_INET, sock.SOCK_STREAM)
		