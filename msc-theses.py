#! /usr/bin/env python3

import requests
import json
import argparse
import os
import time
import datetime
import glob
import pprint
from lxml import html  as lxml_html
from lxml import etree as lxml_etree

years = [ '2021', '2022', '2023', '2024', '2025' ]
major = None

school_info_bsc = [ ('SCI',  'BSc', '045c30ab-bee2-4e5a-9fa1-89a9e18e087b', 63),
                    ('ELEC', 'BSc', '310a65a5-b8ba-44dc-9b26-da36cc4414d8', 48) ]

school_info_msc = [ ('SCI',  'MSc', 'af72e803-f468-4c81-802c-7b8ff8602294', 87),
                    ('ELEC', 'MSc', '9785ec69-7098-4c4a-88d8-32422966cd06', 46),
                    ('ENG',  'MSc', 'fa8d40ed-d19a-4768-bd06-60b5d533195c', 67),
                    ('ARTS', 'MSc', '81ea0a41-6f6f-4cad-98a6-6e09bd6b8068', 72) ]

school_info_dsc = [ ('SCI',  'DSc', 'c019eaac-587a-4f4b-af66-fef325a15a25', 13),
                    ('ELEC', 'DSc', '901639ca-22f7-4fbb-86dd-ec22d2746053', 10) ]

school_info = []

long_names = { 'aat'   : 'Acoustics and Audio Technology',
               'cs'    : 'Computer Science',
               'cs/al' : 'Computer Science / Algorithms, Logic, and Computation',
               'cs/bd' : 'Computer Science / Big Data and Large-Scale Computing',
               'cs/ss' : 'Computer Science / Software Systems and Technologies',
               'cs/wt' : 'Computer Science / Web Technologies, Application and Science',
               'game'  : 'Game Desing and Production',
               'hci'   : 'Human-Computer Interaction',
               'mac'   : 'Macadamia',
               'sec'   : 'Security and Cloud Computing',
               'sse'   : 'Software and Service Engineering',
               'sse/es': 'Software and Service Engineering / Enterprise Systems',
               'sse/sd': 'Software and Service Engineering / Service Design and Engineering',
               'sse/se': 'Software and Service Engineering / Software Engineering',
               'inf'   : 'Information Networks',
               'lstbi' : 'Life Science Bioinformatics and Digital Health',
               'lstbs' : 'Life Science Biosensing and Bioelectronics',
               'lstcs' : 'Life Science Complex Systems',
               'eitcn' : 'EIT Cloud and Network Infrastructures',
               'eitds' : 'EIT Data Science',
               'eithc' : 'EIT HCID',
               'eitvc' : 'EIT Visual Computing and Communication',
               'unk'   : 'unknown major'
              }

major_names = { # BSc
                'SCI3027': 'Tietotekniikka',
                'SCI3026': 'Informaatioverkostot',
                'SCI3029': 'Matematiikka',
                'SCI3103': 'Quantum technology',

                # MSc
                'SCI3042':  'Computer science',
                'SCI3043':  'SSE',
                'SCI3044':  'Macadamia',
                'SCI3046':  'Game design and development',
                'SCI3047':  'Information networks',
                'SCI3053':  'Applied mathematics',
                'SCI3059':  'Biomedical engineering',
                'SCI3060':  'Complex systems',
                'SCI3062':  'International design business management',
                'SCI3068':  'Computer science (minor)',
                'SCI3070':  'Macadamia (minor)',
                'SCI3084':  'Security',
                'SCI3085':  'Security and cloud computing (minor)',
                'SCI3092':  'Bioinformatics and digital health',
                'SCI3097':  'Human-computer interaction',
                'SCI3113':  'SECCLO',

                'SCI3020':  'EIT ICT Human-computer intearction and design',
                'SCI3081':  'EIT ICT Cloud computing and services',
                'SCI3095':  'EIT ICT Data science',
                'SCI3102':  'EIT ICT Visual computing',
                'SCI3115':  'EIT ICT Data science',

                'ELEC3025': 'Control, robotics and autonomous systems',
                'ELEC3029': 'Communications engineering',
                'ELEC3030': 'Acoustics and audio technology',
                'ELEC3031': 'Signal, speech and language processing',
                'ELEC3049': 'Signal processing and data science',
                'ELEC3055': 'Autonomous systems',
                'ELEC3060': 'Electronic and digital systems',
                'ELEC3068': 'Speech and language technology'
              }

# ??? Security and Cloud Computing
# ??? Machine Learning, Data Science and Artificial Intelligenc
# ??? Human-Computer Interaction and Design
# ??? Software and Service Engineering
# ??? Machine Learning, Data Science and Artificial Intelligence (sivuaine
# ??? Cloud and Network Infrastructures

major_names_inv = {}
for k, v in major_names.items():
    if k in ['SCI3095']:
        continue
    if v.find('EIT ICT ')==0:
        v = v[8:]
    v = v.lower()
    assert v not in major_names_inv, \
        f'major_names_inv[] not unique "{v}" -> {major_names_inv[v]} vs {k}'
    major_names_inv[v] = k

use_cache = True
cache_dir = None

majors = {}
alias  = {}
theses = {}

def hack_html(html):
    p = html.find('<html ')
    if p>0:
        html = '<?xml version="1.0"?>\n'+html[p:]
    return html

def html_to_dict(html, debug = False):
    html2   = hack_html(html)
    if html2.lower().find('html')<0:
        print("Doesn't seem like an HTML file.")
        return {}
    #print(html2)
    restree = lxml_html.fromstring(html2)
    tree    = lxml_etree.ElementTree(restree)
    rec = {}
    ff = ['citation_author', 'citation_title', 'citation_publication_date']
    for f in ff:
        for meta in restree.xpath(f"//meta[@name='{f}']"):
            v = meta.attrib['content']
            if debug:
                print(f, v)
            if f=='citation_title':
                rec['title'] = ' '.join(v.split())
            if f=='citation_author':
                rec['author'] = v
            if f=='citation_publication_date':
                rec['issued'] = v

    if 'issued' not in rec:
        rec['issued'] = 'unknown'        

    for div in restree.xpath("//div[@_ngcontent-sc160='' and @class='simple-view-element']"):
        # print(div)
        l1 = div.xpath('h5')
        l2 = div.xpath('div/span')
        if debug and len(l1):
            print(l1[0].text, len(l2))
        if len(l1)==1 and len(l2)>0:
            if debug:
                print(l1[0].text, l2[0].text)
            k = l1[0].text
            v = l2[0].text
            w = []
            for i in l2:
                if i.text != ', ':
                    w.append(i.text)
            if debug and len(w):
                print(l1[0].text, w)

            if k=='Major/Subject' or k=='Oppiaine':
                rec['major'] = v
            if k=='Mcode':
                rec['major_code'] = v
            if k=='Degree programme' or k=='Koulutusohjelma':
                rec['degree_programme'] = v
            if k=='Language' or k=='Kieli':
                rec['language'] = v
            if k=='Pages' or k=='Sivut':
                rec['pages'] = v
            if k=='Keywords' or k=='Avainsanat':
                rec['keywords'] = w

    l = restree.xpath("//ds-aalto-item-supervisor")
    assert len(l)==1, f'failed with supervisor: <{html2}>'
    m = l[0].xpath('div/h5')
    if len(m)>0:
        v = m[0].tail
    else:
        v = "unknown"
    rec['supervisor'] = v.strip()
                
    l = restree.xpath("//ds-aalto-item-advisor")
    assert len(l)==1, 'failed with advisor'
    m = l[0].xpath('div/h5')
    if len(m)==1:
        v = m[0].tail
        rec['advisor'] = v.strip()

    abstxt = []
    l = restree.xpath("//ds-aalto-item-abstract")
    assert len(l)==1, 'failed with abstract 1'
    for m in l[0].xpath('div/span'):
        if m.text:
            t = m.text.replace('\n', ' ').replace('  ', ' ')
            abstxt.append(t)
    # assert len(abstxt), 'failed with abstract 2'
    if abstxt:
        rec['abstract'] = ' | '.join(abstxt)    

    l = restree.xpath("//a[@_ngcontent-sc450='']")
    # assert len(l)<=1, 'failed with files'
    rec['available'] = len(l)>0
    if len(l):
        #print(l[0].attrib['href'])
        rec['url_pdf'] = f'https://aaltodoc.aalto.fi{l[0].attrib["href"]}'
    # print(rec)
    
    return rec

def html_to_links(html):
    l        = []
    restree  = lxml_html.fromstring(hack_html(html))
    tree     = lxml_etree.ElementTree(restree)
    #a_xpath = "//div[@_ngcontent-sc57='']/a[@_ngcontent-sc60='']"
    #a_xpath = "//div[@_ngcontent-dspace-angular-c79='']/a[@_ngcontent-dspace-angular-c127='']"
    a_xpath  = "//ds-truncatable/div/a"
    for a in restree.xpath(a_xpath):
        href = a.attrib['href']
        # print(a, href)
        l.append(href)
    return l

def swap_name(n):
    p = n.find(', ')
    return n[p+2:]+' '+n[:p]
    
def swap_name_not(n):
    p = n.find(', ')
    return n[:p]+n[p+1:] if p>0 else None
    
def fetch_faculty(debug):
    url = 'https://www.aalto.fi/en/department-of-computer-science/contact-us'
    print(f'Scraping names of Aalto CS faculty members from {url}')
    response = requests.request('GET', url)
    if response.status_code!=200:
        return None
    html = response.text
    print(html, file=open('faculty.html', 'w'))
    l = []
    for k, v in alias.items():
        l.append(v)
    restree = lxml_html.fromstring(hack_html(html))
    tree    = lxml_etree.ElementTree(restree)
    if debug:
        print(tree)
    #for td in restree.xpath("//div[@class='aalto-table-wrapper']/table/tbody/tr/td[1]"):
    for td in restree.xpath("//div[@class='aalto-table-wrapper']/table/tbody"):
        if debug:
            print(td)
        if td.text:
            n = td.text.strip()
        else: # <a>
            n = td.getchildren()[0].text.strip()
        #print(td, n)
        if n!="Firstname Lastname" and n not in l:
            l.append(n)
    return l

def fetch_faculty_old2(debug):
    url = 'https://www.aalto.fi/en/department-of-computer-science/contact-us'
    print(f'Scraping names of Aalto CS faculty members from {url}')
    response = requests.request('GET', url)
    if response.status_code!=200:
        return None
    html = response.text
    #html = open('f.html').read()
    l = []
    for k, v in alias.items():
        l.append(v)
    restree = lxml_html.fromstring(hack_html(html))
    tree    = lxml_etree.ElementTree(restree)
    for td in restree.xpath("//div[@class='aalto-table-wrapper']/table/tbody/tr/td[1]"):
        if debug:
            print(td)
        if td.text:
            n = td.text.strip()
        else: # <a>
            n = td.getchildren()[0].text.strip()
        #print(td, n)
        if n!="Firstname Lastname" and n not in l:
            l.append(n)
    return l

def fetch_faculty_old1():
    url = 'https://www.aalto.fi/en/department-of-computer-science/faculty-members'
    print(f'Scraping names of Aalto CS faculty members from {url}')
    response = requests.request('GET', url)
    if response.status_code!=200:
        return None
    html = response.text
    #html = open('f.html').read()
    l = []
    for k, v in alias.items():
        l.append(v)
    restree = lxml_html.fromstring(hack_html(html))
    tree    = lxml_etree.ElementTree(restree)
    for a in restree.xpath("//a[@class='aalto-profile-card__name-link']"):
        n = a.text.strip()
        #print(a, n)
        if n not in l:
            l.append(n)
    return l

def request_with_loop_exclude_5xx(url, n):
    for i in range(n):
        time.sleep(i)
        response = requests.request('GET', url)
        s = response.status_code
        if s<500 or s>599:
            if s!=200:
                return response
            if response.text.find('<title>DSpace</title>')<0:
                return response
    return response

def request_with_loop_old(url, n):
    for i in range(n):
        response = requests.request('GET', url)
        if response.status_code!=200:
            return response
        if response.text.find('<title>DSpace</title>')<0:
            return response
        time.sleep(i)
    return response

def solve_major_code(rec):
    if 'major_code' in rec:
        return rec['major_code']
    
    # if 'major' in rec:
    #     mc = 'unsolvd'
    #     m = rec['major'].lower()
    #     if m in major_names_inv:
    #         mc = major_names_inv[m]
    #     print()
    #     print(f'SOLVE MAJOR CODE {mc} {rec["major"]}')
    #     return f'?{rec["major"]:.6}'

    return 'unknown'


def fetch_one_thesis(s, l, li, ln, url_base, dump_raw, debug):
    rawi = 0
    print(f'{li}/{ln}\r', end='', flush=True)
    # print(i, url, l, flush=True)
    urlx  = url_base+l
    cfile = cache_dir+'/'+l.split('/')[-1]
    jfile = cfile+'.json'
    text  = None
    d = None
    jfilex = None
    #print(l, urlx, cfile)
    if use_cache and os.path.isfile(cfile) and os.path.getsize(cfile):
        if os.path.isfile(jfile) and os.path.getsize(jfile):
            d = json.loads(open(jfile).read())
            if debug:
                print(f'    read JSON       {jfile} -> {urlx}')
        else:
           jfilex = jfile 

        if not d:
            text  = open(cfile).read()
            if debug:
                print(f'    read cached     {cfile} -> {urlx}')
    else:
        response = request_with_loop_exclude_5xx(urlx, 10)
        if response.status_code!=200:
            print(i, urlx, l, 'error', response.status_code)
        elif response.text=='':
            print(i, urlx, l, 'empty doc', response.status_code)
        else:
            if dump_raw:
                ofilen = url.replace('/', '_').replace('?', '_')+'_'+str(rawi)+'.html'
                ofile = open(ofilen, 'w')
                print(response.text, file=ofile)
                print(f'   ... dumped raw HTML in {ofilen}')
                rawi += 1
            text = response.text
            if use_cache:
                jfilex = jfile
                open(cfile, 'wb').write(text.encode())
                if debug:
                    print(f'    stored in cache {cfile} <- {urlx}')

    if text:
        # open('item-page.html', 'w').write(text)
        d = html_to_dict(text)
        if not d:
            print(i, url, l, 'failed')
            return ({}, True)

    # print(i, url, l, d['author'], flush=True)
    d['url_page'] = urlx
    if jfilex:
        d['cache_html'] = cfile
        d['cache_json'] = jfilex
    d['school']   = s[0]
    if jfilex:
        open(jfilex, 'w').write(json.dumps(d, indent=4)+'\n')
        if debug:
            print(f'    stored in JSON  {jfilex}')

    y  = d['issued'][:4]
    mc = solve_major_code(d)
    if (y in years or 'all' in years) and (major is None or mc==major):
        return (d, False)
    else:
        return ({}, True)
                                
def fetch_theses(max_pages, dump_raw, debug):
    rec = []
    for s in school_info:
        print(f'Scraping {s[0]} school {s[1]} theses will continue until cp.page={s[3]} or even longer...')
        urlred = None
        for i in range(max_pages):
            url_base = 'https://aaltodoc.aalto.fi'
            # url = f'{url_base}/handle/123456789/{s[2]}'
            url = f'{url_base}/collections/{s[2]}'
            if i>0:
                url = f'{urlred}?cp.page={i+1}'
            print(f'  fetching {s[0]} {s[1]} {url}', flush=True)
            response = request_with_loop_exclude_5xx(url, 10)
            if response.status_code!=200:
                print(i, url, 'error', response.status_code)
                continue

            # open('index-page.html', 'w').write(response.text)
            if urlred is None:
                urlred = response.url
            ll = html_to_links(response.text)
            if len(ll)==0:
                print(i, url, 'failed with no links')
                continue

            do_break = True
            for li, l in enumerate(ll):
                d, b = fetch_one_thesis(s, l, li, len(ll), url_base, dump_raw, debug)
                do_break = do_break and b
                if d:
                    rec.append(d)
                    
            if do_break:
                break
    return rec

def fetch_theses_cache(debug):
    r = []
    for i in glob.glob(cache_dir+'/*.json'):
        #print(i)
        d  = json.loads(open(i).read())
        y  = d.get('issued', '0000')[:4]
        mc = solve_major_code(d)
        if (y in years or 'all' in years) and (major is None or mc==major):
            r.append(d)
    rec = []
    for s in school_info:
        a = []
        for i in r:
            j = i['school'].split(' ')[0]
            if j==s[0]:
                a.append(i)
        rec.extend(sorted(a, key=lambda d: d['issued'], reverse=True))
    return rec

def edit_dist(a, b):
    debug = False
    d = []
    for i in range(1+len(a)):
        d.append([0] * (1+len(b))) 
    
    for j in range(1, 1+len(b)):
        d[0][j] = d[0][j-1]+1
    for i in range(1, 1+len(a)):
        d[i][0] = d[i-1][0]+1

    for j in range(len(b)):
        for i in range(len(a)):
            s = d[i][j]
            x = d[i+1][j]
            if x<s:
                s = x
            x = d[i][j+1]
            if x<s:
                s = x
            s += 0 if a[i]==b[j] else 1
            d[i+1][j+1] = s
    v = d[-1][-1]
    ax = ''.join(sorted([ i.lower() for i in a ]))
    bx = ''.join(sorted([ i.lower() for i in b ]))
    if debug:
        print(a, b, v, ax, bx, ax==bx)
        print(d)
    return v-0.5 if ax==bx else v

no_hit = set()

def name_or_alias(n):
    thr = 1
    debug = False

    if debug:
        print(f'{n} xxxxx')
    if n is None:
        return n
    
    if n in alias:
        return alias[n]
    if n in no_hit:
        if debug:
            print(f'{n} no_hit')
        return None
    nn = n.split()
    for i in theses.keys():
        mm = i.split()
        if debug:
            print(f'  {n} {mm}')
        l0 = len(nn[ 0]) if len(nn[ 0])<len(mm[ 0]) else len(mm[ 0])
        l1 = len(nn[-1]) if len(nn[-1])<len(mm[-1]) else len(mm[-1])
        hit = False
        if (nn[ 0][:l0]==mm[ 0][:l0] or nn[ 0][-l0:]==mm[ 0][-l0:]) and \
           (nn[-1][:l1]==mm[-1][:l1] or nn[-1][-l1:]==mm[-1][-l1:]):
            hit = True
        if not hit and (nn[0]==mm[0] or nn[-1]==mm[-1]):
            ed2 = edit_dist(nn[ 0], mm[ 0])
            ed1 = edit_dist(nn[-1], mm[-1])
            if debug:
                print(f' edit distances: {ed1} + {ed2}')
            if ed1+ed2<=thr:
                hit = True
        if hit:
            alias[n] = i
            return i
    no_hit.add(n)
    return None
    
def match_record(r, roles):
    rr = []
    for i in roles:
        if r.get(i, '')!='':
            rr.append((r[i], i))
    # print(rr)
    fl = []
    for pp, ppr in rr:
        if pp=='unknown':
            continue
        p = pp
        if p.find(',')<0:
            px = p.find(' ')
            if px>0:
                p = p[:px]+','+p[px:]
                #print(f'COMMA ADDED [{pp}]=>[{p}]')
        n = swap_name(p)
        a = name_or_alias(n)
        if a is not None:
            fl.append((a, ppr))
        else: ## odd cases "firstname, familyname"
            n = swap_name_not(p)
            # print(f'p="{p}" n="{n}"')
            # if n is None:
            #     print(r)
            a = name_or_alias(n)
            if a is not None:
                fl.append((a, ppr))
    f = {}
    for iname, irole in fl:
        if irole=='supervisor' or iname not in f:
            f[iname] = irole
            
    for n, role in f.items():
        mc = solve_major_code(r)
        p = mc.find(' ')
        if p>0:
            mc = mc[:p]
            
        assert len(mc)<9, f'too long major_code <{mc}>'
        av = 'AVAILABLE' if r['available'] else 'NOT available'
        e = (swap_name(r['author']), r['title'], r['issued'], r['school'], mc, \
             av, ', '.join(r['keywords']), r.get('abstract', '*** no abstract ***'), \
             role)
        theses[n].append(e)
        #print('FOUND', n, ':', *e)
        if mc not in per_major_code:
            per_major_code[mc] = []
        per_major_code[mc].append(e)

    return f
        
def find_names(t):
    f = set()
    for a in alias.keys():
        if t.find(a)>0:
            f.add(alias[a])
    return f
        
def add_to_majors(a, i):
    if a not in majors:
        majors[a] = set()
    majors[a].add(i)

def find_majors():
    m = { 'aat'  : 'ccis/Acoustics+and+Audio+Technology+%28AAT%29',
          'cs'   : 'ccis/Computer+Science+%28CS%29',
          'game' : 'ccis/Game+Design+and+Production+%28Game%29', 
          'hci'  : 'ccis/Human-Computer+Interaction+%28HCI%29',
          'mac'  : 'ccis/Machine+Learning%2C+Data+Science+and+Artificial+Intelligence+%28Macadamia%29',
          'sec'  : 'ccis/Security+and+Cloud+Computing+%28Security%29',
          'sse'  : 'ccis/Software+and+Service+Engineering+%28SSE%29',
          'inf'  : 'inf/Major',
          'lstbi': 'lst/Bioinformatics+and+Digital+Health',
          'lstbs': 'lst/Biosensing+and+Bioelectronics',
          'lstcs': 'lst/Complex+Systems',
          'eitcn': 'eitictinno/Cloud+and+Network+Infrastructures',
          'eitds': 'eitictinno/Data+Science',
          'eithc': 'eitictinno/Human+Computer+Interaction+and+Design',
          'eitvc': 'eitictinno/Visual+Computing+and+Communication'
         }

    t = { 'cs' : [ 'cs/al', 'cs/bd', 'cs/ss',  'cs/wt'],
          'sse': [ 'sse/es', 'sse/sd', 'sse/se' ] }
    
    for i, u in m.items():
        url = 'https://into.aalto.fi/display/en'+u+'+2020-2022'
        print('Scraping faculty members in {} ({})'.format(long_names[i], i), url,
              flush=True)
        response = requests.request('GET', url)
        if response.status_code!=200:
            print('Reading {} failed'.format(url))
            continue
        f = find_names(response.text)
        print('  found:', ', '.join(sorted(f)))
        for a in f:
            add_to_majors(a, i)
        if i in t:
            print('Splitting {} in tracks'.format(long_names[i]), flush=True)
            restree = lxml_html.fromstring(response.text)
            tree    = lxml_etree.ElementTree(restree)
            for div in restree.xpath("//div[@class='expand-container conf-macro output-block']"):
                v = lxml_etree.tostring(div, encoding='unicode')
                for j in t[i]:
                    s = long_names[j][len(long_names[i])+3:]
                    if v.find('>'+s+'<')>0:
                        f = find_names(v)
                        for a in f:
                            add_to_majors(a, j)
                        print('  {} ({}) found: {}'.format(s, j,', '.join(sorted(f))))

google_data_file = 'google-data.txt'
scholar_data = None
def google_data(n):
    global scholar_data
    if scholar_data is None:
        scholar_data = dict()
        try:
            with open(google_data_file) as f:
                for l in f:
                    l = l.split('#')[0].strip()
                    if l=='':
                        continue
                    l = l.split(' ')
                    a = []
                    for i in l:
                        if i!='':
                            a.append(i)
                    if len(a)!=9:
                        continue
                    do_add = a[0] not in scholar_data
                    if not do_add:
                        do_add = scholar_data[a[0]][1]<a[1]
                    if do_add:
                        scholar_data[a[0]] = [ i if i!='-' else None for i in a ]
        except:
            pass
        
    n = n.replace(' ', '')
    if n in scholar_data:
        return scholar_data[n]
    return [ None ] * 9
    

def fetch_google_data_inner(n, debug, save):
    headers = {'User-Agent': 'Mozilla/5.0'}

    nx = n.replace(' ', '+')
    #url = 'https://scholar.google.com/scholar?q='+nx
    url = f'https://scholar.google.com/citations?view_op=search_authors&mauthors={nx}'
    time.sleep(1)
    response = requests.request('GET', url, headers=headers)
    if response.status_code!=200:
        print(f'Reading {url} failed: {response.status_code}')
        if response.status_code==429:
            return False
        return True
    if debug:
        print(f'Reading {url} SUCCESSFUL')
    if save:
        fname = f'g-{nx}.html'
        print(response.text, file=open(fname, 'w'))
        print(f'Saved HTML in {fname}')
        
    restrees = lxml_html.fromstring(response.text)
    trees    = lxml_etree.ElementTree(restrees)
    href = None
    val = []
    for a in restrees.xpath("//h3[@class='gs_ai_name']/a"): # "//h4[@class='gs_rt2']/a"
        href  = a.attrib['href']
        if href.find('&')>0:
            hrefx = href
            u = hrefx.find('user=')
            if u>0:
                hrefx = hrefx[u+5:]
            u = hrefx.find('&')
            if u>0:
                hrefx = hrefx[:u]
            if debug:
                print(f'Trying {href} -> {hrefx}')
            href = 'https://scholar.google.com'+href
            #print(href)
            time.sleep(1)
            response = requests.request('GET', href, headers=headers)
            if response.status_code!=200:
                print(f'Reading {href} failed: {response.status_code}')
                continue
            if debug:
                print(f'Reading {href} SUCCESSFUL')
            if save:
                fname = f'g-{hrefx}.html'
                print(response.text, file=open(fname, 'w'))
                print(f'Saved HTML in {fname}')

            aalto = response.text.lower().find('aalto')>0
            if aalto:
                if debug:
                    print('  aalto found')
                restreep = lxml_html.fromstring(response.text)
                treep    = lxml_etree.ElementTree(restreep)
                val = []
                for td in restreep.xpath("//td[@class='gsc_rsb_std']"):
                    val.append(int(td.text))
                    if debug:
                        print(f'  value "{td.text}" found')
                return hrefx, val
    return True
            

scholar = {}
                        
def fetch_google_data(debug):
    skipdays = 14
    
    ss = set()
    order = []
    for n, na in alias.items():
        nn = na.replace(' ', '')
        if nn in ss:
            continue
        gval = google_data(na)
        t = gval[1]
        if t is None:
            t = '2000-01-01T00:00:00.000000'
        t = datetime.datetime.fromisoformat(t)
        order.append([n, na, t])
    order.sort(key=lambda x: x[2])
    # for i in order:
    #     print(i)
    # return
        
    all_na, found_na, skipped_na = set(), set(), set()
    aborted = False
    for n, na, tt in order:
        if debug:
            print(n, na, tt)
        all_na.add(na)
        nn = na.replace(' ', '')
        if nn in scholar:
            if debug:
                print('found in dict and skipping')
            continue

        gval = google_data(na)
        if debug:
            print(f'google_data({na}) : {gval}')
        xtime = gval[1]
        now = datetime.datetime.now()
        if xtime is not None:
            xxtime = datetime.datetime.fromisoformat(xtime)
            #print(xxtime)
            td = now-xxtime
            #print(td)
            skip = td<datetime.timedelta(days=skipdays)
            if debug:
                print(f'{now} - {xxtime} = {td} skip={skip}')
            if skip:
                if gval[2] is not None:
                    found_na.add(na)
                    scholar[nn] = gval
                gvalstr = ' '.join(map(str, gval))
                print(f'Scholar scraping skipped due to recent data: {gvalstr}')
                skipped_na.add(na)
                continue
            
        r = fetch_google_data_inner(n, debug, False)

        if r==False:
            print('... Skipping the rest of the faculty this time. '
                  'Try again later ...')
            aborted = True
            continue

        if r==True:
            continue

        idn = r[0]
        val = r[1]
            
        #print(f'{na} {n} {nx} {idn} {val}')
        if idn is not None and len(val)==6:
            dt = now.isoformat()
            gval = [nn, dt, idn, val[0], val[2], val[4], val[1], val[3], val[5]]
            gvalstr = ' '.join(map(str, gval))
            #print(gvalstr)
            found_na.add(na)
            scholar[nn] = gval
            try:
                with open(google_data_file, 'a') as fp:
                    print(gvalstr, file=fp)
                    print(f'Appended in {google_data_file} "{gvalstr}"')
            except:
                print(f'Appending "{gvalstr}" in {google_data_file} failed')
            #break

    if not aborted:
        for i in found_na:
            all_na.remove(i)
        if all_na:
            print("The following faculty members don't have "+ \
                  f"Aalto Google Scholar page: {', '.join(list(all_na))}")
            dt = datetime.datetime.now().isoformat()
            for i in all_na:
                if i not in skipped_na:
                    try:
                        with open(google_data_file, 'a') as fp:
                            gvalstr = i.replace(' ', '')+f' {dt} - - - - - - -'
                            print(gvalstr, file=fp)
                            print(f'Appended in {google_data_file} "{gvalstr}"')
                    except:
                        print(f'Appending "{gvalstr}" in {google_data_file} failed')

def show_theses(detail, keywords, role):
    counts = []
    for p in people:
        m = ' '.join(sorted(majors[p])) if p in majors else ''
        counts.append((len(theses[p]), p, m))
    counts.sort(reverse=True)
    #print(counts)
    sum = 0
    for i in counts:
        group = i[2] # currently empty
        _,_,_, cites, hidx, _,_,_,_ = google_data(i[1]) 
        if cites:
            scholar = f'h-idx: {hidx}, cites: {cites}'
        else:
            scholar = ''
        
        print(f'{i[0]:3d} {i[1]} ({scholar})')
        sum += i[0]
        if detail:
            for j in theses[i[1]]:
                s = '' if j[3]=='SCI' else j[3][:3]
                if not role:
                    ffield = f'{j[4]:8}'
                else:
                    ffield = '(S)' if j[8]=='supervisor' \
                        else '(A)' if j[8]=='advisor' else '(?)'
                print(f'    {s:3s} {ffield} {j[0]}: {j[1]}. {j[2]}', end='')
                if keywords:
                    print(f'. {j[5]}. {j[6]}. {j[7]}', end='')
                print()
    print(f'{sum:3d} TOTAL')

split = {}
per_major_code = {}

def split_theses():
    for i, j in theses.items():
        # print(i, j)
        if i not in majors:
            add_to_majors(i, 'unk')
        n = len(j)
        d = 0
        t = set()
        for m in majors[i]:
            if '/' not in m:
                d += 1
            else:
                t.add(m)
        e = d*len(t)
        # print(i, n, majors[i], d, t)
        for m in majors[i]:
            if m not in split:
                split[m] = { 'theses': [] }
            if '/' not in m:
                split[m]['theses'].append((i, n/d, 1/d))
            else:
                split[m]['theses'].append((i, n/e, 1/e))

def show_summary():
    # print(per_major_code)
    mcc = []
    for i, j in per_major_code.items():
        mcc.append((len(j), i))
    mcc.sort(reverse=True)
    sum = 0
    for i in mcc:
        print(f'{i[0]:4} {i[1]:8} {major_names.get(i[1], "")}')
        sum += i[0]
    print(f'{sum:4} TOTAL')
    return

    #print(split)
    for m in split:
        s = 0
        p = 0
        for i, j, k in split[m]['theses']:
            #print('XX', m, i, j)
            s += j
            p += k
        split[m]['total']  = s
        split[m]['size']   = p
        split[m]['percap'] = split[m]['total'] / split[m]['size']
        #print('XX', m, split[m]['total'], split[m]['size'],  split[m]['percap'])
    counts = []
    for m, n in split.items():
        counts.append((m, n))
    for m, n in sorted(counts):
        print('{:6s} {:42s} {:5.2f} {:5.2f} {:5.2f}'.
              format(m, long_names[m][0:42], n['total'], n['size'], n['percap']))

def show_student(r, sin):
    c = 0
    s = sin.replace(',', '').split(' ')
    for i in r:
        a = i['author'].replace(',', '').split(' ')
        hit = True
        for j in s:
            hit = hit and j in a
        if hit:
            if c:
                print()
            c += 1
            m = match_record(i, ['supervisor', 'advisor'])
            m = [ f'{n} ({r})' for n, r in m.items() ]
            m = ', '.join(m)
            print(f'Thesis by author "{sin}" #{c}: => {m}')
            pprint.pp(i)

def dump_alias_txt(f):
    l = []
    z = set()
    for k,v in alias.items():
        if v not in z:
            if k!=v:
                print(f'[{k}] : [{v}]')
                l.append(f'{k} : {v}')
                z.add(v)
            else:
                print(f'[{k}]')
                l.append(k)
            
    with open(f, 'w') as fp:
        for i in l:
            print(i, file=fp)
            
# -----------------------------------------------------------------------------

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Aalto CS Dept M.Sc. Thesis listing '
                                     +'per supervisor in 2021-25',
                                     epilog='See also alias.example.txt')
    parser.add_argument('-b', '--bsc', action='store_true',
                        help='show BSc theses instead of MSc')
    parser.add_argument(      '--dsc', action='store_true',
                        help='show DSc theses instead of MSc')
    parser.add_argument(      '--roles', type=str,
                        help='specify comma-separated roles "advisor" and/or "supervisor"')
    parser.add_argument('-f', '--fast', action='store_true',
                        help='fast version: no downloads, just read cached JSON files')
    parser.add_argument('-y', '--years', type=str,
                        help='select years (comma-separated or "all")')
    parser.add_argument('-m', '--major', type=str,
                        help='select a specific major such as "SCI3044"')
    parser.add_argument('-d', '--detail', action='store_true',
                        help='show also authors, titles and issue dates')
    parser.add_argument('-k', '--keywords', action='store_true',
                        help='show also keywords and abstracts')
    parser.add_argument('-t', '--theses', type=str, choices=['dump', 'load', 'skip'],
                        help='either dump or load all theses to/from theses.json')
    parser.add_argument('-s', '--supervisors', type=str, choices=['dump', 'load'],
                        help='either dump or load theses per supervisor to/from supervisors.json')
    parser.add_argument('-a', '--aliasdata', type=str, choices=['dump', 'load'],
                        help='either dump or load automagically created aliases to/from aliases.json')
    parser.add_argument('-p', '--person', type=str, 
                        help='add person names or aliases, format "GivenName SurName" or "Alias:Canonical",'+
                             ' multiple comma separated, see also alias.example.txt')
    parser.add_argument('--raw', action='store_true',
                        help='store raw HTML files for error hunting')
    parser.add_argument('--debug', action='store_true',
                        help='be more verbose')
    parser.add_argument('--max', type=int, default=300,
                        help='set maximum number of pages to be read per school, default=%(default)s')
    parser.add_argument('--parse', type=str,
                        help='read in and parse a given HTML file and quit')
    parser.add_argument('--student', type=str,
                        help='dump full information on one student and quit')
    parser.add_argument('--google', action='store_true',
                        help='fetch Google Scholar data')
    args = parser.parse_args()

    #print(edit_dist('abc', 'axbc'))
    #exit(0)

    #print(fetch_google_data_inner('', True, True))
    #exit(0)

    #print(google_data(''))
    #exit(0)
    
    if args.bsc:
        school_info = school_info_bsc
        cache_dir = 'cache/bsc'
        roles = ['advisor']
    elif args.dsc:
        school_info = school_info_dsc
        cache_dir = 'cache/dsc'
        roles = ['advisor', 'supervisor']
    else:
        school_info = school_info_msc
        cache_dir = 'cache/msc'
        roles = ['supervisor']

    if args.roles:
        roles = args.roles.split(',')
        
    if args.parse:
        s = open(args.parse).read()
        d = html_to_dict(s, True)
        print(d)
        exit(0)

    if use_cache:
        for d in [ 'cache', 'cache/bsc', 'cache/msc', 'cache/dsc' ]:
            if not os.path.isdir(d):
                try:
                    os.mkdir(d)
                except:
                    print(f'Failed to create cache directory "{d}", caching disabled.')
                    use_cache = False
    
    if args.years:
        years = args.years.split(',')

    if args.major:
        major = args.major

    alines = []
    if os.path.isfile('alias.txt'):
        with open('alias.txt') as f:
            for l in f:
                p = l.find('#')
                if p>=0:
                    l = l[:p]
                if len(l):
                    alines.append(l)
                
    if args.person:
        alines.extend(args.person.split(','))

    for i in alines:
        x = i.split(':')
        assert len(x)<3
        ali = x[0].strip()
        can = (x[1] if len(x)>1 and len(x[1])>1 else x[0]).strip()
        if args.debug:
            print(f'Adding alias [{ali}]->[{can}]')
        alias[ali] = can
    

    if args.aliasdata=='load':
        for i, j in json.loads(open('aliases.json').read()).items():
            alias[i] = j

    if args.aliasdata=='dump':
        dump_alias_txt('alias-dump-0.txt')
        print('Dumped to alias-dump-0.txt')
        
    # print(f'Aliases: {alias}')

    people = fetch_faculty(args.debug)
    #print(people)

    for p in people:
        theses[p] = []
        alias[p]  = p

    if args.aliasdata=='dump':
        dump_alias_txt('alias-dump-1.txt')
        print('Dumped to alias-dump-1.txt')
        
    if args.google:
        fetch_google_data(args.debug)
        exit(0)
    
    if (args.theses is None and args.supervisors!='load') or args.theses=='dump':
        if not args.fast:
            rec = fetch_theses(args.max, args.raw, args.debug)
        else:
            rec = fetch_theses_cache(args.debug)
            
    if args.theses=='dump':
        open('theses.json', 'w').write(json.dumps(rec))
        print('Dumped to theses.json')

    if args.theses=='load':
        rec_all = json.loads(open('theses.json').read())
        print('Loaded from theses.json')
        rec = []
        for i in rec_all:
            # does not check args.major
            if i['issued'][:4] in years or 'all' in years:
                rec.append(i)

    #print(rec)

    if args.student:
        show_student(rec, args.student)
        exit(0)
                
    if args.supervisors!='load':
        print('Matching {} records with {} faculty members'.format(len(rec), len(people)))
        for r in rec:
            match_record(r, roles)

    if args.supervisors=='dump':
        open('supervisors.json', 'w').write(json.dumps(theses))
        print('Dumped to supervisors.json')

    if args.supervisors=='load':
        theses = json.loads(open('supervisors.json').read())
        print('Loaded from supervisors.json')

    if args.aliasdata=='dump':
        open('aliases.json', 'w').write(json.dumps(alias))
        dump_alias_txt('alias-dump-2.txt')
        print('Dumped to alias-dump-2.txt and alias.json')

    #find_majors()

    show_theses(args.detail, args.keywords, args.dsc or args.roles)

    split_theses()

    show_summary()

