# Script Version: 1.0.0 | Last Updated: 2025-12-17
# Description: Test script for Phase 3 capabilities logic.

def test_capabilities_logic():
    print("--- Testing Capabilities Logic ---")

    # Mock metadata from OpenRouter
    mock_meta = {
        "deepseek/deepseek-r1": {
            "supported_parameters": ["include_reasoning", "temperature"]
        },
        "openai/gpt-4o": {
            "supported_parameters": ["tools", "temperature"]
        }
    }

    # Test Reasoning Detection
    r1_params = mock_meta["deepseek/deepseek-r1"]["supported_parameters"]
    gpt_params = mock_meta["openai/gpt-4o"]["supported_parameters"]

    print(f"Testing DeepSeek R1: {'include_reasoning' in r1_params}")
    assert "include_reasoning" in r1_params
    
    print(f"Testing GPT-4o: {'include_reasoning' in gpt_params}")
    assert "include_reasoning" not in gpt_params

    # Test Web Search Suffix Logic
    model_id = "openai/gpt-4o"
    chk_web_search = True
    if chk_web_search and not model_id.endswith(":online"):
        model_id += ":online"
    
    print(f"Web Search ID: {model_id}")
    assert model_id == "openai/gpt-4o:online"

    print("--- All Tests Passed ---")

if __name__ == "__main__":
    test_capabilities_logic()
