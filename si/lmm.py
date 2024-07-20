from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
import os


# Language Model Manager
class LMM:
    # LLM providers
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"

    # LLM provider configuration
    LLM_CONFIG = {
        OPENAI: {
            "model": "gpt-4",
            "api_key_env": "OPENAI_API_KEY",
            "default_temperature": 0.7,
        },
        ANTHROPIC: {
            "model": "claude-3-sonnet-20240229",
            "api_key_env": "ANTHROPIC_API_KEY",
            "default_temperature": 0.7,
        },
        GROQ: {
            "model": "llama3-70b-8192",
            "api_key_env": "GROQ_API_KEY",
            "default_temperature": 0.7,
        },
    }
    # Groq isn't fully supported yet because it handles streaming differently
    LLM_PROVIDERS = [OPENAI, ANTHROPIC]

    @staticmethod
    def check_api_key(llm_provider):
        llm_provider = llm_provider.lower()
        if llm_provider not in LMM.LLM_CONFIG:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

        api_key_env = LMM.LLM_CONFIG[llm_provider]["api_key_env"]
        if os.getenv(api_key_env) is None:
            raise ValueError(
                f"API key for {llm_provider} is not set. Please set the {api_key_env} environment variable."
            )
        return True

    @staticmethod
    def get_chat_model(llm_provider, model_name=None, temperature=None, streaming=True):
        llm_provider = llm_provider.lower()
        LMM.check_api_key(llm_provider)

        config = LMM.LLM_CONFIG[llm_provider]
        temp = temperature if temperature is not None else config["default_temperature"]
        model_name = model_name if model_name is not None else config["model"]

        if llm_provider == LMM.OPENAI:
            return ChatOpenAI(model=model_name, temperature=temp, streaming=streaming)
        elif llm_provider == LMM.ANTHROPIC:
            return ChatAnthropic(model=model_name, temperature=temp, streaming=streaming)
        elif llm_provider == LMM.GROQ:
            # Streaming fails with astream_events with langchain_groq, so set it to False. It's fast enough.
            return ChatGroq(model=model_name, temperature=temp, streaming=False)
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")
