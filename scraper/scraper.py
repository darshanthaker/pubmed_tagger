import sys
#if sys.version_info < (3, 1):
#    raise Exception("Program must be run with Python3. Rerun please.")
import urllib2
import urllib
import slate
from urlparse import urlparse
import requests
import xml.etree.ElementTree as ET
from HTMLParser import HTMLParser
from bs4 import BeautifulSoup
from cStringIO import StringIO
from pdb import set_trace

from database import MongoWrapper

class NCBIScraper(object):

    def __init__(self, db):
        self.db = db
        self.mongodb = MongoWrapper('test_db')
        # TODO: Remove the following line after testing!!
        self.mongodb.clear_all()
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{}.fcgi?"

    def wget(self, url, params):
        encoded_params = urllib.urlencode(params)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        try:
            response = opener.open(url + encoded_params)
        except Exception as e: 
            print("HTTP Error {}. URL: {}".format(e, url))
            return None, None
        resp = response.read()
        return resp, response.geturl()

    def wget_xml(self, url, params):
        xml, _ = self.wget(url, params) 
        if xml is None:
            return None
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
        eSearchResult = self.wget_xml(base_url, query_params)
        if eSearchResult is None:
            return
        id_list_tag = eSearchResult.find('IdList')
        id_list = list()
        for ids in id_list_tag:
            id_list.append(ids.text)
        self.fetch_data(id_list)
        self.fetch_external_links(id_list)

    def fetch_data(self, id_list):
        base_url = self.base_url.format('efetch')
        data = dict()
        query_params = dict() 
        query_params['db'] = self.db
        query_params['id'] = ','.join(id_list)
        query_params['retmode'] = 'xml'
        pubmedArticleSet = self.wget_xml(base_url, query_params)
        if pubmedArticleSet is None:
            return
        i = 0
        for article in pubmedArticleSet:
            if article.tag == 'PubmedArticle':
                year, abstract_text = self.parse_article(article)
                if year is None and abstract_text is None:
                    continue
                data[id_list[i]] = abstract_text
            i += 1
        #print(data.keys())

    def fetch_external_links(self, id_list):
        base_url = self.base_url.format('elink')
        data = dict()
        query_params = dict()
        query_params['dbfrom'] = self.db
        #query_params['id'] = '24379703'
        query_params['id'] = ','.join(id_list)
        query_params['cmd'] = 'prlinks'
        eLinkResult = self.wget_xml(base_url, query_params)
        if eLinkResult is None:
            return
        url_list = self.bfs_find(eLinkResult, 'IdUrlList')
        for url_set in url_list:
            assert url_set.tag == 'IdUrlSet'
            id, url = self.parse_url_set(url_set)
            self.parse_url(url)

    def parse_url(self, url):
        response, redirect_url = self.wget(url, {})
        if response is None:
            return
        href = None
        try:
            href = self.parse_html(response)
        except UnicodeDecodeError:
            set_trace()
        parsed_url = urlparse(redirect_url)
        final_url = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_url)
        if href is None:
            print("Couldn't handle this URL :( : {}".format(redirect_url))
            return
        if not href.startswith(final_url) and \
                not href.startswith(parsed_url.scheme):
            final_url += href 
        else:
            final_url = href
        print("Added: {}".format(final_url))
        req = requests.get(final_url)
        pdf = StringIO(req.content)
        #self.dbify(pdf)

    def parse_html(self, data):
        soup = BeautifulSoup(data, 'lxml')
        links = soup.find_all('a')
        for link in links:
            href = link.get('href')
            if href is not None and 'pdf' in href:
                return href

    def dbify(self, pdf):
        doc = slate.PDF(pdf)
        doc = ' '.join(doc)
        entry = {'data': doc}
        self.mongodb.add_entry(entry)

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

class PDFHTMLParsertmp(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and any('pdf' in t for a in attrs for t in a):
            href_ind = [x[0] for x in attrs].index('href')
            self.href = attrs[href_ind][1]

def main():
    scraper = NCBIScraper('pubmed')
    scraper.search({'term': 'cancer', 'retmax': 100})

if __name__ == '__main__':
    main()
