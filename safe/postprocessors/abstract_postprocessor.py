# -*- coding: utf-8 -*-
"""**Abstract postprocessor class, do not instantiate directly**

"""

__author__ = 'Marco Bernasocchi <marco@opengis.ch>'
__revision__ = '$Format:%H$'
__date__ = '10/10/2012'
__license__ = "GPL"
__copyright__ = 'Copyright 2012, Australia Indonesia Facility for '
__copyright__ += 'Disaster Reduction'

import logging

from safe.common.exceptions import PostprocessorError

from third_party.odict import OrderedDict

LOGGER = logging.getLogger('InaSAFE')


class AbstractPostprocessor():
    """
    Abstract postprocessor class, do not instantiate directly.
    but instantiate the PostprocessorFactory class which will take care of
    setting up many prostprocessors. Alternatively you can as well instantiate
    directly a sub class of AbstractPostprocessor.

    Each subclass has to overload the process method and call its parent
    like this: AbstractPostprocessor.process(self)
    if a postprocessor needs parmeters, then it should override the setup and
    clear methods as well and call respectively
    AbstractPostprocessor.setup(self) and AbstractPostprocessor.clear(self).

    for implementation examples see AgePostprocessor which uses mandatory and
    optional parameters
    """

    def __init__(self):
        self._results = None

    def setup(self, params):
        del params
        if self._results is not None:
            self._raise_error('clear needs to be called before setup')
        self._results = OrderedDict()

    def process(self):
        if self._results is None:
            self._raise_error('setup needs to be called before process')

    def results(self):
        return self._results

    def clear(self):
        self._results = None

    def _raise_error(self, message=None):
        if message is None:
            message = 'Postprocessor error'
        raise PostprocessorError(message)

    def _log_message(self, message):
        LOGGER.debug(message)

    def _append_result(self, name, result, metadata=None):
        if metadata is None:
            metadata = dict()
        self._results[name] = {'value': result,
                                 'metadata': metadata}
