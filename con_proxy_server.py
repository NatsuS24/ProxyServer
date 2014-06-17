import asyncore
import logging
import os
import socket
from HeaderHandler import HeaderHandler
from datetime import datetime


class ProxyServer(asyncore.dispatcher):
	def __init__(self):
		self.serverPort = 8080
		self.logger = logging.getLogger('[Proxy]')
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.bind(('', self.serverPort))
		self.address = self.socket.getsockname()
		self.logger.debug('binding to %s'%(str(self.address)))
		self.listen(1)

	def handle_accept(self):
		connSock, addr = self.accept()
		self.logger.debug('accepting -> %s'%str(addr))
		ClientHandler(connSock, addr) ## per user request

	def handle_close(self):
		self.logger.debug("closed")
		self.close()


class ClientHandler(asyncore.dispatcher):
	''''''
	def __init__(self, connSock, addr):
		self.connSock= connSock
		self.address = addr
		self.logger = logging.getLogger('[Client-%s'%str(addr))
		asyncore.dispatcher.__init__(self, sock=connSock)
		self.logger.debug("Connected")
		

	def handle_read(self):
		self.settimeout(20)
		try:
			self.logger.debug("client writing to socket")
			data=''
			while(not(HeaderHandler.get_headerpad() in data)):
				#self.logger.debug("in loop1")
				data += self.recv(1024)
			(ip, port) = self.address
			self.logger.debug(' REQUEST @ %s(%s):\n%s'%(str(ip),str(port),str(data)))
			if (len(data)>0):
				RequestHandler(self.connSock, self.address, data) #per http request browser made
		except(socket.timeout):
			self.handle_close()


	def handle_close(self):
		self.logger.debug("closed")
		self.close()

class RequestHandler(asyncore.dispatcher):
	def __init__(self, clientSock, clientAddr, headerstring, trial=0):
		self.clientSock = clientSock
		self.headerstring = headerstring
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		(ip, port) = clientAddr
		self.logger = logging.getLogger('[RequestHandler-%s]'%(port))
		try:
			self.connect(('www.w3.org', 80))
		except:
			pass
			# if (trial<10):
			# 	trial+=1
			# 	self.debug("could not connect. Retrying..")
			# 	RequestHandler(clientSock, clientAddr, headerstring, trial)
			# self.logger.debug("connection refused")

	def handle_connect(self):
		self.logger.debug("Connected. Sending request.")
		self.send(self.headerstring)

	def handle_read(self):
		self.logger.debug("Host sending data")
		self.settimeout(2)
		while(True):
			try:
				self.logger.debug("reading from socket")
				data = self.recv(2048)
				#self.logger.debug(str(data))
				self.clientSock.send(data)
			except(KeyboardInterrupt, socket.timeout):
				self.logger.debug("exception caught.")
				self.close()
				break

	def handle_close(self):
		self.logger.debug("closed")
		self.close()
				

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG,
						format='%(name)s: %(message)s',)
	server = ProxyServer()
	asyncore.loop()
