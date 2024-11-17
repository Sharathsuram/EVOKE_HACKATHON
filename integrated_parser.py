import os
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import logging
import time  # Added missing import
from Email_parser import connect_to_email, fetch_incoming_emails
from Data_cleaning import EmailProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegratedEmailSystem:
    def __init__(self):
        load_dotenv()
        self.gemini_api_key = os.getenv("gemini_api")
        self.email_processor = EmailProcessor(self.gemini_api_key)
        self.mail_connection = None
        
    def initialize_connection(self):
        """Initialize email connection"""
        self.mail_connection = connect_to_email()
        if not self.mail_connection:
            raise ConnectionError("Failed to connect to email server")
            
    def process_single_email(self, email_data):
        """Process a single email and return analysis"""
        try:
            analysis = self.email_processor.analyze_email(
                email_data['subject'],
                email_data['body']
            )
            
            result = {
                'date': email_data['date'],
                'from': email_data['from'],
                'subject': email_data['subject'],
                'body': email_data['body'],
                'request_type': analysis['request_type'],
                'category': analysis['category'],
                'actions': '\n'.join(analysis['actions']),
                'priority': analysis['priority'],
                'processed_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return result
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            return None

    def save_results(self, results, filename='processed_emails_database.csv'):
        """
        Save processed results to a single CSV file
        
        Args:
            results (dict): Dictionary containing processed email data
            filename (str): Name of the file to save results (defaults to processed_emails_database.csv)
        """
        try:
            # Convert single result to DataFrame
            new_df = pd.DataFrame([results])
            
            # Try to read existing file
            try:
                existing_df = pd.read_csv(filename)
                
                # Concatenate new results with existing data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # Remove any duplicates based on date, subject, and from fields
                combined_df = combined_df.drop_duplicates(
                    subset=['date', 'subject', 'from'], 
                    keep='last'
                )
                
                # Sort by date (latest first)
                combined_df['date'] = pd.to_datetime(combined_df['date'])
                combined_df = combined_df.sort_values(by='date', ascending=False)
                
                # Save updated DataFrame
                combined_df.to_csv(filename, index=False)
                
            except FileNotFoundError:
                # If file doesn't exist, create it with the new data
                new_df.to_csv(filename, index=False)
                
            logger.info(f"Results successfully saved to {filename}")
            
            # Generate HTML display for the latest email
            self.update_html_display(results)
            
        except Exception as e:
            logger.error(f"Error saving results to {filename}: {str(e)}")
            raise

    def update_html_display(self, latest_email):
        try:
            html_template = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Latest Email Processing Results</title>
                <meta http-equiv="refresh" content="60">
                <link rel="stylesheet" href="styles.css">
            </head>
            <body>
                <div class="container">
                    <h2>Latest Processed Email</h2>
                    <div class="section">
                        <p><span class="label">Date:</span> {date}</p>
                        <p><span class="label">From:</span> {from_}</p>
                        <p><span class="label">Subject:</span> {subject}</p>
                        <p><span class="label">Body:</span> {body}</p>
                        <p><span class="label">Request Type:</span> {request_type}</p>
                        <p><span class="label">Category:</span> {category}</p>
                        <p><span class="label">Priority:</span> 
                            <span class="priority-{priority_lower}">{priority}</span>
                        </p>
                        <p><span class="label">Recommended Actions:</span></p>
                        <div class="actions">
                            {actions}
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
            actions_list = latest_email['actions'].split('\n')
            actions_html = '<ol>' + ''.join([f'<li>{action}</li>' for action in actions_list]) + '</ol>'
            html_content = html_template.format(
                date=latest_email['date'],
                from_=latest_email['from'],
                subject=latest_email['subject'],
                body=latest_email['body'],
                request_type=latest_email['request_type'],
                category=latest_email['category'],
                priority=latest_email['priority'],
                priority_lower=latest_email['priority'].lower(),
                actions=actions_html
            )
            with open('latest_email.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info("HTML display updated successfully")
        except Exception as e:
            logger.error(f"Error updating HTML display: {str(e)}")


    def run_continuous_processing(self):
        """Continuously monitor and process incoming emails"""
        try:
            self.initialize_connection()
            logger.info("Starting continuous email processing...")
            
            while True:
                # Fetch new emails
                new_emails = fetch_incoming_emails(self.mail_connection)
                
                if new_emails:
                    logger.info(f"Found {len(new_emails)} new emails")
                    
                    for email_data in new_emails:
                        # Process each email
                        result = self.process_single_email(email_data)
                        
                        if result:
                            # Save results
                            self.save_results(result)
                            
                            # Log high priority items
                            if result['priority'].lower() == 'high':
                                logger.warning(
                                    f"High priority email detected!\n"
                                    f"From: {result['from']}\n"
                                    f"Subject: {result['subject']}\n"
                                    f"Type: {result['request_type']}"
                                )
                                
                else:
                    logger.info("No new emails found")
                    
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Stopping email processing...")
        except Exception as e:
            logger.error(f"Error in continuous processing: {str(e)}")
        finally:
            if self.mail_connection:
                self.mail_connection.logout()

def main():
    system = IntegratedEmailSystem()
    system.run_continuous_processing()

if __name__ == "__main__":
    main()