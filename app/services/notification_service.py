import requests
from flask import current_app

class NotificationService:
    @staticmethod
    def send_sms_via_africastalking(phone_number, message):
        """
        Sends low-bandwidth localized text message alerts through Africa's Talking API Gateway profiles.
        """
        username = current_app.config['AFRICASTALKING_USERNAME']
        api_key = current_app.config['AFRICASTALKING_API_KEY']
        
        if not api_key or api_key == "":
            print(f"[Simulated SMS Engine to {phone_number}]: {message}")
            return True
            
        url = "https://api.africastalking.com/version1/messaging"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "ApiKey": api_key
        }
        data = {
            "username": username,
            "to": phone_number,
            "message": message
        }
        response = requests.post(url, data=data, headers=headers)
        return response.status_code == 201

    @staticmethod
    def send_whatsapp_alert(phone_number, message):
        """
        Transmits real-time transactional reports directly into Meta Cloud WhatsApp Framework endpoints.
        """
        token = current_app.config.get('WHATSAPP_TOKEN')
        phone_id = current_app.config.get('WHATSAPP_PHONE_NUMBER_ID')
        
        if not token:
            print(f"[Simulated WhatsApp to {phone_number}]: {message}")
            return True

        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200