#! /usr/bin/env python

import subprocess
import sys
import os
import shutil
import string
import random
import mimetypes
import traceback
import urllib
import pdb
from twisted.web import server, resource
from twisted.protocols.basic import FileSender
from twisted.python.log import err
from twisted.internet import reactor, defer

import settings
from util import computeHash



randChars  = '%s%s' % (string.ascii_letters, string.digits)


def randomString(length = 10):
    return ''.join(random.choice(randChars) for ii in xrange(length))



def runCmd(args):
    if settings.VERBOSE:
        print 'Running command:', ' '.join(args)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = proc.communicate()
    code = proc.wait()

    if code != 0:
        print out
        print err
        raise Exception('Got error from running command with args ' + repr(args))

    return out, err



def startServingFile(deferred, origFilename, genFilename, convertStr):
    '''Takes a deferred and serves file or generates and serves it.'''

    if genFilename is None:
        try:
            ff = open(origFilename, 'r')
        except IOError:
            print 'Error: original file %s does not exist and generation impossible' % origFilename
            deferred.errback()
            return
        if settings.VERBOSE:
            print 'Serving original file: %s' % origFilename
        deferred.callback(ff)
        return

    else:
        # possible to generate file
        success = False
        try:
            ff = open(genFilename, 'r')
            success = True
            if settings.VERBOSE:
                print 'Serving cached generated file: %s' % genFilename
        except IOError:
            pass

        if success:
            deferred.callback(ff)
            return

        if not os.path.exists(origFilename):
            print 'Error: Trying to convert %s but it does not exist' % origFilename
            deferred.errback()
            return

        tmpGenFilename = genFilename + '.tmp_' + randomString(6)
        # Make directories if they don't exist
        os.makedirs(os.path.dirname(tmpGenFilename))
        # See http://www.imagemagick.org/Usage/resize/#resize for options
        # ^ = fill, > = only shrink larger images
        #completeConvertStr = '%s^>' % convertStr
        completeConvertStr = '%s>' % convertStr
        out,err = runCmd((settings.CONVERT_CMD, origFilename, '-resize', completeConvertStr, tmpGenFilename))
        if settings.VERBOSE:
            print ''
        shutil.move(tmpGenFilename, genFilename)

        ff = open(genFilename, 'r')  # should now work
        if settings.VERBOSE:
            print 'Serving freshly generated file: %s' % genFilename
        deferred.callback(ff)



def sendOpenFile(request, openFile):
    '''Use FileSender to asynchronously send an open file

    [JBY] From: http://stackoverflow.com/questions/1538617/http-download-very-big-file'''

    contentType, junk = mimetypes.guess_type(request.path)
    request.setHeader('Content-Type', contentType if contentType else 'text/plain')
    dd = FileSender().beginFileTransfer(openFile, request)

    def cbFinished(ignored):
        openFile.close()
        request.finish()
    
    dd.addErrback(err)
    dd.addCallback(cbFinished)
    return server.NOT_DONE_YET



class ImageResource(resource.Resource):
    '''Twisted Resource for Images'''

    isLeaf = True
    
    def render_GET(self, request):
        try:
            self.processRequest(request)
        except Exception as exep:
            print '\nError:', exep
            if settings.VERBOSE:
                print 'Exception (returned 404):'
                print '-'*60
                traceback.print_exc(file=sys.stderr)
                print '-'*60
            request.setResponseCode(404)
            request.write(settings.STR404)
            request.finish()
        return server.NOT_DONE_YET

    def processRequest(self, request):
        lenPrefix = len(settings.STRIP_PREFIX)
        if request.path[0:lenPrefix] != settings.STRIP_PREFIX:
            raise Exception('Expected path "%s" to start with "%s"' % (request.path, settings.STRIP_PREFIX))

        rawPath = request.path[lenPrefix:]
        path = urllib.unquote(rawPath)
        
        if settings.VERBOSE:
            print 'rawPath is', repr(rawPath)
            print 'path is', repr(path)

        if settings.ENABLE_HASH_PATH:
            receivedHash = path[:settings.HASH_PATH_LENGTH]
            path = path[settings.HASH_PATH_LENGTH + 1:]  # strip hash from path
            correctHash = computeHash(path, settings.SECRET_HASH_KEY, settings.HASH_PATH_LENGTH)
            if settings.VERBOSE:
                print '  correctHash is', correctHash, ', receivedHash is', receivedHash,
            if receivedHash != correctHash:
                raise Exception('Expected hash %s for path %s but got %s' % (correctHash, path, receivedHash))
        
        parts = path.rsplit('.', 2)
        if settings.VERBOSE:
            print 'parts is', repr(parts)

        # default values
        convertStr = None
        genFilename = None
        origFilename = os.path.join(settings.IMAGE_ROOT, path)

        if len(parts) == 1:
            raise Exception('Does not look like an image filename: %s' % path)
        elif len(parts) == 2:
            pass
        else:
            # Maximum of 3 parts: try the second string as a geometry specifier and normalize it
            origFilename = os.path.join(settings.IMAGE_ROOT, parts[0] + '.' + parts[2])
            geomParts = parts[1].split('x')
            if len(geomParts) == 1:
                try:
                    widthHeightInt = int(geomParts[0])
                except ValueError:
                    raise Exception('Could not convert to int: "%s"' % geomParts[0])
                convertStr = '%dx%d' % (widthHeightInt, widthHeightInt)
                genFilename = os.path.join(settings.IMAGE_CACHE_ROOT,
                                           parts[0] + '.' + ('%d' % widthHeightInt) + '.' + parts[2])
            elif len(geomParts) == 2:
                try:
                    widthInt = int(geomParts[0])
                    heightInt = int(geomParts[1])
                except ValueError:
                    raise Exception('Could not convert to width x height: "%s"' % parts[1])
                convertStr = '%dx%d' % (widthInt, heightInt)
                genFilename = os.path.join(settings.IMAGE_CACHE_ROOT,
                                           parts[0] + '.' + convertStr + '.' + parts[2])
            else:
                raise Exception('Not a valid geometry string: "%s"' % parts[1])


        deferred = defer.Deferred()

        deferred.addCallback(lambda openFile:  sendOpenFile(request, openFile))
        deferred.addErrback(lambda junk:  (request.setResponseCode(404),
                                           request.write(settings.STR404),
                                           request.finish()))
        
        startServingFile(deferred, origFilename, genFilename, convertStr)

        sys.stdout.flush()
        return server.NOT_DONE_YET



if __name__ == '__main__':
    TCP = True
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            TCP = False
            fd = sys.argv[1]
    else:
        port = 8080

    onStr = 'port %d' % port if TCP else 'fd %s' % fd
    print 'Starting Simple Twisted Image Server on %s. Looking for files in %s.' % (onStr, settings.IMAGE_ROOT)
    sys.stdout.flush()

    site = server.Site(ImageResource())
    if TCP:
        reactor.listenTCP(port, site)
    else:
        reactor.listenUNIX(fd, site)
    reactor.run()
