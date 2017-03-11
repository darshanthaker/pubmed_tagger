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
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{}.fcgi?"

    def wget(self, url, params):
        encoded_params = urllib.parse.urlencode(params)
        response = urllib.request.urlopen(url + encoded_params)
        xml = response.read().decode('utf-8')
        root = ET.fromstring(xml)
        return root

    def bfs_find(self, root, to_find):
        queue = [root]
        while len(queue) > 0:
            node = queue.pop(0)
            if node.tag == to_find:
                return node
            for neighbor in node:
                queue.append(neighbor)

    def search(self, query_params):
        assert isinstance(query_params, dict)
        base_url = self.base_url.format('esearch')
        query_params['db'] = self.db
        eSearchResult = self.wget(base_url, query_params)
        id_list_tag = eSearchResult.find('IdList')
        id_list = list()
        for ids in id_list_tag:
            id_list.append(ids.text)
        self.fetch_data(id_list)

    def fetch_data(self, id_list):
        base_url = self.base_url.format('efetch')
        test_id = '28277836'
        query_params = dict() 
        query_params['db'] = self.db
        query_params['id'] = test_id
        query_params['retmode'] = 'xml'
        pubmedArticleSet = self.wget(base_url, query_params)
        for article in pubmedArticleSet:
            self.parse_article(article)

    def parse_article(self, article):
        date_revised_tag = self.bfs_find(article, 'DateRevised')
        year = date_revised_tag[0].text
        abstract_text_tag = self.bfs_find(article, 'AbstractText')
        abstract_text = abstract_text_tag.text
         
def main():
    scraper = NCBIScraper('pubmed')
    scraper.search({'term': 'cancer', 'retmax': 100})

if __name__ == '__main__':
    main()
