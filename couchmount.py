#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jason Davies
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.


from couchdb.client import Database
from couchdb.http import ResourceNotFound
import errno
import fuse
import os
import stat
import sys
from urllib.parse import unquote

fuse.fuse_python_api = (0, 2)

COUCHFS_DIRECTORY_PLACEHOLDER = u'.couchfs-directory-placeholder'

class CouchStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = os.getuid()
        self.st_gid = os.getgid()
        self.st_size = 4096
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

def _normalize_path(path):
    return u'/'.join([part for part in path.split(u'/') if part != u''])

class CouchFSDocument(fuse.Fuse):
    def __init__(self, mountpoint, uri=None, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)
        db_uri, doc_id = uri.rsplit('/', 1)
        self.doc_id = unquote(doc_id)
        self.db = Database(db_uri)

    def get_attachment(self, path):
        missing = object()
        data = self.db.get_attachment(self.db[self.doc_id], path, default=missing)
        if data is missing:
            raise ResourceNotFound()
        if data is None:  # empty attachment
            return b''
        return data.read()

    def get_dirs(self):
        dirs = {}
        attachments = self.db[self.doc_id].get('_attachments', {}).keys()
        for att in attachments:
            parents = [u'']
            for name in att.split('/'):
                filenames = dirs.setdefault(u'/'.join(parents[1:]), set())
                if name != COUCHFS_DIRECTORY_PLACEHOLDER:
                    filenames.add(name)
                    parents.append(name)
        return dirs

    def readdir(self, path, offset):
        path = _normalize_path(path)
        for r in '.', '..':
            yield fuse.Direntry(r)
        for name in self.get_dirs().get(path, []):
            yield fuse.Direntry(name)

    def getattr(self, path):
        path = _normalize_path(path)
        try:
            st = CouchStat()
            if path == '' or path in self.get_dirs().keys():
                st.st_mode = stat.S_IFDIR | 0o775
                st.st_nlink = 2
            else:
                att = self.db[self.doc_id].get('_attachments', {})
                data = att[path]
                st.st_mode = stat.S_IFREG | 0o664
                st.st_nlink = 1
                st.st_size = data['length']
            return st
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT

    def open(self, path, flags):
        path = _normalize_path(path)
        try:
            #data = self.db.get_attachment(self.db[self.doc_id], path.split('/')[-1])
            #att = self.db[self.doc_id].get('_attachments', {})
            #data = att[path.split('/')[-1]]
            parts = path.rsplit(u'/', 1)
            if len(parts) == 1:
                dirname, filename = u'', parts[0]
            else:
                dirname, filename = parts
            if filename in self.get_dirs()[dirname]:
                return 0
            return -errno.ENOENT
        except (KeyError, ResourceNotFound):
            return -errno.ENOENT
        #accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        #if (flags & accmode) != os.O_RDONLY:
        #    return -errno.EACCES

    def read(self, path, size, offset):
        path = _normalize_path(path)
        try:
            data = self.get_attachment(path)
            slen = len(data)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = data[offset:offset+size]
            else:
                buf = b''
            return buf
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT

    def write(self, path, buf, offset):
        path = _normalize_path(path)
        try:
            data = self.get_attachment(path)
            data = data[0:offset] + buf + data[offset+len(buf):]
            self.db.put_attachment(self.db[self.doc_id], data, filename=path)
            return len(buf)
        except (KeyError, ResourceNotFound):
            pass
        return -errno.ENOENT

    def mknod(self, path, mode, dev):
        path = _normalize_path(path)
        self.db.put_attachment(self.db[self.doc_id], b'', filename=path)

    def unlink(self, path):
        path = _normalize_path(path)
        parts = path.rsplit(u'/', 1)
        if len(parts) == 1:
            dirname, filename = u'', parts[0]
        else:
            dirname, filename = parts
        self.db.delete_attachment(self.db[self.doc_id], path)
        if filename != COUCHFS_DIRECTORY_PLACEHOLDER and len(self.get_dirs().get(dirname, [])) == 0:
            print("putting to:", u'%s/%s' % (dirname, COUCHFS_DIRECTORY_PLACEHOLDER))
            self.db.put_attachment(self.db[self.doc_id], b'', filename=u'%s/%s' % (dirname, COUCHFS_DIRECTORY_PLACEHOLDER))

    def truncate(self, path, size):
        path = _normalize_path(path)
        self.db.put_attachment(self.db[self.doc_id], b'', filename=path)
        return 0

    def utime(self, path, times):
        return 0

    def mkdir(self, path, mode):
        path = _normalize_path(path)
        self.db.put_attachment(self.db[self.doc_id], b'', filename=u'%s/%s' % (path, COUCHFS_DIRECTORY_PLACEHOLDER))
        return 0

    def rmdir(self, path):
        path = _normalize_path(path)
        self.db.delete_attachment(self.db[self.doc_id], u'%s/%s' % (path, COUCHFS_DIRECTORY_PLACEHOLDER))
        return 0

    def rename(self, pathfrom, pathto):
        pathfrom, pathto = _normalize_path(pathfrom), _normalize_path(pathto)
        data = self.get_attachment(pathfrom)
        self.db.put_attachment(self.db[self.doc_id], data, filename=pathto)
        self.db.delete_attachment(self.db[self.doc_id], pathfrom)
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


def main():
    args = sys.argv[1:]
    if len(args) not in (2, 3):
        print("CouchDB FUSE Connector: Allows you to browse the _attachments of")
        print(" any CouchDB document on your own filesystem!")
        print()
        print("Remember to URL-encode your <doc_id> appropriately.")
        print()
        print("Usage: python couchmount.py [-d] <http://hostname:port/db/doc_id> <mount-point>")
        sys.exit(-1)

    if len(args) == 2:
        fs = CouchFSDocument(args[1], args[0])
    elif len(args) == 3:
        fs = CouchFSDocument(args[2], args[1])

    fs.parse(errex=1)
    fs.main()

if __name__ == '__main__':
    main()
