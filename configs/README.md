How to create configuration file
================================

This document is intended to describe how the XML-files must be generated, so
they can be read in and used by the script.

Basic format
------------
    <root>
      <database id="path/to/db.db">
        <table id="table>
         <column id="SIMILE keyword">column</column>
         <icon desc="Description of image">image.png</icon>
         <where>column != NULL and column2 != 0</where>
         <filter columns="column1;column2" static="text" />
        </table>
      </database>
    </root>

This is the basic format of the file, but the values have a meaning.

By SIMILE keywords we mean the attributes listed
[here](http://simile-widgets.org/wiki/Timeline_EventSources). Many of the
attributes have not been tested. A simple grep on all the configuration files
will reveal if it has been tested or not, and hence the likelihood that there is
a bug in our program with that attribute.

The text in the icon must point to an image under templates/images, but not the
full path, just the file name.

The text in the column must point to a valid column in the SQLite database.
There can be arbitrary many columns and they can have the same SIMILE keyword.

The text in the where tag will be directly appended after "WHERE "

The table id attribute must be a valid table id the database.

The database id attribute must be the path to the database after what is
"/data/data/com.some.name/" on Android.

There can be arbitrary many databases, tables and columns. Icon and where can be
omitted.

The filter tag is used to be able to perform better filtering of the output. The
static attribute will place the text directly into the event. The columns
attribute will take the result of the SQL query and the those columns.

Extra stuff
-----------

There are some extra keywords that might be used, the following is extra
attributes for the column tag.

- type: Replace the value returned by some other value. "1:Incoming;2:Outgoing"
  will replace 1 with incoming and 2 with outgoing. Format is
  "QueryResult:ReplaceValue;..."
- divide: When there is a timestamp, the default granularity of the timestamp is
  milliseconds since UNIX epoch time, we have also seen some that have seconds
  since UNIX epoch time, divide="1" will handle those kind of scenarios.
- append: Intended to be used to describe the value returned, for example to
  explain the integer returned when displaying the length of a phone call.
  Format is append="text".
- override: By default the description for each value is the name of the column
  in the database. To make analysis easier, this can be overridden here. Format
  is override="text".
- default: Text to show when there is no result. Default is "None".
- query: Same idea as type, only it can run a new query. There are two types of
  queries, "key" and "direct":
  - key: Default option and is meant to retrieve a value based on primary key
	 and foreign key. Used like this: query="SELECT key,value FROM table" "key"
	 is the value we are filtering with, probably primary key in table you are
	 gathering data from and value is what we replace the result with.
  - direct: Direct queries have the format: "direct|SELECT val1,val2 FROM table WHERE
	 id = ?". "direct|" just specifies what type of query this is, you can also
	 specify "key|" for the default option. The question mark will be replaced
	 with the result and all the columns and results from the query will be
	 included. This has to be executed for each event, so it will take longer
	 time than "key". The "key" query will only be executed once.
- filetype: Determines what type of data is stored in that column, the following
  values are supported:
  - json: Must be accompanied with with select="key1;key2;..;"
  - path: The value is a path to a file that can be displayed on the timeline.
- logfile: All the values in this attribute will be printed to the filename.
  This can be useful for some values like, URL, phone numbers etc.

The columns that contain a timestamp are different and can not translated the
same way, the only extra attribute is the "divide" attribute. That is also the
only attribute that makes sense.

Extra tags

- insert: Insert ekstra text, mostly to make filtering easier. Format is:
  ```<insert id="SIMILE keyword">text</insert>```
  If you use the same SIMILE keyword in a column, that will overwrite this

Formatting information

- Regular expression: We have come across one database that doesn't have a fixed
  name, but instead it consist of a user ID. For these kind of scenarios we
  support regular expression for the database id attribute. Both path and DB
  name can be a regular expression, but it must be enclosed in {{...}}. The path
  and DB name should be in it's own regular expression. This is because the
  program will only look in directory to find a match.
- Duplicate databases: When two or more databases have the same format, as far
  as the information the xml file gathers, the "and" keyword can be used. The
  filenames must be enclosed in "[[" and "]]" and each file must be separated by
  " and ". This should be used the same way as regular expression, inside one
  directory. It can only be used once and not inside or before regular
  expression, but each name separated by " and " can contain a regular
  expression. Media files is an example where this is used, internal and
  external storage have similar databases and the same XML-config can be used
  for both.

Information about file
----------------------

Information about the file itself is also stored in the XML file. This is stored
under the information tag under the root tag.

    <information>
     <short>Short description of program</short>
     <tested>
      <device os="Android x.x" device="physical device name/emulator"/>
     </tested>
     <description>Longer description of what is expected output using this file</description>
     <extra>
      <table id="tableName" columns="column1;column2"
       reason="Reason for not using this data" />
     </extra>
    </information>

In some databases there is extra information that we don't know if it is really
useful or we don't know the format of it, this can be marked in the extra tag.
This should be seen as future work.

readXMLInfo.py
--------------

This script can be used to check which devices and operating systems each file
has been tested against. It uses the information under the "information" tag in
each XML file.

    $ ./readXMLInfo.py -h

    usage: readXMLInfo.py [-h]
                      [-s {short,description,tested,all} [{short,description,tested,all} ...]]
                      [-d DEVICE] [-v VERSION] [-i] [-m]

    Read info about configuration files

    optional arguments:
      -h, --help            show this help message and exit
      -s {short,description,tested,extra,all} [{short,description,tested,extra,all} ...], --show
         {short,description,tested,extra,all} [{short,description,tested,extra,all} ...]
                            Display all available info (overrides everything else)
                            (default: ['all'])
      -d DEVICE, --device DEVICE
                            Display information about configuration files the
                            device has been tested against (default: )
      -v VERSION, --version VERSION
                            Display information about a specific OS version number
                            (default: )
      -p PROGRAM, --program PROGRAM
                            Display information about specific program match
                            (default: )
      -i {program,device,version} [{program,device,version} ...], --inverse
         {program,device,version} [{program,device,version} ...]
                            Inverse program, device or version match (default: [])
      -m, --missing         Print those without information (default: False)


Using no option will print all available information that exist, "-m" can be
used to also include programs where information is unavailable. "-s" decides how
much information to display, possible values are: short, description, tested,
extra and all, which displays everything. The name of the XML file is always
printed.

To only print information about specific programs, devices or versions,
use "-p", "-d" or "-v", the program will try to find that text in the corresponding
attribute in the XML file. "-d Galaxy" for example will print information for
any version of the Galaxy devices. "-i" can be used to reverse the match, for
example to find all files where that device has not been tested.
