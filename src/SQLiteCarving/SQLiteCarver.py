#!/usr/bin/python
# -*- coding: utf-8 -*-

# The MIT License (MIT)

# Copyright (c) 2013 Robin Stenvi

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
import sys, time, os, argparse
import struct, string, binascii

# Separate the attribute from the attribute type. Information we are not
# interested in are stripped away. If the field doesn't contain a name and a
# type, the function returns None
def getAttrValue(string):
	# Should be at leat two values separated by space
	i = string.find(" ")
	if i == -1:
		return None
	Name = string[:i]
	Type = string[i+1:]

	# We keep integer primary key, but ignore any other appendices
	ii = Type.find("INTEGER PRIMARY KEY")
	if ii == -1:
		ii = Type.find(" ")
		if ii != -1:
			Type = Type[:ii]
	else:
		Type = Type[:19]
	return {"type" : Type, "name" : Name}

# Retrieves all tables in the database.
def getTables(db):
	con = sqlite.connect(db)
	cursor = con.cursor()
	cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
	tables = cursor.fetchall()
	ret = {}
	for t in tables:
		# Get table name
		tabNamI = t[0].find("(")
		befValues = t[0][:tabNamI]
		befValues = befValues.strip()
		tabNami = befValues.rfind(" ")
		tabName = befValues[tabNami+1:]

		tabName = tabName.strip()

		tabNamI += 1	# After (

		tt = t[0][tabNamI:]
		tabEnd = tt.find(")")
		sql = tt[:tabEnd]
		
		# Split into each attribute which has name and type
		attr = string.split(sql, ",")
		attrs = []
		for a in attr:
			a = a.strip()
			tmp = getAttrValue(a)
			if tmp != None:
				attrs.append(tmp)
		ret[tabName] = attrs
	return ret

# Replace ? with value and return true or false if it matches
def evaluateSignature(sig, value):
	if type(value) is int:
		sig = sig.replace("?", str(value))
		return eval(sig)
	return False


# Creates signatures where ? is replaced by the value and sent to eval
# Don't think this is complete
def createSignature(Type):
	Type = Type.upper()

	# Is an interpretation of the documentation here:
	# https://www.sqlite.org/datatype3.html and here:
	# https://www.sqlite.org/fileformat2.html

	if Type.find("INT") != -1 or Type.find("NUMERIC") != -1 or\
	Type.find("DECIMAL") != -1 or Type.find("DATE") != -1 or\
	Type.find("BOOLEAN") != -1 or Type.find("LONG") != -1:
		return "? >= 0 and ? <= 9"
	
	if Type.find("CHAR") != -1 or Type.find("TEXT") != -1 or Type.find("CLOB"):
		return "(? >= 13 and ? % 2 == 1) or (? == 0)"

	if Type == "BLOB":
		return "(? >= 12 and ? % 2 == 0) or (? == 0)"
	
	if Type.find("FLOAT") != -1 or Type.find("DOUBLE") != -1 or\
	Type.find("REAL") != -1:
		# I think this can be zero
		return "(? == 7) or (? == 0)"
	
	# Just print a message and return something that is always false
	print Type + " is not a valid variable type"
	return "1 == 0"


# Create signatures for all the tables in the database
# Returns a dictonary where the keys are table names
# Each table has a list of columns, where each column is stored as a dictionary
# The column dictionary has 3 keys: "type", "name", "signature"
def createSignatures(db):
	tables = getTables(db)
	for key in tables.keys():
		for column in tables[key]:
			sig = createSignature(column["type"])
			column["signature"] = sig
	return tables


# Interpret a given block and returns the correct value based on the header.
# Only needed when there is a numeric value, int or float
def interpretBlock(headerType, value):
	# 0 and 8 both mean that there is no content and there is fixed value of 0
	if headerType == 0:
		return 0
	
	# Numbers, from 1 bit int to 8 bit floats
	if headerType <= 7:
		tmp = value

		# Valid integers and floats and their corresponding header value
		types = ["", "B", "H", "I", "I", "Q", "Q", "d"]
		if headerType == 3:	# Pad to 4 bytes
			tmp = "\x00" + tmp
		elif headerType == 5:	# Pad to 8 bytes
			tmp = "\x00\x00" + tmp
		return struct.unpack(">" + types[headerType], tmp)[0]
	
	if headerType == 8:
		return 0

	# 9 is no content and fixed value of 1
	if headerType == 9:
		return 1
	
	# Text and blob need no interpretation
	else:
		return value

# Get the length of the content based on the header. Numbers are based on the
# SQLite database file format, can be read here:
# https://www.sqlite.org/fileformat2.html
def getHeaderIntSize(var):
	if var == 0:	return 0
	if var == 1:	return 1
	if var == 2:	return 2
	if var == 3:	return 3
	if var == 4:	return 4
	if var == 5:	return 6
	if var == 6:	return 8
	if var == 7:	return 8
	if var == 8:	return 0
	if var == 9:	return 0
	
	if var >= 12 and (var % 2) == 0:	return (var-12)/2
	if var >= 13 and (var % 2) == 1:	return (var-13)/2
	return None


# Looks through all pages of unallocated space and looks for cell that can match
# any of the tables we are looking for. First it looks after a header that can
# match. Then it checks if the content matches the header.

# This function tries to match as many as possible, need to be filtered later.

# It does require having the entire header intact and having a body that can
# match the beginning of the header.
def findStructure(sigs, block):
	start = 0	# Place to start looking
	add = 1
	end = len(block)
	lengths = []
	ret = {}
	while start < (end-1):

		# File is full of 0s, we should ignore it where there is many in a row
		# TODO:
		# - Only checks two bytes here, if a header start with 3 zero-bytes we
		# will not match it.
		while start < (end-1) and ord(block[start+1]) == 0x00 and ord(block[start]) == 0x00:
			start += 1

		# Check that we are not at the end
		if start >= (end-1):	break
		
		# For each table signature
		for sigKey in sigs.keys():
			add = 0	# Number of bytes into current cell
			var = 0	# Value of the variable int
			found = True
			lengths = []	# No values have been found yet
			
			# For each column, tryy to find a varint that matches it
			for col in sigs[sigKey]:

				# Get the variable int at this location and store number of bytes in
				# add
				tmp = getVarInt(block, start+add)
				if tmp != False:
					var, add2 = tmp
					add += add2
				else:	# Invalid varint, can't be a header
					found = False
					break
				
				# Check if this is a valid header for the signature we are looking
				# at
				if evaluateSignature(col["signature"], var) == False:
					found = False
					break
				else:
					# One possible header, add it to the list
					lengths.append({"type" : col["type"], "name" : col["name"],
					"length" : getHeaderIntSize(var), "header" : var})
					
			if found == True:
				add2 = 0
				add3 = 0
				# For each header that we found
				for l in lengths:
					# Find the length of this attribute
					add2 = l["length"]

					# Abort if we are beyond the length, will still store what we got
					# so far
					if (start + add + add3 + add2) > end:
						break

					# Get the entire attribute, and store it in same list
					l["content"] =\
					interpretBlock(l["header"], block[start+add+add3:start+add+add3+add2])
					add3 += add2
					# TODO:
					# - If we check that the value matches the header here instead of
					# later, we might get better speed. Then we might be able to
					# increase by more than 1 byte after we have found one.

				if sigKey not in ret:
					ret[sigKey] = []
				ret[sigKey].append(lengths)
			add = 1	# We always increment by 1 because we don't know if we are
						# correct or not
		start += add
	return ret

# Checks if it is a valid SQLite 3 header
def isSQLiteHeader(header):
	string = "SQLite format 3"
	return header[:15] == string and ord(header[15]) == 0x00

# Get all blocks of unallocated space, i.e space that may have deleted data
def getData(name):
	f = open(name, "rb")
	content = f.read()	# Read entire file
	filesize = len(content)	# Get length of file
	header = content[:16]	# Header magic number
	if isSQLiteHeader(header) == False:
		print "Wrong header"
		return False

	# Pagesize
	pageSize = struct.unpack(">H", content[16:18])[0]
	offset = pageSize
	pagesIndex = []
	unalloc, free = [],[]

	# Get a list of all page indexes
	while offset < filesize:
		if ord(content[offset]) == 13:
			# This is a leaf table (content)
			pagesIndex.append(offset)
		
		offset = offset + pageSize
	
	# For each page index
	for off in pagesIndex:
		page = content[off:off+pageSize]
		pageByte,bOffset,numCells,cOffset,numFree = struct.unpack(">bhhhb", page[:8])

		# Each cell header is 2 bytes long
		start = 8 + (numCells * 2)
		unallocated = page[start:cOffset]
		unalloc.append(unallocated)

		# Try and get freeblocks
		# Have never seen this before
		if bOffset > 0:
			while bOffset != 0:
				start, size = struct.unpack(">hh", page[bOffset:bOffset+4])
				freeblock = page[bOffset:bOffset+size]
				free.append(freeblock)
				bOffset = start
	return unalloc, free

# Tries to find the value of a varint
# TODO:
# - All numbers are interpreted as positive, not a huge problem, but can lead to
# some mistakes
# - Not very efficient
def getVarInt(block, start):
	pos = 0
	value = []
	complete = False
	while pos < 9 and not complete:
		if (start + pos) >= len(block):
			return False
		Byte = ord(block[start+pos])
		if (Byte & 128) == 128 and pos < 8:
			value.append(Byte - 128)
		elif (Byte & 128) == 128 and pos == 8:
			value.append(Byte)
		else:
			value.append(Byte)
			complete = True
		pos += 1

	comBits = ""
	for i in range(0, len(value)):
		bits = format(value[i], '0{}b'.format(8))
		if i != 8:
			bits = bits[1:]
		comBits += bits
	ret = int(comBits, 2)
	return ret, pos

# Check if string is printable or not, returns false if it is not printable.
# This only checks the low values, but because so many values are low, it is
# quite successful.
# Should be able to check if it is valid UTF-8
def isPrintable(string):
	if string == "" or string == None or type(string) == int:
		return True
	for c in string:
		if c < '\x09':
			return False
		elif c > '\x0b' and c < ' ':
			return False
		elif c == '\x7f':
			return False
	return True

# Remove events that are probably wrong
# For now this is just checking whether there is unprintable characters in the
# text.
# TODO:
# - This can maybe be exanded later, some things that can be used is:
#  - Regexp on url / phone number
#  - Limit the number of characters further, is a bit difficult because of UTF-8
#  - Set minimum and maximum value for timestamps
def removeUnlikely(collection):
	for key in collection.keys():
		dels = []
		for i in range(0, len(collection[key])):
			for c in collection[key][i]:
				if "content" in c and "type" in c:
					if c["type"] == "TEXT":
						ret = isPrintable(c["content"])
						if ret == False:
							dels.append(i)
							break
		for i in reversed(range(0, len(dels))):
			del collection[key][dels[i]]
	return collection

# Place result from several different blocks into one dictionary
def collectItems(result):
	collection = {}
	for r in result:
		for key in r.keys():
			if key not in collection:
				collection[key] = r[key]
			else:
				for l in r[key]:
					collection[key].append(l)
	return collection

# Print a table of all the result
def printTable(tables, collection):
	for key in collection.keys():
		print "TABLE: " + str(key) + "\n"
		for i in range(0, len(tables[key])):
			sys.stdout.write(tables[key][i]["name"] + "(" + tables[key][i]["type"] + ")")
			if i < len(tables[key])-1:
				sys.stdout.write("|")
		print ""
		for c in collection[key]:
			for i in range(len(c)):
				if "content" in c[i]:
					sys.stdout.write(str(c[i]["content"]))
				if i < len(c)-1:
					sys.stdout.write("|")
			print ""
		print "\n"


# Get all unallocated from a list of databases, databases is a list with
# the following format:
#	[
#		{
#			"filename" : "name.db", "path" : "/full/path/", tables : ["table1" ...]
#		},
#		{ .... }
#	]

# The return value has the following format:
#	[
#		{
#			"filename" : "name.db", "rows" :
#				{
#					"table1" :
#					[
#						{
#							"name" : "row", "content" : value"
#						},
#						{ .... }
#					],
#					"table2" : [...]
#				}
#		},
#		{ .... }
#	]
# TODO: Free is not checked yet
def findAllUnallocated(databases, verbose=False):
	ret = []
	for d in databases:
		db = os.path.join(d["path"], d["filename"])
		signatures = createSignatures(db)
		for key in signatures.keys():
			if key not in d["tables"]:
				if verbose == True:
					print "Not searching for " + key
				del signatures[key]
			elif verbose == True:
				print "Searching for " + key
		tmp = getData(db)
		if tmp == False:
			if verbose == True:
				print d["path"] + d["filename"] + " cannot be carved"
			break
		unalloc, free = tmp
		structures = []
		for u in unalloc:
			res = findStructure(signatures, u)
			if res:
				structures.append(res)
		collection = collectItems(structures)
		collection = removeUnlikely(collection)
		ins = {"filename" : d["filename"], "rows" : {}}
		# For each table that we found data for
		for key in collection.keys():
			found = 0
			ins2 = []
			# For each row that we found
			for r in collection[key]:
				ins2.append([])
				for i in range(0, len(r)):
					if "name" in r[i] and "content" in r[i]:
						ins2[found].append( {"name" : r[i]["name"], "content" : r[i]["content"]} )
				found += 1

			ins["rows"][key] = ins2
			if verbose == True:
				print "Found " + str(found) + " records from " + key
		ret.append(ins)
	return ret

if __name__== '__main__':
	# Add parser object
	parser = argparse.ArgumentParser(
	description='Carver for SQLite databases',
	formatter_class=argparse.ArgumentDefaultsHelpFormatter)

	# Path to database file
	parser.add_argument('-p', '--path', dest='path', required=True,\
	help='Path to the database that should be carved')

	# List of tables to carve after
	parser.add_argument('-t', '--tables', dest='tables', nargs='+',\
	default=["LIST"],\
	help='List of tables that should be searched for')
	
	# Which file we should print results to
	parser.add_argument('-o', '--output', dest='output',\
	default=None,\
	help='Which file to write results to')

	# Exclude tables instead of including them
	parser.add_argument('-i', '--inverse', dest='inverse',
	action='store_true', help='Exclude -t instead of include')
	
	# Override the previous list and search for all tables
	parser.add_argument('-a', '--all', dest='all',
	action='store_true', help='Search all tables, ignores -t')
	
	# Dump all unallocated space to file or stdout
	parser.add_argument('-d', '--dump-unallocated', dest='dump',
	action='store_true', help='Dump all unallocated space (binary)')

	args = vars(parser.parse_args())

	db = args["path"]
	findTables = args["tables"]
	checkAll = args["all"]
	output = args["output"]
	inverse = args["inverse"]
	dump = args["dump"]

	if output != None:
		sys.stdout = open(output, 'w')

	# Dump all output to file then exit
	if dump == True:
		unalloc, free = getData(db)
		for u in unalloc:
			sys.stdout.write(u)
		for f in free:
			sys.stdout.write(f)
		sys.exit(0)

	# Create all the signatures
	signatures = createSignatures(db)

	# If the user want to display a list of tables instead of carving data
	if len(findTables) == 1 and findTables[0] == "LIST" and checkAll == False:
		print "TABLES:"
		for k in signatures.keys():
			sys.stdout.write("\t" + k + "(")
			for i in range(0, len(signatures[k])):
				sys.stdout.write(signatures[k][i]["name"])
				if i < len(signatures[k]) -1:
					sys.stdout.write(", ")
			print ")"
		sys.exit(0)	# Exit afterwards, nothing to do


	# Delete signatures from tables we are not looking for
	if checkAll == False:
		for key in signatures.keys():
			# Exclude or include depending on the value of inverse
			if (key in findTables) == inverse:
				del signatures[key]
	
	# Get unallocated space
	unalloc, free = getData(db)

	# Find all possible tables in unallocated space
	structures = []
	for u in unalloc:
		res = findStructure(signatures, u)
		if res:
			structures.append(res)
	
	# Group the records together under one dictionary
	collection = collectItems(structures)

	# Remove records that have data that is unlikely to be correct
	collection = removeUnlikely(collection)

	# Print a list of everything that we found
	printTable(signatures, collection)
