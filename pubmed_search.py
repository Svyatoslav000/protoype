from Bio import Entrez
from config import PUBMED_EMAIL

Entrez.email = PUBMED_EMAIL

def search_pubmed(query, retmax=5):
    handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax)
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]

def fetch_abstracts(pmid_list):
    if not pmid_list:
        return ""
    ids = ",".join(pmid_list)
    handle = Entrez.efetch(db="pubmed", id=ids, rettype="abstract", retmode="text")
    abstracts = handle.read()
    handle.close()
    return abstracts

def get_abstracts_by_inn(inn):
    query = f"{inn}[Title/Abstract] AND (bioequivalence[Title/Abstract] OR pharmacokinetics[Title/Abstract])"
    pmids = search_pubmed(query, retmax=5)
    return fetch_abstracts(pmids)