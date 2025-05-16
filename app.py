from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
from raid import get_raid_targets, parse_args, format_money, format_hours
from pnw_api import get_beige_nations
import sys
import os
from dotenv import load_dotenv
from config import DEBUG

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "development-key")

@app.route('/')
def index():
    """Render the main page with the form."""
    return render_template('index.html')

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    """Process the form and scan for raid targets."""
    if request.method == 'GET':
        # If someone navigates directly to /scan, redirect them to the form
        return redirect(url_for('index'))
    try:
        # Create a namespace object similar to what argparse would return
        class Args:
            pass
        
        args = Args()
        
        try:
            # Import config values as defaults
            from config import MIN_INACTIVE_DAYS, MAX_SOLDIER_RATIO, IGNORE_DNR, MAX_PAGES
            
            # Set default values
            args.inactive_time = float(request.form.get('inactive_time', MIN_INACTIVE_DAYS))
            args.ignore_dnr = request.form.get('ignore_dnr') == 'true'
            args.troop_ratio = float(request.form.get('troop_ratio', MAX_SOLDIER_RATIO))
            args.limit = int(request.form.get('limit', 10))
            args.max_pages = int(request.form.get('max_pages', MAX_PAGES))
        except (ValueError, TypeError) as e:
            flash(f"Invalid form data: {str(e)}", "error")
            return redirect(url_for('index'))
        args.api_key = request.form.get('api_key') # Get API key from form

        try:
            # Get raid targets
            my_nation, targets = get_raid_targets(args.api_key, args) # Pass API key to function
        except ValueError as e:
            # Handle expected API errors with a clear user message
            error_message = str(e)
            print(f"API Error: {error_message}")
            
            # Check for common error types and provide more specific messages
            if "API_KEY" in error_message:
                flash("Politics & War API key is missing or invalid. Please check your environment configuration.", "error")
            elif "authentication failed" in error_message or "invalid or expired" in error_message:
                flash("Authentication to Politics & War API failed. Please check your API key.", "error")
            elif "rate limit" in error_message.lower():
                flash("Politics & War API rate limit exceeded. Please wait a few minutes and try again.", "error")
            else:
                # General API error message
                flash(f"Politics & War API Error: {error_message}", "error")
                
            return redirect(url_for('index'))
        except Exception as e:
            # Handle unexpected errors
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in get_raid_targets: {str(e)}\n{error_details}")
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('index'))
        
        # Print summary and results to console for command-line viewing
        print("\n📊 Summary:")
        print(f"  Found {len(targets)} potential raid targets")
        print("  No targets found" if not targets else "")
        
        print(f"\n🎯 Top {len(targets)} Raid Targets (sorted by score):")
        for i, t in enumerate(targets, 1):
            nation_url = f"https://politicsandwar.com/nation/id={t['id']}"
            print(f"{i}. {t['name']} (ID: {t['id']}) | {t['alliance']}")
            print(f"  Score: {t['score']:,.2f} | Cities: {t.get('city_count', '?')}")
            print(f"  Inactive: {t['inactive_days']}d | Last war: {format_hours(t.get('hours_since_war'))} ago")
            print(f"  War Status: ✅ No active defensive wars")
            print(f"  URL: {nation_url}")
            print(f"  Attack: https://politicsandwar.com/nation/war/declare/declare/id={t['id']}")
            print()
        
        # Prepare data for template
        data = {
            'my_nation': my_nation,
            'targets': targets if targets else [],  # Ensure targets is never None
            'params': {
                'inactive_time': args.inactive_time,
                'ignore_dnr': args.ignore_dnr,
                'troop_ratio': args.troop_ratio,
                'limit': args.limit,
                'max_pages': args.max_pages
            }
        }
        
        # Helper functions for templates - pass as separate arguments to avoid string formatting issues
        return render_template('results.html', data=data, 
                              format_money=format_money, 
                              format_hours=format_hours)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Unhandled error in scan route: {str(e)}\n{error_details}")
        flash(f"An unexpected error occurred: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """API endpoint to get raid targets as JSON."""
    try:
        # Create a namespace object similar to what argparse would return
        class Args:
            pass
        
        args = Args()
        
        # Parse the request JSON
        req_data = request.get_json() or {}
        
        try:
            # Import config values as defaults
            from config import MIN_INACTIVE_DAYS, MAX_SOLDIER_RATIO, IGNORE_DNR, MAX_PAGES
            
            # Set default values
            args.inactive_time = float(req_data.get('inactive_time', MIN_INACTIVE_DAYS))
            args.ignore_dnr = req_data.get('ignore_dnr', IGNORE_DNR)
            args.troop_ratio = float(req_data.get('troop_ratio', MAX_SOLDIER_RATIO))
            args.limit = int(req_data.get('limit', 10))
            args.max_pages = int(req_data.get('max_pages', MAX_PAGES))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
        
        try:
            # Get raid targets
            my_nation, targets = get_raid_targets(args)
            
            # Print results to console for command-line viewing
            print(f"\n🎯 Top {len(targets)} Raid Targets from API (sorted by score):")
            for i, t in enumerate(targets, 1):
                nation_url = f"https://politicsandwar.com/nation/id={t['id']}"
                print(f"{i}. {t['name']} (ID: {t['id']}) | {t['alliance']}")
                print(f"  Score: {t['score']:,.2f} | Cities: {t.get('city_count', '?')}")
                print(f"  Inactive: {t['inactive_days']}d | Last war: {format_hours(t.get('hours_since_war'))} ago")
                print(f"  War Status: ✅ No active defensive wars")
                print(f"  URL: {nation_url}")
                print(f"  Attack: https://politicsandwar.com/nation/war/declare/declare/id={t['id']}")
                print()
        except ValueError as e:
            # Handle expected API errors with specific status codes and messages
            error_message = str(e)
            print(f"API Error in API route: {error_message}")
            
            # Check for common error types and provide more specific status codes
            if "API_KEY" in error_message or "authentication failed" in error_message:
                return jsonify({'error': 'Authentication failed', 'message': error_message}), 401
            elif "rate limit" in error_message.lower():
                return jsonify({'error': 'Rate limit exceeded', 'message': error_message}), 429
            else:
                # General API error
                return jsonify({'error': 'API Error', 'message': error_message}), 400
        except Exception as e:
            # Handle unexpected errors
            import traceback
            error_details = traceback.format_exc()
            print(f"Unexpected error in API get_raid_targets: {str(e)}\n{error_details}")
            return jsonify({'error': 'Server Error', 'message': str(e)}), 500
        
        return jsonify({
            'my_nation': my_nation,
            'targets': targets,
            'params': {
                'inactive_time': args.inactive_time,
                'ignore_dnr': args.ignore_dnr,
                'troop_ratio': args.troop_ratio,
                'limit': args.limit,
                'max_pages': args.max_pages
            }
        })
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Unhandled error in API scan route: {str(e)}\n{error_details}")
        return jsonify({'error': str(e)}), 500

@app.route('/beige')
def beige_index():
    """Render the beige finder main page with the form."""
    return render_template('beige.html')

@app.route('/scan_beige', methods=['POST'])
def scan_beige():
    """Process the form and scan for beige nations."""
    try:
        class Args:
            pass

        args = Args()

        try:
            # Import config values as defaults
            from config import MIN_SCORE_RATIO, MAX_SCORE_RATIO, MAX_PAGES # Import score limits and max pages

            # Get values from form, use config defaults if not provided
            args.api_key = request.form.get('api_key')
            args.limit = int(request.form.get('limit', 10)) # Default limit to 10
            args.max_pages = int(request.form.get('max_pages', MAX_PAGES)) # Use MAX_PAGES from config
            args.ignore_dnr = request.form.get('ignore_dnr') == 'true' # Get ignore_dnr from form

            # Get min and max score ratio from form, use config defaults if not provided
            min_score_ratio_val = float(request.form.get('min_score_ratio', MIN_SCORE_RATIO))
            max_score_ratio_val = float(request.form.get('max_score_ratio', MAX_SCORE_RATIO))

            # Add score ratio to args object for filter_beige_targets
            args.min_score_ratio = min_score_ratio_val
            args.max_score_ratio = max_score_ratio_val


        except (ValueError, TypeError) as e:
            flash(f"Invalid form data: {str(e)}", "error")
            return redirect(url_for('beige_index')) # Redirect to beige index on error

        try:
            # Get beige nations
            # Pass the args object which now includes min/max score ratio
            my_nation, targets = get_beige_nations(args.api_key, args, args.min_score_ratio, args.max_score_ratio)


        except ValueError as e:
            error_message = str(e)
            print(f"API Error: {error_message}")

            if "API_KEY" in error_message:
                flash("Politics & War API key is missing or invalid. Please check your environment configuration.", "error")
            elif "authentication failed" in error_message or "invalid or expired" in error_message:
                flash("Authentication to Politics & War API failed. Please check your API key.", "error")
            elif "rate limit" in error_message.lower():
                flash("Politics & War API rate limit exceeded. Please wait a few minutes and try again.", "error")
            else:
                flash(f"Politics & War API Error: {error_message}", "error")

            return redirect(url_for('beige_index')) # Redirect to beige index on error
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in get_beige_nations: {str(e)}\n{error_details}")
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('beige_index')) # Redirect to beige index on error

        # Prepare data for template
        data = {
            'my_nation': my_nation,
            'targets': targets if targets else [],
            'params': {
                'ignore_dnr': args.ignore_dnr,
                'limit': args.limit,
                'max_pages': args.max_pages
            }
        }

        return render_template('beige-result.html', data=data,
                              format_money=format_money,
                              format_hours=format_hours)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Unhandled error in scan_beige route: {str(e)}\n{error_details}")
        flash(f"An unexpected error occurred: {str(e)}", "error")
        return redirect(url_for('beige_index')) # Redirect to beige index on error

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=DEBUG)
