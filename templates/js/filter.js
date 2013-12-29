/*
filter.js
Handles all the filtering on the timeline in addition to moving between next and
previous event.

Based on the code from:
 https://code.google.com/p/simile-widgets/wiki/Timeline_multiple_filter_boxes
*/

// Center the timeline on the given date
function centerSimileAjax(date)	{
	tl.getBand(0).setCenterVisibleDate(Timeline.DateTime.parseGregorianDateTime(date));
}

var numOfFilters = 4;	// The number of filter boxes that is displayed

/*
Set up the table with two rows of input boxes, two rows of text and one row of
buttons
*/
function setupFilterHighlightControls(div, timeline, bandIndices, theme) {
	// Init Handler
	var handler = function(elmt, evt, target) {
		onKeyPress(timeline, bandIndices, table);
	};

	// Create Table
	var table = document.createElement("table");

	// First Row
	var tr = table.insertRow(0);
	var td = tr.insertCell(0);
	td.innerHTML = "Filters:";

	// Second Row
	tr = table.insertRow(1);
	tr.style.verticalAlign = "top";

	/* Create the text inputs for the filters and add eventListeners */
	for(var i=0; i<numOfFilters; i++) {
		td = tr.insertCell(i); 
		var input = document.createElement("input");
		input.type = "text";
		//SimileAjax.DOM.registerEvent(input, "keypress", handler);
		td.appendChild(input);
		input.id = "filter"+i;
	}

	// Third Row
	tr = table.insertRow(2);
	td = tr.insertCell(0);
	td.innerHTML = "Highlights:";

	// Fourth Row
	tr = table.insertRow(3);

	/* Create the text inputs for the highlights and add event listeners */
	for (var i = 0; i < theme.event.highlightColors.length; i++) {
		td = tr.insertCell(i);

		input = document.createElement("input");
		input.type = "text";
		SimileAjax.DOM.registerEvent(input, "keypress", handler);
		td.appendChild(input);

		input.id = "highlight"+i;

		var divColor = document.createElement("div");
		divColor.style.height = "0.5em";
		divColor.style.background = theme.event.highlightColors[i];
		td.appendChild(divColor);
	}

	// Fifth Row
	tr = table.insertRow(4);
	td = tr.insertCell(0);

	// create the filter button
	var filterButton = document.createElement("button");
	filterButton.innerHTML = "Filter";
	filterButton.id = "filter"
	filterButton.className = "buttons"
	SimileAjax.DOM.registerEvent(filterButton, "click", handler);
	td.appendChild(filterButton);

	// create the clear all button
	td = tr.insertCell(1);
	var highlightButton = document.createElement("button");
	highlightButton.innerHTML = "Clear All";
	highlightButton.id = "clearAll"
	highlightButton.className = "buttons"
	SimileAjax.DOM.registerEvent(highlightButton, "click", function() {
		clearAll(timeline, bandIndices, table);
	});
	td.appendChild(highlightButton);
	
	// Go to previous event
	td = tr.insertCell(2);
	var previousButton = document.createElement("button");
	previousButton.innerHTML = "Previous event";
	previousButton.id = "previous"
	previousButton.className = "buttons"
	SimileAjax.DOM.registerEvent(previousButton, "click", function() {
		goNextPrevious(false);
	});
	td.appendChild(previousButton);
	
	// Go to next event
	td = tr.insertCell(3);
	var nextButton = document.createElement("button");
	nextButton.innerHTML = "Next event";
	nextButton.id = "next"
	nextButton.className = "buttons"
	SimileAjax.DOM.registerEvent(nextButton, "click", function() {
		goNextPrevious(true);
	});
	td.appendChild(nextButton);

	// Append the table to the div
	div.appendChild(table);
}

var timerID = null;
var filterMatcherGlobal = null;
var highlightMatcherGlobal = null;

function onKeyPress(timeline, bandIndices, table) {
	if (timerID != null) {
		window.clearTimeout(timerID);
	}
	timerID = window.setTimeout(function() {
		performFiltering(timeline, bandIndices, table);
	}, 300);
}
function cleanString(s) {
	return s.replace(/^\s+/, '').replace(/\s+$/, '');
}

// Perform the actual filtering or highlighting
function performFiltering(timeline, bandIndices, table) {
	timerID = null;
	var tr = table.rows[1];

	// Add all filter inputs to a new array
	var filterInputs = new Array();
	for(var i=0; i<numOfFilters; i++) {
		filterInputs.push(cleanString(tr.cells[i].firstChild.value));
	}

	var filterMatcher = null;
	var filterRegExes = new Array();
	for(var i=0; i<filterInputs.length; i++) {
		/* if the filterInputs are not empty create a new regex for each one and
			add them to an array */
		if (filterInputs[i].length > 0){
			filterRegExes.push(new RegExp(filterInputs[i], "i"));
		}
		filterMatcher = function(evt) {
			/* iterate through the regex's and check them againstthe evtID
				if match return true, if not found return false */
			if(filterRegExes.length!=0)	{
				for(var j=0; j<filterRegExes.length; j++)	{
					// Uses the EventID attribute as filter instead of text
					if(filterRegExes[j].test(evt.getEventID()) == true)	{
						return true;
					}
				}
			}
			else if(filterRegExes.length==0)	{
				return true;
			}
			return false;
		};
	}

	var regexes = [];
	var hasHighlights = false;
	tr=table.rows[3];
	for (var x = 0; x < tr.cells.length; x++) {
		var input = tr.cells[x].firstChild;
		var text2 = cleanString(input.value);
		if (text2.length > 0) {
			hasHighlights = true;
			regexes.push(new RegExp(text2, "i"));
		}
		else	{
			regexes.push(null);
		}
	}
	var highlightMatcher = hasHighlights ? function(evt) {
		for (var x = 0; x < regexes.length; x++) {
			var regex = regexes[x];
			// Higlight is done on the
			if (regex != null && regex.test(evt.getEventID())) {
				return x;
			}
		}
		return -1;
	} : null;

	// Set the matchers and repaint the timeline
	filterMatcherGlobal = filterMatcher;
	highlightMatcherGlobal = highlightMatcher;
	for (var i = 0; i < bandIndices.length; i++) {
		var bandIndex = bandIndices[i];
		timeline.getBand(bandIndex).getEventPainter().setFilterMatcher(filterMatcher);
		timeline.getBand(bandIndex).getEventPainter().setHighlightMatcher(highlightMatcher);
	}
	timeline.paint();
}


function clearAll(timeline, bandIndices, table) {
	// First clear the filters
	var tr = table.rows[1];
	for (var x = 0; x < tr.cells.length; x++) {
		tr.cells[x].firstChild.value = "";
	}

	// Then clear the highlights
	var tr = table.rows[3];
	for (var x = 0; x < tr.cells.length; x++) {
		tr.cells[x].firstChild.value = "";
	}

	// Is used when moving
	filterMatcherGlobal = null;

	// Then re-init the filters and repaint the timeline
	for (var i = 0; i < bandIndices.length; i++) {
		var bandIndex = bandIndices[i];
		timeline.getBand(bandIndex).getEventPainter().setFilterMatcher(null);
		timeline.getBand(bandIndex).getEventPainter().setHighlightMatcher(null);
	}
	timeline.paint();
}

// Go to next or previous visible depending on "next"
function goNextPrevious(Next)	{
	// Get current date
	var center =  tl.getBand(0).getCenterVisibleDate();
	var now = Date.parse(center);
	
	// Get all the events and create an iterator
	var es = tl.getBand(0).getEventSource();
	var it = es.getAllEventIterator();
	var evt = it.next();

	var prev = now;	// In case there are no more events
	var date = now		// Initialize and create variable
	while(true)	{
		// Only look at events that are not filtered out
		if(filterMatcherGlobal == null || window["filterMatcherGlobal"](evt) == true)	{
			date = evt.getStart();	// Current event start time
			
			// Must be 10 second difference between placement and event we are
			// looking at
			if(Next == true && date > (now+10000))	{
				prev = date;
				break;
			}
			else if(Next == false && date >= (now-10000))
				break;
		}

		evt = it.next();	// Get next event
		prev = date;		// Set the previous value
		
		// Been through all the events
		if(evt == null)
			break;
	}
	var dt = new Date(prev);
	centerSimileAjax(dt.toUTCString());
}

