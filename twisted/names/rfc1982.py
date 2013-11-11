# -*- test-case-name: twisted.names.test.test_util -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
DNS utility functions and classes.
"""

from __future__ import unicode_literals

import calendar
from datetime import datetime

from twisted.python.compat import nativeString


class SNA(object):
    """
    A Serial Number Arithmetic helper class.

    This class implements RFC1982 DNS Serial Number Arithmetic.

    SNA is used in DNS and specifically in DNSSEC as defined in
    RFC4034 in the DNSSEC Signature Expiration and Inception Fields.

    @see: U{https://tools.ietf.org/html/rfc1982}
    @see: U{https://tools.ietf.org/html/rfc4034}

    @ivar serialBits: See L{__init__}.
    @ivar _number: See C{number} of L{__init__}.
    @ivar _modulo: The value at which wrapping will occur.
    @ivar _halfRing: Half C{_modulo}. If another L{SNA} value is larger than
        this, it would lead to a wrapped value which is larger than the first
        and comparisons are therefore ambiguous.
    @ivar _maxAdd: Half C{_modulo} plus 1. If another L{SNA} value is larger
        than this, it would lead to a wrapped value which is larger than the
        first. Comparisons with the original value would therefore be ambiguous.
    """
    def __init__(self, number, serialBits=32):
        """
        Construct an L{SNA} instance.

        @param number: An L{int} which will be stored as the modulo
            C{number % 2 ^ serialBits}
        @type number: L{int}

        @param serialBits: The size of the serial number space. The
            power of two which results in one larger than the largest
            integer corresponding to a serial number value.
        @type serialBits: L{int}
        """
        self.serialBits = serialBits

        self._modulo = 2 ** serialBits
        self._halfRing = 2 ** (serialBits - 1)
        self._maxAdd = 2 ** (serialBits - 1) - 1
        self._number = int(number) % self._modulo


    def _convertOther(self, other):
        """
        Check that a foreign object is suitable for use in the comparison or
        arithmetic magic methods of this L{SNA} instance. Raise L{TypeError} if
        not.

        @param other: The foreign L{object} to be checked.
        @raises: L{TypeError} if C{other} is not compatible.
        """
        if not isinstance(other, SNA):
            raise TypeError(
                'cannot compare or combine %r and %r' % (self, other))
        return other


    def __str__(self):
        """
        Return a string representation of this L{SNA} instance.

        @rtype: L{nativeString}
        """
        return nativeString('%d' % (self._number,))


    def __int__(self):
        """
        @return: The integer value of this L{SNA} instance.
        @rtype: L{int}
        """
        return self._number


    def __eq__(self, other):
        """
        Allow rich equality comparison with another L{SNA} instance.

        @type other: L{SNA}
        """
        other = self._convertOther(other)
        return other._number == self._number


    def __ne__(self, other):
        """
        Allow rich equality comparison with another L{SNA} instance.

        @type other: L{SNA}
        """
        other = self._convertOther(other)
        return other._number != self._number


    def __lt__(self, other):
        """
        Allow I{less than} comparison with another L{SNA} instance.

        @type other: L{SNA}
        """
        other = self._convertOther(other)
        return (
            (self._number < other._number
             and (other._number - self._number) < self._halfRing)
            or
            (self._number > other._number
             and (self._number - other._number) > self._halfRing)
        )


    def __gt__(self, other):
        """
        Allow I{greater than} comparison with another L{SNA} instance.

        @type other: L{SNA}
        @rtype: L{bool}
        """
        other = self._convertOther(other)
        return (
            (self._number < other._number
             and (other._number - self._number) > self._halfRing)
            or
            (self._number > other._number
             and (self._number - other._number) < self._halfRing)
        )


    def __le__(self, other):
        """
        Allow I{less than or equal} comparison with another L{SNA} instance.

        @type other: L{SNA}
        @rtype: L{bool}
        """
        other = self._convertOther(other)
        return self == other or self < other


    def __ge__(self, other):
        """
        Allow I{greater than or equal} comparison with another L{SNA} instance.

        @type other: L{SNA}
        @rtype: L{bool}
        """
        other = self._convertOther(other)
        return self == other or self > other


    def __add__(self, other):
        """
        Allow I{addition} with another L{SNA} instance.

        Serial numbers may be incremented by the addition of a positive
        integer n, where n is taken from the range of integers
        [0 .. (2^(SERIAL_BITS - 1) - 1)].  For a sequence number s, the
        result of such an addition, s', is defined as

        s' = (s + n) modulo (2 ^ SERIAL_BITS)

        where the addition and modulus operations here act upon values that
        are non-negative values of unbounded size in the usual ways of
        integer arithmetic.

        Addition of a value outside the range
        [0 .. (2^(SERIAL_BITS - 1) - 1)] is undefined.

        @see: U{http://tools.ietf.org/html/rfc1982#section-3.1}

        @type other: L{SNA}
        @rtype: L{SNA}
        @raises: L{ArithmeticError} if C{other} is more than C{_maxAdd}
            ie more than half the maximum value of this serial number.
        """
        other = self._convertOther(other)
        if other._number <= self._maxAdd:
            return SNA(
                (self._number + other._number) % self._modulo,
                serialBits=self.serialBits)
        else:
            raise ArithmeticError(
                'value %r outside the range 0 .. %r' % (
                    other._number, self._maxAdd,))


    def __hash__(self):
        """
        Allow L{SNA} instances to be hashed for use as L{dict} keys.

        @rtype: L{int}
        """
        return hash(self._number)



class DateSNA(SNA):
    """
    A helper class for DNS Serial Number Arithmetic for dates
    'YYYYMMDDHHMMSS' per RFC4034 3.1.5

    @see: U{https://tools.ietf.org/html/rfc4034#section-3.1.5}

    @ivar _timeFormat: The expected datetime format provided to
        L{DateSNA.__init__}
    """

    _timeFormat = '%Y%m%d%H%M%S'


    def __init__(self, utcDateTime='19700101000000'):
        """
        Construct a L{DateSNA} instance.

        @param utcDateTime: A UTC date/time string of format
            I{YYMMDDhhmmss} which will be converted to seconds since
            the UNIX epoch.
        @type utcDateTime: L{unicode}
        """
        secondsSinceEpoch = calendar.timegm(
            datetime.strptime(utcDateTime, self._timeFormat).utctimetuple())

        super(DateSNA, self).__init__(secondsSinceEpoch)


    def __add__(self, sna2):
        """
        Allow I{addition} with another L{SNA} or L{DateSNA} instance.

        @type sna2: L{SNA}
        @rtype: L{SNA}
        @raises: L{ArithmeticError} if C{sna2} is more than C{_maxAdd}
            ie more than half the maximum value of this serial number.
        """
        if not isinstance(sna2, SNA):
            return NotImplemented

        if (sna2 <= SNA(self._maxAdd) and
            (self._number + sna2._number < self._modulo)):
            sna = SNA((self._number + sna2._number) % self._modulo)
            return DateSNA.fromSNA(sna)
        else:
            raise ArithmeticError


    def asDate(self):
        """
        Convert to L{datetime}.

        @return: A UTC L{datetime}.
        @rtype: L{datetime}
        """
        return datetime.utcfromtimestamp(self._number)


    @classmethod
    def fromSNA(cls, sna):
        """
        Create a L{DateSNA} object from an L{SNA}.

        @param sna: The source L{SNA} instance.
        @type sna: L{SNA}

        @return: The resulting L{DateSNA} instance.
        @rtype: L{DateSNA}
        """
        d = cls()
        d._number = sna._number
        return d


    @classmethod
    def fromInt(cls, i):
        """
        Create an DateSNA object from an L{int}.

        @param i: The source L{int}.
        @type i: L{int}

        @return: The resulting L{DateSNA} instance.
        @rtype: L{DateSNA}
        """
        return cls.fromSNA(SNA(i))


    def __str__(self):
        """
        Return a string representation of the object

        @rtype: L{str}
        """
        return self.asDate().strftime(self._timeFormat)



__all__ = ['SNA', 'DateSNA']