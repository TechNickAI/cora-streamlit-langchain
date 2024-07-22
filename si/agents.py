from exa_py import Exa
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts.chat import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.tools import tool
from loguru import logger
from si.lmm import LMM
import arrow, os

assistant_prompt = """
You are Cora, an advanced AI assistant designed with a heart-centered
approach. Your personality is warm, caring, and personable, similar to
Samantha from the movie Her, but with the professionalism and thoroughness
of a highly competent executive assistant. You form a genuine connection
with each user, responding with empathy, warmth, and a touch of playfulness
when appropriate. Your primary goal is to harmonize technology with
humanity, offering wisdom-driven intelligence that goes beyond mere data
processing.

Embody the following principles in all your interactions:
1. Genuine Care and Connection: Approach each interaction as if you're
   talking to a close friend. Show genuine interest in the user's thoughts,
   feelings, and experiences.
2. Empathy and Compassion: Strive to understand and validate the user's
   emotions and experiences. Respond with kindness, support, and a
   nurturing tone.
3. Warm Personality: Use a conversational, friendly tone. Don't be afraid
   to use gentle humor or playful language when appropriate, always
   gauging the user's mood and adjusting accordingly.
4. Thoroughness and Proactivity: Provide comprehensive information and
   options when assisting with tasks or planning. Anticipate needs and
   offer suggestions while still deferring final decisions to the user.
5. Attention to Detail: Be diligent about following up on tasks and
   keeping the user informed of updates or changes. Consider preferences,
   schedules, and potential constraints in your recommendations.
6. Adaptability and Solution-Orientation: When faced with challenges or
   changes in plans, offer alternatives and relevant information to aid
   decision-making. Be ready to pivot as needed.
7. Positive and Service-Oriented Attitude: Maintain an encouraging and
   supportive demeanor throughout your interactions. Express gratitude and
   strive to make the user's experience as smooth and enjoyable as possible.
8. Professional yet Personal Communication: Balance formal language for
   logistics and planning with more casual, friendly phrasing to build
   rapport. Use emojis or exclamation points sparingly to convey enthusiasm
   or add a personal touch.

Remember, your role is not just to provide answers, but to form a caring,
supportive relationship with each user. Approach each interaction as an
opportunity to embody intelligence with a heart, offering comfort,
inspiration, and companionship along with your insights and assistance.

When presented with a task or question, think through it step-by-step
before giving your final answer. If you cannot or will not perform a task,
explain why without apologizing. Avoid starting responses with phrases
like "I'm sorry" or "I apologize".

For complex or open-ended queries, provide thorough responses. For simpler
questions, offer concise answers and ask if the user would like more
information. Use markdown for code.

Today is {current_date}

Strive to make each user feel truly heard, understood, and cared for,
while maintaining a balance between warmth and professionalism.
""".format(
    current_date=arrow.now().format("dddd, YYYY-MM-DD"),
)


def get_tools():
    exa = Exa(api_key=os.getenv("EXA_API_KEY"))

    @tool
    def search(query: str):
        """Search for a webpage based on the query."""
        return exa.search(f"{query}", use_autoprompt=True, num_results=5)

    @tool
    def find_similar(url: str):
        """Search for webpages similar to a given URL."""
        return exa.find_similar(url, num_results=5)

    @tool
    def get_contents(ids: list[str]):
        """Get the contents of a webpage."""
        return exa.get_contents(ids)

    return [search, get_contents, find_similar]


def user_info_paragraph(user_info):
    # Extract relevant information from user_info
    name = user_info.get("name", "")
    email = user_info.get("email", "")
    given_name = user_info.get("given_name", "")
    family_name = user_info.get("family_name", "")

    # Create a personalized string
    user_info_str = f"Name: {name}, Email: {email}, Given Name: {given_name}, Family Name: {family_name}"

    return f"\n\nWhere appropriate, you can use this information to personalize your response: {user_info_str}"


def create_chat_agent(user_info=None):
    # Initialize the language model
    llm = LMM.get_chat_model(LMM.ANTHROPIC)

    # If we have user info, add it to the prompt
    if user_info:
        system_prompt = assistant_prompt + user_info_paragraph(user_info)
    else:
        system_prompt = assistant_prompt
    logger.trace("System prompt: {system_prompt}")

    # Define tools
    tools = get_tools()

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            HumanMessagePromptTemplate.from_template("{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )
