import streamlit as st
import requests
import json


insurer_id = st.query_params.get('insurerId', '11')
print(insurer_id)
# Response template for the LLM
RESPONSE_TEMPLATE = """
*Note: The following guidelines must be strictly followed when generating a response:*  

1. **Prohibited Words and Elements**:  
   - Specific words: "Insurer," "User," "llama3.2:latest"  
   - Company-specific names or details unless explicitly provided by the user.  

2. **Avoid Excessive Formatting and Unnecessary Details**:  
   - Do not include extra formatting (e.g., broken down ALE values, repeated sections).  
   - Focus on providing a high-level summary without excessive breakdowns unless specifically requested.  

3. **No Repetitions or Redundant Information**:  
   - Avoid repeating the same data multiple times or formatting values excessively (e.g., breaking ALE into individual characters or formatting them incorrectly).  

4. **Focus on Concise Results**:  
   - The response should give a concise summary or final result, directly answering the user’s query.  

5. **Plain Language and Clarity**:  
   - Use clear, concise language without unnecessary technical jargon or complex explanations unless explicitly requested.  

6. **Implementation Rules**:  
   - Always validate output against these rules before responding.  
   - Use only one format for each value
   - Never mix formatting styles
   - Keep responses concise and direct
   - Remove any redundant information before responding


**Example Expected Response:**  
*"The total ALE for Phishing Attacks in 2023 was $14,270,566.59, and for 2024 it is projected to be $5,101,219.07."*
"""



#MODELS = ["llama3.2:latest", "mistral", "codellama", "neural-chat"]
OLLAMA_API_URL = "http://localhost:11434/api/generate"
INSURER_API_URL = "https://localhost:44346/api/GetInsurerFAIRDetails/"


# Valid parameters
VALID_ATTACK_TYPES = {"phishing", "malware", "ransomware", "ddos"}
VALID_YEARS = set(str(year) for year in range(2020, 2025))

def extract_query_params(query_text):
    """Extract attack type and year from user query with better validation"""
    # Default values
    attack_type = None
    year = None
    
    # Convert query to lowercase for matching
    query_lower = query_text.lower()
    
    # Match attack types
    for attack in VALID_ATTACK_TYPES:
        if attack in query_lower:
            attack_type = attack.capitalize()
            if attack == "ddos":
                attack_type = "DDoS"
            break
    
    # Match years
    for valid_year in VALID_YEARS:
        if valid_year in query_text:
            year = valid_year
            break
    
    return attack_type, year




def get_insurer_data(insurer_id="11", attack_type="", year="", user_id=""):
    try:
        payload = {
            "insurerId": insurer_id,
            "AttackType": attack_type,
            "Year": year,
            "userId": user_id
        }
        
        # Disable SSL verification for local development
        response = requests.post(INSURER_API_URL, json=payload, verify=False)
        response.raise_for_status()  # Raise exception for bad status codes
        return response.json()
    except Exception as e:
        return f"Error fetching insurer data: {str(e)}"


def get_formatted_prompt(user_query, context_data, attack_type, year):
    """Create a formatted prompt using the template"""
    attack_type_text = "Focusing on all attack types" if attack_type is None else f"Specifically analyzing {attack_type} attacks"
    
    template = RESPONSE_TEMPLATE.format(
        year=year,
        attack_type_text=attack_type_text
    )
    
    full_prompt = (
        f"Context: {json.dumps(context_data)}\n\n"
        f"User Question: {user_query}\n\n"
        f"Instructions for response:\n{template}"
    )
    
    return full_prompt


def get_ollama_response(prompt, context_data=None, attack_type=None, year=None, model="llama3.2:latest"):
    try:
        if context_data:
            full_prompt = get_formatted_prompt(prompt, context_data, attack_type, year)
        else:
            full_prompt = prompt
        
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": True
            },
            stream=True
        )
        return response
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}"

def process_stream(response):
    accumulated_message = ""
    for line in response.iter_lines():
        if line:
            json_response = json.loads(line)
            text_chunk = json_response.get('response', '')
            accumulated_message += text_chunk
            yield text_chunk, accumulated_message

def display_messages():
    for msg in st.session_state.messages:
        if msg["role"] == "bot":
            st.markdown(f"**🤖 Bot:** {msg['text']}")
        else:
            st.markdown(f"**💬 You:** {msg['text']}")

# Streamlit app layout
st.title("Secumetrix-Powered Chatbot")


# Initialize session states
if "messages" not in st.session_state:
    welcome_message = (
        "Hello! I can help you analyze FAIR details : "
        
    ).format(insurer_id)
    st.session_state.messages = [{"role": "bot", "text": welcome_message}]
if "input" not in st.session_state:
    st.session_state.input = ""




#st.write("Start chatting with the bot below:")

# Sidebar
selected_model = "llama3.2:latest" 

# Display chat messages
display_messages()

# Add some space between messages and input
st.markdown("---")

# Create a form for user input
with st.form(key="chat_form", clear_on_submit=True):  # Add clear_on_submit
    user_input = st.text_input("You:", key="user_input")
    cols = st.columns([4, 1])
    with cols[0]:
        submit_button = st.form_submit_button("Send")
    with cols[1]:
        clear_button = st.form_submit_button("Clear History")

    

# Handle clear button click
if clear_button:
    st.session_state.messages = [{"role": "bot", "text": "Hello! How can I help you today?"}]
    st.session_state.input = ""
    st.rerun()   

# When form is submitted
if submit_button and user_input:
    current_input = user_input
    
    # Add user message to the chat
    st.session_state.messages.append({"role": "user", "text": current_input})
    
    # Extract attack type and year from user query
    attack_type, year = extract_query_params(current_input)
    # Get the insurer data
    insurer_data = get_insurer_data(insurer_id, attack_type, year)


    # Handle missing parameters
    # if not attack_type or not year:
    #     missing_params = []
    #     if not attack_type:
    #         missing_params.append("attack type (Phishing, Malware, Ransomware, or DDoS)")
    #     if not year:
    #         missing_params.append("year (between 2020-2024)")
        
    #     error_msg = (
    #         "I couldn't find the " + " and ".join(missing_params) + " in your question. "
    #         "Please specify both in your query."
    #     )
    #     st.session_state.messages.append({"role": "bot", "text": error_msg})
    #     st.rerun()
    
    # Create a placeholder for streaming response
    response_placeholder = st.empty()

     # Show loading message while fetching data
    response_placeholder.markdown("**🤖 Bot:** Getting Insurer FAIR analysis information...")
    
    
    
    # Get streaming response from LLM with context
    response = get_ollama_response(current_input, insurer_data, selected_model)
    
    # Process and display streaming response
    full_response = ""
    for chunk, accumulated in process_stream(response):
        response_placeholder.markdown(f"**🤖 Bot:** {accumulated}")
        full_response = accumulated
    
    # Add final response to chat history
    st.session_state.messages.append({"role": "bot", "text": full_response})
    
    # Rerun at the end
    st.rerun()

# System info
#st.sidebar.markdown("---")
#st.sidebar.markdown("### System Info")
#st.sidebar.markdown(f"Current Model: **{selected_model}**")