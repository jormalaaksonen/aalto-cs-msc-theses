#! /usr/bin/env python3

import requests
import json
import argparse
from lxml import html  as lxml_html
from lxml import etree as lxml_etree

parser = argparse.ArgumentParser(description='Aalto CS Dept M.Sc. Thesis listing '
                                 +'per supervisor in 2021-22')
parser.add_argument('-d', '--detail', action='store_true',
                    help='show also authors, titles and issue dates')
args = parser.parse_args()

years = [ '2021', '2022' ]

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
                if title_lang is None or meta.attrib['xml:lang']=='en':
                    rec['title'] = ' '.join(v.split())
                    title_lang = meta.attrib['xml:lang']
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
    
def fetch_faculty():
    url = 'https://www.aalto.fi/en/department-of-computer-science/faculty-members'
    response = requests.request('GET', url)
    if response.status_code!=200:
        return None
    html = response.text
    #html = open('f.html').read()
    l = []
    restree = lxml_html.fromstring(hack_html(html))
    tree    = lxml_etree.ElementTree(restree)
    for a in restree.xpath("//a[@class='aalto-profile-card__name-link']"):
        n = a.text.strip()
        #print(a, n)
        l.append(n)
    return l

def fetch_theses(max_pages):
    print('(Wait... This will continue until offset=430 or even more...)')
    rec = []
    for i in range(max_pages):
        url_base = 'https://aaltodoc.aalto.fi'
        url = url_base+'/handle/123456789/21/recent-submissions'
        if i>0:
            url += '?offset='+str(10*i)
        print('Fetching', url, flush=True)
        response = requests.request('GET', url)
        if response.status_code!=200:
            print(i, url, 'error', response.status_code)
        else:
            ll = html_to_links(response.text)
            do_break = True;
            if len(ll):
                #print(i, url, ll)
                for l in ll:
                    response = requests.request('GET', url_base+l)
                    if response.status_code!=200:
                        print(i, url, l, 'error', response.status_code)
                    else:
                        d = html_to_dict(response.text)
                        if d:
                            #print(i, url, l, d)
                            y = d['issued'][:4]
                            if y in years:
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
alias  = {}

def name_or_alias(n):
    if n in theses:
        return n
    if n in alias:
        return alias[n]
    if n in no_hit:
        return None
    nn = n.split()
    for i in theses.keys():
        mm = i.split()
        l0 = len(nn[ 0]) if len(nn[ 0])<len(mm[ 0]) else len(mm[ 0])
        l1 = len(nn[-1]) if len(nn[-1])<len(mm[-1]) else len(mm[-1])
        if nn[0][:l0]==mm[0][:l0] and (nn[-1][:l1]==mm[-1][:l1] or
                                       nn[-1][-l1:]==mm[-1][-l1:]):
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
    for n in f:
        e = (swap_name(r['creator']), r['title'], r['issued'])
        theses[n].append(e)
        #print('FOUND', n, ':', *e)
            
def show_theses(detail):
    counts = []
    for p in people:
        counts.append((len(theses[p]), p))
    counts.sort(reverse=True)
    #print(counts)
    sum = 0
    for i in counts:
        print('{:3d} {}'.format(*i))
        sum += i[0]
        if detail:
            for j in theses[i[1]]:
                print('      {}: {}. {}'.format(*j))
    print('{:3d} {}'.format(sum, 'TOTAL'))

rec = fetch_theses(200)
#open('dump.json', 'w').write(json.dumps(rec))
#rec = json.loads(open('dump.json').read())
#print(rec)

people = fetch_faculty()
#print(people)

for p in people:
    theses[p] = []

for r in rec:
    match_record(r)

show_theses(args.detail)

#print(alias)
