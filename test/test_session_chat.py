import sys
import os

# Add the project root directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.services.chat import ChatService


def test_chat_session_memory():
    print("==================================================")
    print("      TESTING CONVERSATIONAL SESSION MEMORY")
    print("==================================================")

    chat_service = ChatService()

    # Turn 1: Tell the chat model a name
    name = "John"
    message_1 = f"My name is {name}. Respond with a greeting."
    print(f"User Message 1: {message_1}")

    # Call run_chat without a session_id to let the system generate one
    result_1 = chat_service.run_chat(message_1)
    session_id = result_1["session_id"]
    response_1 = result_1["response"]

    print(f"Assistant Response 1: '{response_1.strip()}'")
    print(f"Generated Session ID: {session_id}")
    print("--------------------------------------------------")

    # Turn 2: Ask the model what the name was, using the same session_id
    message_2 = "What is my name?"
    print(f"User Message 2: {message_2}")

    result_2 = chat_service.run_chat(message_2, session_id=session_id)
    response_2 = result_2["response"]

    print(f"Assistant Response 2: '{response_2.strip()}'")

    # Verify if name is in the response
    if name.lower() in response_2.lower():
        print("\n---> SUCCESS: The model remembered the user's name across chat turns!")
        print("==================================================")
    else:
        print("\n---> FAILURE: The model forgot the context.")
        print("==================================================")
        sys.exit(1)


if __name__ == "__main__":
    test_chat_session_memory()
