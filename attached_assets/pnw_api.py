import requests
import time
from config import API_KEY

API_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
RATE_LIMIT_DELAY = 1  # 1 second delay between requests

def run_query(query: str):
    time.sleep(RATE_LIMIT_DELAY)  # Add delay between requests
    response = requests.post(API_URL, json={"query": query})
    if response.status_code == 429:  # Too Many Requests
        time.sleep(5)  # Wait longer if we hit the rate limit
        response = requests.post(API_URL, json={"query": query})
    response.raise_for_status()
    data = response.json()
    return data

def get_my_nation():
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
    data = run_query(query)
    return data["data"]["me"]["nation"]

def get_nations(page=1):
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
          cities {{
            infrastructure
          }}
          wars(limit: 3) {{
            date
            turnsleft
            attid
            defid
            att_money_looted
            winner
          }}
        }}
        paginatorInfo {{
          hasMorePages
          currentPage
        }}
      }}
    }}
    """
    data = run_query(query)
    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")
    if "data" not in data or "nations" not in data["data"]:
        raise ValueError(f"Unexpected API response structure: {data}")
    return data["data"]["nations"]

def has_treaty(my_alliance, target_alliance, protected_types=None):
    """Check if two alliances have a treaty that should prevent raiding"""
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
