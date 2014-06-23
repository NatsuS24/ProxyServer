import asyncore
import logging
import os
import socket
from requesthandler import HeaderHandler
import requesthandler
from datetime import datetime
import time
import random
from chunkbuffer import ChunkBuffer
from cache import Caching

total_cache_size = 100000
cache_threshold = 2**20

class ProxyServer(asyncore.dispatcher):
	def __init__(self):
		self.serverPort = 8080
		self.logger = logging.getLogger('[Proxy]')
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.bind(('', self.serverPort))
		self.address = self.socket.getsockname()
		self.logger.debug('binding to %s'%(str(self.address)))
		self.listen(1)
		global total_cache_size
		self.cacheTable = Caching(total_cache_size)

	def handle_accept(self):
		connSock, addr = self.accept()
		self.logger.debug('accepting -> %s'%str(addr))
		ClientHandler(connSock, addr, self.cacheTable) ## per user request

	def handle_close(self):
		self.logger.debug("closed")
		self.close()
		time.sleep(2)

class ClientHandler(asyncore.dispatcher):
	''' 
	'''
	def __init__(self, connSock, addr, cacheTable):
		self.cacheTable = cacheTable
		self.connSock= connSock
		self.address = addr
		self.logger = logging.getLogger('[Client-%s'%str(addr))
		asyncore.dispatcher.__init__(self, sock=connSock)
		self.logger.debug("Connected")
		

	def handle_read(self):
		try:
			self.logger.debug("client writing to socket")
			data=''
			data += self.recv(2048)
			(ip, port) = self.address
			if (len(data)>0):
				self.logger.debug(' REQUEST @ %s(%s):\n%s'%(str(ip),str(port),str(data)))
				RequestAnalysisHandler(self.connSock, self.address, self.cacheTable, data) #per http request browser made
		except:
			pass
	def handle_close(self):
		self.logger.debug("closed")
		self.close()
		time.sleep(2)

class RequestAnalysisHandler(asyncore.dispatcher):
	''' anaylze header for each request before actual request'''
	def __init__(self, clientSock, clientAddr, cacheTable, headerstring):
		## buffering
		self.cacheTable = cacheTable
		self.currentChunkIndex = 0
		self.totalContentLength=0
		self.isDownloading = False
		self.clientSock = clientSock
		self.requeststring= headerstring
		self.clientAddr = clientAddr
		self.chunkTable = list()
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
		if (not self.isDownloading):
			## sending header + deciding
			self.logger.debug("Host sending header data")
			header_string = self.recv(4096)
			self.logger.debug('%s -> (%i)'%(header_string,len(header_string)))
			if (len(header_string)>0 and HeaderHandler.get_headerpad() in header_string):
				headerHandler = HeaderHandler(header_string)
				self.logger.debug("Header:\n%s"%str(headerHandler))
				if ('Content-Length' in headerHandler):
					contentLength = int(headerHandler.get_info('Content-Length'))
					self.totalContentLength = contentLength
					global cache_threshold
					if (contentLength>int(cache_threshold)):
						self.perform_accelerated_request(contentLength)
					else: 
						### Perform cache download
						self.perform_cache_request(headerHandler)
				else:
					self.perform_request()
			else:
				self.logger.debug("No header returned.")
				#self.perform_request()
				#time.sleep(1)
				self.close()
		
	def streamChunk(self):
		''' stream all chunks to user once workers have finished downloading. Called by worker. '''
		isDone = True
		self.logger.debug("streaming..")
		for chunkBuf in self.chunkTable:
			if (not chunkBuf.isDoneBuffering()): 
				isDone = False
		if isDone:
			for chunkBuf in self.chunkTable:
				bufString = chunkBuf.getBuffer()

				##self.logger.debug("\n===============================\n%r\n"%str(bufString))
				time.sleep(0.1)
				#self.clientSock.send(bufString)
				lengthSent = len(bufString)
				while(lengthSent>0):
					lengthSent = self.clientSock.send(bufString)
					bufString = bufString[lengthSent:]
			del self.chunkTable
			##self.handle_close()

	def streamWithBuffering(self):
		pass

	def perform_accelerated_request(self, contentLength):
		self.isDownloading=True
		self.logger.debug("Initiating accerleration mode")
		self.isDownloading = True
		div = 10
		del_length = int(contentLength/div)
		cur_length = 0
		chunkIndex = 0
		while(cur_length<=contentLength):
			rangeLength = (cur_length, cur_length+del_length)
			self.logger.debug(rangeLength)
			self.chunkTable.append(ChunkBuffer()) ## each chunktable has chunkbuffer
			chunkTuple = (self.chunkTable, chunkIndex)
			self.logger.debug('---->> (%s, %s)'%(cur_length, contentLength))
			if (contentLength-cur_length< del_length):
				RequestAcceleratedHandler(self.clientSock, self.clientAddr, self.requeststring, rangeLength, chunkTuple, self, isLastTime=True)
				break
			elif (cur_length==0):
				RequestAcceleratedHandler(self.clientSock, self.clientAddr, self.requeststring, rangeLength, chunkTuple, self, isFirstTime=True)
			else:
				RequestAcceleratedHandler(self.clientSock, self.clientAddr, self.requeststring, rangeLength, chunkTuple, self)
			cur_length+=del_length+1
			chunkIndex+=1
			
	def perform_request(self):
		self.logger.debug("Initiating cached mode")
		RequestHandler(self.clientSock, self.clientAddr, self.requeststring)

	def perform_cache_request(self, headerHandler):
		''' Caching here'''
		_ETAG ='ETag' 
		cacheKey = str()
		self.logger.debug("=== %s"%str(headerHandler))
		if (_ETAG in headerHandler):
			cacheKey = headerHandler.get_info(_ETAG)
			self.logger.debug(cacheKey)

		if (cacheKey in self.cacheTable):
			self.logger.debug("Sending from Cache: %s"%(str(cacheKey)))

			data = self.cacheTable.getContent(cacheKey)
			dataLength = len(data)
			while(dataLength>0):
				dataLength = self.clientSock.send(data)
				self.logger.debug(dataLength)
				data = data[dataLength:]
		else:
			totalLength = int(headerHandler.get_info('Content-Length'))
			## downloading with caching
			RequestCacheHandler(self.clientSock, self.clientAddr, self.requeststring, self.cacheTable, cacheKey)

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
			self.clientSock.send(data)
		except(KeyboardInterrupt):
			self.logger.debug("exception caught. Done downloading")
			self.close()

class RequestCacheHandler(asyncore.dispatcher):
	''' Caching Dispatcher here'''
	def __init__(self, clientSock, clientAddr, headerstring, cacheTable, cacheKey):
		self.contentLength = 0
		self.cacheTable= cacheTable
		self.cacheKey = cacheKey
		self.clientSock = clientSock
		self.data=str()
		self.isDoneCaching = False
		self.headerstring = headerstring
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		(ip, port) = clientAddr
		self.logger = logging.getLogger('[RequestCacheHandler-%s]'%(port))
		self.request = requesthandler.RequestHandler(headerstring)
		self.logger.debug("Caching")
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
			self.clientSock.send(data) ##pass to client
			self.data += data
			self.logger.debug(len(self.data))
			self.logger.debug(self.contentLength)
			if (HeaderHandler.get_headerpad() in data): ##HeaderHandeler.get_headerpad()-->\r\n\r\n
				headerstring = data.split(HeaderHandler.get_headerpad())[0]+HeaderHandler.get_headerpad()
				self.logger.debug(headerstring)
				headerHandler = HeaderHandler(headerstring)
				if (headerHandler.get_info('Content-Length')!=None):
					self.contentLength = int(headerHandler.get_info('Content-Length')) + len(headerstring)
				else: 
					global total_cache_size
					self.contentLength = total_cache_size

			if (len(self.data)>= self.contentLength and not(self.isDoneCaching)):
				print("updated")
				self.cacheTable.update(self.cacheKey, self.data)
				self.isDoneCaching = True
				

		except(KeyboardInterrupt):
			self.logger.debug("exception caught. Done downloading")
			self.close()

	# def handle_close(self):
	# 	self.logger.debug("closed")
	# 	#self.close()
	# 	time.sleep(2)

class RequestAcceleratedHandler(asyncore.dispatcher):
	def __init__(self, clientSock, clientAddr, headerstring, chunkrange, chunkTableSet, master, isLastTime=False, isFirstTime=False):
		self.master = master
		(self.chunkTable, self.chunkIndex) = chunkTableSet
		self.isLastTime = isLastTime
		self.isFirstTime = isFirstTime
		self.chunkRange = chunkrange
		self.clientSock = clientSock
		self.headerstring = headerstring
		self.data =''
		self.contentLength=0
		self.curLength=0
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		(ip, port) = clientAddr
		(f, l) = chunkrange
		self.logger = logging.getLogger('[RequestAccelHandler<%i>-%s-range(%s,%s)]'%(int(self.chunkIndex),port, str(f), str(l)))
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
		self.logger.debug('\nAccelerator Request:\n%s'%request.get_request())
		self.send(request.get_request())

	def streamToMaster(self):
		if (self.curLength>=self.contentLength):
			self.logger.debug("Accelerated Worker %i Finished"%(int(self.chunkIndex)))
			chunkBuffer = self.chunkTable[self.chunkIndex] ## accessing buffer collection
			chunkBuffer.finishBuffering()
			self.logger.debug("%i finished buffering."%(int(self.chunkIndex)))
			sz= 0
			for chunk in self.chunkTable:
				sz+=len(chunk)
			print (sz)

			if (sz>=self.master.totalContentLength):
				self.master.streamChunk()

			#self.close()

	def handle_read(self):	
		try:
			#self.logger.debug("reading from socket")
			data = self.recv(4096)
			#self.logger.debug(str(data))

			if (HeaderHandler.get_headerpad() in data):
				## chunked encoding header
				fromRange, toRange = int(self.chunkRange[0]), int(self.chunkRange[1])
				headerAndData = data.split(HeaderHandler.get_headerpad())
				header_string = headerAndData[0]+HeaderHandler.get_headerpad()
				headerObj = HeaderHandler(header_string)
				self.logger.debug("headerPan: \n%s"%str(headerObj))
				#headerObj.update('Transfer-Encoding', 'chunked')
				headerObj.update('HTTP', 'HTTP/1.1 200 OK')
				contentLength = headerObj.get_info('Content-Length')
				if (contentLength==None): contentLength = toRange-fromRange+1 ## important +1, range counts itself on both sides
				else: contentLength = int(contentLength)
				headerObj.remove('Content-Length')
				headerObj.remove('Content-Range')
				self.contentLength = contentLength
				header_string = headerObj.get_request()
				# hexstring = ''#str(hex(contentLength))[2:]
				# _data = hexstring+'\r\n'+headerAndData[1]
				_data = headerAndData[1]
				# add header or nott
				if (self.isFirstTime): data = header_string + _data
				else: data = _data

			self.curLength+=len(data)
			chunkBuffer = self.chunkTable[self.chunkIndex] ## accessing buffer collection
			chunkBuffer.append(data)
			self.streamToMaster()


			''' no longer doing chunk transfer'''
			# if (len(self.data)>=self.contentLength): 
			# 	#if(self.isLastTime): self.data+='\r\n0'
			# 	#self.data+='\r\n'
			# 	self.logger.debug("Host sending data")
			# 	self.logger.debug("size-->%s"%len(self.data))
			# 	self.logger.debug('\n%r\n'%self.data)
			# 	#self.clientSock.send(data)

		except(KeyboardInterrupt, socket.timeout):
			self.logger.debug("exception caught. Done downloading")
			self.close()

	def handle_close(self):
		self.close()
		time.sleep(2)
				

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG,
						format='%(name)s: %(message)s',)
	server = ProxyServer()
	asyncore.loop()
	
	
