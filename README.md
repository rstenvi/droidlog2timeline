droidlog2timeline
=================

This is a python script to generate a graphical timeline based on the
application logs on an Android device. This was created as proof-of-concept to
demonstrate the concept of having one script configured by XML files to gather
available logs on an Android device.

The timeline is displayed using [SIMILE Timeline](http://www.simile-widgets.org/timeline/).

Running the program
-------------------

Three arguments are most important, --path which is needed to find the path to
the application logs, /data/data/ on an Android device. --list must point to a
list of packages installed on the phone, found in /data/system/packages.list on
an Android device. You can also set the output directory (--output), this
directory will contain the html and JavaScript that is needed to generate the
timeline.

You can also set things like time information, logging and verbosity, see
./droidlog2timeline.py --help to get a full list.

Generating new configuration files
----------------------------------

All the configuration files are stored in "configs/". The name of each file is
the folder name of the program + .xml, like "com.android.browser.xml" which is
the configuration file for the browser. If a new version of the application
changes the database structure, we add a number after .xml, the second
configuration file for the browser is com.android.browser.xml.1. These will be
checked by the program in order, the first one that matches the database is
used.

When the program looks for configuration files it uses the first column in
packages.list, to create a new configuration file for a program, you need to
use this name, pluss '.xml'. This also means that the databases from the device
must be stored in the same directory structure as it had on the device.

Documentation
-------------

The ouput log from the program will say which databases the program has
gathered information from, which databases there are no configuration file for
and which databases there are a configuration file for, but it does not match
the format of the database.

Templates
---------

The templates folder is used as a basis for the graphical timeline. index.html,
js/ and css/ are copied to the output directory. If they already exist in the
output directory, they are not copied.

AUTHORS
-------

See file with authors.

LICENSE
-------

This program is released under a MIT license, some icons under templates have a
different license.
