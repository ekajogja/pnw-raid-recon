import requests
import time
import os
from filter_beige import filter_beige_targets # Import the new filtering function
# Removed: from config import API_KEY - API key will be passed as parameter

# Removed: API_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}" - URL will be built in run_query
RATE_LIMIT_DELAY = 1  # 1 second delay between requests

def run_query(api_key: str, query: str):
    """
    Run a GraphQL query against the Politics & War API.

    Args:
        api_key: The Politics & War API key.
        query: GraphQL query string

    Returns:
        JSON response data

    Raises:
        ValueError: If there is an API error, authentication error, or invalid response
    """
    # Check if API key is provided
    if not api_key:
        raise ValueError("API_KEY is not provided. Please enter your Politics & War API key.")

    API_URL = f"https://api.politicsandwar.com/graphql?api_key={api_key}"

    try:
        time.sleep(RATE_LIMIT_DELAY)  # Add delay between requests
        response = requests.post(API_URL, json={"query": query})

        # Handle specific HTTP error codes
        if response.status_code == 401:
            raise ValueError("API authentication failed. Check your API key.")
        elif response.status_code == 403:
            raise ValueError("API access forbidden. Your key may be invalid or lacks permissions.")
        elif response.status_code == 429:  # Too Many Requests
            print("Rate limit hit, waiting to retry...")
            time.sleep(5)  # Wait longer if we hit the rate limit
            response = requests.post(API_URL, json={"query": query})
            if response.status_code != 200:
                raise ValueError(f"Rate limit retry failed with status code {response.status_code}")
        elif response.status_code != 200:
            raise ValueError(f"API request failed with status code {response.status_code}")

        # Parse response as JSON
        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            error_messages = [error.get("message", "Unknown GraphQL error") for error in data.get("errors", [])]
            error_message = "; ".join(error_messages)
            print(f"GraphQL API Error: {error_message}")
            raise ValueError(f"GraphQL API Error: {error_message}")

        # Validate response structure
        if "data" not in data:
            raise ValueError("API response missing 'data' field")

        return data

    except requests.exceptions.RequestException as e:
        # Handle network errors
        print(f"Network error communicating with the API: {str(e)}")
        raise ValueError(f"Network error: {str(e)}")
    except ValueError as e:
        # Re-raise ValueError for specific API errors
        raise
    except Exception as e:
        # Catch any other errors
        print(f"Unexpected error in API query: {str(e)}")
        raise ValueError(f"API query failed: {str(e)}")

def get_my_nation(api_key: str):
    """
    Get information about the currently authenticated nation.

    Args:
        api_key: The Politics & War API key.

    Returns:
        Nation data dictionary

    Raises:
        ValueError: If authentication fails or the API returns an error
    """
    query = """
    {
      me {
        nation {
          id
          score
          alliance {
            id
            name
            treaties {
              alliance1_id
              alliance2_id
              treaty_type
              treaty_url
            }
          }
        }
      }
    }
    """
    # Run the query with already enhanced error handling
    data = run_query(api_key, query)

    # Additional error handling for specific me/nation response errors
    if "data" not in data:
        raise ValueError("API response missing data field")
    if "me" not in data["data"]:
        raise ValueError("API response missing 'me' field - authentication may have failed")
    if not data["data"]["me"] or "nation" not in data["data"]["me"]:
        raise ValueError("Failed to retrieve nation data. Your API key may be invalid or expired.")

    return data["data"]["me"]["nation"]

def get_nations(api_key: str, page=1):
    """
    Get a list of nations from the Politics & War API.

    Args:
        api_key: The Politics & War API key.
        page: Page number for pagination

    Returns:
        Dictionary containing nation data and pagination info

    Raises:
        ValueError: If the API returns an error or unexpected response structure
    """
    query = """
    {{
      nations(page: {page}, first: 500) {{
        data {{
          id
          nation_name
          score
          alliance_id
          vacation_mode_turns
          beige_turns
          color
          soldiers
          tanks
          aircraft
          ships
          missiles
          nukes
          spies
          alliance {{
            id
            name
          }}
          wars {{
            turns_left
            date
            def_id
          }}
          bankrecs(orderBy: {{ column: DATE, order: DESC }}, limit: 10) {{
            date
            sender {{
              id
            }}
            receiver {{
              id
            }}
            money
          }}
        }}
        paginatorInfo {{
          hasMorePages
          currentPage
        }}
      }}
    }}
    """.format(page=page)
    # Run the query - error handling happens in run_query function
    data = run_query(api_key, query)

    # Additional validation for this specific endpoint
    if "data" not in data:
        raise ValueError("API response missing 'data' field")
    if "nations" not in data["data"]:
        raise ValueError("API response missing 'nations' field - API format may have changed")
    if "data" not in data["data"]["nations"]:
        raise ValueError("API response missing nation data")

    # Log success and nation count
    nation_count = len(data["data"]["nations"]["data"])
    print(f"Successfully fetched {nation_count} nations from API (page {page})")

    return data["data"]["nations"]

def get_beige_nations(api_key: str, args, min_score_ratio: float, max_score_ratio: float):
    """
    Get a list of beige nations with 1 beige turn left.

    Args:
        api_key: The Politics & War API key.
        args: An object containing filtering parameters (limit, max_pages, ignore_dnr).
        min_score_ratio: Minimum target score ratio relative to user's nation score.
        max_score_ratio: Maximum target score ratio relative to user's nation score.

    Returns:
        Tuple containing user's nation data and a list of beige nations.

    Raises:
        ValueError: If the API returns an error or unexpected response structure.
    """
    my_nation = get_my_nation(api_key)
    filtered_beige_nations = []
    page = 1
    has_more_pages = True

    while has_more_pages and page <= args.max_pages:
        nations_data = get_nations(api_key, page)
        
        # Filter nations on the current page
        filtered_on_page = filter_beige_targets(nations_data['data'], my_nation, args, min_score_ratio, max_score_ratio)
        
        # Add filtered nations from this page to the overall list
        filtered_beige_nations.extend(filtered_on_page)
        
        # Check if we have reached the limit
        if len(filtered_beige_nations) >= args.limit:
            print(f"Limit of {args.limit} reached, stopping page fetching.")
            break # Stop fetching pages if limit is reached
            
        has_more_pages = nations_data['paginatorInfo']['hasMorePages']
        page += 1

    # Sort and apply limit to the collected filtered nations
    # The filter_beige_targets function already sorts and limits, but we need to re-sort
    # and limit the combined list from multiple pages if the limit wasn't exactly met
    # when breaking the loop. However, since filter_beige_targets now filters page by page,
    # we need to sort and limit the accumulated list here.
    
    # Re-sort the accumulated filtered nations (filter_beige_targets sorts each page)
    filtered_beige_nations.sort(key=lambda x: (x.get('beige_turns', 0), -x.get('score', 0)))

    # Apply the limit to the final sorted list
    final_filtered_nations = filtered_beige_nations[:args.limit]


    return my_nation, final_filtered_nations

def has_treaty(my_alliance, target_alliance, protected_types=None):
    """
    Check if two alliances have a treaty that should prevent raiding.

    Args:
        my_alliance: Alliance data for your nation
        target_alliance: Alliance data for target nation
        protected_types: List of treaty types that prevent raiding

    Returns:
        Boolean indicating if a treaty exists
    """
    if not protected_types:
        # Default treaty types that should prevent raiding
        protected_types = ['MDP', 'MDOAP', 'ODP', 'ODOAP', 'NAP', 'PIAT', 'Protectorate']

    if not my_alliance or not target_alliance:
        return False

    # Check both alliances' treaties
    for treaty in my_alliance.get('treaties', []):
        if (treaty['alliance1_id'] == target_alliance['id'] or
            treaty['alliance2_id'] == target_alliance['id']):
            if treaty['treaty_type'] in protected_types:
                return True

    return False
