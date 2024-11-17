import pandas as pd
import google.generativeai as genai
from typing import Dict, List, Tuple
import os
from datetime import datetime
import re
import logging
from dotenv import load_dotenv
load_dotenv()
# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailProcessor:
    def __init__(self, api_key: str):
        # Initialize Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Define request types and categories for validation
        self.request_types = {
            "claims": [
                "New Claim Submission",
                "Claim Status Inquiry",
                "Claim Documentation",
                "Claim Appeal/Dispute"
            ],
            "billing": [
                "Premium Payment",
                "Billing Dispute",
                "Payment Arrangement Request",
                "Refund Request",
                "Premium Calculation Query"
            ],
            "policy": [
                "Policy Update Request",
                "Policy Cancellation",
                "Coverage Modification",
                "Policy Renewal",
                "New Policy Quote"
            ],
            "technical": [
                "Portal Access Problem",
                "Document Upload Issue",
                "Technical Error",
                "Login Assistance"
            ],
            "information": [
                "Policy Information",
                "Premium Information",
                "Coverage Details",
                "General Inquiry"
            ]
        }
        
        # Keywords for category detection
        self.category_keywords = {
            "claim": ["claim", "accident", "damage", "injury", "loss", "medical", "hospital"],
            "billing": ["bill", "payment", "premium", "charge", "refund", "overcharge", "cost"],
            "policy_update": ["update", "change", "modify", "cancel", "cancellation"],
            "premium_inquiry": ["quote", "cost", "price", "rate", "calculation"],
            "technical_support": ["portal", "website", "login", "technical", "error", "access", "online"]
        }

    def clean_text(self, text: str) -> str:
        """Clean and normalize text data"""
        try:
            if not isinstance(text, str):
                return ""
            
            # Convert to string and lower case
            text = str(text).strip()
            
            # Remove special characters except basic punctuation
            text = re.sub(r'[^\w\s@.,-]', ' ', text)
            
            # Remove extra whitespace
            text = ' '.join(text.split())
            
            return text
        except Exception as e:
            logger.error(f"Error in clean_text: {str(e)}")
            return ""

    def determine_request_type(self, subject: str, body: str) -> str:
        """Determine the specific request type based on content"""
        combined_text = f"{subject} {body}".lower()
        
        # Check for claim-related requests
        if any(word in combined_text for word in ["claim", "accident", "damage", "injury"]):
            if "status" in combined_text:
                return "Claim Status Inquiry"
            return "New Claim Submission"
            
        # Check for billing-related requests
        if any(word in combined_text for word in ["bill", "payment", "charge"]):
            if "dispute" in combined_text or "overcharge" in combined_text:
                return "Billing Dispute"
            return "Premium Payment Request"
            
        # Check for policy-related requests
        if any(word in combined_text for word in ["policy", "coverage"]):
            if "cancel" in combined_text:
                return "Policy Cancellation Request"
            if "update" in combined_text or "change" in combined_text:
                return "Policy Update Request"
            return "Policy Information Request"
            
        # Check for technical issues
        if any(word in combined_text for word in ["portal", "login", "technical", "website"]):
            return "Technical Support Request"
            
        return "General Inquiry"

    def get_default_actions(self, request_type: str) -> List[str]:
        """Get default actions based on request type"""
        default_actions = {
            "New Claim Submission": [
                "Review claim documentation and validate all required information",
                "Create new claim record in the system and assign claim number",
                "Assign appropriate claims handler based on claim type",
                "Send acknowledgment email with claim number and next steps"
            ],
            "Claim Status Inquiry": [
                "Locate claim in system using customer information",
                "Review current claim status and recent updates",
                "Prepare detailed status update for customer",
                "Send status update with estimated timeline for next steps"
            ],
            "Billing Dispute": [
                "Review billing history and identify disputed charges",
                "Investigate validity of dispute and calculate any adjustments",
                "Process necessary corrections or adjustments",
                "Send detailed explanation of resolution to customer"
            ],
            "Policy Cancellation Request": [
                "Verify policyholder identity and policy details",
                "Calculate any refunds or outstanding payments",
                "Process cancellation in system with effective date",
                "Send confirmation of cancellation with final documentation"
            ],
            "Technical Support Request": [
                "Diagnose specific technical issue from user description",
                "Attempt basic troubleshooting steps",
                "Escalate to IT support if necessary",
                "Follow up with user to confirm resolution"
            ]
        }
        
        return default_actions.get(request_type, [
            "Review customer request details",
            "Determine appropriate department for handling",
            "Process request according to standard procedures",
            "Send confirmation and next steps to customer"
        ])

    def analyze_email(self, subject: str, body: str) -> Dict:
        """Analyze email content using Gemini API"""
        try:
            # Clean the inputs
            clean_subject = self.clean_text(subject)
            clean_body = self.clean_text(body or '')
            
            # Determine request type
            initial_request_type = self.determine_request_type(clean_subject, clean_body)
            
            prompt = f"""
            Analyze this insurance-related email and provide a detailed response:

            EMAIL CONTENT:
            Subject: {clean_subject}
            Body: {clean_body}

            TASK: As an insurance service representative, analyze this email and provide specific classification.

            1. REQUEST TYPE CLASSIFICATION
            Identify the SPECIFIC type of request from these categories:

            CLAIMS:
            - New Claim Submission (accident/injury reports, new claims)
            - Claim Status Inquiry (following up on existing claims)
            - Claim Documentation (sending or requesting documents)
            - Claim Appeal/Dispute (disagreeing with claim decision)

            BILLING:
            - Premium Payment Issue (payment problems/questions)
            - Billing Dispute (disagreeing with charges)
            - Payment Arrangement Request (payment plans)
            - Refund Request (requesting money back)

            POLICY:
            - Policy Modification (changes to existing policy)
            - Policy Cancellation (ending policy)
            - Coverage Question (questions about what's covered)
            - New Policy Interest (wanting new policy)

            TECHNICAL:
            - Portal Access Problem (can't access account)
            - Login Issues (password/username problems)
            - Website Technical Error (site not working)
            - Document Upload Problem (can't upload files)

            2. CATEGORY: Pick the main category that best fits:
            - Claim
            - Billing
            - Policy Update
            - Technical Support
            - Other (specify)

            3. RECOMMENDED ACTIONS
            List 4 specific steps starting with action verbs (e.g., Review, Process, Contact, Verify)
            Make each step specific to this exact request.

            4. PRIORITY LEVEL
            High: Accidents, injuries, system-wide technical issues
            Medium: Billing disputes, regular policy updates
            Low: Information requests, general questions

            Format the response EXACTLY as follows:
            Request Type: [Specific type from above categories] - [Brief description]
            Category: [Main category]
            Actions:
            1. [Action verb] [Specific step]
            2. [Action verb] [Specific step]
            3. [Action verb] [Specific step]
            4. [Action verb] [Specific step]
            Priority: [High/Medium/Low]
            """
            
            response = self.model.generate_content(prompt)
            parsed_response = self._parse_gemini_response(response.text)
            
            # If no request type was determined, use the initial determination
            if parsed_response["request_type"] == "Unknown":
                parsed_response["request_type"] = initial_request_type
            
            # Get default actions if none were parsed
            if not parsed_response["actions"]:
                parsed_response["actions"] = self.get_default_actions(parsed_response["request_type"])
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error in analyze_email: {str(e)}")
            return {
                "request_type": initial_request_type,
                "category": self.determine_category(clean_subject, clean_body),
                "actions": self.get_default_actions(initial_request_type),
                "priority": "Medium"
            }

    def determine_category(self, subject: str, body: str) -> str:
        """Determine the main category based on content"""
        combined_text = f"{subject} {body}".lower()
        
        for category, keywords in self.category_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                return category.replace('_', ' ').title()
        
        return "Other"

    def _parse_gemini_response(self, response: str) -> Dict:
        """Parse the Gemini API response with enhanced extraction"""
        parsed_data = {
            "request_type": "Unknown",
            "category": "Unknown",
            "actions": [],
            "priority": "Medium"
        }
        
        try:
            lines = response.split('\n')
            action_verbs = ["review", "process", "send", "contact", "verify", "check", 
                          "update", "analyze", "schedule", "create", "assign", "escalate"]
            
            for line in lines:
                line = line.strip()
                
                if line.lower().startswith("request type:"):
                    request_type = line.split(":", 1)[1].strip()
                    # Ensure we have both type and description
                    if ' - ' in request_type:
                        parsed_data["request_type"] = request_type
                    else:
                        parsed_data["request_type"] = f"{request_type} - General Request"
                
                elif line.lower().startswith("category:"):
                    category = line.split(":", 1)[1].strip()
                    parsed_data["category"] = category.title()
                
                elif line.lower().startswith("priority:"):
                    priority = line.split(":", 1)[1].strip().lower()
                    if priority in ["high", "medium", "low"]:
                        parsed_data["priority"] = priority.capitalize()
                
                elif line[0].isdigit() and "." in line:
                    action = line.split(".", 1)[1].strip()
                    if any(action.lower().startswith(verb) for verb in action_verbs):
                        parsed_data["actions"].append(action)
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error in _parse_gemini_response: {str(e)}")
            return parsed_data

    def process_emails(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process all emails in the DataFrame"""
        results = []
        
        try:
            total_emails = len(df)
            for index, row in df.iterrows():
                logger.info(f"Processing email {index + 1} of {total_emails}")
                
                analysis = self.analyze_email(row['subject'], row.get('body', ''))
                
                result = {
                    'date': row['date'],
                    'from': row['from'],
                    'subject': row['subject'],
                    'body': row.get('body', 'No body content'),
                    'request_type': analysis.get('request_type'),
                    'category': analysis.get('category'),
                    'actions': '\n'.join(analysis.get('actions', [])),
                    'priority': analysis.get('priority'),
                    'processed_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                results.append(result)
                
            return pd.DataFrame(results)
        
        except Exception as e:
            logger.error(f"Error in process_emails: {str(e)}")
            return pd.DataFrame()

def main():
    try:
        # Load your email data
        df = pd.read_excel("sample data.xlsx")
        
        # Initialize processor with your API key
        api_key = os.getenv("gemini_api") # Replace with actual API key
        processor = EmailProcessor(api_key)
        
        # Process emails
        results_df = processor.process_emails(df)
        
        # Save results
        output_file = 'processed_emails.csv'
        results_df.to_csv(output_file, index=False)
        logger.info(f"Results saved to {output_file}")
        print("\nProcessed Results:")
        print(results_df)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()