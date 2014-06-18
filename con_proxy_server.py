import asyncore
import logging
import os
import socket
from requesthandler import HeaderHandler
import requesthandler
from datetime import datetime
import time

total_cache_size = 1000000
cache_threshold = 100000

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
		time.sleep(2)


class ClientHandler(asyncore.dispatcher):
	''' 
	'''
	def __init__(self, connSock, addr):
		self.connSock= connSock
		self.address = addr
		self.logger = logging.getLogger('[Client-%s'%str(addr))
		asyncore.dispatcher.__init__(self, sock=connSock)
		self.logger.debug("Connected")
		

	def handle_read(self):
		print("--")
		try:
			self.logger.debug("client writing to socket")
			data=''
			data += self.recv(2048)
			(ip, port) = self.address
			if (len(data)>0):
				self.logger.debug(' REQUEST @ %s(%s):\n%s'%(str(ip),str(port),str(data)))
				RequestAnalysisHandler(self.connSock, self.address, data) #per http request browser made
		except:
			pass
	def handle_close(self):
		self.logger.debug("closed")
		self.close()
		time.sleep(2)

class RequestAnalysisHandler(asyncore.dispatcher):
	''' anaylze header for each request before actual request'''
	def __init__(self, clientSock, clientAddr, headerstring):
		print("create new request analys")
		self.clientSock = clientSock
		self.headerstring = headerstring
		self.clientAddr = clientAddr
		(ip, port) = clientAddr
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.logger = logging.getLogger('[RequestAnalysis-%s]'%(str(port)))
		self.request = requesthandler.RequestHandler(headerstring)
		try:
			if ("Host" in self.request):
				host = self.request.get_info("Host")
				self.logger.debug(host)
				self.connect((host, 80))
		except:
			self.close()
	def handle_connect(self):
		self.logger.debug("Sending HEAD request")
		host=self.request.get_info("Host")
		path =self.request.get_info("Path")
		head_request = HeaderHandler.create_headerrequest(host, path=path)
		self.logger.debug(head_request)
		self.send(head_request)

	def handle_read(self):
		self.logger.debug("Host sending header data")
		header_string = self.recv(4096)
		print(header_string,len(header_string))
		if (len(header_string)>0 and HeaderHandler.get_headerpad() in header_string):
			headerHandler = HeaderHandler(header_string)
			self.logger.debug("Header:\n%s"%str(headerHandler))
			if ('Content-Length' in headerHandler):
				contentLength = int(headerHandler.get_info('Content-Length'))
				global cache_threshold
				if (contentLength>int(cache_threshold)):
					self.perform_accelerated_request(contentLength)
				else: self.perform_cached_request()
			else:
				self.perform_cached_request()
		else:
			self.close()
	
	def handle_close(self):
		self.logger.debug("closed.")
		self.close()
		time.sleep(2)

	def perform_accelerated_request(self, contentLength):
		self.logger.debug("Initiating accerleration mode")
		del_length = int(contentLength/9)
		cur_length = 0
		while(cur_length<=contentLength):
			rangeLength = (cur_length, cur_length+del_length-1)
			self.logger.debug(rangeLength)
			if (cur_length+del_length-1>=contentLength):
				RequestAcceleratedHandler(self.clientSock, self.clientAddr, self.headerstring, rangeLength, isLastTime=True)
			elif (cur_length==0):
				RequestAcceleratedHandler(self.clientSock, self.clientAddr, self.headerstring, rangeLength, isFirstTime=True)
			else:
				RequestAcceleratedHandler(self.clientSock, self.clientAddr, self.headerstring, rangeLength)
			cur_length+=del_length
			

	def perform_cached_request(self):
		self.logger.debug("Initiating cached mode")
		RequestHandler(self.clientSock, self.clientAddr, self.headerstring)


class RequestHandler(asyncore.dispatcher):
	def __init__(self, clientSock, clientAddr, headerstring):
		self.clientSock = clientSock
		self.headerstring = headerstring
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		(ip, port) = clientAddr
		self.logger = logging.getLogger('[RequestHandler-%s]'%(port))
		self.request = requesthandler.RequestHandler(headerstring)
		try:
			host = self.request.get_info("Host")
			self.connect((host, 80))
		except:
			self.close()

	def handle_connect(self):
		self.logger.debug("Connected. Sending request.")
		self.send(self.headerstring)

	def handle_read(self):
		self.logger.debug("Host sending data")
		try:
			self.logger.debug("reading from socket")
			data = self.recv(2048)
			#self.logger.debug(str(data))
			self.clientSock.send(data)
		except(KeyboardInterrupt, socket.timeout):
			self.logger.debug("exception caught. Done downloading")
			self.close()

	def handle_close(self):
		self.logger.debug("closed")
		self.close()
		time.sleep(2)

class RequestAcceleratedHandler(asyncore.dispatcher):
	def __init__(self, clientSock, clientAddr, headerstring, chunkrange, isFirstTime=False,isLastTime=False):
		self.isLastTime = isLastTime
		self.isFirstTime = isFirstTime
		self.chunkRange = chunkrange
		self.clientSock = clientSock
		self.headerstring = headerstring
		self.data =''
		self.contentLength=0
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		(ip, port) = clientAddr
		(f, l) = chunkrange
		self.logger = logging.getLogger('[RequestAccelHandler-%s-range(%s,%s)]'%(port, str(f), str(l)))
		self.request = requesthandler.RequestHandler(headerstring)
		try:
			host = self.request.get_info("Host")
			self.connect((host, 80))
		except:
			self.close()

	def handle_connect(self):
		self.logger.debug("Connected. Sending request.")
		request = requesthandler.RequestHandler(self.headerstring)
		fromRange, toRange = int(self.chunkRange[0]), int(self.chunkRange[1])
		request.update('Range', 'bytes=%s-%s'%(str(fromRange), str(toRange)))
		self.logger.debug(request.get_request())
		self.send(request.get_request())

	def handle_read(self):
		try:
			self.logger.debug("reading from socket")
			data = self.recv(4096)
			#self.logger.debug(str(data))

			if (HeaderHandler.get_headerpad() in data):
				## chunked encoding header
				fromRange, toRange = int(self.chunkRange[0]), int(self.chunkRange[1])
				headerAndData = data.split(HeaderHandler.get_headerpad())
				header_string = headerAndData[0]+HeaderHandler.get_headerpad()
				
				self.logger.debug("FContent: %s"%(fromRange))
				headerObj = HeaderHandler(header_string)
				headerObj.update('Transfer-Encoding', 'chunked')
				headerObj.update('HTTP', 'HTTP/1.1 200 OK')
				contentLength = int(headerObj.get_info('Content-Length'))
				headerObj.remove('Content-Length')
				self.contentLength = contentLength
				header_string = headerObj.get_request()
				hexstring = str(hex(contentLength+1))[2:]
				_data = hexstring+'\r\n'+headerAndData[1]
				self.logger.debug("response:\n%s"%header_string)
				if (self.isFirstTime): data = header_string + _data
				else: data = _data
				self.data+=data
			else: self.data+=data
			if (len(self.data)>=self.contentLength): 
				if(self.isLastTime): self.data+='\r\n0'
				self.data+='\r\n'
				self.logger.debug("Host sending data")
				self.logger.debug("size-->%s"%len(self.data))
				self.logger.debug('\n%r\n'%self.data)
				self.clientSock.send(data)
				self.close()

		except(KeyboardInterrupt, socket.timeout):
			self.logger.debug("exception caught. Done downloading")
			self.close()

	def handle_close(self):
		self.logger.debug("closed")
		self.close()
		time.sleep(2)
				

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG,
						format='%(name)s: %(message)s',)
	server = ProxyServer()
	asyncore.loop()
	
	
