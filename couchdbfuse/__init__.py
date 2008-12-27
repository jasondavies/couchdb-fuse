#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jason Davies
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.


from couchdb import Database, Document, ResourceNotFound, Row, Server, \
    ViewResults
import errno
import fuse
import os
import stat
import sys
from time import time
try:
    import simplejson as json
except ImportError:
    import json # Python 2.6
from urllib import quote, unquote

fuse.fuse_python_api = (0, 2)

class CouchStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 4096
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class CouchFSDocument(fuse.Fuse):
    def __init__(self, mountpoint, uri=None, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)
        db_uri, doc_id = uri.rsplit('/', 1)
        self.doc_id = unquote(doc_id)
        self.db = Database(db_uri)

    def get_dirs(self):
        dirs = {}
        attachments = self.db[self.doc_id].get('_attachments', {}).keys()
        for att in attachments:
            parents = [u'']
            for name in att.split('/'):
                dirs.setdefault(u'/'.join(parents[1:]), set()).add(name)
                parents.append(name)
        return dirs

    def readdir(self, path, offset):
        for r in '.', '..':
            yield fuse.Direntry(r)
        for dirname in self.get_dirs().get(path[1:], []):
            yield fuse.Direntry(dirname.encode('utf-8'))

    def getattr(self, path):
        try:
            st = CouchStat()
            if path == '/' or path[1:] in self.get_dirs().keys():
                st.st_mode = stat.S_IFDIR | 0775
                st.st_nlink = 2
            else:
                att = self.db[self.doc_id].get('_attachments', {})
                data = att[path[1:]]
                st.st_mode = stat.S_IFREG | 0664
                st.st_nlink = 1
                st.st_size = data['length']
            return st
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT

    def open(self, path, flags):
        try:
            #data = self.db.get_attachment(self.db[self.doc_id], path.split('/')[-1])
            #att = self.db[self.doc_id].get('_attachments', {})
            #data = att[path.split('/')[-1]]
            dirname, filename = path.rsplit('/', 1)
            if filename in self.get_dirs()[dirname[1:]]:
                return 0
            return -errno.ENOENT
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT
        #accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        #if (flags & accmode) != os.O_RDONLY:
        #    return -errno.EACCES

    def read(self, path, size, offset):
        try:
            data = self.db.get_attachment(self.db[self.doc_id], path[1:])
            slen = len(data)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = data[offset:offset+size]
            else:
                buf = ''
            return buf
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT

    def write(self, path, buf, offset):
        try:
            data = self.db.get_attachment(self.db[self.doc_id], path[1:])
            data = data[0:offset] + buf + data[offset+len(buf):]
            self.db.put_attachment(self.db[self.doc_id], data, filename=path[1:])
            return len(buf)
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT

    def mknod(self, path, mode, dev):
        name = path[1:]
        self.db.put_attachment(self.db[self.doc_id], u'', filename=name)
        return 0

    def unlink(self, path):
        name = path[1:]
        self.db.delete_attachment(self.db[self.doc_id], name)
        return 0

    def truncate(self, path, size):
        name = path[1:]
        self.db.put_attachment(self.db[self.doc_id], u'', filename=name)
        return 0

    def utime(self, path, times):
        return 0

    def mkdir(self, path, mode):
        self.db.put_attachment(self.db[self.doc_id], u'', filename=u'%s/%s' % (path[1:], u'.couchdb-fuse-placeholder'))
        return 0

    def rmdir(self, path):
        for filename in self.get_dirs().get(path[1:]):
            self.db.delete_attachment(self.db[self.doc_id], u'%s/%s' % (path[1:], filename))
        return 0

    def rename(self, pathfrom, pathto):
        return 0

    def fsync(self, path, isfsyncfile):
        return 0

    def statfs(self):
        """
        Should return a tuple with the following 6 elements:
            - blocksize - size of file blocks, in bytes
            - totalblocks - total number of blocks in the filesystem
            - freeblocks - number of free blocks
            - availblocks - number of blocks available to non-superuser
            - totalfiles - total number of file inodes
            - freefiles - nunber of free file inodes
    
        Feel free to set any of the above values to 0, which tells
        the kernel that the info is not available.
        """
        st = fuse.StatVfs()
        block_size = 1024
        blocks = 1024 * 1024
        blocks_free = blocks
        blocks_avail = blocks_free
        files = 0
        files_free = 0
        st.f_bsize = block_size
        st.f_frsize = block_size
        st.f_blocks = blocks
        st.f_bfree = blocks_free
        st.f_bavail = blocks_avail
        st.f_files = files
        st.f_ffree = files_free
        return st


class CouchFS(fuse.Fuse):
    """FUSE interface to a CouchDB database."""

    def __init__(self, mountpoint, uri=None, *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)
        self.fuse_args.mountpoint = mountpoint
        if uri is not None:
            self.server = Server(uri)
        else:
            self.server = Server()

    def getcouchattrs(self, path):
        attr = self.server
        attrs = [attr]
        parts = [x for x in path[1:].split('/') if x != '']
        i = 0
        for part in parts:
            if isinstance(attr, Database):
                if part == '_view':
                    attr = attr.view('_all_docs')['_design/':'_design/ZZZ']
                    attr.is_view = True
                elif part == '_all_docs':
                    attr = attr.view('_all_docs')
            elif isinstance(attr, ViewResults):
                if getattr(attr, 'is_view', False):
                    attr = list(attr['_design/'+part])[0]
                    attr.is_view = True
                else:
                    if attr.view.name != '_all_docs':
                        part = json.loads(unquote(part))
                    results = list(attr.view()[part])
                    if len(results) == 1:
                        attr = results[0]
                    else:
                        attr = attr.view()[part+'/':part+'/ZZZ']
                        if i + 1 < len(parts):
                            parts[i+1] = '%s/%s' % (part, parts[i+1])
            elif isinstance(attr, Row):
                if getattr(attr, 'is_view', False):
                    db = self.server[parts[0]]
                    attr = db.view('_view/' + '/'.join(parts[i-1:i+1]), group=True)
                elif part == 'value':
                    attr = attr.value
            else:
                attr = attr[part]
            attrs.append(attr)
            i += 1
        return attrs

    def getattr(self, path):
        try:
            st = CouchStat()
            attr = self.getcouchattrs(path)[-1]
            if (isinstance(attr, Server) or isinstance(attr, Database) or
                    isinstance(attr, Document) or isinstance(attr, ViewResults)
                    or isinstance(attr, Row)):
                st.st_mode = stat.S_IFDIR | 0755
                st.st_nlink = 2
            else:
                data = json.dumps(attr)
                st.st_mode = stat.S_IFREG | 0444
                st.st_nlink = 1
                st.st_size = len(data)
            return st
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT

    def readdir(self, path, offset):
        attr = self.getcouchattrs(path)[-1]
        for r in '.', '..':
            yield fuse.Direntry(r)
        if isinstance(attr, Server):
            for db_name in self.server:
                yield fuse.Direntry(db_name.encode('utf-8'))
            return
        if isinstance(attr, Database):
            yield fuse.Direntry('_all_docs')
            yield fuse.Direntry('_view')
            return
        if isinstance(attr, ViewResults):
            is_view = getattr(attr, 'is_view', False)
            for row in list(attr):
                dirname = row.key
                if attr.view.name != '_all_docs':
                    dirname = quote(json.dumps(row.key))
                else:
                    dirname = dirname.split('/')[attr.options.get('startkey', '').count('/')]
                if is_view:
                    dirname = dirname.split('/')[-1]
                yield fuse.Direntry(dirname.encode('utf-8'))
            return
        if isinstance(attr, Row):
            is_view = getattr(attr, 'is_view', False)
            if is_view:
                db = self.getcouchattrs(path)[1]
                for r in db[attr.id]['views']:
                    yield fuse.Direntry(r.encode('utf-8'))
            else:
                yield fuse.Direntry('value')
            return
        for r in attr.keys():
            yield fuse.Direntry(r.encode('utf-8'))

    def open(self, path, flags):
        try:
            attr = self.getcouchattrs(path)[-1]
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
        try:
            attr = self.getcouchattrs(path)[-1]
            data = json.dumps(attr)
            slen = len(data)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = data[offset:offset+size]
            else:
                buf = ''
            return buf
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT

    def write(self, path, buf, offset):
        pass

    def unlink(self, path):
        attr = self.getcouchattrs(path)[-1]

    def mkdir(self, path, mode):
        server = self.getcouchattrs(path)[0]
        if isinstance(server, Server):
            server.create(path.split('/')[-1])

def main():
    args = sys.argv[1:]
    if len(args) not in (2,):
        print "CouchDB FUSE Connector: Allows you to browse the _attachments of"
        print " any CouchDB document on your own filesystem!"
        print
        print "Remember to URL-encode your <doc_id> appropriately."
        print
        print "Usage: python couchdbfuse.py <http://hostname:port/db/doc_id> <mount-point>"
        sys.exit(-1)

    if len(args) == 1:
        fs = CouchFS(args[0])
    elif len(args) == 2:
        fs = CouchFSDocument(args[1], args[0])

    fs.parse(errex=1)
    fs.main()
