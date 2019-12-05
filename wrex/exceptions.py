class WOSError(Exception):
    pass


class WOSDefaultsError(WOSError):
    pass


class WOSStaleQueryError(WOSError):
    pass


class WOSHTTPError(WOSError):
    pass


class WOSError400(WOSHTTPError):
    def __init__(self, message, *args):
        self.message = 'Query returned status code 400: "Bad request"\n' \
                       'Response message: {}\n\n' \
                       'Check your query structure to make sure you have correctly defined fields!'.format(message)
        super(WOSHTTPError, self).__init__(self.message, *args)


class WOSError403(WOSHTTPError):
    def __init__(self, message, *args):
        self.message = 'Query returned status code 403: "Forbidden"\n' \
                       'Response message: {}\n\n' \
                       'Have you set the correct api key using self.setkey()?'.format(message)
        super(WOSHTTPError, self).__init__(self.message, *args)


class WOSError404(WOSHTTPError):
    def __init__(self, message, *args):
        self.message = 'Query returned status code 404: "Not found"\n' \
                       'Response message: {}'.format(message)
        super(WOSHTTPError, self).__init__(self.message, *args)


class WOSError429(WOSHTTPError):
    def __init__(self, message, *args):
        self.message = 'Query returned status code 429: "Throttle error"\n' \
                       'Response message: {}\n\n' \
                       'Check whether you are hitting the API a lot at once!'.format(message)
        super(WOSHTTPError, self).__init__(self.message, *args)


class WOSError500(WOSHTTPError):
    def __init__(self, message, *args):
        self.message = 'Query returned status code 500: "Internal server error"\n' \
                       'Response message: {}'.format(message)
        super(WOSHTTPError, self).__init__(self.message, *args)
