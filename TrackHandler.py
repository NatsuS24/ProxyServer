import os
import subprocess

class TrackHandler(object):
	'''
		Handles file writing in the format of <column1>\t<column2>\t<column3>
	'''
	def __init__(self, track_path):
		if (not os.path.exists(track_path)): 
			#print("path dun exists, will create %s"%(track_path))
			fi = open(track_path, 'w')
			fi.close()
		self._track_path = track_path
		tracklist = open(track_path, 'r')
		self.track_rows = [self._split_trackstring(row) for row in tracklist]
		tracklist.close()
		#print(self.toString())

	def toString(self): 
		trackrows = 'Track:%s\n'%self._track_path
		for row in self.track_rows: 
			trackrows += "%s\t%s\t%s\n"%(row[0], row[1], row[2])
		return trackrows

	def __str__(self): return self.toString()

	def remove(self): os.remove(self._track_path)
	def get_trackpath(self): return self._track_path
	def get_trackrows(self): return track_rows
	def get_trackrowforfileurl(self, filename, url):
		for line in self.track_rows: 
			if line[1]==url and line[0]==filename: return line
		return None

	def get_trackvalueforfileurl(self, filename, url):
		line = self.get_trackrowforfileurl(filename, url)
		if (line!=None): return int(line[2])
		else: return None

	def write(self, filename, url, track_val):
		## if same file name dif url, replace 
		## same name n same url -> update track value
		self._update_trackrows(filename, url, track_val)
		#print("write operation: \n%s"%(self.toString()))
		tracker = open(self._track_path, 'w')
		tracker.close()
		tracker = open(self._track_path, 'a')
		for row in self.track_rows:
			tracker.write(self._create_trackstring(row[0], row[1], row[2]))
		tracker.close()

	def erase(self, filename, url):
		self.track_rows = [row for row in self.track_rows if (not(row[0]==filename and row[1]==url))]
		#print(self.track_rows)
		tracker = open(self._track_path, 'w')
		tracker.close()
		tracker = open(self._track_path, 'a')
		for row in self.track_rows:
			tracker.write(self._create_trackstring(row[0], row[1], row[2]))
		tracker.close()

	def append(self, filename, url, track_val):
		tracker = open(self._track_path, 'a')
		entry = self._create_trackstring(filename, url, track_val)
		tracker.write(entry)
		self.track_rows.append(entry)
		tracker.close()

	def hastrack(self, filename, url):
		trackpath = self.get_trackrowforfileurl(filename, url)
		if (trackpath != None): return True
		return False


	def _update_trackrows(self, filename, url, track_val):
		temp_list = []
		isReplaced=False
		for line in self.track_rows:
			if (line!=None):
				_filename, _url, _val = line[0], line[1], line[2]
				if (_filename==filename and _url==url and _val != track_val): 
					#case 1 - old entry for same name and url but different tracking value
					temp_list.append(self._create_trackstring(filename, url, track_val))
					isReplaced = True
				elif (_filename == filename and _url!=url):
					temp_list.append(self._create_trackstring(filename, url, track_val))
					isReplaced = True
				else: #case 3 - old entries for different name and url
					temp_list.append(self._create_trackstring(_filename, _url, _val))
		if (not isReplaced): temp_list.append(self._create_trackstring(filename, url, track_val)) #replacement not found ==> new entry 
		self.track_rows = [self._split_trackstring(rawline) for rawline in temp_list]

	def _create_trackstring(self, name, url, val):  return "%s\t%s\t%s\t\n"%(name, url, str(val))
	def _split_trackstring(self, trackstring): 
		_trackstring = trackstring.split('\t')
		if (len(trackstring)>3): return (_trackstring[0], _trackstring[1], _trackstring[2])
		else: return None

if (__name__ == '__main__'):
	''' case 1
	hello	world	5	
	hello1	world1	5	--> hello world1 6
	'''
	t = TrackHandler('/Users/Shared/rget_natcha/aduh.txt')
	#t.write('hello', 'world2', 7)
	#assert (t.hastrack('hello2', 'world1'))
	# t.append('hello', 'world', 10)
	# t.append('hello1', 'world', 10)
	# t.append('hello3', 'world2', 10)
	print(str(t.hastrack('hello1', 'world')))
	print(str(t.get_trackrowforfileurl('hello1', 'world')))
	t.erase('hello4', 'world1')
