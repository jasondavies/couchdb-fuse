CouchDB-FUSE
============

A FUSE interface to CouchDB.

Requirements
------------

 * A system FUSE implementation such as libfuse or macFUSE
 * Python 3.10 or greater

Installation
------------

Install it from a checkout with:

    python3 -m pip install .

This also installs the Python dependencies,
[`fuse-python`](https://pypi.org/project/fuse-python/) and
[CouchDB-Python](https://couchdb-python.readthedocs.io/en/latest/).

You can also install the published package from [PyPI][2]:

    python3 -m pip install CouchDB-FUSE

[2]: https://pypi.org/project/CouchDB-FUSE/

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

[3]: https://web.archive.org/web/20090107050156/http://jchris.mfdz.com/code/2008/11/my_couch_or_yours__shareable_ap

Happy Couching!
