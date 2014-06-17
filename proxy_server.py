import os
import socket
from HeaderHandler import HeaderHandler
from datetime import datetime

class ProxyServer(object):
	def __init__(self):
		self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.serverPort = 8080
		self.connection.bind(('', self.serverPort))
		self.address = self.connection.getsockname()
		self.connection.listen(1)
		print("Proxy Server started...")

	def serve(self):
		client_count = 0
		while True:
			try:
				print("Waiting for client's response..")
				connSocket, addr = self.connection.accept()
				print("coming from %s with socket%s"%(addr, connSocket))
				header_data = ''
				while(True):
					data = connSocket.recv(1)
					if (len(data)>0):
						header_data+=data
					if (HeaderHandler.get_headerpad() in header_data):
						break
				
				print("Header:\n%s"%header_data)	
				print("\n[Client: %i] - %s\n"%(client_count, datetime.now()))
				client_count+=1
				client = ClientHandler(self.connection, connSocket, addr)
				client.request(header_data)
				
			except (KeyboardInterrupt):
				print("Interuppted")
				self.connection.close()


class ClientHandler(object):
	def __init__(self, serverSock, connSock, addr):
		self.serverSock = serverSock
		self.clientSock = connSock
		self.clientAddr = addr
		self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def get_header(self, headerstring):
		self.connection.send(headerstring)
		header_string = str()
		while True:
			data = self.connection.recv(1)
			if (len(data)>0):
				header_string+=data
				if (HeaderHandler.get_headerpad() in header_string):
					print("Received Header")
					return HeaderHandler(header_string)

	def request(self, headerstring):
		#print(socket.gethostbyname('www.w3.org'))
		self.connection.connect(('www.w3.org', 80))
		print("Connected to host.")
		# headerHandler = self.get_header(headerstring)
		#print(headerHandler)
		# requestString = headerHandler.form_httprequest('www.w3.og', path='http://www.w3.org/')
		#print('Requesting: \n%s'%headerstring)
		self.connection.settimeout(1)
		self.connection.send(headerstring)
		dataLength = 0
		while(True):
			try:
				recvData = self.connection.recv(1024)
				#print(recvData)
				dataLength+=len(recvData)
				if (len(recvData)>0):
					self.clientSock.send(recvData)
				# if ('Content-Length' in headerHandler):
				# 	if (dataLength>=int(headerHandler.get_info('Content-Length'))):
				# 		print("Process Finished.")
				# 		break
			except(socket.timeout, KeyboardInterrupt):
				print("ERROR: Client closed")
				self.connection.close()
				break
				raise



if __name__ == '__main__':
	server = ProxyServer()
	server.serve()



