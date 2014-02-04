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

import re, os

def getAllFilesReg(Dir, regexp="[a-z]+.[a-zA-Z0-9\.]+.xml[\.0-9]*"):
	ret = []
	dirFiles = os.listdir(Dir)
	reg = re.compile(regexp)
	for d in dirFiles:
		if reg.match(d):	ret.append(d)
	return ret

def unixToSystemPath(Path):
	paths = Path.split("/")
	ret = paths[0];
	for i in range(1, len(paths)):
		ret = os.path.join(ret, paths[i])
	return ret