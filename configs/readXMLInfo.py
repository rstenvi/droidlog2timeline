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

import sys, time, csv, os, re
import argparse

try:
	from lxml import etree as ET
except ImportError:
	print "Unable to import lxml, install with easy_install lxml"
	sys.exit(0)

# Read all the XML files into our own list of dictionaries
def readXMLs(files):
	ret = []
	for File in files:
		ins = {"name" : File}
		ins2 = {}
		f = open(File, "r")
		tree = ET.parse(f)
		root = tree.getroot()
		info = root.find("information")
		if info == None:
			ins["info"] = None
		else:
			for c in info.iterchildren("*"):
				if c.tag == "description":
					ins2["description"] = c.text.replace("\n", " ").strip()
				elif c.tag == "tested":
					devices = []
					for d in c.iterchildren("device"):
						devices.append({"os" : d.get("os"), "device" : d.get("device")})
					ins2["tested"] = devices
				elif c.tag == "short":
					ins2["short"] = c.text
				elif c.tag == "extra":
					tables = []
					for t in c.iterchildren("table"):
						tableE = {"id" : t.get("id"), "columns" : t.get("columns"),\
						"reason" : t.get("reason")}
						if tableE["columns"] != None:
							tableE["columns"] = tableE["columns"].split(";")
						else:
							tableE["columns"] = []
						tables.append(tableE)
					ins2["extra"] = tables
			ins["info"] = ins2
		ret.append(ins)
	return ret

# Print information about one program
def printOne(info, show):
	print info["name"]
	if "short" in show:
		sys.stdout.write("\tShort: ")
		if "short" in info["info"]:
			print info["info"]["short"]
		else:
			print "Unavailable"
	if "description" in show:
		sys.stdout.write("\tDescription: ")
		if "description" in info["info"]:
			print info["info"]["description"]
		else:
			print "Unavailable"
	if "tested" in show:
		print "\tTested against:"
		if "tested" in info["info"]:
			for d in info["info"]["tested"]:
				print "\t\tOS: " + d["os"] + "  Device: " + d["device"]
		else:
			print "\t\tUnavailable"
	if "extra" in show and "extra" in info["info"]:
		print "\tExtra tables that might be of interest"
		for l in info["info"]["extra"]:
			sys.stdout.write("\t\tTable: " + str(l["id"]))
			sys.stdout.write(" (")
			for i in range(0, len(l["columns"])):
				sys.stdout.write(l["columns"][i])
				if i < len(l["columns"])-1:
					sys.stdout.write(", ")
			print ")"
			print "\t\t\tReason not included: " + str(l["reason"])
	print ""

# Print everything that shouldn't be filtered out
def printEverything(infoList, show, device, os, program, match, missing):
	for info in infoList:
		if info["info"] == None:
			if missing == True and (program in info["name"]) == match["program"]:
				print info["name"]
				print "\tNo information available"
		elif "name" in info and (program in info["name"]) == match["program"]:
			if "tested" in info["info"]:
				display = 0
				for d in info["info"]["tested"]:
					if (device in d["device"].lower()) == match["device"]\
					and (os in d["os"].lower()) == match["version"]:
						display += 1
				if (match["device"] and match["version"] and display > 0) or\
				( display == len(info["info"]["tested"]) ):
					printOne(info, show)
			else:
				if (device == "" and match["device"] == True)\
				and (os == "" and match["version"] == True):
					printOne(info, show)

if __name__== '__main__':
	# All available options for what to show
	showOptions = ["short", "description", "tested", "extra", "all"]

	# Which options should be inversed
	notInverse = {"program" : True, "device" : True, "version" : True}

	# Add the parser object
	parser = argparse.ArgumentParser(description='Read info about configuration files',
	formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	
	# Which information to display
	parser.add_argument('-s', '--show', dest='show', type=str,\
	choices=showOptions, nargs='+', default=["all"],\
	help='Display all available info (overrides everything else)')

	# Add filter for which devices to display from
	parser.add_argument('-d', '--device', dest='device', default="", type=str,\
	help='Display information about configuration files the device has been tested against')

	# Add filter for which versions to display from
	parser.add_argument('-v', '--version', dest='version', default="",
	type=str, help='Display information about a specific OS version number')
	
	# Add filter for which programs to display from
	parser.add_argument('-p', '--program', dest='program', default="",
	type=str, help='Display information about specific program match')

	# Inverse the filter from program, device or version
	parser.add_argument('-i', '--inverse', dest='inverse', type=str,\
	nargs='+', choices=["program", "device", "version"], default=[],\
	help="Inverse program, device or version match")

	# Print out the name where information is missing
	parser.add_argument('-m', '--missing', dest='missing', action='store_true',\
	help="Print those without information")

	# Parse alle the arguments, will exit if there is an error
	args = vars(parser.parse_args())

	# Get script path, should hold all the available XML files
	scriptPath = os.path.dirname(os.path.realpath(__file__))
	
	# Include common functions
	sys.path.insert(0, '../src/droidlog')
	import droidlog

	# Get a list of all configuration files
	Files = droidlog.getAllFilesReg(scriptPath)

	# Read in all the information
	infoList = readXMLs(Files)

	# Check if we should inverse any of the filters
	for key in notInverse.keys():
		if key in args["inverse"]:
			notInverse[key] = False

	# If the user had "all" in show we make it the entire list
	show = args["show"]
	if "all" in show:
		show = showOptions
	
	# Print what the user has chosen
	printEverything(infoList, show, args["device"].lower(),\
	args["version"].lower(), args["program"], notInverse, args["missing"])

