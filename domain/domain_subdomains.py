#!/usr/bin/env python

import base
import sys
import requests
from bs4 import BeautifulSoup
import re
from termcolor import colored
import time
import warnings
import json

warnings.filterwarnings("ignore")

ENABLED = True


'''
Author(s): @upgoingstar & @khasmek
'''

class style:
    BOLD = '\033[1m'
    END = '\033[0m'



def check_and_append_subdomains(subdomain, subdomain_list):
    if subdomain not in subdomain_list:
        subdomain_list.append(subdomain)
    return subdomain_list

def check_and_append_other_domains(other_domain, other_related_domain_list):
    if other_domain not in other_related_domain_list:
        other_related_domain_list.append(other_domain)
    return other_related_domain_list

def subdomains(domain, subdomain_list):
    print colored(' [+] Extracting subdomains from DNS Dumpster\n', 'blue')
    r = requests.get("https://dnsdumpster.com/", verify=False)
    cookies = {}
    if 'csrftoken' in r.cookies.keys():
        cookies['csrftoken'] = r.cookies['csrftoken']
        data = {}
        data['csrfmiddlewaretoken'] = cookies['csrftoken']
        data['targetip'] = domain
        headers = {}
        headers['Referer'] = "https://dnsdumpster.com/"
        req = requests.post("https://dnsdumpster.com/", data=data, cookies=cookies, headers=headers, verify=False)
        soup = BeautifulSoup(req.content, 'lxml')
        subdomains_new = soup.findAll('td', {"class": "col-md-4"})
        for subd in subdomains_new:
            if domain in subd.text:
                subdomain_list = check_and_append_subdomains(subd.text.split()[0], subdomain_list)
    return subdomain_list


def subdomains_from_netcraft(domain, subdomain_list):
    print colored(' [+] Extracting subdomains Netcraft\n', 'blue')
    target_dom_name = domain.split(".")
    req1 = requests.get("http://searchdns.netcraft.com/?host=%s" % domain)
    link_regx = re.compile('<a href="http://toolbar.netcraft.com/site_report\?url=(.*)">')
    links_list = link_regx.findall(req1.content)
    for x in links_list:
        dom_name = x.split("/")[2].split(".")
        if (dom_name[len(dom_name) - 1] == target_dom_name[1]) and (dom_name[len(dom_name) - 2] == target_dom_name[0]):
            subdomain_list = check_and_append_subdomains(x.split("/")[2], subdomain_list)
    num_regex = re.compile('Found (.*) site')
    num_subdomains = num_regex.findall(req1.content)
    if not num_subdomains:
        num_regex = re.compile('First (.*) sites returned')
        num_subdomains = num_regex.findall(req1.content)
    if num_subdomains:
        if num_subdomains[0] != str(0):
            num_pages = int(num_subdomains[0]) / 20 + 1
            if num_pages > 1:
                last_regex = re.compile(
                    '<td align="left">%s.</td><td align="left">\n<a href="(.*)" rel="nofollow">' % (20))
                last_item = last_regex.findall(req1.content)[0].split("/")[2]
                next_page = 21

                for x in range(2, num_pages):
                    url = "http://searchdns.netcraft.com/?host=%s&last=%s&from=%s&restriction=site%%20contains" % (
                        domain, last_item, next_page)
                    req2 = requests.get(url)
                    link_regx = re.compile('<a href="http://toolbar.netcraft.com/site_report\?url=(.*)">')
                    links_list = link_regx.findall(req2.content)
                    for y in links_list:
                        dom_name1 = y.split("/")[2].split(".")
                        if (dom_name1[len(dom_name1) - 1] == target_dom_name[1]) and (
                                    dom_name1[len(dom_name1) - 2] == target_dom_name[0]):
                            subdomain_list = check_and_append_subdomains(y.split("/")[2], subdomain_list)
                    last_item = links_list[len(links_list) - 1].split("/")[2]
                    next_page = 20 * x + 1
        else:
            pass
    else:
        pass
    return subdomain_list

def find_domains_from_next_page_ct(page_identifier, domain, subdomain_list, other_related_domain_list):
    url = "https://transparencyreport.google.com/transparencyreport/api/v3/httpsreport/ct/certsearch/page?p=%s" % page_identifier
    req2 = requests.get(url)
    obj2 = req2.text
    new_obj2= obj2.replace(")]}'\n\n", '')
    dd2 = json.loads(new_obj2)
    details2 = dd2[0][1]
    for x in details2:
        if "*" in x[1]:
            x[1] = x[1].replace("*.", "")
        if x[1].endswith(domain):
            subdomain_list = check_and_append_subdomains(x[1], subdomain_list)
        else:
            other_related_domain_list = check_and_append_other_domains(x[1], other_related_domain_list)
    nextpage_details = dd2[0][3]
    if nextpage_details[3] != nextpage_details[4]:
        page_identifier = nextpage_details[1]
        find_domains_from_next_page_ct(page_identifier, domain, subdomain_list, other_related_domain_list)


def subdomains_from_google_ct(domain, subdomain_list, other_related_domain_list):
    print colored(' [+] Extracting subdomains from Certificate Transparency Reports\n', 'blue')
    url = 'https://transparencyreport.google.com/transparencyreport/api/v3/httpsreport/ct/certsearch?include_expired=true&include_subdomains=true&domain=%s' % (domain)
    req = requests.get(url)
    obj = req.text
    new_obj= obj.replace(")]}'\n\n", '')
    dd = json.loads(new_obj)
    details = dd[0][1]
    for x in details:
        if "*" in x[1]:
            x[1] = x[1].replace("*.", "")
        if x[1].endswith(domain):
            subdomain_list = check_and_append_subdomains(x[1], subdomain_list)
        else:
            other_related_domain_list = check_and_append_other_domains(x[1], other_related_domain_list)

    nextpage_details = dd[0][3]
    if nextpage_details[3] != nextpage_details[4]:
        page_identifier = nextpage_details[1]
        find_domains_from_next_page_ct(page_identifier, domain, subdomain_list, other_related_domain_list)
    return subdomain_list, other_related_domain_list


def banner():
    print colored(style.BOLD + '---> Finding subdomains, will be back soon with list. \n' + style.END, 'blue')


def main(domain):
    time.sleep(0.3)
    subdomain_list = []
    other_related_domain_list = []
    subdomain_list = subdomains(domain, subdomain_list)
    subdomain_list = subdomains_from_netcraft(domain, subdomain_list)
    subdomain_list, other_related_domain_list = subdomains_from_google_ct(domain, subdomain_list, other_related_domain_list)\
    # not printing list of 'other_related_domain_list' anywhere. This is done for later changes.
    return subdomain_list


def output(data, domain=""):
    print colored("List of subdomains found\n", 'green')
    for sub in data:
        print sub


if __name__ == "__main__":
    if len(sys.argv) != 0:
        #try:
        domain = sys.argv[1]
        banner()
        result = main(domain)
        output(result, domain)
        #except Exception as e:
    else:
        print "Please provide a domain name as argument"
        