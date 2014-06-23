import sys
from datetime import datetime

class Caching:
	#receive etag and content
	#create timestamp
	def __init__(self, maxcachesize):
		self.cachetable = {}
		self.maxsize = maxcachesize

	#create a new cache
	def __str__(self): return str(self.cachetable)
	def __contains__(self, key): return key in self.cachetable
	def update(self, etags, contents):
		print("[Cache Class] update cache")
		if (self.isFull() == True):
			self.delete()

		if (etags in self.cachetable):
			(time, new_contents) = self.cachetable[etags]
			new_contents+= contents
		else:
			new_contents = contents

		self.cachetable[etags] = (datetime.now(),new_contents)

	#delete LRU cache
	def delete(self):
		keyetag = min(self.cachetable, key=self.cachetable.get)
		self.cachetable.pop(keyetag)

	#get content from specific tag
	def getContent(self, etags):
		contents = self.cachetable[etags]
		return contents[1]

	#check cache reach full size or not
	def isFull(self):
		totalsize=0
		for field in self.cachetable:
			totalsize+=len(self.cachetable[field][1])
		if (totalsize>= self.maxsize):
			return True
		else:
			print totalsize
			return False


if (__name__=='__main__'):
	
	cache = Caching(10)
	cache.update('e123', '12345')
	cache.update('e123', '678')
	print(cache)


	# cached_content = cache.getContent('e214354653')
	cache.isFull() #boolean

