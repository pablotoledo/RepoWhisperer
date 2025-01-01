from agents.cloning_repository import clone_repository
from agents.analysis_agent import analyze_repository
from agents.format_converter_agent import convert_to_qwen_format
from agents.relevant_files_agent import RelevantFilesIdentifier

def main():
    # Clone the repository
    clone_repository()
    
    # Analyze the cloned repository and get the results
    analysis_results, repository_name = analyze_repository()
    if analysis_results is None:
        print("Error: Could not analyze repository")
        return
    
    # Identify relevant files based on analysis
    file_identifier = RelevantFilesIdentifier()
    relevant_files = file_identifier.identify_relevant_files(analysis_results)
    if relevant_files is None:
        print("Error: Could not identify relevant files")
        return
    
    # Generate synthetic data using pure Python
    synthetic_data_path = file_identifier.generate_synthetic_data(relevant_files, repository_name)
    print(f"Synthetic data generated at: {synthetic_data_path}")
    
    # Convert analysis results to Qwen format
    convert_to_qwen_format(analysis_results)
    
    print("Process completed successfully!")

if __name__ == '__main__':
    main()