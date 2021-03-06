import sys
#if sys.version_info < (3, 1):
#    raise Exception("Program must be run with Python3. Rerun please.")
import urllib2
import urllib
import textract
from urlparse import urlparse
import requests
import xml.etree.ElementTree as ET
from HTMLParser import HTMLParser
from bs4 import BeautifulSoup
import tempfile
from pdb import set_trace

from database import MongoWrapper
from query import craft_query
from util import timing

class GenericScraper(object):

    def __init__(self):
        pass

    def wget(self, url, params={}, headers=None):
        encoded_params = urllib.urlencode(params)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        if headers is not None:
            opener.addheaders = headers
        try:
            response = opener.open(url + encoded_params)
        except Exception as e: 
            print("{}. URL: {}".format(e, url + encoded_params))
            return None, None
        resp = response.read()
        return resp, response.geturl()

    def wget_xml(self, url, params):
        xml, _ = self.wget(url, params=params) 
        if xml is None:
            return None
        root = ET.fromstring(xml)
        return root

    def equivalent_urlschemes(self, href, scheme):
        if href.startswith(scheme) or href.startswith('http'):
            return True
        else:
            return False

    # exclude_words is a manually identified list of edge cases.
    def parse_html(self, data, primary_tag='a', secondary_tag='href', \
            include_words=['pdf'], exclude_words=['epdf', 'pdf+html'], \
            download_words=['download pdf', 'pdf']):
        soup = BeautifulSoup(data, 'lxml')
        links = soup.find_all(primary_tag)
        tags = list()
        for link in links:
            tag = link.get(secondary_tag)
            if tag is None:
                continue
            include = all([x in tag for x in include_words])
            exclude = all([x not in tag for x in exclude_words])
            download = any([x in link.get_text().lower() for x in download_words])
            if (include and exclude) or download:
                tags.append((tag, download))
        # Prefer links that contain keywords in download_words.
        tags = sorted(tags, key=lambda x: not x[1])
        #if len(tags) > 1:
        #    print(tags)
        if len(tags) != 0:
            return tags[0][0]

    def add_to_db(self, data, mongodb):
        # mongodb.add_entry(data)
        return True

    def parse_pdf(self, pdf, mongodb):
        temp = tempfile.NamedTemporaryFile(suffix='.pdf')
        temp.write(pdf)
        temp.flush()
        try:
            doc = textract.process(temp.name)
        except:
            print("PDF Parsing failed!")
            temp.close()
            return False
        temp.close()
        entry = {'data': doc}
        self.add_to_db(entry, mongodb)
        return True

class ElsevierScraper(GenericScraper):

    def __init__(self, mongodb):
        self.mongodb = mongodb
        self.base_url = 'https://api.elsevier.com/content/article/pii/{}'    
        self.api_key = 'c989efb8e4d2c0474a3c4fa3007d2b72'

    def get_pii(self, url):
        start_index = url.find('pii/') + len('pii/')
        if start_index == -1:
            return None
        return url[start_index:]

    def parse_url(self, url):
        if 'elsevier' not in url:
            return False
        pii = self.get_pii(url)
        base_url = self.base_url.format(pii)
        if pii is None:
            return False
        headers = [('X-ELS-APIKey', self.api_key), ('Accept', 'text/plain')]
        response, _ = self.wget(base_url, headers=headers)
        print("Added: {}".format(url))
        entry = {'data': response}
        return self.add_to_db(entry, self.mongodb)

class WileyScraper(GenericScraper):

    def __init__(self, mongodb):
        self.mongodb = mongodb

    def parse_url(self, url):
        if 'wiley' not in url:
            return False
        response, _ = self.wget(url)
        if response is None:
            return False
        pdf_href = self.parse_html(response)
        if pdf_href is None:
            return False
        response, _ = self.wget(pdf_href)  
        if response is None:
            return False
        pdf_href = self.parse_html(response, primary_tag='iframe', secondary_tag='src')
        if pdf_href is None:
            return False
        response, _ = self.wget(pdf_href)
        if response is None:
            return False
        print("Added: {}".format(url))
        return self.parse_pdf(response, self.mongodb)

class ASCOScraper(GenericScraper):

    def __init__(self, mongodb):
        self.mongodb = mongodb

    def parse_url(self, url):
        if 'asco' not in url:
            return False
        response, redirect_url = self.wget(url)
        if response is None:
            return False
        href = self.parse_html(response)
        href = href.replace('pdf', 'pdfdirect')
        parsed_url = urlparse(redirect_url)
        final_url = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_url)
        if href is None:
            print("Couldn't handle this URL :( : {}".format(redirect_url))
            return False
        if not self.equivalent_urlschemes(href, parsed_url.scheme):
            if not href.startswith('/'):
                final_url += '/' + href
            else:
                final_url += href 
        else:
            final_url = href
        try:
            req = requests.get(final_url)
        except requests.exceptions.ConnectionError as e:
            print("Connection Error in getting pdf from {}".format(final_url))
            return False

        print("Added: {}".format(final_url))
        return self.parse_pdf(req.content, self.mongodb)

class OvidScraper(GenericScraper):

    def __init__(self, mongodb):
        self.mongodb = mongodb

    def get_ovid_from_line(self, link):
        url = None
        ovid = 'ovidFullTextUrlForButtons'
        for line in link.get_text().splitlines():
            if ovid in line:
                start = line.find('"')   
                end = line.find('"', start + 1)
                url = line[start + 1:end]
                break
        return url 

    def get_ovid_url(self, data):
        soup = BeautifulSoup(data, 'lxml')
        links = soup.find_all('script')
        ovid = 'ovidFullTextUrlForButtons'
        for link in links:
            if ovid not in link.get_text():
                continue
            url = self.get_ovid_from_line(link)
            if url is not None:
                return url 

    def ovidweb(ovid_url):
        pass

    def parse_url(self, url):
        if 'ovid' not in url:
            return False
        response, _ = self.wget(url) 
        if response is None:
            return False
        ovid_url = self.get_ovid_url(response)
        if ovid_url is None:
            return False
        if 'ovidweb' in ovid_url:
            return ovidweb(ovid_url)
        response, redirect_url = self.wget(ovid_url)
        href = self.parse_html(response, primary_tag='iframe', secondary_tag='src')

        parsed_url = urlparse(redirect_url)
        final_url = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_url)
        if href is None:
            print("Couldn't handle this URL :( : {}".format(redirect_url))
            return False
        if not self.equivalent_urlschemes(href, parsed_url.scheme):
            if not href.startswith('/'):
                final_url += '/' + href
            else:
                final_url += href 
        else:
            final_url = href
        try:
            req = requests.get(final_url)
        except requests.exceptions.ConnectionError as e:
            print("Connection Error in getting pdf from {}".format(final_url))
            return False

        print("Added: {}".format(final_url))
        return self.parse_pdf(req.content, self.mongodb)
        
class NCBIScraper(GenericScraper):


    def __init__(self, db):
        self.mongodb = MongoWrapper('test_db')
        # TODO: Remove the following line after testing!!
        self.mongodb.clear_all()
        self.elsevier_scraper = ElsevierScraper(self.mongodb)
        self.wiley_scraper = WileyScraper(self.mongodb)
        self.asco_scraper = ASCOScraper(self.mongodb)
        self.ovid_scraper = OvidScraper(self.mongodb)
        self.db = db
        self.all_scrapers = {'elsevier': (self.elsevier_scraper, False), \
                             'asco': (self.asco_scraper, False), \
                             'wiley': (self.wiley_scraper, True), \
                             'ovid': (self.ovid_scraper, True), \
                             '': (self, False)} # Default scraper.
        self.successful = 0
        self.total = 0
        self.id_to_journals = dict()
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{}.fcgi?"

    def search(self, query_params):
        assert isinstance(query_params, dict)
        base_url = self.base_url.format('esearch')
        query_params['db'] = self.db
        query_params['usehistory'] = 'y'
        eSearchResult = self.wget_xml(base_url, query_params)
        if eSearchResult is None:
            return
        count = int(eSearchResult.find('Count').text)
        webenv = eSearchResult.find('WebEnv').text
        retmax = 400
        for i in range(0, count, retmax):
            query_params['WebEnv'] = webenv
            query_params['retstart'] = i   
            query_params['retmax'] = retmax
            self.limited_search(query_params)
    
    def limited_search(self, query_params):
        base_url = self.base_url.format('esearch')
        eSearchResult = self.wget_xml(base_url, query_params)
        if eSearchResult is None:
            return
        id_list_tag = eSearchResult.find('IdList')
        id_list = list()
        for ids in id_list_tag:
            id_list.append(ids.text)
        journals = self.fetch_abstracts(id_list)
        self.fetch_external_links(id_list)

    def bfs_find(self, root, to_find):
        queue = [root]
        while len(queue) > 0:
            node = queue.pop(0)
            if node.tag == to_find:
                return node
            for neighbor in node:
                queue.append(neighbor)

    def fetch_abstracts(self, id_list):
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
                [_, abstract_text, journal] = self.parse_article(article)
                if abstract_text is None and journal is None:
                    print("COULDNT FIND")
                    continue
                print("journal: {}".format(journal))
                data[id_list[i]] = abstract_text
                self.id_to_journals[id_list[i]] = journal
            i += 1
        #print(data.keys())
        return journals

    def try_all_scrapers(self, id, url):
        _, redirect_url = self.wget(url) # Get redirect URL
        for (keyword, val) in self.all_scrapers:
            scraper = val[0]
            use_redirect = val[1]
            if use_redirect:
                new_url = redirect_url
            else:
                new_url = url
            if new_url is None:
                return
            if keyword in new_url:
                if self.scraper.parse_url(new_url):
                    self.successful += 1
                    print("Successful journal: {}".format(self.id_to_journals[id]))
                return
         
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
            if url is None:
                continue
            self.total += 1
            if self.total == 100:
                print("STATUS UPDATE: {}/{}".format(self.successful, self.total))
            self.try_all_scrapers(id, url)
"""            
            if 'elsevier' in url:
                if self.elsevier_scraper.parse_url(url):
                    self.successful += 1
                continue
            if 'asco' in url:
                if self.asco_scraper.parse_url(url):
                    self.successful += 1
                continue
            if redirect_url is None:
                continue
            if 'wiley' in redirect_url:
                if self.wiley_scraper.parse_url(redirect_url):
                    self.successful += 1
                continue
            if 'ovid' in redirect_url:
                if self.ovid_scraper.parse_url(redirect_url):
                    self.successful += 1
                continue
            if self.parse_url(url):
                self.successful += 1
"""

    def parse_url(self, url):
        response, redirect_url = self.wget(url)
        if response is None:
            return False
        href = None
        try:
            href = self.parse_html(response)
        except UnicodeDecodeError:
            set_trace()
        parsed_url = urlparse(redirect_url)
        final_url = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_url)
        if href is None:
            print("Couldn't handle this URL :( : {}".format(redirect_url))
            return False
        #if not href.startswith(final_url) and \
        if not self.equivalent_urlschemes(href, parsed_url.scheme):
            if not href.startswith('/'):
                final_url += '/' + href
            else:
                final_url += href 
        else:
            final_url = href
        try:
            req = requests.get(final_url)
        except requests.exceptions.ConnectionError as e:
            print("Connection Error in getting pdf from {}".format(final_url))
            return False

        print("Added: {}".format(final_url))
        #if not self.parse_pdf(req.content, self.mongodb):
        #    set_trace()
        return self.parse_pdf(req.content, self.mongodb)
        
    def parse_url_set(self, url_set):
        id = self.bfs_find(url_set, 'Id').text
        url = self.bfs_find(url_set, 'Url')
        if url is not None:
            url = url.text
        return id, url

    def parse_article(self, article):
        try:
            journal_tag = self.bfs_find(article, 'Journal')
            journal_name = self.bfs_find(journal_tag, 'Title').text
        except:
            journal_name = None
        try:
            year = self.bfs_find(article, 'DateRevised')[0].text
        except:
            year = None
        try:
            abstract_text = self.bfs_find(article, 'AbstractText').text
        except:
            abstract_text = None
        return [year, abstract_text, journal_name]

@timing
def main():
    scraper = NCBIScraper('pubmed')
    query = craft_query('queries/stillbirth')
    scraper.search({'term': query})
    print("Retrieved {}/{} successfully".format(scraper.successful, scraper.total))

if __name__ == '__main__':
    main()
