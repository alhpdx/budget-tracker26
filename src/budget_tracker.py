import os
import json
import csv
from datetime import datetime, timedelta
from io import StringIO
import requests

# Configuration
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = os.environ.get('DATABASE_ID')
BUDGET_CYCLE_START_DAY = 20

BUDGETS = {
    'Groceries': 800,
    'Food & Dining': 800,
    'Transportation': 100,
    'Entertainment': 300,
    'Fitness & Wellness': 400,
    'Pet Care': 50
}

CATEGORY_MAPPINGS = {
    'Groceries': ['Groceries', 'Whole Foods', 'Trader Joe', 'Costco', 'Fred Meyer'],
    'Food & Dining': ['Dining & Drinks', 'Restaurants', 'Uber Eats', 'Grubhub', 'Pizza', 'Taco Bell'],
    'Transportation': ['Auto & Transport', 'Uber', 'Lyft', 'Parking'],
    'Entertainment': ['Entertainment & Rec', 'Movies', 'Cinema', 'Theater', 'StubHub', 'AMC'],
    'Fitness & Wellness': ['Fitness', 'Gym', 'Life Time'],
    'Pet Care': ['Pets', 'Pet', 'Vet', 'Animal Hospital', 'Chewy']
}

def get_budget_cycle():
    """Get current budget cycle (20th to 19th)"""
    today = datetime.now()
    current_day = today.day
    
    if current_day >= BUDGET_CYCLE_START_DAY:
        cycle_start = datetime(today.year, today.month, BUDGET_CYCLE_START_DAY)
        if today.month == 12:
            cycle_end = datetime(today.year + 1, 1, BUDGET_CYCLE_START_DAY - 1)
        else:
            cycle_end = datetime(today.year, today.month + 1, BUDGET_CYCLE_START_DAY - 1)
    else:
        if today.month == 1:
            cycle_start = datetime(today.year - 1, 12, BUDGET_CYCLE_START_DAY)
        else:
            cycle_start = datetime(today.year, today.month - 1, BUDGET_CYCLE_START_DAY)
        cycle_end = datetime(today.year, today.month, BUDGET_CYCLE_START_DAY - 1)
    
    return cycle_start, cycle_end

def categorize_transaction(name, rocket_category):
    """Map transaction to budget category"""
    for category, keywords in CATEGORY_MAPPINGS.items():
        for keyword in keywords:
            if keyword.lower() in name.lower() or keyword.lower() in rocket_category.lower():
                return category
    return None

def process_csv(csv_content):
    """Process Rocket Money CSV and return spending by category"""
    spending = {cat: 0 for cat in BUDGETS.keys()}
    cycle_start, cycle_end = get_budget_cycle()
    
    reader = csv.DictReader(StringIO(csv_content))
    transaction_count = 0
    
    for row in reader:
        try:
            date_str = row['Date']
            amount = float(row['Amount']) if row['Amount'] else 0
            name = row.get('Name', '')
            rocket_category = row.get('Category', '')
            
            # Skip invalid transactions
            if amount <= 0 or 'Credit Card Payment' in name or 'Automatic Payment' in name:
                continue
            
            # Check if in budget cycle
            tx_date = datetime.strptime(date_str, '%Y-%m-%d')
            if cycle_start <= tx_date <= cycle_end:
                category = categorize_transaction(name, rocket_category)
                if category:
                    spending[category] += round(amount, 2)
                    transaction_count += 1
        except Exception as e:
            print(f"Error processing row: {e}")
            continue
    
    print(f"Processed {transaction_count} transactions")
    return spending

def update_notion(spending):
    """Update Notion database with spending data"""
    
    if not NOTION_TOKEN or not DATABASE_ID:
        print("ERROR: NOTION_TOKEN or DATABASE_ID not set")
        return
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Get all pages in database
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    
    response = requests.post(url, headers=headers, json={})
    
    if response.status_code != 200:
        print(f"ERROR: Failed to query database: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    pages = data.get('results', [])
    
    # Update each category page
    for page in pages:
        props = page['properties']
        category_name = props.get('Category', {}).get('title', [])
        
        if category_name:
            category = category_name[0]['text']['content'] if category_name else None
            
            if category and category in spending:
                spent_amount = spending[category]
                budget_amount = BUDGETS.get(category, 0)
                
                # Update the Notion page
                update_url = f"https://api.notion.com/v1/pages/{page['id']}"
                
                update_data = {
                    "properties": {
                        "Spent": {
                            "number": spent_amount
                        },
                        "Remaining": {
                            "number": max(0, budget_amount - spent_amount)
                        },
                        "% Used": {
                            "number": round((spent_amount / budget_amount) * 100) if budget_amount > 0 else 0
                        }
                    }
                }
                
                update_response = requests.patch(update_url, headers=headers, json=update_data)
                
                if update_response.status_code == 200:
                    print(f"✓ Updated {category}: ${spent_amount:.2f} / ${budget_amount}")
                else:
                    print(f"ERROR updating {category}: {update_response.status_code}")

def main():
    """Main function"""
    print("Starting budget tracker...")
    
    # Check if CSV file exists in repo
    csv_file = 'rocket_money_export.csv'
    
    if os.path.exists(csv_file):
        with open(csv_file, 'r') as f:
            csv_content = f.read()
        
        spending = process_csv(csv_content)
        update_notion(spending)
        print("✓ Budget tracking complete!")
    else:
        print(f"WARNING: {csv_file} not found. Upload your Rocket Money CSV to the repo.")
        print("Notion database not updated.")

if __name__ == "__main__":
    main()
