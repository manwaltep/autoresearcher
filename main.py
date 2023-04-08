#!/usr/bin/env python3
import requests
import openai
import os
from dotenv import load_dotenv
from termcolor import colored
from prompts import literature_review_prompt, extract_answer_prompt

load_dotenv()

# Set API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is missing from .env"

# Configure OpenAI and Pinecone
openai.api_key = OPENAI_API_KEY

def fetch_papers(search_query, limit=100, year_range=None):
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": search_query,
        "limit": limit,
        "fields": "title,url,abstract,authors,citationStyles,journal,citationCount,year,externalIds"
    }

    if year_range is not None:
        params["year"] = year_range

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data['data']
    else:
        raise Exception(f"Failed to fetch data from Semantic Scholar API: {response.status_code}")


def fetch_and_sort_papers(search_query, limit=100, top_n=20, year_range="2010-2023"):
    papers = fetch_papers(search_query, limit, year_range)
    sorted_papers = sorted(papers, key=lambda x: x['citationCount'], reverse=True)
    return sorted_papers[:top_n]

def openai_call(prompt: str, use_gpt4: bool = False, temperature: float = 0.5, max_tokens: int = 100):
    if not use_gpt4:
        #Call GPT-3.5 turbo model
        messages=[{"role": "user", "content": prompt}]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].message.content.strip()
    else:
        #Call GPT-4 chat model
        messages=[{"role": "user", "content": prompt}]
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages = messages,
            temperature=temperature,
            max_tokens=max_tokens,
            n=1,
            stop=None,
        )
        return response.choices[0].message.content.strip()



def extract_answers_from_papers(papers, research_question, use_gpt4=False, temperature=0.1, max_tokens=150):
    answers = []
    default_answer = "No answer found."

    for paper in papers:
        abstract = paper.get("abstract", "")
        # citation = get_citation_by_doi(paper["externalIds"]["DOI"])
        if "externalIds" in paper and "DOI" in paper["externalIds"]:
            citation = get_citation_by_doi(paper["externalIds"]["DOI"])
        else:
            citation = paper["url"]

        prompt = extract_answer_prompt.format(research_question=research_question, abstract=abstract)
        answer = openai_call(prompt, use_gpt4=use_gpt4, temperature=temperature, max_tokens=max_tokens)

        answer_with_citation = f"{answer} {citation}"
        if answer != default_answer:
            answer_with_citation = f"{answer} SOURCE: {citation}"
            answers.append(answer_with_citation)
            print(colored(f"Answer found!", "green"))
            print(colored(f"{answer_with_citation}", "cyan"))

    return answers

def get_citation_by_doi(doi):
    url = f"https://api.citeas.org/product/{doi}?email=eimen@aietal.com"
    response = requests.get(url)
    data = response.json()
    return data["citations"][0]["citation"]

def combine_answers(answers, research_question, use_gpt4=False, temperature=0.1, max_tokens=1800):
    answer_list = "\n\n".join(answers)
    prompt = literature_review_prompt.format(research_question=research_question, answer_list=answer_list)
    literature_review = openai_call(prompt, use_gpt4=use_gpt4, temperature=temperature, max_tokens=max_tokens)

    return literature_review


# Set your research question and API key
research_question = "AI impact on the economy"

print(colored(f"Research question: {research_question}", "yellow", attrs=["bold", "blink"]))
print(colored("Auto Researcher initiated!", "yellow"))

# Fetch the top 20 papers for the research question
print(colored("Fetching top 20 papers...", "yellow"))
search_query = research_question
top_papers = fetch_and_sort_papers(search_query)
print(colored("Top 20 papers fetched!", "green"))

# Extract answers and from the top 20 papers
print(colored("Extracting answers and study qualities from papers...", "yellow"))
answers = extract_answers_from_papers(top_papers, research_question)
print(colored("Answers and study qualities extracted!", "green"))

# Combine answers into a concise academic literature review
print(colored("Synthesizing answers...", "yellow"))
literature_review = combine_answers(answers, research_question)
print(colored("Literature review generated!", "green"))

# Print the academic literature review
print(colored("Academic Literature Review:", "cyan"), literature_review, "\n")