# Listen is copyright 2005 The Open Planning Project.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307 USA.

import StringIO, mimetools, re, warnings

warnings.simplefilter('ignore', DeprecationWarning)
import multifile
warnings.simplefilter('default', DeprecationWarning)

from nous.mailpost.MailBoxerTools import mime_decode_header

# these functions are from Products/MailBoxer/MailBoxer_tools.py with a
# small modification to unpackMultifile to fix a bug

def unpackMail(mailString):
    """

    returns body, content-type, html-body and attachments for mail-string.
    """
    return unpackMultifile(multifile.MultiFile(StringIO.StringIO(mailString)))


def unpackMultifile(multifile, attachments=None):
    """ Unpack multifile into plainbody, content-type, htmlbody and attachments.
    """
    if attachments is None:
        attachments=[]
    textBody = htmlBody = contentType = ''

    msg = mimetools.Message(multifile)
    maintype = msg.getmaintype()
    subtype = msg.getsubtype()

    name = msg.getparam('name')

    if not name:
        # Check for disposition header (RFC:1806)
        disposition = msg.getheader('Content-Disposition')
        if disposition:
            matchObj = re.search('(?i)filename="*(?P<filename>[^\s"]*)"*',
                                   disposition)
            if matchObj:
                name = matchObj.group('filename')

    # Recurse over all nested multiparts
    if maintype == 'multipart':
        multifile.push(msg.getparam('boundary'))
        multifile.readlines()
        while not multifile.last:
            multifile.next()

            (tmpTextBody, tmpContentType, tmpHtmlBody, tmpAttachments) = \
                                       unpackMultifile(multifile, attachments)

            # Return ContentType only for the plain-body of a mail
            if tmpContentType:# and not textBody:
                textBody += tmpTextBody
                contentType = tmpContentType

            if tmpHtmlBody:
                htmlBody = tmpHtmlBody

            if tmpAttachments:
                attachments = tmpAttachments

        multifile.pop()
        return (textBody, contentType, htmlBody, attachments)

    # Process MIME-encoded data
    plainfile = StringIO.StringIO()

    try:
        mimetools.decode(multifile,plainfile,msg.getencoding())
    # unknown or no encoding? 7bit, 8bit or whatever... copy literal
    except ValueError:
        mimetools.copyliteral(multifile,plainfile)

    body = plainfile.getvalue()
    plainfile.close()

    # Get plain text
    if maintype == 'text' and subtype == 'plain' and not name:
        textBody = body
        contentType = msg.get('content-type', 'text/plain')
    else:
        # No name? This should be the html-body...
        if not name:
            name = '%s.%s' % (maintype,subtype)
            htmlBody = body

        attachments.append({'filename' : mime_decode_header(name),
                            'filebody' : body,
                            'maintype' : maintype,
                            'subtype' : subtype})

    return (textBody, contentType, htmlBody, attachments)

