import os
import sys
import subprocess

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_check(name, check_fn):
    print(f"[{'RUNNING'}] {name}", end="\r")
    try:
        result, details = check_fn()
        if result:
            print(f"[{'PASS':<7}] {name} - {details}")
            return True
        else:
            print(f"[{'FAIL':<7}] {name} - {details}")
            return False
    except Exception as e:
        print(f"[{'FAIL':<7}] {name} - Error: {e}")
        return False

def check_dependencies():
    # Ensure no external LLM libraries exist in the virtualenv
    result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    banned = ["openai", "anthropic", "google-generativeai", "transformers"]
    found = [b for b in banned if b in result.stdout.lower()]
    if found:
        return False, f"Found banned dependencies: {found}"
    return True, "No external AI dependencies found."

def check_database():
    if not os.path.exists("recovery.db"):
        return False, "recovery.db not found. Run setup_demo.py"
    return True, "recovery.db exists."

def check_tests():
    result = subprocess.run([sys.executable, "-m", "pytest", "backend/tests"], capture_output=True, text=True)
    if result.returncode == 0:
        return True, "All tests passed."
    return False, "Pytest failed. Check logs."

def check_safety_mode():
    try:
        from backend.app.core.config import settings
        if settings.PAYMENT_EXECUTION_MODE != "SIMULATED":
            return False, f"PAYMENT_EXECUTION_MODE is {settings.PAYMENT_EXECUTION_MODE}. Must be SIMULATED."
        return True, "PAYMENT_EXECUTION_MODE is SIMULATED."
    except Exception as e:
        return False, f"Could not read config: {e}"

def check_external_ai_calls():
    # Grep the codebase for explicit API calls or references to Claude/OpenAI
    import glob
    for filepath in glob.glob("backend/**/*.py", recursive=True):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().lower()
            if "import openai" in content or "import anthropic" in content:
                return False, f"Found external AI import in {filepath}"
    return True, "No external AI API usage detected."

def main():
    print("========================================")
    print("AI Revenue Recovery - Project Validation")
    print("========================================\n")
    
    checks = [
        ("Dependency Audit", check_dependencies),
        ("Database Verification", check_database),
        ("Safety Mode Verification", check_safety_mode),
        ("External AI Audit", check_external_ai_calls),
        ("Regression Tests", check_tests),
    ]
    
    all_passed = True
    for name, check_fn in checks:
        if not run_check(name, check_fn):
            all_passed = False
            
    print("\n========================================")
    if all_passed:
        print("RESULT: PASS - System is Buildathon Ready")
        sys.exit(0)
    else:
        print("RESULT: FAIL - Validation errors found")
        sys.exit(1)

if __name__ == "__main__":
    main()
