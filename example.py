import json
import os
import sys
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_path = os.path.join(project_root, "src")
sys.path.append(src_path)

from yars.yars import YARS
from yars.utils import display_results

# Initialize the YARS Reddit miner
miner = YARS()


def display_data(miner, query, limit, sort, time_filter):
    """Search Reddit and display results in terminal."""

    # Search Reddit with configurable sort and time filter
    search_results = miner.search_reddit(query, limit=limit, sort=sort, time_filter=time_filter)
    display_results(search_results, f"SEARCH (query='{query}', sort='{sort}', time='{time_filter}')")

    return search_results


def scrape_search_data(search_results, query, sort, time_filter, filename=None):
    """Scrape full details for each search result, saving to a dynamic JSON file with search summary at top."""

    # Generate dynamic filename from query parameters if not provided
    if filename is None:
        safe_query = re.sub(r'[^\w\-]', '_', query)
        filename = f"search_{safe_query}_{sort}_{time_filter}.json"

    try:
        print(f"\nFound {len(search_results)} results for '{query}' (sort={sort}, time={time_filter})")

        # Build output with search summary at the top
        output = {
            "search_info": {
                "query": query,
                "sort": sort,
                "time_filter": time_filter,
                "total_results": len(search_results),
            },
            "search_results": search_results,
            "posts": [],
        }

        # Scrape details and comments for each search result
        for i, result in enumerate(search_results, 1):
            permalink = result["permalink"]
            post_details = miner.scrape_post_details(permalink)
            print(f"Processing post {i}/{len(search_results)}: {result['title'][:60]}")

            if post_details:
                post_data = {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "permalink": result.get("permalink", ""),
                    "description": result.get("description", ""),
                    "body": post_details.get("body", ""),
                    "comments": post_details.get("comments", []),
                }
                output["posts"].append(post_data)
                save_to_json(output, filename)
            else:
                print(f"Failed to scrape details for post: {result['title']}")

    except Exception as e:
        print(f"Error occurred while scraping search results: {e}")


def save_to_json(data, filename):
    """Save data to a JSON file."""
    try:
        with open(filename, "w") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving data to JSON file: {e}")


# Main execution
if __name__ == "__main__":
    query = "Plaud"
    sort = "top"
    time_filter = "week"
    limit = 2

    # Display search results in terminal
    search_results = display_data(miner, query=query, limit=limit, sort=sort, time_filter=time_filter)

    # Scrape detailed post data and save to dynamic JSON file
    scrape_search_data(search_results, query=query, sort=sort, time_filter=time_filter)
