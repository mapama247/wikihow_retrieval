"""
Usage example:
     python main.py --langs es pt --out_dir my_wikihow_articles --max_per_category 50

This would retrieve 50 articles from each category of the Spanish and Portuguese
WikiHow websites and store their contents in a directory called `my_wikihow_articles`.
"""

import os
import re
import csv
import bs4
import time
import json
import uuid
import pprint
import datetime
import argparse
import requests
import collections
import wikihowunofficialapi
import pandas as pd
from typing import List

# Home page and important keywords for every language-specigic WikiHow site
languages = {
    "en": ( "https://www.wikihow.com", "Special", "Category"),
    "es": ( "https://es.wikihow.com", "Especial", "Categoría"),
    "pt": ( "https://pt.wikihow.com", "Especial", "Categoria"),
    "de": ( "https://de.wikihow.com", "Spezial", "Kategorie"),
    "fr": ( "https://fr.wikihow.com", "Spécial", "Catégorie"),
    "nl": ( "https://nl.wikihow.com", "Speciaal", "Categorie"),
    "ru": ( "https://ru.wikihow.com", "Служебная", "Категория"),
    "zh": ( "https://zh.wikihow.com", "Special", "Category"),
    "id": ( "https://id.wikihow.com", "Istimewa", "Kategori"),
    "it": ( "https://www.wikihow.it", "Speciale", "Categoria"),
    "cz": ( "https://www.wikihow.cz", "Speciální", "Kategorie"),
    "vn": ( "https://www.wikihow.vn", "Đặc_biệt", "Thể_loại"),
    "jp": ( "https://www.wikihow.jp", "特別", "カテゴリ"),
    "hi": ( "https://hi.wikihow.com", "विशेष", "श्रेणी"),
    "ko": ( "https://ko.wikihow.com", "특수", "분류"),
    "th": ( "https://th.wikihow.com", "พิเศษ", "หมวดหมู่"),
    "tr": ( "https://www.wikihow.com.tr", "Özel", "Kategori"),
    # "ar": ( "https://ar.wikihow.com", "خاص", "تصنيف"), # PENDING
    # "fa": ( "https://www.wikihowfarsi.com", "ویژه", "رده:جه"), # PENDING
}

def parse_args() -> argparse.Namespace:
    """ Parses command-line arguments. """
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--langs', default='es', nargs='*', choices=list(languages.keys()))
    parser.add_argument('-o', '--out_dir', default='./output', type=str)
    parser.add_argument('-m', '--max_per_category', default=-1, type=int)
    parser.add_argument('-d', '--delay', default=5, type=int)
    return parser.parse_args()

def get_id(url_addr:str) -> str:
    """ Returns the article ID given a URL. """
    _home_page = "https://" + url_addr.split("https://")[1].split("/")[0] + "/"
    site = url_addr.replace(_home_page, '')
    r = requests.get(f"{_home_page}api.php?format=json&action=query&prop=info&titles={site}")
    _pages = r.json()['query']['pages']
    for key in _pages.keys():
        article_id = _pages[key]['pageid']
    return article_id

def get_categories(language: str) -> List[str]:
    """ Returns a list of categories available in a language-specific WikiHow website. """
    home_page, special_trans, _ = languages[language]
    url_categories = requests.get(f"{home_page}/{special_trans}:CategoryListing")
    categories_soup = bs4.BeautifulSoup(url_categories.content, "html.parser")
    categories_list = categories_soup.find_all("a", {"id": re.compile('cat_list_.*')})
    categories_list = [cat.text.replace(" ", "-") for cat in categories_list]
    return categories_list

def get_num_pages(language: str, category_name: str) -> int:
    """ Returns the number of pages in the given category. """
    home_page, _, category_trans = languages[language]
    cat_page = requests.get(f"{home_page}/{category_trans}:{category_name}")
    soup = bs4.BeautifulSoup(cat_page.content, "html.parser")
    pages = soup.find_all("ul", class_="pagination")
    total_pages = len(pages[0].find_all("li")) if pages else 1
    return total_pages

def get_urls(language: str, category_name: str, page_number: int) -> List[str]:
    """ Returns a list of URLs for the given page and category. """
    home_page, _, category_trans = languages[language]
    curr_page = requests.get(f"{home_page}/{category_trans}:{category_name}?pg={page_number}")
    soup = bs4.BeautifulSoup(curr_page.content, "html.parser")
    responsive_thumbs = soup.find_all("div", class_="responsive_thumb")
    urls_list = [responsive_thumb.find("a", href=True)["href"] for responsive_thumb in responsive_thumbs]
    return urls_list

def generate_urls_file(langs: List[str], out_dir: str) -> None:
    print(f"Storing all URL addresses in {out_dir}/urls.jsonl...")
    set_of_urls = set()
    for _lang in langs:
        _categories = get_categories(_lang)
        for _category in _categories:
            _npages = get_num_pages(_lang, _category)
            for _page in range(1, _npages+1):
                _urls = get_urls(_lang, _category, _page)
                urls_file = open(os.path.join(out_dir, "urls.jsonl"), "a")
                for _url in _urls:
                    if _url not in set_of_urls:
                        set_of_urls.add(_url)
                        _id = uuid.uuid4().__str__()
                        _row = {"id": _id, "lang": _lang, "category": _category, "page": _page, "is_processed": False, "url": _url}
                        urls_file.writelines([json.dumps(_row, ensure_ascii=False), "\n"])
    print("Done!")

def process_article(url_addr: str) -> dict:
    """ Processes the article from a given URL and returns a dictionary with its content and some metadata. """
    article = wikihowunofficialapi.Article(url_addr).get()

    methods = []
    for method in article["methods"]:
        steps = []
        for step in method.steps:
            step_content = f"{step.number}. {step.title}\n{step.description}"
            steps.append(step_content)
        method = {
            "number": method.number,
            "title": method.title,
            "steps": steps,
        }
        methods.append(method)

    processed = {
        "url": article["url"],
        "title": article["title"],
        "intro": article["intro"],
        "methods": methods,
        "num_methods": article["n_methods"],
        "is_steps": True if len(methods)==1 and methods[0]["title"]=="Pasos" else False,
        # "summary": article["summary"],
        # "tips": article["tips"],
        "expert_author": article["is_expert"],
        "num_refs": article["references"],
        # "num_votes": article["num_votes"],
        # "num_views": article["views"],
        # "helpfulness": article["percent_helpful"],
    }
    return processed

if __name__ == "__main__":
    start_time = time.time()

    args = parse_args()
    print(args)

    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)

    URLS_FILE_PATH = os.path.join(args.out_dir,"urls.jsonl")
    if not os.path.isfile(URLS_FILE_PATH):
        generate_urls_file(args.langs, args.out_dir)

    df_all = pd.read_json(URLS_FILE_PATH, lines=True)
    dfs    = [elem.loc[~elem['is_processed']] for _,elem in df_all.groupby(["lang","category"])]
    counts = collections.defaultdict(dict)

    for i,df in enumerate(dfs,1):
        if df.shape[0] == 0:
            continue
        if args.max_per_category>0:
            df = df.head(args.max_per_category)
        print(f"Processing category {i}/{len(dfs)}.{df['category'].iloc[0]} from WIKI-HOW-{df['lang'].iloc[0].upper()}...")
        out_filename = f"{args.out_dir}/wikihow_{df['lang'].iloc[0]}_{df['category'].iloc[0].lower()}.jsonl"
        out_file = open(out_filename, 'a')
        for j, row in enumerate(df.itertuples(), 1):
            time.sleep(args.delay)  # to prevent being banned
            try:
                processed_article = process_article(row.url)
                out_file.writelines([json.dumps(processed_article, ensure_ascii=False), "\n"])
                print(f"\t{j}/{df.shape[0]}) Processed: [{row.id}] {processed_article['title']}")

                df_all.loc[df_all["id"]==row.id, "is_processed"] = True
                with open(URLS_FILE_PATH, "w") as f:
                    f.write(df_all.to_json(orient="records", lines=True, force_ascii=False))

                if row.category in counts[row.lang]:
                    counts[row.lang][row.category] += 1
                else:
                    counts[row.lang][row.category] = 1

            except:
                print(f"\t{j}/{df.shape[0]}) Error: Could not process {row.url}")

    pprint.pprint(counts)
    print(f"Num unprocessed: {df_all['is_processed'].value_counts()[0]}")
    print(f"Num processed:   {df_all['is_processed'].value_counts()[1]}")
    print(f"Total runtime:   {str(datetime.timedelta(seconds=round(time.time() - start_time)))}")
