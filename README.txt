============
CouchDB-FUSE
============

Usage
-----

Currently you can mount a CouchDB server on a given mount-point as follows:

  python couchdbfuse.py [http://hostname:port/] mount-point

If [http://hostname:port/] is omitted, `http://localhost:5984/' is used.

File system layout
------------------

CouchDB-FUSE then sets up a file system layout looking like this:

mount-point/
    db1
        _all_docs/
            id1
            id2
            ...
        _design/
            designdoc1/
                _attachments/
                    attachment1.html
                    ...
                views/
                    view1/
                        map
                        reduce
                    ...
                ...
        _view/
            designdoc1/
                view1/
                    key1
                    key2
                    ...
    ...

Caveats
-------

At the moment keys returned by views aren't escaped so complex keys don't work.
I'm not sure how useful being able to query views is, so this might be removed.

TODO
----

 * Write support!
