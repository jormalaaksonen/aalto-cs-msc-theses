#! /usr/bin/env python3

import requests
import json
import argparse
import os
from lxml import html  as lxml_html
from lxml import etree as lxml_etree

years = [ '2021', '2022', '2023' ]

school_info = [ (21, 'SCI', 1070), (22, 'ELEC', 530), (18, 'ENG', 770), (23, 'ARTS', 820) ]

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
    p = html.find('\n')
    if p>0:
        html = '<?xml version="1.0"?>'+html[p:]
    return html

def html_to_dict(html):
    restree = lxml_html.fromstring(hack_html(html))
    tree    = lxml_etree.ElementTree(restree)
    rec = { 'contributor': []}
    ok = False
    title_lang = None
    ff = ['DC.creator', 'DC.title', 'DCTERMS.issued',
          'DC.type', 'DC.contributor']
    for f in ff:
        for meta in restree.xpath("//meta[@name='"+f+"']"):
            v = meta.attrib['content']
            #print(f, v)
            if f=='DC.type'and v=="Master's thesis":
                ok = True
            if f=='DC.title':
                l = meta.attrib.get('xml:lang', 'en')
                if title_lang is None or l=='en':
                    rec['title'] = ' '.join(v.split())
                    title_lang = l
            if f=='DC.creator':
                rec['creator'] = v
            if f=='DCTERMS.issued':
                rec['issued'] = v
            if f=='DC.contributor' and v.find(',')>0:
                rec['contributor'].append(v)

    return rec if ok else None

def html_to_links(html):
    l = []
    restree = lxml_html.fromstring(hack_html(html))
    tree    = lxml_etree.ElementTree(restree)
    for a in restree.xpath("//span[@class='content']/a"):
        href = a.attrib['href']
        #print(a, href)
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

def fetch_theses(max_pages, dump_raw):
    debug = False
    rec = []
    for s in school_info:
        print(f'Scraping {s[1]} school will continue until offset={s[2]} or even longer...')
        for i in range(max_pages):
            url_base = 'https://aaltodoc.aalto.fi'
            url = url_base+'/handle/123456789/'+str(s[0])+'/recent-submissions'
            if i>0:
                url += '?offset='+str(10*i)
            print('  fetching', url, flush=True)
            response = requests.request('GET', url)
            if response.status_code!=200:
                print(i, url, 'error', response.status_code)
            else:
                ll = html_to_links(response.text)
                do_break = True;
                if len(ll):
                    rawi = 0
                    #print(i, url, ll)
                    for l in ll:
                        urlx  = url_base+l
                        cfile = 'cache/'+l.split('/')[-1]
                        text  = None
                        #print(l, urlx, cfile)
                        if use_cache and os.path.isfile(cfile) and os.path.getsize(cfile):
                            text = open(cfile).read()
                            if debug:
                                print(f'    read cached     {cfile} -> {urlx}')
                        else:
                            response = requests.request('GET', urlx)
                            if response.status_code!=200:
                                print(i, url, l, 'error', response.status_code)
                            elif response.text=='':
                                print(i, url, l, 'empty doc', response.status_code)
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
                            d = html_to_dict(text)
                            if d:
                                #print(i, url, l, d)
                                y = d['issued'][:4]
                                if y in years:
                                    d['school'] = s[1]
                                    do_break = False
                                    rec.append(d)
                            else:
                                print(i, url, l, 'failed')
                else:
                    print(i, url, 'failed')
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
    for p in r['contributor']:
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
        e = (swap_name(r['creator']), r['title'], r['issued'], r['school'])
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
                                     +'per supervisor in 2021-23')
    parser.add_argument('-y', '--years', type=str,
                        help='select years (comma-separated)')
    parser.add_argument('-d', '--detail', action='store_true',
                        help='show also authors, titles and issue dates')
    parser.add_argument('-r', '--rec', type=str, choices=['dump', 'load'],
                        help='either dumps or loads rec structure to/from json')
    parser.add_argument('-a', '--alias', type=str, choices=['dump', 'load'],
                        help='either dumps or loads alias structure to/from json')
    parser.add_argument('-p', '--person', type=str, 
                        help='add names or aliases, format "FName SName" or "Alias:Canonical", multiple comma separated')
    parser.add_argument('-t', '--theses', type=str, choices=['dump', 'load'],
                        help='either dumps or loads theses structure to/from json')
    parser.add_argument('--raw', action='store_true',
                        help='store raw HTML files for error hunting')
    args = parser.parse_args()

    if use_cache and not os.path.isdir('cache'):
        if not os.mkdir('cache'):
            print('Failed to create cache directory.')
            use_cache = False
    
    if args.years:
        years = args.years.split(',')
    
    if args.person:
        l = args.person.split(',')
        for i in l:
            x = i.split(':')
            assert len(x)<3
            ali = x[0].strip()
            can = (x[1] if len(x)>1 and len(x[1])>1 else x[0]).strip()
            #print(f'[{ali}]->[{can}]')
            alias[ali] = can
        # print(f'aliases: {alias}')

    if args.rec is None or args.rec=='dump':
        rec = fetch_theses(200, args.raw)
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

    if args.alias=='dump':
        open('alias.json', 'w').write(json.dumps(alias))
        print('Dumped to alias.json')
    if args.alias=='load':
        for i, j in json.loads(open('alias.json').read()).items():
            alias[i] = j

    #find_majors()

    #find_h_indices()

    show_theses(args.detail)

    split_theses()

    show_summary()

