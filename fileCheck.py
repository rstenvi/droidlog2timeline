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

# Check if all the necessary files are present where they should be.

import os.path

def checkFileHierarchy(Path, Files):
	if os.path.isdir(Path) == False:
		return False
	
	# Keys in dictionaries are folders, list are files
	if type(Files) == list:
		for l in Files:
			if os.path.isfile(os.path.join(Path, l)) == False:
				return False
	elif type(Files) == dict:
		for k in Files.keys():
			if os.path.isdir(os.path.join(Path, k)) == False:
				return False
			elif checkFileHierarchy(os.path.join(Path, k), Files[k]) == False:
				return False
	else:
		return False
	return True

def checkLibrary(Path="libraries", jquery="jquery_1.10.2", simile="timeline_2.3.0"):
	Files = {
		jquery : ["jquery.js", "jquery-ui.css", "jquery-ui.js"],
		simile : {
			"timeline_ajax" : [],
			"timeline_js" : []
		}
	}
	return checkFileHierarchy(Path, Files)

def checkWebapp(Path="webapp"):
	Files = {
		"css" : ["datepicker.css", "main.css"],
		"images" : [],
		"js" : ["filter.js", "timeline.js"],
		"libraries" : {
			"jquery_1.10.2" : ["jquery.js", "jquery-ui.css", "jquery-ui.js"],
			"timeline_2.3.0" : {
				"timeline_ajax" : [],
				"timeline_js" : []
			}
		}
	}
	return checkFileHierarchy(Path, Files)

if __name__== '__main__':
	print "Webapp = " + str(checkWebapp())
	print "Library = " + str(checkLibrary())
