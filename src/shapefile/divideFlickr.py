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

# Divide the flickr geojson files into a structure more appropriate for us.

import json, pprint, sys, os

# Converts a string to valid file name
def getValidFileName(name):
	ret = name.lower()
	ret = ret.replace(" ", "_")
	ret = ret.replace(",", "-")
	ret = ret.encode("ascii", "ignore")
	return ret

def findStringFromList(string, List):
	rets = []
	for l in List:
		if string.endswith(l):
			return l
	return ""

def divideJson(Json, divisors=[], Split="NOSPLIT", useSplits=[], compress=True):
	ret = {}
	divisors.append("unknown")
	for div in divisors:
		if div not in ret:
			ret[div] = {
				"type" : Json.get("type", ""),
				"name" : Json.get("name", ""),
				"description" : Json.get("description", ""),
				"license" : Json.get("license", ""),
				"features" : []
			}
			if compress == True:
				if 'description' in ret[div]: del ret[div]['description']
	for feature in Json.get("features", []):
		if "properties" in feature and "label" in feature["properties"]:
			if compress == True:
				if "id" in feature:	del feature["id"]
				if "properties" in feature:
					if "woe_id" in feature["properties"]:
						del feature["properties"]["woe_id"]
					if "place_id" in feature["properties"]:
						del feature["properties"]["place_id"]
					if "place_type_id" in feature["properties"]:
						del feature["properties"]["place_type_id"]
				if "geometry" in feature:
					if "created" in feature["geometry"]:
						del feature["geometry"]["created"]
					if "alpha" in feature["geometry"]:
						del feature["geometry"]["alpha"]
					if "points" in feature["geometry"]:
						del feature["geometry"]["points"]
					if "edges" in feature["geometry"]:
						del feature["geometry"]["edges"]
					if "is_donuthole" in feature["geometry"]:
						del feature["geometry"]["is_donuthole"]
					if "link" in feature["geometry"]:
						del feature["geometry"]["link"]
			name = feature["properties"]["label"]
			label = getLabel(name, Split, useSplits)

			divisor = findStringFromList(label, divisors)
			if divisor != "":
				ret[divisor]["features"].append(feature)
			else:
				ret["unknown"]["features"].append(feature)
		else:
			print "Feature " + feature.get("id", "unknown") + " does not have correct format"
			sys.exit(0)
	return ret


def getLabel(name, Split, useSplits):
	name = name.split(Split)
	label = ""
	if len(name) == 1:
		label = name[0]
	else:
		for use in useSplits:
			if use >= len(name):
				# The flickr dataset seems to be missing this region on the county
				# dataset, we need to add it to not mess up the rest of the
				# divisions
				if name[0] == "Rotorua District":
					name.insert(1, "Bay of Plenty")
				else:
					return "".join(name)
			label += name[use]
	return label

def getLabels(Json, Split="NOSPLIT", useSplits=[]):
	labels = []
	for feature in Json.get("features", []):
		if "properties" in feature and "label" in feature["properties"]:
			tmp = feature["properties"]["label"]
			label = getLabel(tmp, Split, useSplits)
			labels.append(label)
	return labels

def addPaths(Json, append, Split="NOSPLIT", useSplits=[]):
	for feature in Json.get("features", []):
		if "properties" in feature:
			label = getLabel(feature["properties"].get("label", "unknown"), Split,\
			useSplits)
			feature["properties"]["next"] = getValidFileName(label) + "_" + append
		else:
			print "Proprties is non-existent in " + feature.get("id", "Unknown")
	return Json

# Print json to file
def printJson(Json, File, pretty=False):
	f = open(File, "w")
	if pretty == True:
		f.write(json.dumps(Json, sort_keys=True, indent=4, separators=(',', ':')))
	else:
		f.write(json.dumps(Json))

# Read in a file and return the result as JSON
def readFileAsJson(File):
	if os.path.isfile(File) == False:
		print str(File) + " doesn't exist, have you downlaoded the Flickr dataset"
		print "http://code.flickr.net/tag/shapefile/"
		print "Download version 2.0.1(important) and extract it in this directory"
		sys.exit(0)
	with open(File) as f:
		contents = f.read()
	try:
		Json = json.loads(contents)
	except ValueError, v:
		print "ValueError: ", v
		print "Make sure it is version 2.0.1 of the dataset"
		sys.exit(0)
	if type(Json) != dict:
		print File + " is not a valid Json file"
	return Json

# Make sure that all the links work as expected
def sanityCheck(File, Dir):
	realFile = os.path.join(Dir, File)
	if os.path.exists(realFile):
		Json = readFileAsJson(realFile)
		if "features" not in Json:
			print "File " + realFile + " is missing features"
			sys.exit(0)
		for feature in Json["features"]:
			if "properties" not in feature:
				print "File " + realFile + " is missing property key"
				sys.exit(0)
			if "next" in feature["properties"]:
				sanityCheck(feature["properties"]["next"], "sources")
	else:
		print "File " + realFile + " does not exist"
		sys.exit(0)


if __name__ == "__main__":
	# Read in all countries
	print "Reading in list of countries"
	countriesJson = readFileAsJson("flickr_shapes_countries.geojson")

	# Get all possible countries
	countries = getLabels(countriesJson)

	# Add a path to each specific country file that we haven't created yet
	countriesJson = addPaths(countriesJson, "regions.geojson")

	if os.path.isdir("sources") == False:
		os.mkdir("sources")

	# Write out new file of countries
	print "Writing new file with countries\n"
	printJson(countriesJson, os.path.join("sources", "countries.geojson"))

	# Read in all regions
	print "Reading in list of regions"
	regionsJson = readFileAsJson("flickr_shapes_regions.geojson")

	# Get a label, 0 is region, 2 is country, needed to filter
	regions = getLabels(regionsJson, ",", [0, 2])
	
	# Add a path to each county
	regionsJson = addPaths(regionsJson, "counties.geojson", ",", [0, 2])

	# Divide the regions based on the country
	regionsDivided = divideJson(regionsJson, countries)
	
	# Print out new region files
	count = 0
	for key in regionsDivided.keys():
		printJson(regionsDivided[key], os.path.join("sources", getValidFileName(key) +\
		"_regions.geojson"))
		count += 1
	print "Wrote " + str(count) + " new files with regions\n"

	print "Reading in list of counties"
	countiesJson = readFileAsJson("flickr_shapes_counties.geojson")

	countiesDivided = divideJson(countiesJson, regions, ",", [0,1,2])

	print "Reading in list of localities"
	localitiesJson = readFileAsJson("flickr_shapes_localities.geojson")
	localitiesDivided = divideJson(localitiesJson, regions, ",", [0,1,2])

	print "Reading in list of neighbourhoods"
	neighbourhoodsJson = readFileAsJson("flickr_shapes_neighbourhoods.geojson")
	neighbourhoodsDivided = divideJson(neighbourhoodsJson, regions, ",", [0,1,2,4])


	for key in localitiesDivided.keys():
		for feature in localitiesDivided[key].get("features", []):
			countiesDivided[key]["features"].append(feature)
		for feature in neighbourhoodsDivided.get("features", []):
			countiesDivided[key]["features"].append(feature)
	
	count = 0
	for key in countiesDivided.keys():
		printJson(countiesDivided[key], os.path.join("sources", getValidFileName(key) +\
		"_counties.geojson"))
		count += 1
	print "Wrote " + str(count) + " new files with counties\n"

	# Final sanity check to make sure it was printed correctly
	print "Running checks to see if everything is correct\n"
	sanityCheck("countries.geojson", "sources")

	print "New files written under 'sources, you can now delete the downloaded files"
