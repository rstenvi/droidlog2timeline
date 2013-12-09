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
- query: Same idea as type, only it is meant to be used on foreign keys and get
  the value that this key represent. An example is
  query="SELECT key,value FROM table". The key is what is returned from the
  original query, the value is the column in the new table which we will replace
  the key with. Both key and value are columns in the new table.

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
