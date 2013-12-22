droidlog2timeline
=================

This is a python script to generate a graphical timeline based on the
application logs on an Android device. This was created as proof-of-concept to
demonstrate the concept of having one script configured by XML files to gather
available logs on an Android device.

Android is in constant change, and many users have older Android versions.
Different users also have different applications installed. We wanted to create
a program that can handle this kind of environment without having to constantly
change the soure code.

The timeline is displayed using [SIMILE Timeline](http://www.simile-widgets.org/timeline/).

This is now under development and a release will be coming soon.

Using the program
-------------------

The Android logs first have to be retrieved in some way. The program only uses
data from "/data/data/" on the device. If you retrieve an image you have to
mount it first. A list of all programs that the program should gather logs from
must also be passed to the program, ls /data/data/ > packages.list will work.

The full list of possible flags are shown below:

    usage: droidlog2timeline.py [-h] [-p PATH] [-c CONFIG] [-l LIST] [-s SKEW]
                                [-e EARLIESTDATE] [-d LATESTDATE] [-t TIMEZONE]
                                [-o OUTPUT] [-L LOG] [-v] [-a] [-H] [-C] [-D]

    droidlog2timeline - Create timeline for Android

    optional arguments:
      -h, --help            show this help message and exit
      -p PATH, --path PATH  Path to the /data/data/ directory in Android (default:
                            /mnt/data/data/)
      -c CONFIG, --config CONFIG
                            Path to XML configuration files (default: configs)
      -l LIST, --list LIST  Full path to list of packages on the phone (default:
                            packages.list)
      -s SKEW, --skew SKEW  Number of seconds to skew the clock (default: 0)
      -e EARLIESTDATE, --earliestdate EARLIESTDATE
                            Earliest date to record (yyyy-mm-ddThh:mm) (default:
                            None)
      -d LATESTDATE, --latestdate LATESTDATE
                            Latest date to record (yyyy-mm-ddThh:mm) (default:
                            None)
      -t TIMEZONE, --timezone TIMEZONE
                            Timezone of the phone (GMT+XXXX) (default: GMT+0000)
      -o OUTPUT, --output OUTPUT
                            Output directory (default: output/)
      -L LOG, --log LOG     Logfile of what has been done (default: droidlog.log)
      -v, --verbose         Verbose output (default: False)
      -a, --logcat          Use LogCat files instead of sqlite databases (default:
                            False)
      -H, --hashcheck       Check that the files are not modified after
                            interaction with them, exits if they don't match
                            (default: False)
      -C, --carve           Carve for information in unallocated space (default:
                            False)
      -D, --disallow-override
                            Disallow override of attribute names (default: False)

Description of each flag:
- path Must point to a directory that that looks like /data/data/ on an Android
  device.
- config Directory to find all the XML configuration files. Don't use this
  unless you have a separate directory with configuration files.
- list Packages installed on the phone, or more clearly a list of directories in
  "path". ls "path" > packages.list will produce the correct result.
- skew Set a skew on the clock, this is a constant clock skew and it will not
  handle a clock that has been skewed more and more over time.
- earliestdate Set the earliest date for when to create a timeline for. Format
  is yyyy-mm-ddThh:mm. This can be useful if the timeline is unresponsive when
  navigating it.
- latestdate Same as the previous, just the latest date.
- timezone Set the timezone that the phone is in, Format is: GMT+XXXX.
- output Set a different output directory, default is "output/" in the working
  directory.
- log Set a different log file, default is droidlog.log. This log file contains
  information about what has been done, which databases has been used and what
  type of queries has been run against each database.
- verbose Say what is going on while it happens, by default nothing is printed.
- logcat Create timeline from LogCat logs instead of databases. Path must now
  point to a directory containing three files, "radio.log", "main.log" and
  "events.log". As far as we can see, these logs are hard to interpret and
  doesn't provide that useful results.
- hashcheck Calculate a hash value for the files before and after we have
  interacted with them. This was mostly implemented so that we could be sure
  that we didn't modify the files.
- carve Carve for rows in unallocated space. This function tries to reconstruct
  deleted rows, the row is not used if we don't reconstruct a timestamp.
- disallow-override The XML-files can specify a new value descriptor to describe
  each value, this makes it easier to analyse, but then you don't know which
  attribute a value belongs to. This option will disable this feature.

The end result is an XML file that can be read by SIMILE Timeline. This can be
viewed in a browser. Either just open index.html in output in a browser or
create a local web server with Python:

    python -m SimpleHTTPServer

Then go to localhost:8000/output/ The first method doesn't work in all browsers,
the second does.

If this timeline is unresponsive, you probably have too many events. Try
limiting the number of events by setting an earliest date.

Changing or generating new configuration files
----------------------------------

The configuration files is the main part of the program, these files say what
kind of information to retrieve and how to display that information.
They are stored under "configs/". The name of each file is
the folder name of the program + .xml, like "com.android.browser.xml" which is
the configuration file for the browser. If a new version of the application
changes the database structure, we add a number after .xml, the second
configuration file for the browser is com.android.browser.xml.1. These will be
checked by the program in order, the first one that matches the database is
used.

It is because of this structure that the databases must be stored in the same
hierarchy as it was on the device. When the program is looking for an XML file,
it uses the name in "list".

See separate README file under configs directory.

Logging
-------------

The ouput log from the program will say which databases the program has
gathered information from, which databases there are no configuration file for
and which databases there are a configuration file for, but it does not match
the format of the database.


Templates
---------

The templates folder is used as a basis for the graphical timeline. index.html,
js/, images/ and css/ are copied to the output directory. If they already exist in the
output directory, they are not copied.

Future work
-----------

See TODO list for what is planned in the future. If you find a bug or want a
feature that is not mentioned in the TODO list, create an issue.

AUTHORS
-------

See file with authors.

LICENSE
-------

This program is released under the MIT license, some icons under templates have a
different license.
