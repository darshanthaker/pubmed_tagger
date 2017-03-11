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
        self.fetch_external_links(id_list)

    def fetch_data(self, id_list):
        base_url = self.base_url.format('efetch')
        data = dict()
        query_params = dict() 
        query_params['db'] = self.db
        query_params['id'] = ','.join(id_list)
        query_params['retmode'] = 'xml'
        pubmedArticleSet = self.wget(base_url, query_params)
        i = 0
        for article in pubmedArticleSet:
            if article.tag == 'PubmedArticle':
                year, abstract_text = self.parse_article(article)
                if year is None and abstract_text is None:
                    continue
                data[id_list[i]] = abstract_text
            i += 1
        print(data)

    def fetch_external_links(self, id_list):
        base_url = self.base_url.format('elink')
        data = dict()
        query_params = dict()
        query_params['dbfrom'] = self.db
        query_params['id'] = '28278500'
        #query_params['id'] = ','.join(id_list)
        query_params['cmd'] = 'prlinks'
        eLinkResult = self.wget(base_url, query_params)
        url_list = self.bfs_find(eLinkResult, 'IdUrlList')
        for url_set in url_list:
            assert url_set.tag == 'IdUrlSet'
            id, url = self.parse_url_set(url_set)
            self.parse_url(url)

    def parse_url(self, url):
        pass

    def parse_url_set(self, url_set):
        id = self.bfs_find(url_set, 'Id').text
        url = self.bfs_find(url_set, 'Url').text
        return id, url

    def parse_article(self, article):
        try:
            date_revised_tag = self.bfs_find(article, 'DateRevised')
            year = date_revised_tag[0].text
            abstract_text_tag = self.bfs_find(article, 'AbstractText')
            abstract_text = abstract_text_tag.text
        except:
            return None, None
        return year, abstract_text
         
def main():
    scraper = NCBIScraper('pubmed')
    scraper.search({'term': 'cancer', 'retmax': 100})

if __name__ == '__main__':
    main()
