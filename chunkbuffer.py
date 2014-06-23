
class ChunkBuffer(object):
	def __init__(self, string=''):
		self.bufferedString= string
		self._isDone = False

	def __str__(self): return self.bufferedString
	def __len__(self): return len(self.bufferedString)
	def isDoneBuffering(self): return self._isDone
	def finishBuffering(self): self._isDone = True
	def recvBuffer(self, index):
		buffered_portion, bufferedString = self.bufferedString[:index], self.bufferedString[index:]
		self.bufferedString = bufferedString
		return buffered_portion

	def getBuffer(self): return self.recvBuffer(len(self.bufferedString))
	def append(self, appendedString):
		self.bufferedString += appendedString



if __name__ == '__main__':
	cb = ChunkBuffer('abcd')
	print('%r'%str(cb))
	print(len(cb))
	# print(cb)
	# print cb.recvBuffer(3)
	# print cb
	# cb.append('efg')
	# print cb
	# print cb.isDoneBuffering()
	# cb.finishBuffering()
	# print cb.isDoneBuffering()
	# print cb.getBuffer()
	# print cb


