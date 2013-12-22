SQLiteCarver.py
===============

This is a Python script that can be used to carve files from a SQLite database.
It can be used as a standalone tool and in scripts. Was created to support
droidlog2timeline, but can be used against any SQLite database.

The goal is to reconstruct the original data and find out which data belongs to
which attributes.

How to use the tool
-------------------
    $ ./SQLiteCarver.py -h
    usage: SQLiteCarver.py [-h] [-p PATH] [-t TABLES [TABLES ...]] [-a]

    Carver for SQLite databases

    optional arguments:
        -h, --help            show this help message and exit
        -p PATH, --path PATH  Path to the database that should be carved (default:
                              None)
        -t TABLES [TABLES ...], --tables TABLES [TABLES ...]
                              List of tables that should be searched for (default:
                              ['LIST'])
        -o OUTPUT, --output OUTPUT
                              Which file to write results to (default: None)
        -i, --inverse         Exclude -t instead of include (default: False)
        -a, --all             Search all tables, ignores -t (default: False)
        -d, --dump-unallocated
                              Dump all unallocated space (binary) (default: False)

Chosing one or more tables to search after gives better accuracy. Especially
when there are tables that have just a few attributes. In those cases we are
likely to find many possible matches, but most are probably wrong.

The result is printed to screen or to file if that is choosen.

-d produces a dump of all unallocated space. This way you can search for strings
and exclude all the allocated rows. This can be useful if you don't really care
about the complete row, but just want to find an URL for example.

If neither -a or -t is set, the program will print out all the tables and their
attribute names.

How the SQLite database looks like
----------------------------------

A good description og the SQLite DB file format can be found
[here](https://www.sqlite.org/fileformat2.html). I will briefly go over what is
important for carving.

The file is layed out in pages, each page can be 2^N bytes long. How long each
page is, is found in the first page, which is the header page. The first 100
bytes of the header page contains quite a lot of other information as well, I
will not repeat that here.

The first byte of each page says what kind of page it is. Leaf page (byte 0x0D)
contains actual data, meaning the rows that the user sees. This does not include
indexes, which are stored in a different type of page. When I say page further
down I mean leaf page.

The first 8 byte of each page contains information about the page, page type as
mentioned earlier is the first, then we have some information about what is
allocated and unallocated space. Then we have 2 bytes for each cell or record in
this page.

SQLite tries to place all the data towards the
end of the page, so unallocated data is located right after the header and until
the first allocated byte. Extra bytes in between the allocated bytes can also be
found in a free list, this is referred to in the header as a free list.

Rows in the file is implemented as a cell with a header and a body. The header
is a series of variable length integers (varint). A variable length integer is just an
integer that can represent a number of 64 bits using 1 to 9 bytes. It uses less
space on low numbers. The first varint in the header is the number of bytes in
the cell (including overflow), the second is the number of bytes in the header
(including the current one). Then N varints follows, where N is the number of
attributes in the table that the row belongs to. Each one of the varints says
how many bytes is in the body for that attribute and what type of attribute it
is, text int etc. The order is the same as when the table was created. Before
the header in the cell we also have a varint with the entire size of the cell
and a varint for the row ID.

The byte streams in the body must be interpreted based on the type the attribute
is. The different types is basically blob, text, int and float. The numbers are
represented as big-endian numbers.

How carving is implemented
--------------------------

The program first get a list of all tables and their attribute types and names.
The SQLite library is used for this. This was done because it is assumed that
the file is valid and usable. Based on this we create a signature for all the
attributes and what we expect to see in the header. For text as an example, we
expect to see an odd number larger than or equal to 13. Each table will contain
N signatures, where N is the number of attributes in the table.

Then the program finds all unallocated and free memory. Based on the signatures
calculated earlier, it looks for a header that matches any of the signatures we
calculated. If it finds a match in the header and signature, it will look for a
body that matches that header. When matching a body with a header, we only
look if it's theoretically possible, meaning that we don't take the attribute
type and exepcted value into account. This is something that can and should be
done later.

After we have found "all" possible deleted rows, we start filtering out what
cannot be correct. For now this is just, looking at non-printable values in what
is supposed to be text fields. Experiments have shown that this yields fairly
decent results.

