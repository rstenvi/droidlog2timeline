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

import sys, os
import shutil	# To copy files
import requests	# To download files
import zipfile		# To unzip SIMILE library

def downloadFile(url, name):
	print "Downloading: " + str(url)
	f = requests.get(url)
	if f.status_code == requests.codes.ok:
		File = open(name, "wb")
		File.write(f.content)
	else:
		f.raise_for_status()

def unzipFile(File, path):
	print "Unzipping " + File
	zFile = zipfile.ZipFile(File)
	for name in zFile.namelist():
		(dirname, filename) = os.path.split(name)
		if filename == "":
			# Directory
			if not os.path.exists(os.path.join(path, dirname)):
				os.mkdir(os.path.join(path, dirname))
		else:
			# Regular file
			fd = open(os.path.join(path, name), "wb")
			fd.write(zFile.read(name))
			fd.close()
	zFile.close()

def downloadAll(mainFolder):
	prefixJQ = os.path.join(mainFolder, "jquery_1.10.2")

	downloads = [
		{"url" : "http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.js",
		"path" : os.path.join(prefixJQ, "jquery.js")},
		{"url" : "http://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.js",
		"path" : os.path.join(prefixJQ, "jquery-ui.js")},
		{"url" : "http://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/themes/ui-lightness/jquery-ui.css",
		"path" : os.path.join(prefixJQ, "jquery-ui.css")}
	]

	Simile = "https://simile-widgets.googlecode.com/files/timeline_libraries_v2.3.0.zip"
	simileTmp = ".simile-tmp.zip"
	
	# Create necessary directories for jquery
	if not os.path.exists(prefixJQ):
		os.makedirs(prefixJQ)

	for d in downloads:
		downloadFile(d["url"], d["path"])

	downloadFile(Simile, simileTmp)
	unzipFile(simileTmp, mainFolder)

	os.remove(simileTmp)

if __name__== '__main__':
	downloadAll("libraries")
