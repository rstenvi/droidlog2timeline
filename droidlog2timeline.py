#!/usr/bin/python
# -*- coding: utf-8 -*-

# The MIT License (MIT)

# Copyright (c) 2013 John-André Bjørkhaug, Christoffer Hallstensen,
# Robin Stenvi and Made Ziius

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sqlite3 as sqlite
import sys, time, csv, os, re
import argparse
from datetime import datetime
import math
import shutil	# To copy files
import hashlib, json

try:
	from lxml import etree as ET
except ImportError:
	print "Unable to import lxml, install with easy_install lxml"
	sys.exit(0)


# Global variable that determines if the output is verbose or not
verbose = False
storagePaths = []	# Root storage mount points

# If we can create symlinks or not, only possible on UNIX
createSymlinks = False

# Global status description for error messages
globalStatus = ""

# Root output directory
output = ""

# All opened files that are used when printing logs
fileOpened = {}

# Print error message and exit
def exitError(msg):
	print "ERROR: Message: " + str(msg) + " Status: "
	sys.exit(0)

# Calculate SHA-1 hash value of a file
def sha1OfFile(filepath):
	if verbose:
		print "Calculating hash value of " + filepath
	with open(filepath, 'rb') as f:
		return hashlib.sha1(f.read()).hexdigest()


# Get a dictionary representing the JSON input, keys are defined in keyWrite
def getJsonKeys(keys, keyWrite, Json):
	Dict = json.loads(Json)
	ret = {}
	for key, keyW in zip(keys, keyWrite):
		if key in Dict:
			ret[keyW] = Dict[key]
	return ret


# Read and interpret logs
# The format is something like this:
#  11-21 22:23:05.082 I/force_gc( 2591): bg
#  in main or
#  11-22 17:16:51.136 I/power   (  168): *** set_screen_state 1
#  in the rest
def readLogcat(fname, timezone):
	if verbose:
		print "Reading logs from " + fname

	# Different levels and their shorthand letters
	Levels = {"V" : "Verbose", "D" : "Debug", "I" : "Information", "W" :\
	"Warning", "E" : "Error", "F" : "Fatal", "S" : "Silent"}
	ret = []	# List of dictionaries to return
	with open(fname) as f:
		lines = f.readlines()
	year = datetime.now().year
	for line in lines:
		dateI = line.find(" ")
		date = line[:dateI]	# The date without clock
		line = line[dateI+1:]
		clockI = line.find(" ")
		clock = line[:clockI]	# The clock with milliseconds
		line = line[clockI+1:]

		tmp1 = line.find(" ")
		tmp2 = line.find("(")
		if tmp1 < tmp1:	real = tmp1
		else:					real = tmp2

		info = line[:real]	
		info = info.split("/")
		level = info[0]
		Type = info[1]
		msg = line[real+1:].strip()
		
		timeI = clock.find(".")
		date = time.strptime(str(year)+"-"+date + "T" + clock[:timeI],\
		"%Y-%m-%dT%H:%M:%S")
		realDate = time.strftime("%b %d %Y %H:%M:%S", date)
		realDate += clock[timeI:] + " " + timezone

		if level in Levels:
			level = Levels[level]
		tmpDic = {"date" : realDate, "level" : level, "type" : Type, "msg" : msg}
		ret.append(tmpDic)
	return ret

# Return a dictionary instead of a tuple from sqlite3
# Is only called from SQLite, not directly
def dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d

# Print all links to new javascript file
def printLinks(webapp):
	links = []
	ignore = ["images", "js", "libraries", "css"]
	files = os.listdir(webapp)
	for f in files:
		if (os.path.isdir(os.path.join(webapp, f))) and (f not in ignore):
			links.append(f)
	
	try:
		File = open(os.path.join(webapp, "links.js"), "w")
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
		sys.exit(0)
	
	File.write("var Links = new Array();\n")
	for l in links:
		File.write("Links.push('" + os.path.join(l, "index.html") + "');\n")

# Writes out JavaScript varialbes we have created during the script
def printVariables(fname, images, intervals, timezone=0):
	if verbose:
		print "Writing JavaScript variables"
	try:
		f = open(fname, "w")
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
		sys.exit(0)
	
	f.write("var timeZone=" + str(timezone) + ";\n")
	f.write("var interval1=Timeline.DateTime." + intervals[0] + ";\n")
	f.write("var interval2=Timeline.DateTime." + intervals[1] + ";\n")
	f.write("var interval3=Timeline.DateTime." + intervals[2] + ";\n")
	f.write("var interval4=Timeline.DateTime." + intervals[3] + ";\n")
	f.write("var XMLFile = \"logs.xml\";\n")
	f.write("var Images= new Array();\n")
	f.write("var imageDesc = new Array();\n")

	# All image paths and their description
	printed = []
	for i in images:
		if i not in printed:
			printed.append(i)
			f.write("Images.push('" + i["file"] + "');\n")
			f.write("imageDesc.push('" + i["description"] + "');\n")


# Read in list of packages installed on the phone
# Is compatible with packages.list on the phone, but a simple ls will also give
# the correct results
def readPackagesList(name, pathData):
	ret = []
	if name == None or os.path.isfile(packages) == False:
		if verbose:
			print "Listing contents of " + str(pathData) + " to get programs"
		ret = droidlog.getAllFilesReg(pathData, "[a-z]+.[a-zA-Z0-9\.]+")
	else:
		if verbose:
			print "Reading list of packages from " + name
		with open(name, "r") as csvfile:
			reader = csv.reader(csvfile, delimiter=' ', quotechar='"')
			for row in reader:
				ret.append(row[0])
	return ret

# Checks if a regular expression matches against a file
# firstPath contains everything up to and including com.xxx.yyy
def replaceRegFile(firstPath, name, regStart, regEnd):
	ret = ""
	
	# Generate regular expression
	regExp = name[regStart+2:regEnd]

	# Should always match entire string
	if regExp[len(regExp)-1] != '$':
		regExp += "$"
	dirRe = re.compile(regExp)
	
	findPath = firstPath
	
	# Find out additional path
	extraPathI = name[:regStart].rfind("/")
	if extraPathI != -1:
		findPath = os.path.join(firstPath, name[:extraPathI+1])
	
	# List all the files in this path
	dirFiles = os.listdir(findPath)
	
	# Check if any of those files mathes our query
	results = []
	for l in dirFiles:
		if dirRe.match(l):	results.append(l)
	
	# We only accept it if there is one good match
	if len(results) == 1:
		ret = name[:regStart] + results[0] + name[regEnd+2:]
	return ret


# Finds regular expression in paths and checks to see what to replace it with
def findAndReplaceReg(fullName, pathData, appName):
	# Look for any regular expression in filename
	regFind = fullName.find("{{")
	# As long as there is regular expressions in the filename
	while regFind != -1:
		# If this is inside a double, we can't find the file
		doubleFind = fullName.find("[[")
		if doubleFind != -1 and doubleFind < regFind:
			return fullName
		regEnd = fullName.find("}}")
		tmp = replaceRegFile(os.path.join(pathData, appName), fullName, regFind,\
		regEnd)

		# If it is not empty we found a match
		if tmp != "":
			fullName = tmp
		else:
			# No match is found, will fail later
			break
		# Try to find another regular expression
		regFind = fullName.find("{{")
	return fullName

# Checks if the same script goes for several databases. If it does it adds them
# to our list
def findAndReplaceDouble(pathProgram, fullName, allNames, DB):
	# Check if this consist of duplicate databases
	doubleFind = fullName.find("[[")
	if doubleFind != -1:
		doubleFind2 = fullName.find("]]")
		doubleName = fullName[doubleFind+2:doubleFind2]
		names = doubleName.split(" and ")
		for n in names:
			n = n.strip()
		for n in names:
			# Need to check for regular expressions inside each name
			if n.find("{{") == 0:
				regEnd = n.find("}}")
				n = replaceRegFile(os.path.join(pathProgram, fullName[:doubleFind]), n, 0, regEnd)
				
				if n == "":	# Nothing to find, got to next
					continue
			
			DB1 = {"name" : fullName[:doubleFind] + n}
			allNames.append(DB1["name"])
			DB.append(DB1)
	else:
		allNames.append(fullName)
	return allNames, DB

# Read in configuration XML-file into a list of dictionaries
# Will store any arbitrary attributes, interpreting them is not done here
def readXML(name, imageDesc, pathData, disallowOverride, logPath):
	ret = []
	try:
		f = open(name, "r")
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
		sys.exit(0)
	
	# Find program directory
	nameStart = name.rfind("/")
	nameEnd = name.find(".xml")
	appName = name[nameStart+1:nameEnd]
	
	# Get root of our file
	tree = ET.parse(f)
	root = tree.getroot()

	# For each database
	for dbT in root.iter("database"):
		DB = []	# List of duplicate databases
		allNames = []	# All database names that are duplicates
		fullName = dbT.get("id")	# Path to DB
		
		# Check for regular expressions in DB path
		fullName = findAndReplaceReg(fullName, pathData, appName)

		# Check for duplicate databases
		allNames, DB = findAndReplaceDouble(os.path.join(pathData, appName), fullName, allNames, DB)

		tables = []	# All tables in this database
		for elem in dbT.iter("table"):
			table = {}
			table["name"] = elem.get("id")

			# Set status in case of error
			globalStatus = "Reading XML file: " + name + " DB: " + fullName + " Table: " + table["name"]

			columns = []	# All columns
			inserts = []	# Static text inserted in attribute
			queries = []	# Queries to replace foreign key
			for el in elem.iterchildren():
				if el.tag == "column":
					column = {}

					# Set some default values
					column["name"] = el.text	# Column name in DB
					column["print"] = el.text	# What we should say column is called
					column["default"] = "None"	# When column is empty

					# Various attributes that belong to the column. Some are
					# interpreted here, if they are not mentioned here they are
					# parsed when running the queries against the DB.
					attrs = {}
					for e in el.items():
						# Use self-define header for column value
						if e[0] == "override" and disallowOverride == False:
							column["print"] = e[1]

						# Specify default value to use when not found
						elif e[0] == "default":
							column["default"] = e[1]

						# Several XML files can specify the same logfile, so we store
						# them in a global dictionary and places the link the column
						# attributes
						elif e[0] == "logfile":
							if e[1] not in fileOpened.keys():
								try:
									fileOpened[e[1]] = open(os.path.join(logPath, e[1]), "w")
								except IOError as e:
									print "I/O error({0}): {1}".format(e.errno, e.strerror)
									sys.exit(0)
							attrs["log"] = fileOpened[e[1]]

						# Queries that has to be executes
						elif e[0] == "query":
							vals = e[1].split("|")
							# "key" is default value, is meant to replace foreign key
							if len(vals) <= 1 or vals[0] == "key":
								if len(vals) == 1:
									vals.insert(0, "key")
								queries.append(vals[1])
							elif len(vals) > 2:
								exitError(str(e[1]) + " has too many dividers")
							attrs["query"] = {"type" : vals[0], "query" : vals[1]}
						# Add other stuff we don't need to parse here
						else:
							attrs[e[0]] = e[1]

					column["attrs"] = attrs
					columns.append(column)

				# Can only be 1 icon tag
				elif el.tag == "icon":
					icon = {"file" : "../images/" + el.text, "description" :\
					el.get("desc")}
					table["icon"] = icon
					imageDesc.append(icon)

				# Can only be 1 where tag
				elif el.tag == "where":
					table["where"] = el.text

				elif el.tag == "insert":
					insert = {"name" : el.text, "id" : el.get("id")}
					inserts.append(insert)

				# Can only be one filter tag so we add it directly
				elif el.tag == "filter":
					table["filter"] = {}
					tabID = el.get("columns", None)
					if tabID != None:
						cols = tabID.split(";")
						table["filter"]["columns"] = cols
					table["filter"]["static"] = el.get("static", "")
			if "filter" in table:
				for t in table["filter"].get("columns", []):
					for c in columns:
						if c["name"] == t:
							c["attrs"]["filter"] = True
			table["columns"] = columns
			table["inserts"] = inserts
			table["queries"] = queries
			tables.append(table)

		# Add all duplicate databases to return value
		for name in allNames:
			ret.append({"name" : name, "tables" : tables})
	return ret

# Retrieve the info from the database, runs a simple query and return the result
def getInfoDB(db, columns, table, where=None, Log=None):
	get = "SELECT "
	ret = {}
	gets = []
	for c in columns:
		get += c["name"] + ","
		gets.append(c["name"])
	get = get[:-1]	# Remove last ","
	get += " FROM " + table
	if(where != None):
		get += " WHERE " + where
	return execQuery(db, get, Log)

# Executes any query against a given database
def execQuery(db, query, Log=None):
	retValue = True
	ret = {}
	try:
		cur = db.cursor()
		cur.execute(query)
		ret = cur.fetchall()
		if Log != None:
			Log.append(query)
	except sqlite.Error, e:
		print "WARNING:  %s: Query: " % e.args[0], query
		retValue = False
	return ret, retValue

def findDir(dirs, find):
	for Dir in dirs:
		files = os.listdir(Dir)
		if find in files:
			return Dir
	return None

def createMedia(path, xml):
	error = False
	ret = error
	images = ["jpg", "png", "jpeg"]
	videos = ["mp4", "flv"]
	audios = ["mp3", "ogg", "3gpp"]
	Type = None

	# Should be full path
	if path[0] != "/":
		return error
	else:
		path = path[1:]
	
	# Only matches file ending now, magic numbers would be more accurate
	endingI = path.rfind(".")
	# Return error if there is no ending
	if endingI == -1:
		return error
	ending = path[endingI+1:].lower()
	
	if ending in images:
		Type = "image"
	elif ending in videos:
		Type = "video"
	elif ending in audios:
		Type = "audio"
	else:
		return error	# File type not supported

	# Get the name of the first directory
	firstDirI = path.find("/")
	if firstDirI == -1:
		return error
	firstDir = path[:firstDirI]

	# Find if we have this directory in any of our paths
	prefix = findDir(storagePaths, firstDir)
	if prefix == None:
		return error
	
	# Crate full path to file
	fullPath = os.path.join(prefix, path)

	# Find the name of the file
	mediaNameI = fullPath.rfind("/")
	mediaName = fullPath[mediaNameI+1:]

	# The path for the web server
	mediaPath = os.path.join(output, Type + "s")
	
	# Create directory if it doesn't exist
	if not os.path.exists(mediaPath):
		os.mkdir(mediaPath)

	# Full path to file
	mediaPath = os.path.join(mediaPath, mediaName)

	# Create the file for the web server, use symlink if chosen
	if createSymlinks == True:
		if not os.path.exists(mediaPath):
			os.symlink(fullPath, mediaPath)
	elif not os.path.exists(mediaPath):
		shutil.copy2(fullPath, mediaPath)

	Tag = ""

	if Type == "image":
		Tag = "<img src='" + os.path.join(Type + "s", mediaName) + "' />"
	elif Type == "audio" or Type == "video":
		localPath = os.path.join(Type + "s", mediaName)
		TypeIns = Type + "/" + ending
		Tag = "<" + Type + " controls type='" + TypeIns + "' src='" + localPath +\
		"'>Your browser does not support the " + Type + " tag.</" + Type + ">"
	
	bef = xml.text
	if bef == None:
		bef = ""
	bef +=  Tag.encode('ascii', 'xmlcharrefreplace')
	xml.text = bef
	return True

# Find the value of a query we did earlier
def getQueryCompleted(query, column):
	ret = "Unknown"
	for res in column.get("queryResult", {}).get("result", {}):
		if query.get(column.get("name", ""), "invalid") == \
		res.get(column["queryResult"].get("key", ""), "ivalid2"):
			ret = removeInvalid(res.get(column["queryResult"].get("value", ""), "Unknown"))
			break
	return ret


# Run a new query to replace the appropriate value
def getQueryNew(db, column, insert, dbName):
	# Get the base query
	run = column["attrs"]["query"].get("query", "Missing column")

	# Exit if there is nothing to replace
	if run.find("?") == -1:
		exitError("Invalid query :'" + run + "'")

	# Replace the '?' with the user previous result
	run = run.replace("?", insert)

	# Execute the query
	res, succ = execQuery(db, run)
	if succ == False:
		if db:	db.close()
		exitError("Unable to connect to '" + str(dbName) + "'")

	# Use default value if we can't find a value
	if len(res) == 0:		return column["default"]

	# Might be multiple results, we add all and separate by newline in html
	ret = ""
	for r in res:
		ret += "<br />"
		for k in r.keys():
			ret += "<i>" + k + "</i>: " + removeInvalid(r[k])
	return ret

# Convert JSON to a string based on the columns selected
def getFileTypeJson(column, query, localStorage):
	ret = "Error"
	# Get all different JSON keys that should be selected
	Keys = column["attrs"]["select"].split(";")

	KeyGet = []		# The actual key
	KeyWrite = []	# What we write

	for key in Keys:
		# If new name is specified
		tmp = key.split(" AS ")

		# If new name is not specified, we add one equal to default name
		if len(tmp) == 1:	tmp.append(tmp[0])

		# Ignore empty
		if len(tmp[0]) == 0:	continue

		# Append keys
		KeyGet.append(tmp[0])
		KeyWrite.append(tmp[1])

	# Get a dictionary with our self-defined keys
	Dict = getJsonKeys(KeyGet, KeyWrite, query[column["name"]])

	for key in Dict:
		ret += "<br /><i>" + str(key) + ": </i>" + str(Dict[key])
		if "store" in column["attrs"] and column["attrs"]["store"].lower() != "false":
			localStorage[key] = str(Dict[key])
	return ret, localStorage

# Executes a set of predefined queries to retrieve value for foreign keys
def runSetQueries(table, db, dbName, Queries):
	for q in table["queries"]:
		qq, succ = execQuery(db, q, Queries)
		if succ == False:
			if db:	db.close()
			exitError("Could not connect to DB '" + dbName + "'")

		for c in table["columns"]:
			if "query" in c["attrs"] and c["attrs"]["query"]["query"] == q\
			and c["attrs"]["query"]["type"] == "key":

				# TODO:
				# - Is a little strict on what it accepts, should be able to
				# handle redundant spaces
				# Decompose the query to find the key and value
				tmp = c["attrs"]["query"]["query"]
				first = tmp.find(" ")
				second = tmp.find(",")
				firstV = tmp[first+1:second]

				while tmp[second+1] == " ":	second += 1
				tmp = tmp[second+1:]
				first = tmp.find(" ")
				secondV = tmp[:first]

				# Create 1 result that holds the entire result and which field
				# is the key and which field is the value
				c["queryResult"] = {"key" : firstV, "value" : secondV, "result" :
				qq}
	return table

# Uses the configuration XML-file and the source database to create new XML-file
# that is input to the timeline
def runQueries(dbName, xmlO, xml, skew, startD, endD, timezone, Queries,
unallocated):
	db = sqlite.connect(dbName)
	db.row_factory = dict_factory
	dateT = 0
	for t in xmlO["tables"]:	# For all the tables
		count = 0
		if "where" not in t:
			t["where"] = None
		# Execute the actual query
		query, succ = getInfoDB(db, t["columns"], t["name"], t["where"], Queries)
		if unallocated != None:
			for row in unallocated[t["name"]]:
				query.append(row)

		# Return if we fail, might just be wrong XML file, so should not exit
		if succ == False:
			if db:	db.close()
			return False

		# We run all the XML-defined queries beforehand to avoid having to run
		# them for every field value
		t = runSetQueries(t, db, dbName, Queries)

		# Defines 1 event
		for q in query:
			event = ET.Element("event")
			localStorage = {}
			
			# Get static filter that should be used for this event
			Filter = ""
			if "filter" in t:	Filter = t["filter"].get("static", "")

			# Get the icon that should be displayed, default is blue dot
			if "icon" in t:
				if "file" in t["icon"]:
					event.set("icon", t["icon"]["file"])

			# Insert attributes that have been specified
			for i in t["inserts"]:	event.set(i["id"], i["name"])

			# Go through all the columns and add attributes
			for c in t["columns"]:
				ins = ""	# The value that is inserted into the XML attribute

				# q[c["name"]] holds the result for this columns and is not subject
				# to change, which "ins" is.

				# Set default value if we are unable find a real value
				if q[c["name"]] == None or q[c["name"]] == "":
					ins = c["default"]

				# Type specifies values that should be replaced, usually integers
				# that are replaced by hardcoded strings. We also add the real value
				# in parentheses.
				elif "type" in c["attrs"]:
					types = c["attrs"]["type"].split(";")
					for ty in types:
						if ty != "" and str(ty.split(":")[0]) == str(q[c["name"]]):
							ins = ty.split(":")[1] + " (" + str(q[c["name"]]) + ")"
							break
					# Fallback if it's unknown, print the real value
					if ins == "":
						ins = str(q[c["name"]])

				# Column should not be interpreted as simple text
				elif "filetype" in c["attrs"]:
					Type = c["attrs"]["filetype"]

					# Field is JSON
					if Type == "json" and "select" in c["attrs"]:
						ins, localStorage = getFileTypeJson(c, q, localStorage)

					# Field is path, print as usual, but also option to include media
					elif Type == "path":
						ins = str(q[c["name"]])
						createMedia(ins, event)

					# Unsopported filetype
					else:
						exitError("Unsupported filetype '" + Type + "'")


				# Replace value with result from different table
				elif "query" in c["attrs"]:
					# Query is already executed
					if c["attrs"]["query"]["type"] == "key" and "queryResult" in c:
						ins = getQueryCompleted(q, c)
					
					# We have to execute a new query
					elif c["attrs"]["query"]["type"] == "direct":
						ins = getQueryNew(db, c, str(q[c["name"]]), dbName)

				# We don't need to format or replace anything, we just need to encode
				# the variable correctly
				elif type(q[c["name"]]) == int or type(q[c["name"]]) == long or type(q[c["name"]]) == float:
					ins = str(q[c["name"]])
				else:
					ins = q[c["name"]]
				
				# Should always be encoded with valid html
				ins = removeInvalid(ins).encode('ascii', 'xmlcharrefreplace')

				# If we should store this column, this column can then be referenced
				# by the XML file
				if "store" in c["attrs"] and c["attrs"]["store"].lower() != "false":
					key = c["attrs"]["store"]
					
					# Check if we should use default name or not
					if key.lower() == "true":	key = c["name"]

					localStorage[key] = q[c["name"]]
				
				# Write to log file if that is specified
				if "log" in c["attrs"]:
					c["attrs"]["log"].write(q[c["name"]] + "\n")

				# Add to filter if this column is specified with it
				if c["attrs"].get("filter", False) == True:
					Filter += removeInvalid(ins).encode('ascii', 'xmlcharrefreplace')
				
				# Static text is appended to the result
				if "append" in c["attrs"]: 	ins += " " + c["attrs"]["append"]

				# Static text is prepended to the result
				if "prepend" in c["attrs"]:	ins = c["attrs"]["prepend"] + " " + ins

				# id should always be included in the column tag
				if "id" in c["attrs"]:
					# Title is formatted i bit differently, so this is an exception
					if c["attrs"]["id"] == "title":
						event.set("title", "[" + c["print"] + "] " + ins)
					else:
						# Title for column is in bold
						ins2 = "<b>" + c["print"] + "</b> "
						
						# Description should not be placed as attribute but inside the
						# tag
						if c["attrs"]["id"] == "description":
							bef = event.text
							if bef != "" and bef != None:	bef += "<br />"
							else:	bef = ""
							bef += ins2 + ins
							event.text = bef
						
						else:
							# Timestamps must be formatted accordingly
							if c["attrs"]["id"] == "start" or c["attrs"]["id"] == "end":
								# Default divide value (milliseconds, UNIX)
								divide = 1000
								subtract = 0

								# Different epoch than UNIX
								if "epoch" in c["attrs"]:
									if c["attrs"]["epoch"].lower() == "windows":
										divide = 10000000	# Standard in Windows
										subtract = 11644473600
									else:
										exitError("Epoch '" + c["attrs"]["epoch"] + \
										"' is not supported")

								# Change the value we shoulde divide by
								if "divide" in c["attrs"]:
									# Divide can be float or integer
									divide = c["attrs"]["divide"]
									divide = float(divide) if '.' in divide else int(divide)

								val = int( ( (long(ins)/divide) - subtract) )
								
								# If this is start, it should be used as a basis for
								# filtering out too early or too late events
								if c["attrs"]["id"] == "start":
									dateT = int(math.floor(val))

								# Get a time we can write in the event
								ins = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(val+skew))

								# Set time event
								event.set(c["attrs"]["id"], ins)

							# All other events that are not title, description, start
							# or end
							else:
								event.set(c["attrs"]["id"], ins2 + ins)
				else:
					# Must supply an ID attribute in XML file
					exitError("No id attribute in " + c["name"])

			# Always set filter, might be empty
			event.set("eventID", Filter)

			# Check if goes beyond our boundaries
			if dateT <= endD and dateT >= (startD-1):
				xml.append(event)
				count += 1

		if verbose:
			print "Selected " + str(count) + " records from database '" + dbName +\
			"', table '" + str(t["name"]) + "'"
	if db:
		db.close()
	return True

def removeInvalid(chunk):
	if type(chunk) == int or type(chunk) == float or type(chunk) == long:
		return str(chunk)
	chunk = ' '.join(chunk .split())
	return ''.join([ch for ch in chunk if ord(ch) < 127 and ord(ch) > 31 or ord(ch) == 9 ])


# Retrieve all unallocated from one database
# Converts the result to a format that can be read just like the results
# received from the original query
def getUnallocated(xmlConfig, dbPath):
	dbFile = xmlConfig["name"]

	# Make a list of all table names
	tables = []
	for t in xmlConfig["tables"]:
		tables.append(t["name"])

	# Data we send to chose which records we are going to select
	send = [{"filename" : dbFile, "path" : dbPath, "tables" : tables}]

	# All data in unallocated space
	res = SQLiteCarver.findAllUnallocated(send, verbose)
	
	# Transform the input to what it looks like when we get it from the SQL
	# queries
	sqlResult = {}
	for r in res:
		for t in tables:
			sqlResult[t] = []
			if t in r["rows"]:
				for l in r["rows"][t]:
					ins = {}
					for ll in l:
						ins[ll["name"]] = ll["content"]
					sqlResult[t].append(ins)
	
	# Delete rows where we don't have a timestamp
	# Add mark in title that says it is from unallocated space
	# Add attributes we are missing
	for col in xmlConfig["tables"]:
		dels = []
		count = 0
		for r in sqlResult[col["name"]]:
			for c in col["columns"]:
				if c["attrs"]["id"] == "start" or c["attrs"]["id"] == "end":
					if c["name"] not in r or r[c["name"]] == 0:
						dels.append(count)
						break
				if c["name"] not in r:
					r[c["name"]] = c["default"]
				if c["attrs"]["id"] == "title":
					r[c["name"]] = str(r[c["name"]]) + " (Unallocated)"
			count += 1
		for i in reversed(range(0, len(dels))):
			del sqlResult[col["name"]][dels[i]]
	# TODO:
	# - Should also write unallocated log to a separate file
	return sqlResult

if __name__== '__main__':
	# Add the parser object
	parser = argparse.ArgumentParser(description=' droidlog2timeline - Create timeline for Android',
	formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	
	# Path to the Android data directory
	parser.add_argument('-p', '--path', dest='path',default="/mnt/data/data/",\
	help='Path to the /data/data/ directory in Android')

	# Path to the XML configuration files
	parser.add_argument('-c', '--config', dest='config', default='configs',\
	help='Path to XML configuration files')

	# Path to the CSV file that contain the list of all the packages installed on
	# the phone
	parser.add_argument('-l', '--list', dest='list', default=None, type=str,\
	help='Full path to list of packages on the phone')

	# Number of seconds to skew the clock
	parser.add_argument('-s', '--skew', dest='skew', type=int,
	default=0, help='Number of seconds to skew the clock')

	# Earliest date to record, can be used to limit the amount of data that need
	# to be parsed
	parser.add_argument('-e', '--earliestdate', dest='earliestdate', type=str,
	default=None, help='Earliest date to record (yyyy-mm-ddThh:mm)')
	
	# Latest possible date
	parser.add_argument('-d', '--latestdate', dest='latestdate', type=str,
	default=None, help='Latest date to record (yyyy-mm-ddThh:mm)')

	# The timezone that the phone is in. Not sure what timesone the database
	# timestamps are in.
	parser.add_argument('-t', '--timezone', dest='timezone', type=str,
	default="+00:00", help='Timezone of the phone (+XXXX)')

	# The directory for output
	parser.add_argument('-o', '--output', dest='output', type=str,
	default="webapp/output/", help='Output directory')

	# Log file, can be used as documentation for what has been done
	parser.add_argument('-L', '--log', dest='log', type=str,
	default="logs", help='Logfile of what has been done')

	# Verbose output
	parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
	help="Verbose output")

	# Use LogCat logs instead of SQLite databases
	parser.add_argument('-a', '--logcat', dest='logcat', action='store_true',
	help="Use LogCat files instead of sqlite databases")
	
	# Add the possibility to check the hash of each file so we can be sure that
	# SQLite doesn't change the file
	parser.add_argument('-H', '--hashcheck', dest='hashcheck', action='store_true',
	help="Check that the files are not modified after interaction with them, "+
	"exits if they don't match")

	# Whether or not we should carve for information in unallocated space,
	# default is not
	parser.add_argument('-C', '--carve', dest='carve', action='store_true',
	help="Carve for information in unallocated space")
	
	# Disallow override
	parser.add_argument('-D', '--disallow-override', dest='disallow',
	action='store_true',
	help="Disallow override of attribute names")
	
	# Use symlinks for media
	parser.add_argument('-S', '--symlinks', dest='symlinks',
	action='store_true',
	help="Use symlinks for displaying media, only possible on UNIX")

	# Root paths for gathering media
	parser.add_argument('-r', '--root-paths', dest='roots', nargs='+', default=[],\
	help='Root paths for various mount points')

	# Get program directory
	thisPath = os.path.dirname(os.path.realpath(__file__))

	workPath = os.getcwd()	# Get working directory
	
	args = vars(parser.parse_args())

	disallow_override = args["disallow"]

	createSymlinks = args["symlinks"]

	storagePaths = args["roots"]

	# Transform them all to full paths, needed for symlinks
	for i in range(0, len(storagePaths)):
		if os.path.isabs(storagePaths[i]) == False:
			storagePaths[i] = os.path.join(workPath, storagePaths[i])

	Carve = args["carve"]
	if Carve:
		# Import module for SQLite carving
		sys.path.insert(0, 'src/SQLiteCarving')
		import SQLiteCarver

	sys.path.insert(0, 'src/droidlog')
	import droidlog


	verbose = args["verbose"]

	pathConfig = os.path.join(thisPath, args["config"])	# Path to configuration files

	pathData = args["path"]	# Path to database files

	packages = args["list"]	# List of packages installed on the phone

	logdir = args["log"]
	if not os.path.exists(logdir):
		os.makedirs(logdir)

	try:
		log = open(os.path.join(logdir, "droidlog2timeline.log"), "w")	# Output file
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
		sys.exit(0)

	skew = args["skew"]

	timezone = args["timezone"]

	logCat = args["logcat"]

	hashcheck = args["hashcheck"]

	Queries = []

	output = args["output"]
	if not os.path.exists(output):
		os.makedirs(output)

	templates = os.path.join(thisPath, "templates")
	shutil.copy2(os.path.join(templates, "index.html"),\
	os.path.join(output, "index.html"))

	# Generate timestamps for earliest and latest date
	startD = args["earliestdate"]
	endD = args["latestdate"]
	if startD == None:
		startD = 10	# Then we avoid places where date is 0
	else:
		startD = time.strptime(startD, "%Y-%m-%dT%H:%M")
		startD = time.mktime(startD)


	if endD == None:
		# Max time possible
		endD = math.pow(2, 32)
	else:
		endD = time.strptime(endD, "%Y-%m-%dT%H:%M")
		endD = time.mktime(endD)

	if os.path.isdir(pathConfig) == False:
		print pathConfig + " is not a directory"
		sys.exit(0)
	
	if os.path.isdir(pathData) == False:
		print pathData + " is not a directory"
		sys.exit(0)
	
	try:
		f = open(os.path.join(output, "logs.xml"), "w")	# Output file
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
		sys.exit(0)

	root = ET.Element('data')	# Root element
	
	# Get all packages we should check, can gather this from the device:
	# /data/system/packages.list
	packs = readPackagesList(packages, pathData)
	if verbose:
		print "Read in " + str(len(packs)) + " possible packages"
	log.write("PACKAGES " + str(len(packs)) + " possible packages\n")

	imageDescs = []

	intervals = []

	if logCat == True:
		intervals = ["SECOND", "MINUTE", "HOUR", "DAY"]
		files = ["radio.log", "main.log", "events.log"]
		for fi in files:
			evs = readLogcat(os.path.join(pathData, fi), timezone)
			for e in evs:
				event = ET.Element("event")
				event.set("title", e["msg"])
				event.text = "Type: " + e["type"] + "</br>" + "Level: " +\
				e["level"]
				event.set("start", e["date"])
				root.append(event)


	else:	# SQLite databases
		root.set("date-time-format", "iso8601")
		dbPath = ""
		XMLconf = ""
		unallocated = None
		intervals = ["MINUTE", "HOUR", "DAY", "MONTH"]
		for l in packs:
			count = 0
			while True:
				ret = True
				# Find the correct ending, .1, .2, etc
				ending = "" if count == 0 else "." + str(count)
				XMLconf = os.path.join(pathConfig, l) + ".xml" + ending

				# Check if file exist
				if os.path.isfile(XMLconf) == False:
					log.write("MISSING " + XMLconf + "\n")
					ret = False
					break
				else:
					log.write("TRYING " + XMLconf + "\n")
					
				tmpImageDescs = []
				xmlO = readXML(XMLconf, tmpImageDescs, pathData, disallow_override, logdir)	# Read xml configuration
				eventList = []	# Temporary storage we append if we succeed
				dbFinds = 0
				for x in xmlO:	# For each database
					tmpDir = os.path.join(pathData, l)
					dbPath = os.path.join(tmpDir, x["name"])	# Full path
					if os.path.isfile(dbPath) == False:
						log.write("MISSING " + dbPath + "\n")
						continue
					dbFinds += 1
					if hashcheck:
						hashSum = sha1OfFile(dbPath)
					if Carve:
						tmpDir = os.path.join(pathData, l)
						unallocated = getUnallocated(x, tmpDir)
					ret = runQueries(dbPath, x, eventList, skew, startD, endD,
					timezone, Queries, unallocated)
					if hashcheck:
						hashSum2 = sha1OfFile(dbPath)
						if hashSum != hashSum2:
							print "Hash of sqlite database " + dbPath + \
							" has changed from " + hashSum + " to " + hashSum2
							sys.exit(0)
						log.write("HASH " + hashSum + " " + dbPath + "\n")
					if ret == False:
						break
				if ret == True and dbFinds > 0:
					for q in Queries:	log.write("QUERY " + q + "\n")
					Queries = []
					log.write("SUCCESS " + XMLconf + " " + dbPath + "\n")
					for e in eventList:	root.append(e)
					for i in tmpImageDescs:	imageDescs.append(i)
					break
				count += 1
			if ret == False:	# After "while True" loop
				if verbose == True:
					print "Unable to extract logs using " + XMLconf

	# Write full XML file to disk
	f.write(str(ET.tostring(root, pretty_print=True, xml_declaration=True)))

	# Print JavaScript variables that are used by the timeline
	printVariables(os.path.join(output, "variables.js"), imageDescs, intervals,\
	int(timezone[:3]))

	# Go up one directory and print new file with links
	printLinks(os.path.dirname(os.path.dirname(output)))
