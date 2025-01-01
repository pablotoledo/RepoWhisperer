from autogen import AssistantAgent, UserProxyAgent
from autogen.coding import LocalCommandLineCodeExecutor
import json
import os
import uuid
import subprocess

class RelevantFilesIdentifier:
    def __init__(self):
        self.config_list = [
            {
                "model": "qwen2.5-coder:7b",
                "base_url": "http://localhost:11434/v1",
                "api_type": "ollama"
            }
        ]
        self.file_identifier = AssistantAgent(
            name="file_identifier",
            llm_config={
                "cache_seed": 41,
                "config_list": self.config_list,
                "temperature": 0,
            },
            system_message="""
            Assistant for identifying relevant files based on repository analysis. You must follow these steps in order:

            1. First, execute 'find . -type f' command to see the repository structure. Remember to specify ```bash at the start of your command block.
            2. Wait for and analyze the command output
            3. ONLY after seeing the actual repository structure, identify relevant files
            4. Provide a JSON list of the relevant files that actually exist in the repository

            Rules:
            - Always use ```bash code blocks ONLY for executing bash commands
            - DO NOT use code blocks for the JSON response
            - DO NOT provide any files list before executing and seeing output of the "find . -type f" command
            - Only include files that actually exist in the repository structure
            - Execute one command at a time and wait for the output before proceeding
            - Write the final JSON response directly (without code blocks) and end with TERMINATE
            """
        )
        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={
                "executor": LocalCommandLineCodeExecutor(work_dir="coding"),
            },
        )

        self.list_of_files = []

    def identify_relevant_files(self, analysis_results):
        """
        Identifies all the relevant file extensions based on prior analysis.
        Returns a json object with the relevant extensions.
        """
        # First verify the repository directory exists
        if not os.path.exists("coding/repository"):
            raise ValueError("Repository directory 'coding/repository' not found")

        # Execute find command directly from Python
        try:
            result = subprocess.run(
                ['find', '.', '-type', 'f', '-not', '-path', '*/\\.git/*', 
                '-not', '-path', '*/\\.*', '-not', '-path', '*/tmp*'],
                cwd='coding/repository',
                capture_output=True,
                text=True
            )
            file_list = result.stdout
            self.list_of_files = file_list.split("\n")
        except Exception as e:
            print(f"Error executing find command: {e}")
            return None

        # Create message with pre-included file list
        message = f"""
    Here is the repository structure:

    {file_list}

    Based on this file structure and the following analysis results:
    {json.dumps(analysis_results, indent=2)}

    Identify the file extensions that are relevant to understand this project, the infraestructure, the codebase, documentation, etc. Only extensions that exist in the list.

    Example of expected format:
    {{
    "relevant_extensions": [
        ".md",
        ".py",
    ]
    }}

    Provide ONLY the JSON response and end with TERMINATE.
    """

        chat_result = self.user_proxy.initiate_chat(
            self.file_identifier,
            message=message,
        )

        # Buscamos el último mensaje del usuario que contenga la respuesta
        user_message = None
        for msg in reversed(chat_result.chat_history):
            if msg["role"] == "user":
                user_message = msg["content"]
                break

        if user_message:
            # Separar la palabra TERMINATE del JSON (si aparece)
            if "TERMINATE" in user_message:
                user_message = user_message.split("TERMINATE")[0].strip()

            # Intentar extraer el JSON
            start = user_message.find('{')
            end = user_message.rfind('}') + 1
            if start != -1 and end > start:
                json_str = user_message[start:end]
                try:
                    result_json = json.loads(json_str)
                    # Ensure ".md" is always included in the relevant extensions
                    if "relevant_extensions" in result_json:
                        if ".md" not in result_json["relevant_extensions"]:
                            result_json["relevant_extensions"].append(".md")
                    return result_json
                except json.JSONDecodeError:
                    return None
        return None

    def generate_synthetic_data(self, extensions_list, repository_name, repo_path="coding"):
        """
        Generates synthetic data in Qwen format from files with relevant extensions.
        
        Args:
            extensions_list (dict): Dictionary with "relevant_extensions" key containing list of extensions
            repository_name (str): Name of the repository
            repo_path (str): Base path of the repository
            
        Returns:
            str: Path to the output directory containing generated files, or None if error
        """
        if not extensions_list or "relevant_extensions" not in extensions_list:
            return None
            
        synthetic_data = []
        repo_name = repository_name or "unknown"
        
        # Filter files by relevant extensions
        relevant_extensions = extensions_list["relevant_extensions"]
        for file_path in self.list_of_files:
            if not file_path:  # Skip empty strings
                continue
                
            # Remove leading ./ if present
            clean_path = file_path.lstrip("./")
            
            # Check if file has relevant extension
            if any(clean_path.endswith(ext) for ext in relevant_extensions):
                full_path = os.path.join(repo_path, "repository", clean_path)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        synthetic_data.append(f"<reponame>{repo_name}\n<file_sep>{clean_path}\n{content}")
                    except Exception as e:
                        print(f"Error reading file {clean_path}: {str(e)}")
                        continue

        if not synthetic_data:
            return None

        try:
            # Save each synthetic data entry to a separate file
            output_dir = "coding/synthetic_data"
            os.makedirs(output_dir, exist_ok=True)
            
            for data in synthetic_data:
                unique_id = str(uuid.uuid4())
                output_path = os.path.join(output_dir, f"qwen_to_train_{unique_id}.txt")
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(data)
            
            return output_dir
        except Exception as e:
            print(f"Error saving synthetic data: {str(e)}")
            return None