import unittest
import mox
import urllib2
from textwrap import dedent

from zope.testing import doctest


mailString = dedent('''\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:id1
SUMMARY:Play Doom
DTSTART:20050228T000000
DURATION:PT2H
END:VEVENT
BEGIN:VEVENT
UID:id3
SUMMARY:Sleep (zzz)
DTSTART:20050302T000000
DURATION:PT8H
END:VEVENT
BEGIN:VEVENT
UID:id4
SUMMARY:Wake up
DTSTART:20050302T080000
DURATION:PT0H
END:VEVENT
END:VCALENDAR
''')


def doctest_postEmail():
    r"""Tests for postEmail.

    Let's try posting a simple email to the url:

        >>> url = 'http://localhost/got_mail'
        >>> req = urllib2.Request(url)

        >>> mox.StubOutWithMock(urllib2, 'Request', use_mock_anything=True)
        >>> mox.StubOutWithMock(urllib2, 'urlopen')

    The email body gets urlquoted and passed as "Mail" parameter:

        >>> data = 'Mail=' + urllib2.quote(mailString)

        >>> mm = urllib2.Request(url).AndReturn(req)
        >>> mm = urllib2.urlopen(req, data=data)

        >>> mox.ReplayAll()

        >>> from nous.mailpost import postEmail
        >>> postEmail(url,
        ...           mailString,
        ...           authorization="",
        ...           attachments=[])

        >>> mox.VerifyAll()

    """


def setUp(test):
    test.globs['mox'] = mox.Mox()


def tearDown(test):
    test.globs['mox'].UnsetStubs()


def test_suite():
    return unittest.TestSuite([
            doctest.DocTestSuite(setUp=setUp,
                                 tearDown=tearDown,
                                 optionflags=doctest.ELLIPSIS),
            doctest.DocTestSuite('nous.mailpost',
                                 optionflags=doctest.ELLIPSIS),
            ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
