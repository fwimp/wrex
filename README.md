# Web of Science Recursive EXplorer (wrex)
`wrex` is a Python 3.6+ package that wraps the Clarivate Web of Science API and enables quick exploration of a bibliographic space.

## `wrex.WOS`
`wrex` contains a submodule called `WOS` which wraps the WOS API and allows for a simple method to interrogate the API programmatically.

### Usage example
Data in `wrex` is passed around in the form of `WOSpaper` objects, often wrapped into `WOSquery` objects. To perform a query, one uses the `query()` function, along with a `WOSconnection` object (which stores the WOS API connection settings).

#### Making a query
Here is an example of performing a simple query:
```python
WOS = WOSconnection(key="...", parameters={"databaseId": "WOS", "count": 100, "firstRecord": 1})

quertstr = "AU=(Knuth, D*)"
currquery = query(WOS, querystr)
```

This returns a `WOSquery` object containing the unpacked response along with various metadata about the query. To check the status of the query, we can use the `WOSquery.status()` method which will list the number of currently retrieved records along with a general status report of completeness.

If not all the data has been retrieved, we can use the `WOSquery.getall()` method to request the rest of the data. This will query for the data using the connection settings at the time when the original connection was made.

The set of papers returned from the query is available in the dictionary `WOSquery.data`, which is indexed by WOS ID (e.g. "WOS:000111222333444")

The entire `WOSquery` object is iterable, and returns each `WOSpaper` object in turn:
```python
for x in testquery:
    print(x)
```

Finally the entire query can be exported to the WOS text format using `WOSquery.export()` which returns a string ready to be printed to a file.

#### Extracting and inspecting a single paper
To extract a paper from the query, one simply needs to index the data dict as follows:
```python
currpaper = currquery.data["WOS:A1972O163300004"]
```

You can then print the `WOSpaper` object to reveal simple data about the paper:

```python
print(currpaper)
```
_Output:_
```
UID: WOS:A1972O163300004
Title: HISTORY OF SORTING
Authors: KNUTH, DE and 0 other/s
```

If we wish to see more data about the paper we have two main options. Either we access the raw data from `WOSpaper.rawdata` or we can print the dictionary of fields using `WOSpaper.fielddict()`:
```python
print(currpaper.fielddict())
```
_Output:_
```
PT J
LA English
DT Article
NR 0
TC 0
PU CAHNERS-DENVER PUBLISHING CO
PI OAK BROOK
PA 2000 CLEARWATER DR, OAK BROOK, IL 60523-8809
PY 1972
VL 18
IS 12
PG 0
GA O1633
UT WOS:A1972O163300004
AU KNUTH, DE
AF KNUTH, DE
TI HISTORY OF SORTING
SO DATAMATION
J9 DATAMATION
JI Datamation
SN 0011-6963
WC Computer Science, Hardware & Architecture; Computer Science, Software Engineering
SC Computer Science
ER
```
