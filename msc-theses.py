#! /usr/bin/env python3

import requests
import json
import argparse
import os
import time
from lxml import html  as lxml_html
from lxml import etree as lxml_etree

years = [ '2021', '2022', '2023', '2024' ]

school_info = [ ('SCI', 21, 65), ('ELEC', 22, 30), ('ENG', 18, 43), ('ARTS', 23, 50) ]

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

use_cache = True

majors = {}

alias  = {
}

theses = {}

def hack_html(html):
    p = html.find('<html ')
    if p>0:
        html = '<?xml version="1.0"?>\n'+html[p:]
    return html

def html_to_dict(html, debug = False):
    html2   = hack_html(html)
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
    v = l[0].xpath('div/h5')[0].tail
    rec['supervisor'] = v.strip()
                
    l = restree.xpath("//ds-aalto-item-advisor")
    assert len(l)==1, 'failed with advisor'
    m = l[0].xpath('div/h5')
    if len(m)==1:
        v = m[0].tail
        rec['advisor'] = v.strip()
                
    # print(rec)
    
    return rec

def html_to_links(html):
    l = []
    restree = lxml_html.fromstring(hack_html(html))
    tree    = lxml_etree.ElementTree(restree)
    for a in restree.xpath("//div[@_ngcontent-sc57='']/a[@_ngcontent-sc60='']"): # 
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
    
def fetch_faculty():
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

def request_with_loop(url, n):
    for i in range(n):
        response = requests.request('GET', url)
        if response.status_code!=200:
            return response
        if response.text.find('<title>DSpace</title>')<0:
            return response
        time.sleep(i)
    return response

def fetch_one_thesis(s, l, li, ln, url_base, dump_raw, debug):
    rawi = 0
    print(f'{li}/{ln}\r', end='', flush=True)
    # print(i, url, l, flush=True)
    urlx  = url_base+l
    cfile = 'cache/'+l.split('/')[-1]
    text  = None
    #print(l, urlx, cfile)
    if use_cache and os.path.isfile(cfile) and os.path.getsize(cfile):
        text = open(cfile).read()
        if debug:
            print(f'    read cached     {cfile} -> {urlx}')
    else:
        response = request_with_loop(urlx, 10)
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
        y = d['issued'][:4]
        if y in years or y=='unkn':
            d['school'] = s[0]
            return (d, False)
        else:
            return ({}, True)
                                
def fetch_theses(max_pages, dump_raw, debug):
    rec = []
    for s in school_info:
        print(f'Scraping {s[0]} school will continue until cp.page={s[2]} or even longer...')
        urlred = None
        for i in range(max_pages):
            url_base = 'https://aaltodoc.aalto.fi'
            url = f'{url_base}/handle/123456789/{s[1]}'
            if i>0:
                url = f'{urlred}?cp.page={i+1}'
            print(f'  fetching {s[0]} {url}', flush=True)
            response = request_with_loop(url, 10)
            if response.status_code!=200:
                print(i, url, 'error', response.status_code)
                continue

            # open('index-page.html', 'w').write(response.text)
            if urlred is None:
                urlred = response.url
            ll = html_to_links(response.text)
            if len(ll)==0:
                print(i, url, 'failed')                

            do_break = True
            for li, l in enumerate(ll):
                d, b = fetch_one_thesis(s, l, li, len(ll), url_base, dump_raw, debug)
                do_break = do_break and b
                if d:
                    rec.append(d)
                    
            if do_break:
                break
    return rec

no_hit = set()

def name_or_alias(n):
    if n in alias:
        return alias[n]
    if n in no_hit:
        return None
    nn = n.split()
    for i in theses.keys():
        mm = i.split()
        l0 = len(nn[ 0]) if len(nn[ 0])<len(mm[ 0]) else len(mm[ 0])
        l1 = len(nn[-1]) if len(nn[-1])<len(mm[-1]) else len(mm[-1])
        if (nn[ 0][:l0]==mm[ 0][:l0] or nn[ 0][-l0:]==mm[ 0][-l0:]) and \
           (nn[-1][:l1]==mm[-1][:l1] or nn[-1][-l1:]==mm[-1][-l1:]):
            alias[n] = i
            return i
    no_hit.add(n)
    return None
    
def match_record(r):
    f = set()
    for p in [ r['supervisor'] ]:
        n = swap_name(p)
        a = name_or_alias(n)
        if a is not None:
            f.add(a)
        else: ## odd cases "firstname, familyname"
            n = swap_name_not(p)
            a = name_or_alias(n)
            if a is not None:
                f.add(a)
    for n in f:
        e = (swap_name(r['author']), r['title'], r['issued'], r['school'])
        theses[n].append(e)
        #print('FOUND', n, ':', *e)

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

scholar = {}
                        
def find_h_indices():
    for n in alias:
        if alias[n] in scholar:
            continue
        nx = n.replace(' ', '+')
        url = 'https://scholar.google.com/scholar?q='+nx
        response = requests.request('GET', url)
        if response.status_code!=200:
            print('Reading {} failed'.format(url))
            continue
        restrees = lxml_html.fromstring(response.text)
        trees    = lxml_etree.ElementTree(restrees)
        h_index = None
        for a in restrees.xpath("//h4[@class='gs_rt2']/a"):
            href = a.attrib['href']
            #print(a, href)
            if href.find('&')>0:
                href = 'https://scholar.google.com'+href[:href.find('&')]
                #print(href)
                response = requests.request('GET', href)
                if response.status_code!=200:
                    print('Reading {} failed'.format(url))
                    continue
                aalto = response.text.lower().find('aalto')>0
                if aalto:
                    restreep = lxml_html.fromstring(response.text)
                    treep    = lxml_etree.ElementTree(restreep)
                    val = []
                    for td in restreep.xpath("//td[@class='gsc_rsb_std']"):
                        val.append(int(td.text))
                    h_index = val[2]
                    break
                
        print('{} ({}) {} {}'.format(alias[n], n, h_index, href))
        if h_index:
            scholar[alias[n]] = (h_index, href)
            
def show_theses(detail):
    counts = []
    for p in people:
        m = ' '.join(sorted(majors[p])) if p in majors else ''
        counts.append((len(theses[p]), p, m))
    counts.sort(reverse=True)
    #print(counts)
    sum = 0
    for i in counts:
        print('{:3d} {} ({})'.format(*i))
        sum += i[0]
        if detail:
            for j in theses[i[1]]:
                s = '' if j[3]=='SCI' else j[3][:3]
                print('    {:3s} {}: {}. {}'.format(s, *j))
    print('{:3d} {}'.format(sum, 'TOTAL'))

split = {}

def split_theses():
    for i, j in theses.items():
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
    
# -----------------------------------------------------------------------------

# print(html_to_dict(open('zzz.html').read()))

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Aalto CS Dept M.Sc. Thesis listing '
                                     +'per supervisor in 2021-24',
                                     epilog='See also alias.example.txt')
    parser.add_argument('-y', '--years', type=str,
                        help='select years (comma-separated)')
    parser.add_argument('-d', '--detail', action='store_true',
                        help='show also authors, titles and issue dates')
    parser.add_argument('-r', '--rec', type=str, choices=['dump', 'load'],
                        help='either dumps or loads rec structure to/from json')
    parser.add_argument('-a', type=str, choices=['dump', 'load'],
                        help='either dumps or loads alias structure to/from json')
    parser.add_argument('-p', '--person', type=str, 
                        help='add names or aliases, format "GivenName SurName" or "Alias:Canonical",'+
                             ' multiple comma separated, see also alias.example.txt')
    parser.add_argument('-t', '--theses', type=str, choices=['dump', 'load'],
                        help='either dumps or loads theses structure to/from json')
    parser.add_argument('--raw', action='store_true',
                        help='store raw HTML files for error hunting')
    parser.add_argument('--debug', action='store_true',
                        help='be more verbose')
    parser.add_argument('--max', type=int, default=100,
                        help='set maximum number of pages to be read per school, default=%(default)s')
    parser.add_argument('--parse', type=str,
                        help='read in and parse given file and quit')
    args = parser.parse_args()

    if args.parse:
        s = open(args.parse).read()
        d = html_to_dict(s, True)
        print(d)
        exit(0)

    if use_cache and not os.path.isdir('cache'):
        os.mkdir('cache')
        if not os.path.isdir('cache'):
            print('Failed to create cache directory.')
            use_cache = False
    
    if args.years:
        years = args.years.split(',')

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
    # print(f'aliases: {alias}')

    if args.rec is None or args.rec=='dump':
        rec = fetch_theses(args.max, args.raw, args.debug)

    if args.rec=='dump':
        open('rec.json', 'w').write(json.dumps(rec))
        print('Dumped to rec.json')

    if args.rec=='load':
        rec = json.loads(open('rec.json').read())
        print('Loaded from rec.json')
    #print(rec)

    people = fetch_faculty()
    #print(people)

    for p in people:
        theses[p] = []
        alias[p]  = p

    if args.theses!='load':
        print('Matching {} records with {} faculty members'.format(len(rec), len(people)))
        for r in rec:
            match_record(r)

    if args.theses=='dump':
        open('theses.json', 'w').write(json.dumps(theses))
        print('Dumped to theses.json')
    if args.theses=='load':
        theses = json.loads(open('theses.json').read())
        print('Loaded from theses.json')

    if args.a=='dump':
        open('alias.json', 'w').write(json.dumps(alias))
        print('Dumped to alias.json')
    if args.a=='load':
        for i, j in json.loads(open('alias.json').read()).items():
            alias[i] = j

    #find_majors()

    #find_h_indices()

    show_theses(args.detail)

    split_theses()

    #show_summary()

