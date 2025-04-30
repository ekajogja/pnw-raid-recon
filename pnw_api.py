import requests
import time
import os
from config import API_KEY

API_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
RATE_LIMIT_DELAY = 1  # 1 second delay between requests

def run_query(query: str):
    """
    Run a GraphQL query against the Politics & War API.
    
    Args:
        query: GraphQL query string
    
    Returns:
        JSON response data
    
    Raises:
        ValueError: If there is an API error, authentication error, or invalid response
    """
    # Check if API key is set
    if not API_KEY:
        raise ValueError("API_KEY is not set. Please set your Politics & War API key in the environment variables.")
    
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

def get_my_nation():
    """
    Get information about the currently authenticated nation.
    
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
          soldiers
          spies
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
    data = run_query(query)
    
    # Additional error handling for specific me/nation response errors
    if "data" not in data:
        raise ValueError("API response missing data field")
    if "me" not in data["data"]:
        raise ValueError("API response missing 'me' field - authentication may have failed")
    if not data["data"]["me"] or "nation" not in data["data"]["me"]:
        raise ValueError("Failed to retrieve nation data. Your API key may be invalid or expired.")
        
    return data["data"]["me"]["nation"]

def get_nations(page=1):
    """
    Get a list of nations from the Politics & War API.
    
    Args:
        page: Page number for pagination
    
    Returns:
        Dictionary containing nation data and pagination info
    
    Raises:
        ValueError: If the API returns an error or unexpected response structure
    """
    query = f"""
    {{
      nations(page: {page}, first: 500) {{
        data {{
          id
          nation_name
          score
          last_active
          alliance_id
          soldiers
          spies
          vacation_mode_turns
          color
          alliance {{
            id
            name
          }}
          cities {{
            infrastructure
          }}
          wars {{
            turnsleft
            date
          }}
        }}
        paginatorInfo {{
          hasMorePages
          currentPage
        }}
      }}
    }}
    """
    # Run the query - error handling happens in run_query function
    data = run_query(query)
    
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
