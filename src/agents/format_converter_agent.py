from autogen import AssistantAgent, UserProxyAgent
from autogen.coding import LocalCommandLineCodeExecutor
import json
import os
import uuid
import jsonlines

config_list = [
    {
        "model": "qwen2.5-coder:7b",
        "base_url": "http://localhost:11434/v1",
        "api_type": "ollama"
    }
]

# Formato correcto para Qwen SFT
QWEN_FORMAT = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the main technology used in this project?"},
        {"role": "assistant", "content": "Based on the repository analysis, the main technology is Python with AutoGen framework."}
    ]
}

def is_termination_msg(x: dict) -> bool:
    """Check if the message indicates termination."""
    content = x.get("content", "").strip()
    if "```" in content:
        return False
    return content.endswith("TERMINATE")

format_converter = AssistantAgent(
    name="format_converter",
    llm_config={
        "cache_seed": 41,
        "config_list": config_list,
        "temperature": 0.1,
    },
    system_message=f"""
Assistant for converting repository analysis data to Qwen SFT training format.
Follow these exact steps in order:

1. Create a JSONL file where each line contains a messages array
2. Each message array must include system, user, and assistant messages
3. After verifying the command succeeded, confirm the file was created
4. End your message with TERMINATE on a new line
5. Never include TERMINATE in any bash commands

The exact format for each line should be:
{json.dumps(QWEN_FORMAT, indent=2)}

Requirements:
1. Each analysis question and answer should become a messages array
2. Keep the exact JSON structure as shown above
3. Use proper JSON formatting and escaping
4. Generate a JSONL file (one JSON object per line)
5. Wait for command confirmation before terminating
"""
)

user_proxy_converter = UserProxyAgent(
    name="user_proxy_converter",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=is_termination_msg,
    code_execution_config={
        "executor": LocalCommandLineCodeExecutor(work_dir="coding"),
    },
)

def convert_to_qwen_format(analysis_results):
    """
    Convert analysis results to Qwen SFT training format and save to file.
    
    Args:
        analysis_results (dict): Analysis results to convert
        
    Returns:
        str: Path to the generated JSONL file
    """
    os.makedirs("coding/synthetic_data", exist_ok=True)
    
    # Generate a unique ID for the output file
    unique_id = str(uuid.uuid4())
    output_file_path = f"synthetic_data/qwen_format_{unique_id}.jsonl"  # Note: Changed to .jsonl
    
    # Convertir los resultados del análisis al formato correcto
    formatted_data = []
    
    # Procesar cada pregunta del análisis
    if "questions" in analysis_results:
        for question in analysis_results["questions"]:
            formatted_entry = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful coding assistant."
                    },
                    {
                        "role": "user",
                        "content": question["question"]
                    },
                    {
                        "role": "assistant",
                        "content": question["answer"]
                    }
                ]
            }
            formatted_data.append(formatted_entry)
    
    # Escribir directamente el archivo JSONL
    try:
        with jsonlines.open(os.path.join("coding", output_file_path), 'w') as writer:
            writer.write_all(formatted_data)
        print(f"Successfully created {output_file_path}")
        return output_file_path
    except Exception as e:
        print(f"Error creating file: {str(e)}")
        return None