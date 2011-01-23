CouchDB-FUSE
============

A FUSE interface to CouchDB.  See the [blog post][1] for more details.

[1]: http://www.jasondavies.com/blog/2008/11/25/edit-couchdb-attachments-directly-with-couchdb-fuse/

Requirements
------------

 * [Python FUSE bindings](http://fuse.sourceforge.net/)
 * [CouchDB-Python](http://code.google.com/p/couchdb-python/) 0.5 or greater

Installation
------------

Make sure the requirements above are installed, then run `python setup.py
install`.  You can also install the latest stable version from [PyPI][2] by
running `easy_install CouchDB-FUSE`.

[2]: http://pypi.python.org/pypi/CouchDB-FUSE

Usage
-----

    $ mkdir mnt
    $ couchmount http://localhost:5984/jasondavies/_design%2Flinks mnt/
    $ ls mnt/
    $ touch mnt/foo
    $ ls mnt/
    foo
    $ 

Use cases
---------

 * If you've read [My Couch or Yours? Shareable Apps Are The Future][3] by
   jchris, this is a great time-saver if you want to edit HTML, JavaScript, CSS
   or even image files directly using your favourite editor.
 * Uploading large numbers of files repetitively through Futon or even via a
   Python prompt becomes tedious very quickly: drag'n'drop or `cp *` is the way
   forward!

[3]: http://jchris.mfdz.com/code/2008/11/my_couch_or_yours__shareable_ap

Happy Couching!
