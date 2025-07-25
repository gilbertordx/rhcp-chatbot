import nltk

def main():
    """
    Downloads all necessary NLTK data for the RHCP chatbot.
    """
    print("--- Starting NLTK data setup ---")
    
    packages = ['punkt', 'wordnet', 'omw-1.4', 'punkt_tab']
    
    for package in packages:
        try:
            print(f"Checking for NLTK package: {package}...")
            nltk.data.find(f'tokenizers/{package}' if package == 'punkt' else f'corpora/{package}')
            print(f"Package '{package}' already installed.")
        except LookupError:
            print(f"Package '{package}' not found. Downloading...")
            nltk.download(package, quiet=True)
            print(f"Package '{package}' downloaded successfully.")
            
    print("--- NLTK data setup complete ---")

if __name__ == "__main__":
    main() 