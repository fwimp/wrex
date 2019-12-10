import requests
import json
import copy
from . import exceptions
from .const import __version__, query_repeat_timeout
import datetime


class WOSconnection:
    """
    The WOSconnection class provides an easy way to define, store, and retrieve the parameters required for WOS access.
    """
    def __init__(self, key, apiurl="https://wos-api.clarivate.com/api/wos", parameters=None):
        """Initialise a WOSconnection instance

        Parameters
        ----------
        key: str
            The personal API key provided by Clarivate
        apiurl: str
            The url of the WOS API (default https://wos-api.clarivate.com/api/wos)
        parameters
        """
        self.apiurl = apiurl
        self.key = key
        if parameters:
            self.parameters = parameters
        else:
            self.parameters = {
                "databaseId": "WOS",
                "count": 100,
                "firstRecord": 1
            }

    def __repr__(self):
        return 'wrex.{0}(key="{2}", apiurl="{1}", defaults={3})'.format(self.__class__.__name__, self.apiurl, self.key,
                                                                        self.parameters)

    def __str__(self):
        return 'Connection class for WOS REST API @ {0}\nAPI Key = {1}\nDefaults = {2}'.format(self.apiurl, self.key,
                                                                                               self.parameters)


class WOSquery:
    def __init__(self, response, connection, querystr="", count=100):
        self.querystr = querystr
        self.queryid = -1
        self.found = 0
        self.searched = 0
        self.stale = False
        self.timestamp = datetime.datetime.now()

        self.connection = None
        self.repack_connection(connection)

        self.data = {}
        self.parse_responsedata(response, firstrun=True)

        self.count = count
        self.complete = False
        self.check_complete()

    def __repr__(self):
        return 'wrex.{0}(response, querystr="{1}")'.format(self.__class__.__name__, self.querystr)

    def __str__(self):
        # TODO: printing should maybe return something like the following:
        # WOS query for "" containing 10/29 results.
        return '{0}(querystr="{1}", queryid={2}, found={3}, searched={4}, data)'.format(self.__class__.__name__,
                                                                                        self.querystr, self.queryid,
                                                                                        self.found, self.searched)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, position):
        # TODO: This is a horribly hacky way to do this, we should instead implement __iter__ and __next__
        return self.data[list(self.data.keys())[position]]

    def repack_connection(self, conn):
        self.connection = WOSconnection(conn.key, conn.apiurl, conn.parameters)

    def parse_responsedata(self, response, firstrun=False):
        parsed = json.loads(response.text)

        if firstrun:
            self.queryid = int(parsed["QueryResult"]["QueryID"])
            self.found = int(parsed["QueryResult"]["RecordsFound"])
            self.searched = int(parsed["QueryResult"]["RecordsSearched"])
            self.data.update({x["UID"]: WOSpaper(x) for x in parsed["Data"]["Records"]["records"]["REC"]})
        else:
            self.data.update({x["UID"]: WOSpaper(x) for x in parsed["Records"]["records"]["REC"]})

    def getall(self, showprogress=False):
        # Check whether complete first, just in case
        self.check_complete()
        self.check_stale()
        # TODO: If stale, redo query and THEN run rest of getall
        repeats = 0
        threshold = query_repeat_timeout
        previous_len = len(self.data)
        while not self.complete:
            tempresponse = query_byid(self.connection, self.queryid, firstRecord=len(self.data) + 1, returnraw=True)
            self.parse_responsedata(tempresponse)
            self.check_complete()
            if showprogress:
                print("Retrieved records: {}/{}".format(len(self.data), self.found))
                print(tempresponse.headers)
            # Timeout after threshold
            if len(self.data) == previous_len:
                repeats += 1
                if repeats >= threshold:
                    missing = self.found - len(self.data)
                    print("Could not retrieve {}/{} entries. Trying one last time".format(missing, self.found))
                    tempresponse = query_byid(self.connection, self.queryid, count=missing, firstRecord=len(self.data) + 1,
                                              returnraw=True)
                    self.parse_responsedata(tempresponse)
                    print("Could not retrieve {}/{} entries. Exiting after {} tries".format(missing, self.found, threshold))
                    break
            else:
                repeats = 0
            previous_len = len(self.data)

    def check_complete(self, returnstatus=False):
        self.complete = len(self.data) >= self.found
        if returnstatus:
            return self.complete

    def check_stale(self, returnstatus=False):
        age = datetime.datetime.now() - self.timestamp
        if age.days > 0:
            print("Query is stale! Age: {}".format(age))
            self.stale = True
        else:
            print("Query is fresh! Age: {}".format(age))
            self.stale = False
        if returnstatus:
            return self.stale

    def status(self):
        # TODO - Should this return a string or just print straight out?
        self.check_complete()

        print("Retrieved records: {}/{}".format(len(self.data), self.found))
        if self.complete:
            print("Data complete!")
        else:
            print("Data incomplete.\n\nRun WOSquery.getall() to retrieve data.")

    def export(self, verbose=False):
        outstr = "FN Web of Science Recursive EXplorer (wrex)\nVR {}\n".format(__version__)
        if verbose:
            exportdata = []
            for y, x in self.data.items():
                print(y)
                exportdata.append(x.fielddict())
        else:
            exportdata = [x.fielddict() for _, x in self.data.items()]
        outstr += "\n".join(exportdata)
        outstr += "\nEF"
        return outstr


class WOSpaper:
    def __init__(self, rawdata):
        self.rawdata = rawdata
        self.uid = ""
        self.title = ""
        self.authors = []
        self.year = 0
        self.volume = 0
        self.issue = 0
        self.identifiers = dict()
        self.publication = ""
        self.keywords = []
        self._fielddict = dict()

        self.parse_rawdata()

    def __repr__(self):
        return ""

    def __str__(self):
        return "UID: {0}\nTitle: {1}\nAuthors: {2} and {3} other/s\n".format(self.uid, self.title,
                                                                             self.authors[0]["full_name"],
                                                                             len(self.authors) - 1)

    def parse_rawdata(self):
        self.uid = self.rawdata["UID"]
        self.title = self.rawdata["static_data"]["summary"]["titles"]["title"][-1]["content"]
        self.authors = self.rawdata["static_data"]["summary"]["names"]["name"]
        self.year = self.rawdata["static_data"]["summary"]["pub_info"]["pubyear"]

    #         self.volume = self.rawdata["static_data"]["summary"]["pub_info"]["vol"]
    #         self.issue = self.rawdata["static_data"]["summary"]["pub_info"]["issue"]
    #         self.identifiers = {x["type"]: x["value"] for x in self.rawdata["dynamic_data"]["cluster_related"]["identifiers"]["identifier"]}
    #         self.publication = self.rawdata["static_data"]["summary"]["titles"]["title"][0]["content"]
    #         self.keywords = self.rawdata["static_data"]["item"]["keywords_plus"]["keyword"]

    def fielddict(self, regenerate=False, printmissing=False):
        if not self._fielddict:
            self._fielddict = make_field_dict(self.rawdata, printmissing)
        elif regenerate:
            self._fielddict = make_field_dict(self.rawdata, printmissing)
        return "\n".join([make_field_str(x, self._fielddict[x]) for x in self._fielddict])


def rawquery(conn, querystr):
    """
    Perform a query against the WOS API and return the raw response.

    Parameters
    ----------
    conn : WOSconnection
        The WOSconnection object containing the API connection data.
    querystr : str
        The query that should be asked to the WOS API.

    Returns
    -------
    requests.response
        Populated requests response object

    """
    queryparams = copy.deepcopy(conn.parameters)
    queryparams["usrQuery"] = querystr
    response = requests.get(conn.apiurl, headers={"X-ApiKey": conn.key}, params=queryparams)
    return response


def query(conn, querystr, returnraw=False):
    """Perform a query against the WOS API, parse the response and return a parsed variant.

    Parameters
    ----------
    conn:
    querystr:
    returnraw:

    Returns
    -------
    WOSquery
    response
        If `returnraw` is True
    """

    responsecodes = {
        400: exceptions.WOSError400,
        403: exceptions.WOSError403,
        404: exceptions.WOSError404,
        429: exceptions.WOSError429,
        500: exceptions.WOSError500
    }
    response = rawquery(conn, querystr)
    if response.status_code in responsecodes.keys():
        raise responsecodes[response.status_code](json.loads(response.text)["message"])
    if returnraw:
        return response
    else:
        return WOSquery(response, conn, querystr=querystr, count=conn.parameters["count"])


def rawquery_byid(conn, queryid, count=None, firstRecord=None):
    queryparams = copy.deepcopy(conn.parameters)
    if count:
        queryparams["count"] = count
    if firstRecord:
        queryparams["firstRecord"] = firstRecord
    if "usrQuery" in queryparams.keys():
        del queryparams["usrQuery"]
    response = requests.get(conn.apiurl + "/query/{}".format(queryid), headers={"X-ApiKey": conn.key}, params=queryparams)
    return response


def query_byid(conn, queryid, count=None, firstRecord=None, returnraw=False):
    """
    Perform a query against the WOS API, parse the response and return a parsed variant.

    :param querystr:
    :param returnraw:
    :return:
    """
    responsecodes = {
        400: exceptions.WOSError400,
        403: exceptions.WOSError403,
        404: exceptions.WOSError404,
        429: exceptions.WOSError429,
        500: exceptions.WOSError500
    }
    response = rawquery_byid(conn, queryid, count, firstRecord)
    if response.status_code in responsecodes.keys():
        raise responsecodes[response.status_code](json.loads(response.text)["message"])
    if count is None:
        count = conn.parameters["count"]  # Just to make sure the resulting query object is formed accurately
    if returnraw:
        return response
    else:
        return WOSquery(response, conn, querystr="", count=count)


def getall(q, showprogress=False):
    """ Helper function to provide an alternate interface for getting the full data of a query."""
    q.getall(showprogress)
    return q


def make_field_str(fieldname, fielddata, verbose=False):
    outstr = "{} ".format(fieldname)
    if verbose:
        print("{}: {}".format(fieldname, fielddata))
    if isinstance(fielddata, list):
        fielddata = [str(x) for x in fielddata]
        outstr += "\n   ".join(fielddata)
    else:
        outstr += str(fielddata)
    return outstr


def list_from_WOSlist(raw, key=None):
    # TODO: Needs a refactor to handle if raw is just a list rather than a dict.
    if isinstance(raw, list):
        # This is the expected configuration
        if key is None:
            return raw
        else:
            return [x[key] for x in raw]
    elif isinstance(raw, dict):
        if key is None:
            return raw
        else:
            return raw[key]
    else:
        return [raw]


def dict_from_WOSlist(raw, key="type", content="content"):
    try:
        return {x[key]: x[content] for x in raw}
    except TypeError:
        return {raw[key]: raw[content]}


def dict_from_WOSmultilist(raw, key="type", content="content"):
    finaldict = dict()
    for x in raw:
        try:
            finaldict[x[key]] += "; {}".format(x[content])
        except KeyError:
            finaldict[x[key]] = x[content]
    return finaldict


def make_field_dict(rawdata, printmissing=False):
    # This multiple try/except segment is long-winded but right now I'm leaving it here for ease of understanding
    # It could possibly be done with another sub-function

    # TODO: Look at FITTING the data in here to the published model and fix it to be so if needed.
    #   - Make model validator
    #   - Make code which fixes non-canonical output to be in model style
    #   - Parse KNOWN GOOD models to fit appropriately
    workingdict = dict()
    missing = set()
    # Parse simple fields
    try:
        workingdict["PT"] = rawdata["static_data"]["summary"]["pub_info"]["pubtype"][0]
    except KeyError:
        missing.add("PT")

    try:
        if rawdata["static_data"]["fullrecord_metadata"]["languages"]["count"] <= 1:
            workingdict["LA"] = rawdata["static_data"]["fullrecord_metadata"]["languages"]["language"]["content"]
        else:
            ladict = dict_from_WOSlist(rawdata["static_data"]["fullrecord_metadata"]["languages"]["language"])
            workingdict["LA"] = ladict["primary"]
    except KeyError:
        missing.add("LA")

    try:
        workingdict["DT"] = rawdata["static_data"]["summary"]["doctypes"]["doctype"]
    except KeyError:
        missing.add("DT")

    try:
        workingdict["AB"] = rawdata["static_data"]["fullrecord_metadata"]["abstracts"]["abstract"]["abstract_text"]["p"]
    except KeyError:
        missing.add("AB")

    try:
        workingdict["RP"] = rawdata["static_data"]["fullrecord_metadata"]["reprint_addresses"]["address_name"]["address_spec"]["full_address"]
    except KeyError:
        missing.add("RP")
    except TypeError:
        # Right now if we can't get a single address we ignore it.
        # In future this dict should be correctly parsed, see WOS:000477903700010
        missing.add("RP")

    try:
        workingdict["NR"] = rawdata["static_data"]["fullrecord_metadata"]["refs"]["count"]
    except KeyError:
        missing.add("NR")

    try:
        workingdict["TC"] = rawdata["dynamic_data"]["citation_related"]["tc_list"]["silo_tc"]["local_count"]
    except KeyError:
        missing.add("TC")

    try:
        workingdict["PU"] = rawdata["static_data"]["summary"]["publishers"]["publisher"]["names"]["name"]["full_name"]
    except KeyError:
        missing.add("PU")

    try:
        workingdict["PI"] = rawdata["static_data"]["summary"]["publishers"]["publisher"]["address_spec"]["city"]
    except KeyError:
        missing.add("PI")

    try:
        workingdict["PA"] = rawdata["static_data"]["summary"]["publishers"]["publisher"]["address_spec"]["full_address"]
    except KeyError:
        missing.add("PA")

    try:
        workingdict["PD"] = rawdata["static_data"]["summary"]["pub_info"]["pubmonth"]
    except KeyError:
        missing.add("PD")

    try:
        workingdict["PY"] = rawdata["static_data"]["summary"]["pub_info"]["pubyear"]
    except KeyError:
        missing.add("PY")

    try:
        workingdict["VL"] = rawdata["static_data"]["summary"]["pub_info"]["vol"]
    except KeyError:
        missing.add("VL")

    try:
        workingdict["IS"] = rawdata["static_data"]["summary"]["pub_info"]["issue"]
    except KeyError:
        missing.add("IS")

    try:
        workingdict["PG"] = rawdata["static_data"]["summary"]["pub_info"]["page"]["page_count"]
    except KeyError:
        missing.add("PG")

    try:
        workingdict["GA"] = rawdata["static_data"]["item"]["ids"]["content"]
    except KeyError:
        missing.add("GA")

    try:
        workingdict["UT"] = rawdata["UID"]
    except KeyError:
        missing.add("UT")

    # Parse lists from lists of dicts
    try:
        workingdict["AU"] = list_from_WOSlist(rawdata["static_data"]["summary"]["names"]["name"], "wos_standard")
    except KeyError:
        missing.add("AU")

    try:
        workingdict["AF"] = list_from_WOSlist(rawdata["static_data"]["summary"]["names"]["name"], "full_name")
    except KeyError:
        missing.add("AF")
    #     workingdict["OI"] = list_from_WOSlist(rawdata["static_data"]["summary"]["names"]["name"], "orcid_id")

    try:
        workingdict["ID"] = list_from_WOSlist(rawdata["static_data"]["item"]["keywords_plus"]["keyword"])
    except KeyError:
        missing.add("ID")
    #     workingdict["C1"] = list_from_WOSlist(rawdata["static_data"]["summary"]["names"]["name"])

    # Parse dicts from lists of dicts
    titlesdict = dict_from_WOSlist(rawdata["static_data"]["summary"]["titles"]["title"])

    try:
        workingdict["TI"] = titlesdict["item"]
    except KeyError:
        missing.add("TI")

    try:
        workingdict["SO"] = titlesdict["source"]
    except KeyError:
        missing.add("SO")

    try:
        workingdict["J9"] = titlesdict["abbrev_29"]
    except KeyError:
        missing.add("J9")

    try:
        workingdict["JI"] = titlesdict["abbrev_iso"]
    except KeyError:
        missing.add("JI")

    identdict = {}
    try:
        identdict = dict_from_WOSlist(rawdata["dynamic_data"]["cluster_related"]["identifiers"]["identifier"],
                                      content="value")
    except (TypeError, KeyError):
        missing.update(["AR", "DI", "PM", "SN", "EI"])

    if identdict:
        try:
            workingdict["AR"] = identdict["art_no"]
        except KeyError:
            missing.add("AR")

        try:
            workingdict["DI"] = identdict["doi"]
        except KeyError:
            missing.add("DI")

        try:
            workingdict["PM"] = identdict["pmid"]
        except KeyError:
            missing.add("PM")

        try:
            workingdict["SN"] = identdict["issn"]
        except KeyError:
            missing.add("SN")

        try:
            workingdict["EI"] = identdict["eissn"]
        except KeyError:
            missing.add("EI")
    categorydict = {}
    try:
        categorydict = dict_from_WOSmultilist(
            rawdata["static_data"]["fullrecord_metadata"]["category_info"]["subjects"]["subject"],
            key="ascatype")
    except (TypeError, KeyError):
        missing.update(["WC", "SC"])

    try:
        workingdict["WC"] = categorydict["traditional"]
    except KeyError:
        missing.add("WC")

    try:
        workingdict["SC"] = categorydict["extended"]
    except KeyError:
        missing.add("SC")

    # End Record
    workingdict["ER"] = ""

    if missing and printmissing:
        print("Missing fields: {}\n".format(missing))
    return workingdict