import os
import subprocess
import sys

def install_requirements():
    """Instalē nepieciešamās Python bibliotēkas"""
    requirements = [
        "google-generativeai",
        "python-dotenv"
    ]
    
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ Instalēts: {package}")
        except subprocess.CalledProcessError:
            print(f"✗ Neizdevās instalēt: {package}")

def create_directories():
    """Izveido nepieciešamās mapes"""
    directories = ["sample_inputs", "outputs"]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Izveidota mape: {directory}")

def setup_environment():
    """Palīdz iestatīt vidi mainīgos"""
    api_key = input("Ievadiet savu Google Gemini API atslēgu (vai Enter, lai izlaistu): ")
    
    if api_key:
        with open(".env", "w") as f:
            f.write(f"GOOGLE_API_KEY={api_key}\n")
        print("✓ API atslēga saglabāta .env failā")
    else:
        print("ℹ API atslēgu var iestatīt vēlāk .env failā vai kā vidi mainīgo")

if __name__ == "__main__":
    print("=== AI CV Vērtētāja Iestatīšana ===\n")
    
    install_requirements()
    print()
    
    create_directories()
    print()
    
    setup_environment()
    print("\n=== Iestatīšana pabeigta ===")
    print("Palaidiet: python cv_evaluator_enhanced.py")
