import imaplib
import email
from email.header import decode_header
import pandas as pd
from datetime import datetime
import time
import os
from dotenv import load_dotenv
load_dotenv()
# Email configuration
IMAP_SERVER = "imap.gmail.com"  # Replace with your email provider's IMAP server
EMAIL = os.getenv("user_email")
PASSWORD = os.getenv("password")

def connect_to_email():
    """Connect to the email server and select the inbox."""
    try:
        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")  # Select the inbox folder
        return mail
    except Exception as e:
        print(f"Failed to connect to the email server: {e}")
        return None

def fetch_incoming_emails(mail):
    """Fetch all incoming emails from the inbox."""
    emails = []
    try:
        # Use the "SINCE" filter with the current date to fetch new emails
        today = datetime.now().strftime("%d-%b-%Y")  # e.g., "17-Nov-2024"
        status, messages = mail.search(None, f"SINCE {today}")
        if status != "OK":
            print("Failed to retrieve incoming emails.")
            return emails

        # Fetch email data
        email_ids = messages[0].split()
        for email_id in email_ids:
            # Fetch the email by ID
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                print(f"Failed to fetch email ID {email_id.decode()}")
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Parse the email content
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    from_ = msg.get("From")

                    # Extract email date
                    date = msg.get("Date")
                    date = datetime.strptime(date[:31], "%a, %d %b %Y %H:%M:%S %z").astimezone().strftime('%Y-%m-%d %H:%M:%S')

                    # Extract email body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    # Format the body to ensure it's stored in a single cell
                    body = " ".join(body.splitlines()).strip()

                    # Append email data to the list
                    emails.append({"date": date, "subject": subject, "from": from_, "body": body})
    except Exception as e:
        print(f"Error fetching incoming emails: {e}")
    return emails

def save_to_csv(emails):
    """Save the email data to a CSV file, sorted latest to oldest."""
    try:
        # Convert emails to a DataFrame
        today = datetime.now().strftime("%Y-%m-%d")  # e.g., "2024-11-17"
        filename = f"emails_{today}.csv" 
        df = pd.DataFrame(emails)

        # If the file already exists, append new emails
        try:
            existing_df = pd.read_csv(filename)
            df = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset=["subject", "from", "date"])

        except FileNotFoundError:
            pass

        # Sort by date (latest to oldest)
        df["date"] = pd.to_datetime(df["date"])
        df.sort_values(by="date", ascending=False, inplace=True)

        # Save to CSV
        df.to_csv(filename, index=False)
        print(f"Emails saved to {filename}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def main():
    """Main function to parse incoming emails periodically."""
    mail = connect_to_email()
    if not mail:
        return

    print("Starting email monitoring...")
    try:
        while True:
            print("Checking for incoming emails...")
            emails = fetch_incoming_emails(mail)
            if emails:
                save_to_csv(emails)
            else:
                print("No new emails.")
            time.sleep(60)  # Check every 60 seconds (adjust as needed)
    except KeyboardInterrupt:
        print("\nStopping email monitoring.")
    finally:
        mail.logout()

if __name__ == "__main__":
    main()
