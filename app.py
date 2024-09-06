from flask import Flask, request, jsonify
import os
import openai
from openai import AsyncOpenAI

app = Flask(__name__)

# Load the model and tokenizer globally to avoid reloading on every request
# Load the pre-trained model and tokenizer

openai.api_key = 'your api key'



@app.route('/webhook', methods=['POST'])
def webhook():
    # Get the request from Dialogflow
    req = request.get_json(silent=True, force=True)
    print(req)

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
                    {"role": "system", "content": "You are a helpful assistant. your response should be within 70 tokens"},
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

    # Send the response back to Dialogflow
    fulfillment_response = {
        "fulfillmentText": response_text,
        "outputContexts": output_contexts
    }

    return jsonify(fulfillment_response)

if __name__ == '__main__':
    # Run the app on the default Flask port 5000
    app.run(port=5000, debug=True)
