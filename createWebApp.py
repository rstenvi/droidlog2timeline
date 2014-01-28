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

# Create the basis for a web application
def createWebApp(output, libraries, template):
	if not os.path.exists(output):
		os.mkdir(output)

	if os.path.exists(libraries):
		shutil.copytree(libraries, os.path.join(output, "libraries"))
	else:
		print libraries + " doesn't exist, need to download first"
		sys.exit(0)

	if os.path.exists(template):
		shutil.copytree(os.path.join(template, "css"), os.path.join(output, "css"))
		shutil.copytree(os.path.join(template, "js"), os.path.join(output, "js"))
		shutil.copytree(os.path.join(template, "images"), os.path.join(output, "images"))
		shutil.copy2(os.path.join(template, "listoutputs.html"), os.path.join(output, "index.html"))
	else:
		print template + " doesn't exist"
		sys.exit(0)


if __name__== '__main__':
	createWebApp("webapp", "libraries", "templates")
	print "Created web application directory in " + output
