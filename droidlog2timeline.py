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
import sys, time, csv, os
import argparse
from datetime import datetime
import math
import shutil	# To copy files
import hashlib

try:
	from lxml import etree as ET
except ImportError:
	print "Unable to import lxml, install with easy_install lxml"
	sys.exit(0)

# Global variable that determines if the output is verbose or not
verbose = False

# Calculate SHA-1 hash value of a file
def sha1OfFile(filepath):
	if verbose:
		print "Calculating hash value of " + filepath
	with open(filepath, 'rb') as f:
		return hashlib.sha1(f.read()).hexdigest()

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

# Writes out JavaScript varialbes we have created during the script
def printVariables(fname, images, intervals):
	if verbose:
		print "Writing JavaScript variables"
	f = open(fname, "w")
	f.write("var interval1=Timeline.DateTime." + intervals[0] + ";\n")
	f.write("var interval2=Timeline.DateTime." + intervals[1] + ";\n")
	f.write("var interval3=Timeline.DateTime." + intervals[2] + ";\n")
	f.write("var interval4=Timeline.DateTime." + intervals[3] + ";\n")
	f.write("var XMLFile = \"logs.xml\";\n")
	f.write("var Images= new Array();\n")
	f.write("var imageDesc = new Array();\n")

	# All image paths and their description
	for i in images:
		f.write("Images.push('" + i["file"] + "');\n")
		f.write("imageDesc.push('" + i["description"] + "');\n")


# Read in list of packages installed on the phone
# Is compatible with packages.list on the phone, but a simple ls will also give
# the correct results
def readPackagesList(name):
	if verbose:
		print "Reading list of packages from " + name
	ret = []
	with open(name, "r") as csvfile:
		reader = csv.reader(csvfile, delimiter=' ', quotechar='"')
		for row in reader:
			ret.append(row)
	return ret

# Read in configuration XML-file into a list of dictionaries
# Will store any arbitrary attributes, interpreting them is not done here
def readXML(name, imageDesc):
	ret = []
	f = open(name, "r")
	tree = ET.parse(f)
	root = tree.getroot()

	for dbT in root.iter("database"):
		DB = {}
		DB["name"] = dbT.get("id")
		tables = []
		for elem in dbT.iter("table"):
			table = {}
			table["name"] = elem.get("id")
			columns = []
			inserts = []
			queries = []
			for el in elem.iterchildren():
				if el.tag == "column":
					column = {}
					column["name"] = el.text
					column["print"] = el.text
					column["default"] = "None"
					attrs = {}
					for e in el.items():
						if e[0] == "override":
							column["print"] = e[1]
						elif e[0] == "default":
							column["default"] = e[1]
						else:
							attrs[e[0]] = e[1]
						if e[0] == "query":
							queries.append(e[1])
					column["attrs"] = attrs
					columns.append(column)
				elif el.tag == "icon":
					icon = {"file" : "images/" + el.text, "description" :\
					el.get("desc")}
					table["icon"] = icon
					imageDesc.append(icon)
				elif el.tag == "where":
					table["where"] = el.text
				elif el.tag == "insert":
					insert = {"name" : el.text, "id" : el.get("id")}
					inserts.append(insert)
			table["columns"] = columns
			table["inserts"] = inserts
			table["queries"] = queries
			tables.append(table)
		DB["tables"] = tables
		ret.append(DB)
	return ret

# Retrieve the info from the database, runs a simple query and return the result
def getInfoDB(db, columns, table, where=None, Log=None):
	retValue = True
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
	try:
		cur = db.cursor()
		cur.execute(get)
		ret = cur.fetchall()
		if Log != None:
			Log.append(get)
	except sqlite.Error, e:
		print "Error %s:" % e.args[0]
		retValue = False
	return ret, retValue

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
		print "Error %s:" % e.args[0]
		retValue = False
	return ret, retValue


# Uses the configuration XML-file and the source database to create new XML-file
# that is input to the timeline
def runQueries(dbName, xmlO, xml, skew, startD, endD, timezone, Queries):
	db = sqlite.connect(dbName)
	db.row_factory = dict_factory
	dateT = 0
	for t in xmlO["tables"]:	# For all the tables
		count = 0
		if "where" not in t:
			t["where"] = None
		# Execute the actual query
		query, succ = getInfoDB(db, t["columns"], t["name"], t["where"], Queries)

		# Exit if we fail
		if succ == False:
			if db:	db.close()
			return False

		# We run all the XML-defined queries beforehand to avoid having to run
		# them for every field value
		for q in t["queries"]:
			qq, succ = execQuery(db, q, Queries)
			if succ == False:
				if db:	db.close()
				return False
			for c in t["columns"]:
				if "query" in c["attrs"] and c["attrs"]["query"] == q:
					# TODO:
					# - Is a little strict on what it accepts, should be able to
					# handle redundant spaces
					# Decompose the query to find the key and value
					tmp = c["attrs"]["query"]
					first = tmp.find(" ")
					second = tmp.find(",")
					firstV = tmp[first+1:second]
					while tmp[second+1] == " ":
						second += 1
					tmp = tmp[second+1:]
					first = tmp.find(" ")
					secondV = tmp[:first]

					# Create 1 result that holds the entire result and which field
					# is the key and which field is the value
					c["queryResult"] = {"key" : firstV, "value" : secondV, "result" :
					qq}
		for q in query:	# For each result
			event = ET.Element("event")
			if "icon" in t:
				if "file" in t["icon"]:
					event.set("icon", t["icon"]["file"])
			for i in t["inserts"]:
				event.set(i["id"], i["name"])
			for c in t["columns"]:
				ins = ""
				if q[c["name"]] == None:
					ins = c["default"]
				elif "type" in c["attrs"]:
					types = c["attrs"]["type"].split(";")
					for ty in types:
						if int(ty.split(":")[0]) == q[c["name"]]:
							ins = ty.split(":")[1]
							break
				elif type(q[c["name"]]) == int or type(q[c["name"]]) == long:
					ins = str(q[c["name"]])
				else:
					ins = q[c["name"]].encode('ascii', 'xmlcharrefreplace')

				# Separate case where we need to get the result from a different DB
				# The queries have been done already, just need to find it
				if "query" in c["attrs"] and "queryResult" in c:
					for res in c["queryResult"]["result"]:
						if q[c["name"]] == res[c["queryResult"]["key"]]:
							ins = str(res[c["queryResult"]["value"]])
							break
				
				if "append" in c["attrs"]:
					ins += " " + c["attrs"]["append"]
				if "prepend" in c["attrs"]:
					ins = c["attrs"]["prepend"] + " " + ins
					print ins

				if "id" in c["attrs"]:
					if c["attrs"]["id"] == "title":
						event.set("title", "[" + c["print"] + "] " + ins)
					else:
						ins2 = "<b>" + c["print"] + "</b> "
						if c["attrs"]["id"] == "description":
							bef = event.text
							if bef != "" and bef != None:	bef += "<br />"
							else:	bef = ""
							bef += ins2 + ins
							event.text = bef
						else:
							if c["attrs"]["id"] == "start" or c["attrs"]["id"] == "end":
								divide = 1000
								if "divide" in c["attrs"]:
									divide = int(c["attrs"]["divide"])
								if c["attrs"]["id"] == "start":
									dateT = int(math.floor(long(q[c["name"]])/divide))
								ins = time.strftime('%b %d %Y %H:%M:%S ' + timezone,\
								time.localtime((int(q[c["name"]])/divide)+skew))
								event.set(c["attrs"]["id"], ins)
							else:
								event.set(c["attrs"]["id"], ins2 + ins)
				else:
					return False
			if dateT < endD and dateT > (startD-1):
				xml.append(event)
				count += 1
		if verbose:
			print "Selected " + str(count) + " records from database '" + dbName +\
			"', table '" + str(t["name"]) + "'"
	if db:
		db.close()
	return True

if __name__== '__main__':
	# Add the parser object
	parser = argparse.ArgumentParser(description='Create timeline for Android',
	formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	
	# Path to the Android data directory
	parser.add_argument('-p', '--path', dest='path',default="/mnt/data/data/",\
	help='Path to the /data/data/ directory in Android')

	# Path to the XML configuration files
	parser.add_argument('-c', '--config', dest='config', default='configs',\
	help='Path to XML configuration files')

	# Path to the CSV file that contain the list of all the packages installed on
	# the phone
	parser.add_argument('-l', '--list', dest='list', default='packages.list',\
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
	default="GMT+0000", help='Timezone of the phone (GMT+XXXX)')

	# The directory for output
	parser.add_argument('-o', '--output', dest='output', type=str,
	default="output/", help='Output directory')

	# Log file, can be used as documentation for what has been done
	parser.add_argument('-L', '--log', dest='log', type=str,
	default="droidlog.log", help='Logfile of what has been done')

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

	# Get program directory
	thisPath = os.path.dirname(os.path.realpath(__file__))

	workPath = os.getcwd()	# Get working directory
	
	args = vars(parser.parse_args())

	verbose = args["verbose"]

	pathConfig = thisPath + "/" + args["config"]	# Path to configuration files

	pathData = args["path"]	# Path to database files

	packages = args["list"]	# List of packages installed on the phone

	logfile = args["log"]
	log = open(logfile, "w")	# Output file

	skew = args["skew"]

	timezone = args["timezone"]

	logCat = args["logcat"]

	hashcheck = args["hashcheck"]

	Queries = []

	output = args["output"]
	if not os.path.exists(output):
		os.makedirs(output)
	if not os.path.exists(thisPath + "/templates/"):
		print "No path to templates"
		sys.exit(0)
	if not os.path.isfile(thisPath + "/templates/index.html"):
		print "File " + thisPath + "/templates/index.html does not exist"
	shutil.copy2(thisPath + "/templates/index.html", output + "/index.html")
	if os.path.exists(thisPath + "/templates/js/"):
		if os.path.exists(output + "/js/") == False:
			shutil.copytree(thisPath + "/templates/js/", output + "/js/")
	if os.path.exists(thisPath + "/templates/css/"):
		if os.path.exists(output + "/css/") == False:
			shutil.copytree(thisPath + "/templates/css/", output + "/css/")
	if os.path.exists(thisPath + "/templates/images/"):
		if os.path.exists(output + "/images/") == False:
			shutil.copytree(thisPath + "/templates/images/", output + "/images/")


	# Generate timestamps for earliest and latest date
	startD = args["earliestdate"]
	endD = args["latestdate"]
	if startD == None:
		startD = 1
	else:
		startD = time.strptime(startD, "%Y-%m-%dT%H:%M")
		startD = time.mktime(startD)
	if endD == None:
		endD = int(math.ceil(time.mktime(time.gmtime())))
		add = True
		if timezone[3] == "-":
			add = False
		zone = timezone[4:]
		num = int(zone[:2])*3600
		num += int(zone[2:])*60
		if add == False:
			num = -num
		endD += num
	else:
		endD = time.strptime(endD, "%Y-%m-%dT%H:%M")
		endD = time.mktime(endD)

	if os.path.isdir(pathConfig) == False:
		print pathConfig + " is not a directory"
		sys.exit(0)
	
	if os.path.isdir(pathData) == False:
		print pathData + " is not a directory"
		sys.exit(0)
	
	if os.path.isfile(packages) == False:
		print packages + " is not a valid file"
		sys.exit(0)

	# Should let the user chose output dir, so we don't cludder this dir
	# But then we also need to change the html file
	f = open(output + "/logs.xml", "w")	# Output file

	root = ET.Element('data')	# Root element
	
	# Get all packages we should check, can gather this from the device:
	# /data/system/packages.list
	packs = readPackagesList(packages)
	if verbose:
		print "Read in " + str(len(packs)) + " possible packages"
	log.write("PACKAGES " + str(len(packs)) + " possible packages\n")

	imageDescs = []

	intervals = []

	if logCat == True:
		intervals = ["SECOND", "MINUTE", "HOUR", "DAY"]
		files = ["radio.log", "main.log", "events.log"]
		for fi in files:
			evs = readLogcat(pathData + "/" + fi, timezone)
			for e in evs:
				event = ET.Element("event")
				event.set("title", e["msg"])
				event.text = "Type: " + e["type"] + "</br>" + "Level: " +\
				e["level"]
				event.set("start", e["date"])
				root.append(event)


	else:	# SQLite databases
		dbPath = ""
		XMLconf = ""
		intervals = ["MINUTE", "HOUR", "DAY", "MONTH"]
		for l in packs:
			count = 0
			while True:
				ret = True
				# Find the correct ending, .1, .2, etc
				ending = "" if count == 0 else "." + str(count)
				XMLconf = pathConfig + "/" + l[0] + ".xml" + ending

				# Check if file exist
				if os.path.isfile(XMLconf) == False:
					log.write("MISSING " + XMLconf + "\n")
					ret = False
					break
				else:
					log.write("TRYING " + XMLconf + "\n")
					
				tmpImageDescs = []
				xmlO = readXML(XMLconf, tmpImageDescs)	# Read xml configuration
				eventList = []	# Temporary storage we append if we succeed
				for x in xmlO:	# For each database
					dbPath = pathData + "/" + l[0] + "/" + x["name"]	# Full path
					if os.path.isfile(dbPath) == False:
						log.write("MISSING " + dbPath + "\n")
						ret = False
						break
					if hashcheck:
						hashSum = sha1OfFile(dbPath)
					ret = runQueries(dbPath, x, eventList, skew, startD, endD,
					timezone, Queries)
					if hashcheck:
						hashSum2 = sha1OfFile(dbPath)
						if hashSum != hashSum2:
							print "Hash of sqlite database " + dbPath + \
							" has changed from " + hashSum + " to " + hashSum2
							sys.exit(0)
						log.write("HASH " + hashSum + " " + dbPath + "\n")
					if ret == False:
						break
				if ret == True:
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
	printVariables(output + "/variables.js", imageDescs, intervals)
