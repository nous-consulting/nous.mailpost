#####
###  MailBoxerTools - generic mail-decoding-tools for MailBoxer
##   Copyright (C) 2004 Maik Jablonski (maik.jablonski@uni-bielefeld.de)
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
##   along with this program; if not, write to the Free Software
###  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#####

import StringIO, re, rfc822, mimetools, warnings

warnings.simplefilter('ignore', DeprecationWarning)
import multifile, mimify
warnings.simplefilter('default', DeprecationWarning)

def splitMail(mailString):
    """ returns (header,body) of a mail given as string
    """
    msg = mimetools.Message(StringIO.StringIO(str(mailString)))

    # Get headers
    mailHeader = {}
    for (key,value) in msg.items():
        mailHeader[key] = value

    # Get body
    msg.rewindbody()
    mailBody = msg.fp.read()

    return (mailHeader, mailBody)


def mime_decode_header(header):
    """ Returns the unfolded and undecoded header
    """
    # unfold the header
    header = re.sub(r'\r?\n\s+',' ', header)

    # simple hack around some bugs in mimify.mime_decode_header
    # it checks only for =?iso-8859-1?q?, but there many variants
    # in the wild... so we normalize it here, maybe we loose something,
    # but in most cases we should get better results
    header = re.sub(r'(?i)=\?iso-8859-1[0-9]?\?[a-z]\?',
                               r'=?iso-8859-1?q?', header)
    return mimify.mime_decode_header(header)


def parseaddr(header):
    """ wrapper for rfc822.parseaddr, returns (name, addr)
    """
    return rfc822.parseaddr(header)


def parseaddrList(header):
    """ wrapper for rfc822.AddressList, returns list of (name, addr)
    """
    return list(rfc822.AddressList(header))


def lowerList(stringlist):
    """ lowers all items of a list
    """
    return [item.lower() for item in stringlist]


def getPlainBodyFromMail(mailString):
    """ get content-type and body from mail given as string
    """
    (textBody, contentType, htmlBody, attachments) = unpackMail(mailString)
    if contentType:
        return (contentType, textBody)
    else:
        charset = ""
        match = re.search('(?is)<meta.*?content="text/html;[\s]*charset=([^"]*?)".*?>',
                                                                  htmlBody)
        if match:
            charset="charset=%s;" % match.group(1)
        return ('text/plain;%s' % charset, convertHTML2Text(htmlBody))


def headersAsString(mailString, customHeaders={}):
    """ returns the headers as a string, optionally patching the headers with
        custom headers.

    """
    msg = mimetools.Message(StringIO.StringIO(mailString))
    # patch the headers with our custom headers
    for hdr in customHeaders.keys():
        msg[hdr] = customHeaders[hdr]

    return str(msg).strip()


def unpackMail(mailString):
    """ returns body, content-type, html-body and attachments for mail-string.
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
            if tmpContentType and not textBody:
                textBody = tmpTextBody
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


def convertHTML2Text(html):
    """ converts given html to plain text.
    """
    from sgmllib import SGMLParser
    class HTMLStripper(SGMLParser):
        """ Remove tags and translate entities.
        """
        text = ''

        def handle_data(self, data):
            self.text = self.text + data

        def __str__(self):
            return self.text.strip()

    p = HTMLStripper()
    p.feed(html)
    p.close()
    return str(p)
