from flask import Flask, request, jsonify
import openai
import json

app = Flask(__name__)

# Load the model and tokenizer globally to avoid reloading on every request
# Load the pre-trained model and tokenizer

openai.api_key = ''


def load_data():
    # Load JSON data
    with open('data.json') as f:
        data = json.load(f)
    
    # Alternatively, load Excel data
    # data = pd.read_excel('data.xlsx').to_dict(orient='records')

    return data

# Function to find user details by phone number
def find_user_by_phone(phone_number, data):
    for entry in data:
        if entry['phone'] == phone_number:
            return entry
    return None



@app.route('/webhook', methods=['POST'])
def webhook():
    # Get the request from Dialogflow
    req = request.get_json(silent=True, force=True)
    print(req)

    intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName', '')

    if intent_name == "Ask For Phone Number":

         # Extract the phone number from the request
        phone_number = req.get('queryResult', {}).get('parameters', {}).get('phone-number', '')

         # Check if phone_numbers is a list and extract the first phone number if available
        if phone_number and isinstance(phone_number, list):
            phone_number = phone_number[0]  # Get the first number from the list
        else:
            phone_number = ''  # Default if no phone number is found

        # Load the data
        data = load_data()
        print(data)

        # Find the user by phone number
        user_details = find_user_by_phone(phone_number, data)
        print(user_details)

        if user_details:
            # Format the response text
            response_text = ""
            # Add data to output contexts for further use in Dialogflow
            output_contexts = [{
                "name": f"{req['session']}/contexts/user_details",
                "lifespanCount": 5,
                "parameters": {
                    "name": user_details['name'],
                    "address": user_details['address'],
                    "email": user_details['email'],
                    "phone": user_details['phone']
                }
            }]
        else:
            response_text = "No details found for the given phone number."
            output_contexts = []


    elif intent_name == "Default Fallback Intent":
        # Extract the question or user query from Dialogflow
        query_text = req.get('queryResult', {}).get('queryText', '')
        contexts = req.get('queryResult', {}).get('outputContexts', [])

        # Check if the conversation is active with ChatGPT
        chatgpt_active = any(ctx.get('name').endswith('chatgpt_active') for ctx in contexts)

        try:
            if "bye" in query_text.lower():
                # Terminate the ChatGPT session
                response_text = "Goodbye! If you need more assistance, feel free to ask."
                output_contexts = []  # Clear contexts to end the session
            else:
                # Continue the conversation with ChatGPT if chatgpt_active is set
                if chatgpt_active or not contexts:  # No specific context means new chat session
                    response = openai.chat.completions.create(
                    model="gpt-4",  # Specify the model (e.g., "gpt-3.5-turbo" or "gpt-4")
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. your response should be within 40 tokens"},
                        {"role": "user", "content": query_text}
                    ],
                    max_tokens = 100
                )
                    response_text = response.choices[0].message.content
                    print(response_text)
                    # Set context to continue with ChatGPT
                    output_contexts = [{"name": f"{req['session']}/contexts/chatgpt_active", "lifespanCount": 5}]
                else:
                    response_text = "I'm sorry, I didn't understand that. Can you please rephrase?"
                    output_contexts = [{"name": f"{req['session']}/contexts/chatgpt_active", "lifespanCount": 5}]

        except Exception as e:
            # Handle any exceptions that occur during the response generation
            response_text = f"An error occurred: {str(e)}"
            print(response_text)
            output_contexts = [{"name": f"{req['session']}/contexts/chatgpt_active", "lifespanCount": 5}]
    else:
        # Default response if no specific intent is matched
        response_text = "I'm sorry, I didn't understand that. Could you please rephrase?"
        output_contexts = []
    
    # Send the response back to Dialogflow
    fulfillment_response = {
        "fulfillmentText": response_text,
        "outputContexts": output_contexts
    }

    return jsonify(fulfillment_response)

if __name__ == '__main__':
    # Run the app on the default Flask port 5000
    app.run(port=5000, debug=True)
