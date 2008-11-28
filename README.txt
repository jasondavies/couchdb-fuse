============
CouchDB-FUSE
============

Requirements
------------

 * CouchDB-Python version SVN-r125 or greater

Installation
------------

This *should* be as easy as:

  easy_install CouchDB-FUSE

Usage
-----

Currently you can mount a CouchDB document's attachments on a given mount-point
as follows:

  couchmount http://hostname:port/dbname/doc_id mount-point
