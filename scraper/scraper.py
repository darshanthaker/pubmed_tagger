import sys
# In order to import urllib.request successfully.
if sys.version_info < (3, 1):
    raise Exception("Program must be run with Python3. Rerun please.")
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pdb import set_trace

class NCBIScraper(object):

    def __init__(self, db):
        self.db = db
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"

    def search(self, query_params):
        assert isinstance(query_params, dict)
        query_params['db'] = self.db
        encoded_params = urllib.parse.urlencode(query_params)
        response = urllib.request.urlopen(self.base_url + encoded_params)
        html = response.read().decode('utf-8')
        tree = ET.fromstring(html)
        idlist_tag = tree.find('IdList')
        idlist = list()
        for child in idlist_tag:
            idlist.append(child.text)
        self.fetch(idlist)

    def fetch(self, idlist):
        pass

def main():
    scraper = NCBIScraper('pubmed')
    scraper.search({'term': 'cancer', 'retmax': 100})

if __name__ == '__main__':
    main()
