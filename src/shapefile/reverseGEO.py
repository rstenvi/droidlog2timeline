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

# reverse geocoding based on longitude and latitude locations

import json, pprint, os

# determine if a point is inside a given polygon or not
# Polygon is a list of (x,y) pairs.
# Taken from http://www.ariel.com.au/a/python-point-int-poly.html
def point_inside_polygon(x,y,poly):
    n = len(poly)
    inside =False

    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x,p1y = p2x,p2y

    return inside

# Class to store the json files and check the name of a location.
# If the json files are structured appropriately, it uses a hiararchical
# structure. It can for example only read in one json file of continents, then
# read in countries and cities for the continents it finds.
class geoFiles:

	# Initalize the object with the base directory where all the files are kept
	# and an initial file in that directory where we can start searching for
	# places. Typically this is a list of countries or continents that points to
	# additional files that further describes a region in the first file.
	def __init__(self, Base, first):
		self.base = Base

		# this holds the first element we should check
		# next is a list of dictionaries with this and next as keys
		# This works as an n-tree
		self.start = {"this" : self.readFile(first), "next" : []}

		# List of previously found end feature, these are checked first to save
		# time. Most locations are probably in the same area, so this should be
		# faster in most cases. It is not sorted in any particular order.
		self.previous = {"features" : []}

		# The order of how we choose, highest number is what we prefer.
		self.order = {
			# Default value to return if we are unable to get key in the other
			# dictionary.
			"unknown" : 0,
			"country" : 1,
			"region" : 2,
			"county" : 3,
			"locality" : 4,
			"neighbourhood" : 5
		}

	# Get a list of polygons in a more suitable format
	def getPolygons(self, coord, Type="MultiPolygon"):
		if Type != "MultiPolygon":
			print Type + " is not supported"
			return []
		polygons = []
		for polygon in coord:
			poly = polygon[0]
			holes = []
			for i in range(1, len(polygon)):
				holes.append(polygon[i])
			polygons.append( {"polygon" : poly, "holes" : holes} )
		return polygons

	# Retrieves a dictionary of the features we are interested in
	def getFeature(self, feature):
		Type = feature.get("type", "")
		placeType = feature["properties"].get("place_type", "")
		Next = feature["properties"].get("next", None)
		name = feature["properties"].get("label", "")
		geometry = feature.get("geometry", {})
		gemType = geometry.get("type", "")
		bbox = geometry.get("bbox", [-180.0, -90.0, 180.0, 90.0])
		coordinates = geometry.get("coordinates", [])
		polygons = self.getPolygons(coordinates, gemType)
		ret = {"type" : Type, "place_type" : placeType, "next" : Next, "name" : name,
		"geometry" : {"type" : gemType, "bbox" : bbox, "polygons" :
		polygons} }
		return ret


	# Read in one file and return a dictionary with all the data we need
	def readFile(self, File):
		File = os.path.join(self.base, File)
		insert = {"file" : File}
		contents = {}
		try:
			f = open(File)
			contents = f.read()
		except IOError as e:
			print "Unable to find geolocation files ({0}): {1}".format(e.errno, e.strerror)
			return {}
		Json = json.loads(contents)

		insert["name"] = Json.get("name", "")
		insert["type"] = Json.get("type", "")
		insert["features"] = []

		for feature in Json["features"]:
			ins = self.getFeature(feature)
			insert["features"].append(ins)

		return insert

	# Checks to see if we have already read in a file, returns None if it has not
	# been read in
	def findSecond(self, File, Array):
		for l in Array:
			if l.get("this", {}).get("file", "") == File:
				return l
		return None
	
	# Check to see if a file exist in memory, if not read it in and return the
	# dictionary
	def readNext(self, File, Array):
		if File == None:
			return {"this" : None, "next" : []}
		place = self.findSecond(File, Array)
		if place == None:
			place = self.readFile(File)
			place = {"this" : place, "next" : []}
			Array.append( place )
		return place

	# Find all places where the coordinates might fit in
	def findCoordinate(self, x, y, places):
		rets = []
		for a in places.get("features", []):
			gem = a.get("geometry", {})
			polygons = gem.get("polygons", [])
			for poly in polygons:
				if point_inside_polygon(x, y, poly["polygon"]):
					if len(poly["holes"]) <= 0 or point_inside_polygon(x, y,\
					poly["holes"]) == False:
						rets.append(a)
						break	# Break out of inner-loop
		return rets

	# Find the place that we should use, based on self.order
	def findCorrectPlace(self, places):
		# If there is only 0 or 1 places, we can jsut return it
		if len(places) <= 1:
			return places

		# Get the maximum locality of all the places
		maxPlaceType = 0
		for place in places:
			place_type = self.order.get(place.get("place_type", "unknown"), 0)
			if place_type > maxPlaceType:
				maxPlaceType = place_type

		# Remove any places that has less locality than the max we found
		places = [x for x in places if not self.order.get(place.get("place_type", "unknown"), 0) < maxPlaceType ]
		return places


	# Do reverse geocoding on a set of coordinates to find the place. This
	# function will read in extra files if necessary. The label in the last
	# result is what is returned
	def reverseGeocode(self, longi, lat):

		# Look through previous first and see if we have seen that place before.
		# It only looks at the final place, not the chain, which might be more
		# effective.
		l = self.findCoordinate(longi, lat, self.previous)
		results = self.findCorrectPlace(l)
		if len(results) == 1:
			return results[0].get("name", "Unknown")

		# Not found in previous, need to go through entire chain
		place = self.start
		results = []
		previous = {}
		while place.get("this") != None:
			l = self.findCoordinate(longi, lat, place.get("this"))
			results = self.findCorrectPlace(l)
			if len(results) == 0:
				result = None
			elif len(results) == 1:
				result = results[0]
			else:
				# Some areas might overlap, we go one step deeper in and see if we
				# find a match longer in, the first match we find is assumed to be
				# correct. If this is the last step in, we take the previous
				# value we had, if any.

				# Set result to None if we don't find any matches
				result = None
				for res in results:
					place = self.readNext(res.get("next", None), place.get("next") )
					if place.get("this", None) != None:
						l = self.findCoordinate(longi, lat, place.get("this"))
						res2 = self.findCorrectPlace(l)

						# We found a single match, we assume this is good, and don't
						# try to find any more matches
						if len(res2) == 1:
							result = res2[0]
							break
			
			# Found no match or too many matches, we return the previous value we
			# had
			if result == None:
				self.previous["features"].append(previous)
				return previous.get("name", "Unknown")

			# We have found one match, set this as the previous value and see if we
			# can go deeper.
			previous = result
			place = self.readNext(result.get("next", None), place.get("next") )

		# Everything worked and we return the previous value, which is also the
		# current value.
		self.previous["features"].append(previous)
		return previous.get("name", "Unknown")

if __name__ == "__main__":
	print "Only import on this file"
