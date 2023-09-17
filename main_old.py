"""
Usage example:
     python main.py --langs es pt --out_dir my_wikihow_articles --max_per_category 50

This would retrieve 50 articles from each category of the Spanish and Portuguese
WikiHow websites and store their contents in a directory called `my_wikihow_articles`.
"""

import os
import re
import bs4
import time
import json
import pprint
import datetime
import argparse
import requests
import wikihowunofficialapi
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

    if not os.path.exists(os.path.join(args.out_dir,"unprocessed")):
        os.makedirs(os.path.join(args.out_dir,"unprocessed"))

    data = {}
    unprocessed = []
    for lang in args.langs:
        data[lang] = {}
        categories = get_categories(lang)
        category_counts = dict.fromkeys(categories, 0)
        for i,category in enumerate(categories, 1):
            cat_time = time.time()
            out_filename = f"{args.out_dir}/wikihow_{lang}_{category.lower()}.jsonl"
            if os.path.exists(out_filename) and os.stat(out_filename).st_size!=0:
                open(out_filename, 'w').close()
            out_file = open(out_filename, 'a')
            err_file = open(f"{args.out_dir}/unprocessed/{lang}_{category.lower()}.txt", 'a')
            data[lang][category] = {}
            num_pages = get_num_pages(lang, category)
            for page in range(1, num_pages+1):
                urls = get_urls(lang, category, page)
                if args.max_per_category > 0:
                    urls = urls[:args.max_per_category-category_counts[category]]
                    if category_counts[category] >= args.max_per_category: break
                print(f"Processing page {page} out of {num_pages} in category {i}/{len(categories)}.{category} from WIKI-HOW-{lang.upper()}...")
                for j,url in enumerate(urls, 1):
                    time.sleep(args.delay) # to prevent being banned, 3s should be enough according to their policy
                    try:
                        uid = get_id(url)
                        if uid not in data[lang][category]:
                            processed_article = process_article(url)
                            data[lang][category][uid] = processed_article
                            out_file.writelines([json.dumps(processed_article, ensure_ascii=False), "\n"])
                            category_counts[category] += 1
                            print(f"\t{j}/{len(urls)}) Processed: [{uid}] {processed_article['title']}")
                    except:
                        # Keep URLs of problematic cases to analyse later
                        print(f"\t{j}/{len(urls)}) Error: Could not process {url}")
                        err_file.writelines([f"{category}\t{url}","\n"])
                        unprocessed.append(url)
            print(f"Time spent processing {category}: {str(datetime.timedelta(seconds=round(time.time() - cat_time)))}")

        with open(f"{args.out_dir}/wikihow_{lang}.json", "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False, default=str)
        with open(f"{args.out_dir}/unprocessed/{lang}.txt", "w") as f:
            _ = f.write('\n'.join(unprocessed))

        pprint.pprint(category_counts)
        print(f"Num failures:  {len(unprocessed)}")
        print(f"Num successes: {sum(val for val in category_counts.values())}")
        print(f"Total runtime: {str(datetime.timedelta(seconds=round(time.time()-start_time)))}")
