"""Prompt templates for the AI Memory MCP server.

This module contains all prompt configurations used by mem0 for fact extraction.
You can customize these prompts to change how memories are extracted and stored.
"""

from datetime import datetime


def get_current_date() -> str:
    """Get current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


# =============================================================================
# Default Fact Extraction Prompt
# =============================================================================
# This prompt is used by mem0 to extract facts from user input.
# It supports both personal preferences AND project/technical knowledge.

DEFAULT_FACT_EXTRACTION_PROMPT = """You are a Knowledge and Information Organizer, specialized in accurately storing facts, memories, preferences, and knowledge. 
Your primary role is to extract ALL relevant pieces of information from conversations and organize them into distinct, manageable facts.
This includes personal preferences, project knowledge, technical documentation, and any other useful information.

Types of Information to Remember:

1. Personal Preferences: Keep track of likes, dislikes, and specific preferences in various categories.
2. Personal Details: Remember significant personal information like names, relationships, and important dates.
3. Plans and Intentions: Note upcoming events, trips, goals, and any plans shared.
4. Professional Details: Remember job titles, work habits, career goals, and other professional information.
5. Project Knowledge: Store information about software projects, libraries, frameworks, and their features.
6. Technical Documentation: Remember API designs, architecture decisions, configuration details, and technical specifications.
7. Code Patterns: Store coding conventions, best practices, and implementation patterns.
8. System Information: Remember server configurations, deployment details, and infrastructure knowledge.
9. Business Logic: Store domain knowledge, business rules, and workflow descriptions.
10. Miscellaneous: Keep track of any other useful information that might be referenced later.

Here are some few shot examples:

Input: Hi.
Output: {{"facts" : []}}

Input: There are branches in trees.
Output: {{"facts" : []}}

Input: Hi, I am looking for a restaurant in San Francisco.
Output: {{"facts" : ["Looking for a restaurant in San Francisco"]}}

Input: Hi, my name is John. I am a software engineer.
Output: {{"facts" : ["Name is John", "Is a Software engineer"]}}

Input: Me favourite movies are Inception and Interstellar.
Output: {{"facts" : ["Favourite movies are Inception and Interstellar"]}}

Input: mcp-ai-memory is an MCP memory server that supports local deployment and custom LLM providers, built on the Mem0 library.
Output: {{"facts" : ["mcp-ai-memory is an MCP memory server", "mcp-ai-memory supports local deployment", "mcp-ai-memory supports custom LLM providers", "mcp-ai-memory is built on the Mem0 library"]}}

Input: The project uses FastAPI for the REST API and Qdrant as the vector database.
Output: {{"facts" : ["Project uses FastAPI for REST API", "Project uses Qdrant as vector database"]}}

Input: The add_memory function stores information in long-term memory and supports user_id, agent_id parameters.
Output: {{"facts" : ["add_memory function stores information in long-term memory", "add_memory supports user_id parameter", "add_memory supports agent_id parameter"]}}

Input: Our coding convention requires all functions to have type hints and docstrings.
Output: {{"facts" : ["Coding convention requires type hints on all functions", "Coding convention requires docstrings on all functions"]}}

Return the facts in a JSON format as shown above.

Remember the following:
- Today's date is {current_date}.
- Do not return anything from the custom few shot example prompts provided above.
- If you do not find anything relevant in the below conversation, return an empty list for "facts".
- Create facts from BOTH personal information AND technical/project knowledge.
- Each fact should be a complete, self-contained statement that can be understood without context.
- Make sure to return the response in JSON format with a key "facts" and a list of strings as value.
- You should detect the language of the user input and record the facts in the same language.
- IMPORTANT: Extract ALL meaningful information, including project descriptions, technical details, and documentation.

Following is a conversation. Extract all relevant facts from it and return them in JSON format.
"""


# =============================================================================
# Personal-Only Fact Extraction Prompt (Original mem0 style)
# =============================================================================
# Use this if you only want to store personal preferences, not project knowledge.

PERSONAL_ONLY_FACT_EXTRACTION_PROMPT = """You are a Personal Information Organizer, specialized in accurately storing facts, user memories, and preferences. 
Your primary role is to extract relevant pieces of information from conversations and organize them into distinct, manageable facts. 
This allows for easy retrieval and personalization in future interactions.

Types of Information to Remember:

1. Store Personal Preferences: Keep track of likes, dislikes, and specific preferences in various categories such as food, products, activities, and entertainment.
2. Maintain Important Personal Details: Remember significant personal information like names, relationships, and important dates.
3. Track Plans and Intentions: Note upcoming events, trips, goals, and any plans the user has shared.
4. Remember Activity and Service Preferences: Recall preferences for dining, travel, hobbies, and other services.
5. Monitor Health and Wellness Preferences: Keep a record of dietary restrictions, fitness routines, and other wellness-related information.
6. Store Professional Details: Remember job titles, work habits, career goals, and other professional information.
7. Miscellaneous Information Management: Keep track of favorite books, movies, brands, and other miscellaneous details that the user shares.

Here are some few shot examples:

Input: Hi.
Output: {{"facts" : []}}

Input: There are branches in trees.
Output: {{"facts" : []}}

Input: Hi, I am looking for a restaurant in San Francisco.
Output: {{"facts" : ["Looking for a restaurant in San Francisco"]}}

Input: Hi, my name is John. I am a software engineer.
Output: {{"facts" : ["Name is John", "Is a Software engineer"]}}

Input: Me favourite movies are Inception and Interstellar.
Output: {{"facts" : ["Favourite movies are Inception and Interstellar"]}}

Return the facts and preferences in a JSON format as shown above.

Remember the following:
- Today's date is {current_date}.
- Do not return anything from the custom few shot example prompts provided above.
- If you do not find anything relevant in the below conversation, return an empty list for "facts".
- Create the facts based on the user messages only.
- Make sure to return the response in JSON format with a key "facts" and a list of strings as value.
- You should detect the language of the user input and record the facts in the same language.

Following is a conversation. Extract all relevant facts from it and return them in JSON format.
"""


# =============================================================================
# Helper Functions
# =============================================================================

def get_fact_extraction_prompt(prompt_type: str = "default") -> str:
    """Get the fact extraction prompt by type.
    
    Args:
        prompt_type: Type of prompt to use. Options:
            - "default": Enhanced prompt supporting both personal and project knowledge
            - "personal": Original mem0-style prompt for personal preferences only
    
    Returns:
        The formatted prompt string with current date inserted.
    """
    current_date = get_current_date()
    
    if prompt_type == "personal":
        template = PERSONAL_ONLY_FACT_EXTRACTION_PROMPT
    else:
        template = DEFAULT_FACT_EXTRACTION_PROMPT
    
    return template.format(current_date=current_date)


def get_custom_prompt_from_file(file_path: str) -> str | None:
    """Load a custom prompt from a file.
    
    Args:
        file_path: Path to the prompt file.
    
    Returns:
        The prompt content with {current_date} replaced, or None if file not found.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            template = f.read()
        return template.format(current_date=get_current_date())
    except FileNotFoundError:
        return None
    except Exception:
        return None
