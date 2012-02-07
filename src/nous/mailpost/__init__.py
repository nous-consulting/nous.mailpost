# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
import email
import os
import sys
import urllib
import urllib2
import base64
import hashlib
from StringIO import StringIO

from nous.mailpost.mailboxer_tools import unpackMail
from nous.mailpost.MailBoxerTools import getPlainBodyFromMail
from nous.mailpost.MailBoxerTools import headersAsString


# Meaningful exit-codes for a smtp-server
EXIT_USAGE = 64
EXIT_NOUSER = 67
EXIT_NOPERM = 77
EXIT_TEMPFAIL = 75

try:
    import syslog
    syslog.openlog('u2timailer')
    log_critical = lambda msg: syslog.syslog(syslog.LOG_CRIT|syslog.LOG_MAIL, msg)
    log_error = lambda msg: syslog.syslog(syslog.LOG_ERR|syslog.LOG_MAIL, msg)
    log_warning = lambda msg: syslog.syslog(syslog.LOG_WARNING|syslog.LOG_MAIL, msg)
    log_info = lambda msg: syslog.syslog(syslog.LOG_INFO|syslog.LOG_MAIL, msg)
except:
    # if we can't open syslog, just fake it
    fake_logger = lambda msg: sys.stderr.write(msg+"\n")
    log_critical = fake_logger
    log_error = fake_logger
    log_warning = fake_logger
    log_info = fake_logger


class BrokenHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)


def installBrokenRedirectHandler():
    """Install the broken redirect handler.

    urllib2 handles server-responses (errors) much better than urllib.

    urllib2 is, in fact, too much better. Its built-in redirect
    handler can mask authorization problems when a cookie-based
    authenticator is in use -- as with Plone. Also, I can't think of
    any reason why we would want to allow redirection of these
    requests!

    So, let's create and install a disfunctional redirect handler.

    """
    opener = urllib2.build_opener(BrokenHTTPRedirectHandler())
    urllib2.install_opener(opener)


def postEmail(callURL, mailString, authorization, attachments):
    req = urllib2.Request(callURL)
    if authorization:
        auth = base64.encodestring(authorization).strip()
        req.add_header('Authorization', 'Basic %s' % auth)
    data = 'Mail='+urllib.quote(mailString)
    for attachment in attachments:
        data += '&md5[]=' + getAttachmentFilename(attachment)
        data += '&mime-type[]=%s/%s' % (attachment['maintype'], attachment['subtype'])
        data += '&filename[]=' + attachment['filename']
    urllib2.urlopen(req, data=data)


def getAuthorization(url):
    auth_mark = url.find('@')
    if auth_mark<>-1:
        return url[len('http://'):auth_mark]
    return ''


def stripAuthentication(url):
    return url.replace(getAuthorization(url) + '@', '')


def getAttachmentFilename(attachment):
    return hashlib.md5(attachment['filebody']).hexdigest()


def copy_chunked(source, dest, chunk_size):
    """ Copy from source file to destination file in sized chunks
    """
    size = 0

    while True:
        if isinstance(source, str):
            chunk = source[size:(size+chunk_size)]
        else:
            chunk = source.read(chunk_size)

        size += len(chunk)
        dest.write(chunk)

        if len(chunk) < chunk_size:
            break

    return size


def storeAttacment(attachment, upload_dir):
    filename = getAttachmentFilename(attachment)
    dir_path = [upload_dir]
    segment = ''
    for c in list(filename):
        segment += c
        if len(segment) > 7:
            dir_path.append(segment)
            segment = ''
    if segment:
        dir_path.append(segment)
    filename = os.path.join(*dir_path)
    if os.path.exists(filename):
        return

    os.makedirs(os.path.dirname(filename))
    f = open(filename, 'w')
    size = copy_chunked(StringIO(attachment['filebody']), f, 4096)
    f.close()


def processAttachments(mailString, upload_dir):
    # check to see if we have attachments
    text_body, content_type, html_body, attachments = unpackMail(mailString)

    num_attachments = len(attachments)
    if num_attachments or html_body:
        mail = email.message_from_string(mailString)
        mail.set_payload(mail.get_payload()[0])
        mailString = mail.as_string()

    # store attachment on the filesystem
    for attachment in attachments:
        storeAttacment(attachment, upload_dir)

    return mailString, attachments


def processEmailAndPost(callURL, mailString, upload_dir):
    # XXX refactor and test
    urlParts = urllib2.urlparse.urlparse(callURL)
    urlPath = '/'.join(filter(None, list(urlParts)[2].split('/'))[:-1])
    baseURL = urllib2.urlparse.urlunparse(urlParts[:2]+(urlPath,)+urlParts[3:])+'/'

    authorization = getAuthorization(callURL)
    callURL = stripAuthentication(callURL)

    # Get the raw mail
    mailString, attachments = processAttachments(mailString, upload_dir)

    postEmail(callURL, mailString, authorization, attachments)


def main():
    args = list(sys.argv)
    args = args[:-2]
    # Check if we have at least one parameter
    if len(args) == 1:
        log_critical('no parameters given, should specify URL of u2ti instance'
                     ' and directory for uploaded files')
        sys.exit(EXIT_USAGE)
    # And not more than 2
    elif len(args) > 3:
        log_critical('only 2 parameters should be specified (%s given)'  % (len(args)-1))
        sys.exit(EXIT_USAGE)

    # Get the url to call
    callURL = args[1]
    if callURL.find('http://') == -1:
        log_critical('URL is specified (%s) is not a valid URL' % callURL)
        log_critical('%s' % args)
        sys.exit(EXIT_USAGE)

    # Get the path for uploaded files
    upload_dir = args[2]
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    if not os.path.isdir(upload_dir):
        log_critical('File upload directory (%s) is invalid' % upload_dir)
        sys.exit(EXIT_USAGE)

    mailString = sys.stdin.read()
    installBrokenRedirectHandler()
    try:
        processEmailAndPost(callURL, mailString, upload_dir)
    except Exception, e:
        # If MailBoxer doesn't exist, bounce message with EXIT_NOUSER,
        # so the sender will receive a "user-doesn't-exist"-mail from MTA.
        if hasattr(e, 'code'):
            if e.code == 404:
                log_error("URL at %s doesn't exist (%s)" % (callURL, e))
                sys.exit(EXIT_NOUSER)
            else:
                # Server down? EXIT_TEMPFAIL causes the MTA to try again later.
                log_error('A problem, "%s", occurred uploading email to URL %s (error code was %s)' % (e, callURL, e.code))
                sys.exit(EXIT_TEMPFAIL)
        else:
            # Server down? EXIT_TEMPFAIL causes the MTA to try again later.
            log_error('A problem, "%s", occurred uploading email to server %s' % (e, callURL))
            sys.exit(EXIT_TEMPFAIL)
