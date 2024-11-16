import imaplib
import email
from email.header import decode_header
from datetime import datetime
import email.utils
import os
import pandas as pd

def connect_to_email(email_address, password, imap_server="imap.gmail.com"):
    """Connect to email server using IMAP"""
    try:
        imap = imaplib.IMAP4_SSL(imap_server)
        imap.login(email_address, password)
        return imap
    except Exception as e:
        print(f"Error connecting to email: {str(e)}")
        return None

def get_latest_email(imap, folder="INBOX"):
    """Read only the latest email and return as a pandas DataFrame"""
    try:
        # Select the mailbox
        status, messages = imap.select(folder)
        
        # Get total number of emails
        status, messages = imap.search(None, 'ALL')
        
        # Get the last (most recent) email ID
        latest_email_id = messages[0].split()[-1]
        
        # Lists to store email data
        dates = []
        subjects = []
        senders = []
        bodies = []
        timestamps = []
        
        # Fetch the latest email
        status, msg = imap.fetch(latest_email_id, "(RFC822)")
        
        for response in msg:
            if isinstance(response, tuple):
                email_msg = email.message_from_bytes(response[1])
                
                # Parse date
                date_tuple = email.utils.parsedate_tz(email_msg["Date"])
                if date_tuple:
                    timestamp = email.utils.mktime_tz(date_tuple)
                    local_date = datetime.fromtimestamp(timestamp)
                    timestamps.append(local_date)
                    dates.append(local_date.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    timestamps.append(datetime.min)
                    dates.append(email_msg["Date"])
                
                # Get subject
                subject = decode_header(email_msg["Subject"])[0]
                subject = subject[0].decode() if isinstance(subject[0], bytes) else subject[0]
                subjects.append(subject)
                
                # Get sender
                from_ = decode_header(email_msg.get("From", ""))[0]
                from_ = from_[0].decode() if isinstance(from_[0], bytes) else from_[0]
                senders.append(from_)
                
                # Get body
                body = ""
                if email_msg.is_multipart():
                    for part in email_msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                continue
                else:
                    try:
                        body = email_msg.get_payload(decode=True).decode()
                    except:
                        body = "Unable to decode message body"
                
                bodies.append(body)
        
        # Create DataFrame for the latest email
        latest_df = pd.DataFrame({
            'Timestamp': timestamps,
            'Date': dates,
            'From': senders,
            'Subject': subjects,
            'Body': bodies
        })
        
        return latest_df

    except Exception as e:
        print(f"Error reading email: {str(e)}")
        return pd.DataFrame()

def update_email_database(new_email_df, filename='email_database.csv'):
    """Update the email database with the new email"""
    try:
        # Check if database file exists
        if os.path.exists(filename):
            # Read existing database
            existing_df = pd.read_csv(filename)
            
            # Combine new email with existing database
            updated_df = pd.concat([new_email_df, existing_df], ignore_index=True)
        else:
            # If no existing database, use only the new email
            updated_df = new_email_df
        
        # Save updated database
        updated_df.to_csv(filename, index=False)
        return updated_df
    
    except Exception as e:
        print(f"Error updating database: {str(e)}")
        return None

def main():
    # Email configuration
    EMAIL_ADDRESS = "sharath.suram@gmail.com"
    EMAIL_PASSWORD = "wupz dbrw qkzc zknz"
    
    # Connect to email
    imap = connect_to_email(EMAIL_ADDRESS, EMAIL_PASSWORD)
    if not imap:
        return
    
    try:
        # Get only the latest email
        print("Fetching latest email...")
        latest_email_df = get_latest_email(imap)
        
        if not latest_email_df.empty:
            # Update the database with the new email
            updated_df = update_email_database(latest_email_df)
            
            if updated_df is not None:
                print("\nLatest Email:")
                print(latest_email_df.to_string(index=False))
                print("\nDatabase updated successfully")
            else:
                print("Error updating database")
        else:
            print("No new emails found or error occurred")
        
    finally:
        # Always logout
        imap.logout()

if __name__ == "__main__":
    main()