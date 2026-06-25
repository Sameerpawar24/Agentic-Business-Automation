import sys
import os

# Add the project directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.core.zai_chat import get_fallback_llm
from langchain_core.messages import HumanMessage
from src.core.config import settings


def test_fallback_success():
    print("==================================================")
    print("        TESTING MODEL FALLBACK MECHANISM")
    print("==================================================")
    print(f"Groq API Key: {settings.GROQ_API_KEY[:10]}... (status: {'Configured' if settings.GROQ_API_KEY else 'Empty'})")
    print(f"Z.ai API Key: {settings.ZAI_API_KEY} (status: {'Configured' if settings.ZAI_API_KEY != 'your-zai-token' else 'Using Placeholder'})")
    print(f"Z.ai Base URL: {settings.ZAI_BASE_URL}")
    print(f"Z.ai Model: {settings.ZAI_MODEL}")
    print("--------------------------------------------------")

    # 1. Get default fallback model
    model = get_fallback_llm()

    # 2. Prepare test messages
    messages = [HumanMessage(content="Say the word 'success' only.")]

    print("Sending request (Primary model Z.ai should fail, triggering fallback to Groq)...")
    try:
        response = model.invoke(messages)
        print("\n---> INVOCATION RESULT SUCCESS!")
        print(f"---> Model Response Content: '{response.content.strip()}'")
        print("==================================================")
    except Exception as e:
        print(f"\n---> INVOCATION RESULT FAILED!")
        print(f"---> Error detail: {e}")
        print("==================================================")
        sys.exit(1)


if __name__ == "__main__":
    test_fallback_success()
