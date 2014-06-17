from urlparse import urlparse

class HeaderHandler(object):
	
	def __init__(self, headerstring):
		self.header = headerstring
		print('aduh:\n%s'%self.header)
		self.header_table = dict()
		headerList = self.header.split('\r\n')
		for i in range(len(headerList)):
			#print(headerList[i])
			if (i==0):
				self.header_table['HTTP'] = headerList[i]
				status = headerList[i].split(' ')
				if ('HTTP' in headerList[i] and len(status)>=3):
					self.header_table['HTTP_STATUS'] = int(status[1])
					self.header_table['HTTP_REASON'] = status[2]
				else: 
					print("INVALID HTTP HEADER")


			elif (':' in headerList[i]):
				field = (headerList[i])[:headerList[i].find(':')]
				content = (headerList[i])[headerList[i].find(':')+1:]
				if (content[0]==' '): content=content[1:]
				self.header_table[field] = content
				# header_row = headerList[i].split(':')
				# value = ''.join(header_row[1:])[0:]
				# if (value[0]==' '): value = value[1:]
				# self.header_table[header_row[0]] = value
	def __str__(self):
		header=str()
		for key in self.header_table.keys(): header+= '%s: %s\n'%(key, self.header_table[key])
		return header
	def __contains__(self, elm):
		return elm in self.header_table

	def get_info(self, key): 
		if (key in self.header_table): return self.header_table[key]
		else: return None
	def is_statusOK(self):
		if ('HTTP_STATUS' in self.header_table):
			return ((self.header_table['HTTP_STATUS'] >= 200 and self.header_table['HTTP_STATUS']< 300))
		return False
	def is_redirected(self):
		if (not self.is_statusOK()):
			if ('Location' in self.header_table and (self.get_info('HTTP_STATUS')>=300 and self.get_info('HTTP_STATUS')<400)): return True
		return False
	def form_httprequest(self, host, path='/', track=0, port=None):
		if (port == None): port = ''
		else: port = ":%s"%(str(port))
		request = 'GET %s HTTP/1.1\r\nHost: %s%s'%(path, host, port)
		request += '\r\nConnection: keep-alive'
		request += '\r\nRange: bytes=%i-'%(track)
		if ('Content-Type' in self.header_table): request += ('\r\nAccept: %s'%(self.header_table['Content-Type']))
		
		return (request + HeaderHandler.get_headerpad())


	@staticmethod
	def create_httprequest(host, path='/', track_from=0, track_to=None):
		if track_to==None: track_to=''
	 	else: track_to = str(track_to)
		request='GET %s HTTP/1.1\r\nHost: %s\r\nAccept: */*\r\nConnection: keep-alive\r\nContent-Length: 0'%(path, host)
		request += '\r\nRange: bytes=%i-%s'%(track_from, track_to)
		return request + '\r\n\r\n'
	@staticmethod
	def create_headerrequest(host, path='/', port=None):
		if (port == None): port = ''
		else: port = ":%s"%(str(port))
		return 'HEAD %s HTTP/1.1\r\nHost: %s%s\r\n\r\n'%(path, host, port)
	@staticmethod
	def get_headerpad(): return '\r\n\r\n'





