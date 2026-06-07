import httpx
import sys
import json
from datetime import datetime

# Model list from JDOS v1.2 requirement
REQUIRED_MODELS = [
    "qwen3",
    "qwen-coder",
    "qwen2.5-vl",
    "nomic-embed-text"
]

OLLAMA_URL = "http://localhost:11434/api/tags"

async def verify_models():
    print(f"--- JARVIS Model Verification Pass ({datetime.now().isoformat()}) ---")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(OLLAMA_URL)
            if response.status_code != 200:
                print(f"[ERROR] Failed to connect to Ollama: {response.status_code}")
                return
            
            data = response.json()
            installed_models = [m["name"].split(":")[0] for m in data.get("models", [])]
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "ollama_status": "online",
                "models": {}
            }
            
            all_verified = True
            for model in REQUIRED_MODELS:
                status = "INSTALLED" if model in installed_models else "MISSING"
                report["models"][model] = status
                icon = "✅" if status == "INSTALLED" else "❌"
                print(f"{icon} {model}: {status}")
                if status == "MISSING":
                    all_verified = False
            
            with open("verification_report.json", "w") as f:
                json.dump(report, f, indent=2)
            
            print("\nReport saved to verification_report.json")
            
            if not all_verified:
                print("\n[WARNING] Some required models are missing.")
                # We don't exit with error here as per "No model downloads. Verification only."
            else:
                print("\n[SUCCESS] All required models verified.")

    except Exception as e:
        print(f"[ERROR] Unexpected error during verification: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(verify_models())
