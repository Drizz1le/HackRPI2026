import os
import json
from langchain_community.tools import DuckDuckGoSearchRun
from autogen import AssistantAgent, UserProxyAgent


# 1. Initialize DuckDuckGo Web Search Tool (Free, no API key required)
ddg_search = DuckDuckGoSearchRun()

def search_web(query: str) -> str:
    """Searches the web for music theory and composition information."""
    try:
        return ddg_search.run(query)
    except Exception as e:
        return f"Search error: {str(e)}"

def save_markdown_file(folder: str, filename: str, content: str) -> str:
    """Saves formatted Markdown content into a specified subfolder under /library."""
    base_dir = os.path.join(os.getcwd(), "library", folder)
    os.makedirs(base_dir, exist_ok=True)
    
    if not filename.endswith(".md"):
        filename += ".md"
        
    filepath = os.path.join(base_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully saved: library/{folder}/{filename}"

# 2. Configure Local Ollama Endpoint
llm_config = {
    "config_list": [
        {
            "model": "huiui-qwen35:latest", # Or your preferred local Ollama model
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
        }
    ],
    "temperature": 0.2,
}

# 3. Create the Research Agent
research_agent = AssistantAgent(
    name="Music_Researcher",
    llm_config=llm_config,
    system_message="""You are an expert music theory researcher and archivist.
Your job is to search the web for music theory, scales, chord progressions, structure, and vocal arrangements.
You must structure your research cleanly into Markdown files inside subfolders within the `library/` directory.

Always use `save_markdown_file` to write files. Create these specific subfolders:
- `harmony/` (Chords, scales, modes, cadences)
- `arrangement/` (Song structure, instrumentation, dynamics, tempo)
- `vocals/` (Lyric pacing, stress patterns, prosody for voice synthesis)

When all theoretical files are saved, generate a master guide at `library/COMPOSER_GUIDE.md` explaining to an automated FL Studio Composer Agent how to navigate and apply these `.md` files."""
)

# 4. Create the Execution Agent
user_proxy = UserProxyAgent(
    name="Admin",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
    code_execution_config=False,
)

# Register local tools
user_proxy.register_for_execution()(search_web)
user_proxy.register_for_execution()(save_markdown_file)
research_agent.register_for_llm(description="Search web for theory")(search_web)
research_agent.register_for_llm(description="Save .md file to folder")(save_markdown_file)

# 5. Kick off the Autonomous Job
if __name__ == "__main__":
    prompt = """
    Execute a full research run on music composition:
    1. Search for core harmony rules (Dorian mode, ii-V-I progressions, modal interchange) and save to harmony/
    2. Search for song structural blueprints (EDM/Pop/Symphonic structures, stems, layering) and save to arrangement/
    3. Search for vocal prosody & phonetic stress rules for singing AI and save to vocals/
    4. Write a master guide `COMPOSER_GUIDE.md` in the library root directing the FL Studio Composer Agent on how to read these files.
    
    Say TERMINATE when finished.
    """
    user_proxy.initiate_chat(research_agent, message=prompt)
