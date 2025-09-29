"""
Script to generate an HTML file from broadcast analysis using Anthropic's Claude API.

This script is designed to operate within the NCV Special Monitor project.
It takes a user ID and a broadcast ID (lv_value) as inputs, locates the
corresponding `data.json` file under the `SpecialUser` directory, extracts
the AI analysis text, removes any HTML tags from it, and then sends
the cleaned analysis along with a configured prompt to the Claude API.

The response from Claude is assumed to be HTML code. Any leading or
trailing code fences (for example, triple backticks or similar wrappers)
are stripped before writing the result to disk. The output file is named
`{lv_value}_{live_title}_image.html` and saved in the same directory as
the source `data.json`.

Configuration values such as the Claude API key, the model name, and the
HTML generation prompt are read from `config/global_config.json` under
the `api_settings` section. If this file is missing or does not contain
the expected keys, the script will exit with an error message.

Usage:
    python Claude_imagehtml_generator.py <user_id> <lv_value>

Example:
    python Claude_imagehtml_generator.py 21639740 lv348713909
"""

import json
import os
import re
import sys
from typing import Optional, Tuple

try:
    import requests  # type: ignore
except ImportError:
    # `requests` may not be installed in the environment; provide a fallback
    requests = None  # type: ignore


def load_global_config(config_path: str) -> Tuple[str, str, str, int]:
    """Load API settings from the global configuration file.

    Args:
        config_path: Path to `global_config.json`.

    Returns:
        A tuple containing (api_key, model, prompt, max_tokens).

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        KeyError: If required keys are missing from the config.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    api_settings = config.get('api_settings')
    if not api_settings:
        raise KeyError("Missing 'api_settings' section in global_config.json")
    api_key = api_settings.get('claude_api_key')
    model = api_settings.get('html_generate_ai_model')
    prompt = api_settings.get('html_generate_prompt')
    max_tokens = api_settings.get('max_tokens', 64000)  # デフォルト値64000（Claude 4 Sonnet上限）
    if not api_key:
        raise KeyError("Missing 'claude_api_key' in api_settings")
    if not model:
        raise KeyError("Missing 'html_generate_ai_model' in api_settings")
    if prompt is None:
        raise KeyError("Missing 'html_generate_prompt' in api_settings")
    return api_key, model, prompt, max_tokens


def find_user_directory(base_dir: str, user_id: str) -> Optional[str]:
    """Locate the directory for a specific user based on the user_id.

    The expected directory naming convention is `<user_id>_<display_name>`.

    Args:
        base_dir: Path to the `SpecialUser` directory.
        user_id: The numeric user ID as a string.

    Returns:
        The path to the user directory if found, otherwise None.
    """
    if not os.path.isdir(base_dir):
        return None
    for entry in os.listdir(base_dir):
        entry_path = os.path.join(base_dir, entry)
        if os.path.isdir(entry_path) and entry.startswith(f"{user_id}_"):
            return entry_path
    return None


def find_lv_directory(user_dir: str, lv_value: str) -> Optional[str]:
    """Locate the directory for a specific broadcast based on the lv_value.

    Args:
        user_dir: Path to the user directory.
        lv_value: The broadcast ID (e.g., 'lv123456789').

    Returns:
        The path to the lv directory if found, otherwise None.
    """
    if not os.path.isdir(user_dir):
        return None
    for entry in os.listdir(user_dir):
        entry_path = os.path.join(user_dir, entry)
        if os.path.isdir(entry_path) and entry == lv_value:
            return entry_path
    return None


def extract_analysis_and_title(data_path: str) -> Tuple[str, str]:
    """Extract the AI analysis and live title from a data.json file.

    Args:
        data_path: Path to the `data.json` file.

    Returns:
        A tuple of (ai_analysis, live_title).

    Raises:
        FileNotFoundError: If the data.json file does not exist.
        KeyError: If expected fields are missing.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"data.json not found: {data_path}")
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    user_data = data.get('user_data', {})
    broadcast_info = data.get('broadcast_info', {})
    ai_analysis = user_data.get('ai_analysis')
    live_title = broadcast_info.get('live_title')
    if ai_analysis is None:
        raise KeyError("Missing 'ai_analysis' in user_data of data.json")
    if live_title is None:
        raise KeyError("Missing 'live_title' in broadcast_info of data.json")
    return str(ai_analysis), str(live_title)


def strip_html_tags(text: str) -> str:
    """Remove HTML tags (e.g., `<p>`, `<br/>`) from the given text.

    Args:
        text: The input text possibly containing HTML tags.

    Returns:
        The text with HTML tags removed.
    """
    # Replace line breaks with spaces before stripping tags to preserve spacing
    cleaned = re.sub(r'<[^>]+>', '', text)
    return cleaned.strip()


def call_claude(api_key: str, model: str, prompt: str, analysis: str, max_tokens: int) -> str:
    """Call the Anthropic Claude API to generate HTML based on analysis and prompt.

    This function uses the `requests` library to send a POST request to the
    Anthropic API. It expects a JSON response containing the generated text.

    Args:
        api_key: The API key for authenticating with the Claude API.
        model: The model name to use for generation (e.g., 'claude-3-haiku').
        prompt: The base prompt describing the HTML generation task.
        analysis: The cleaned analysis text to feed into Claude.
        max_tokens: The maximum number of tokens to generate.

    Returns:
        The generated HTML content as a string.

    Raises:
        RuntimeError: If the API returns an error or the request fails.
    """
    if requests is None:
        raise RuntimeError(
            "The 'requests' library is required to call the Claude API. Please install it."
        )

    # モデルに応じてmax_tokensを調整
    if 'opus' in model.lower():
        adjusted_max_tokens = min(max_tokens, 32000)
    elif 'sonnet' in model.lower():
        adjusted_max_tokens = min(max_tokens, 64000)
    else:
        adjusted_max_tokens = min(max_tokens, 8192)

    # Compose the full prompt by combining the configured prompt and the analysis.
    full_prompt = f"{prompt}\n\n{analysis}" if prompt else analysis

    # Inform the user of the exact prompt being sent to the API. This helps with
    # debugging and transparency when checking what input is provided to Claude.
    try:
        print("Sending the following prompt to Claude API:\n" + full_prompt)
        print(f"Using model: {model}, max_tokens: {adjusted_max_tokens}")
    except Exception:
        # If printing fails for any reason, silently continue; this should not
        # block API calls.
        pass

    # Define endpoint and payload for the Anthropic API. This uses the messages
    # endpoint which is recommended for newer Claude models. If this does not
    # match your API version, adjust accordingly.
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        # Set the version header required by Anthropic; adjust as needed.
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "max_tokens": adjusted_max_tokens,
        # Keep the temperature low for deterministic HTML generation
        "temperature": 0.2,
        "messages": [
            {
                "role": "user",
                "content": full_prompt
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(
            f"Claude API request failed with status {response.status_code}: {response.text}"
        )
    try:
        result = response.json()
    except Exception:
        raise RuntimeError(f"Failed to parse Claude API response: {response.text}")
    # The structure of the response for the messages API typically contains a
    # 'content' field inside the first message. Adjust if using a different
    # endpoint or API version.
    # Example expected structure: {"content": [{"type": "text", "text": "<html>...</html>"}]}
    message_content = result.get('content')
    if not message_content:
        raise RuntimeError(f"Claude API returned no content: {result}")
    # If content is a list of message blocks, concatenate the text fields.
    if isinstance(message_content, list):
        html_parts = []
        for block in message_content:
            # Some API versions wrap the response in a dictionary with 'text'
            if isinstance(block, dict):
                text = block.get('text')
                if text:
                    html_parts.append(text)
            elif isinstance(block, str):
                html_parts.append(block)
        raw_html = ''.join(html_parts)
    elif isinstance(message_content, str):
        raw_html = message_content
    else:
        # Unexpected format
        raise RuntimeError(f"Unexpected Claude API content format: {message_content}")

    return raw_html


def strip_wrapping(text: str) -> str:
    """Strip wrapping characters such as code fences from Claude's response.

    Claude may return its response wrapped in triple backticks (```) or
    specifying the language (e.g., ```html). This function removes such
    wrappers from the beginning and end of the string.

    Args:
        text: The raw text returned by the API.

    Returns:
        The unwrapped text.
    """
    # Trim whitespace
    cleaned = text.strip()
    # Remove leading code fence if present
    cleaned = re.sub(r'^```[\w\s]*\n', '', cleaned)
    # Remove trailing code fence if present
    cleaned = re.sub(r'\n```$', '', cleaned)
    return cleaned.strip()


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename.

    Replaces or removes characters that are invalid or problematic in file
    names. Spaces are replaced with underscores, and characters other than
    alphanumerics, underscores, hyphens, and periods are removed.

    Args:
        name: The original string.

    Returns:
        A sanitized version safe for use as a filename.
    """
    # Replace whitespace with underscores
    name = re.sub(r'\s+', '_', name)
    # Remove any characters not allowed in filenames
    name = re.sub(r'[^\w\-\.]+', '', name)
    return name


def generate_html_file(lv_value: str, user_id: str) -> None:
    """Main function orchestrating the retrieval and HTML generation process.

    Args:
        lv_value: The broadcast ID (e.g., 'lv123456789').
        user_id: The user ID string (e.g., '21639740').
    """
    # Determine paths relative to this script file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    special_user_dir = os.path.join(script_dir, 'SpecialUser')
    config_path = os.path.join(script_dir, 'config', 'global_config.json')

    # Load configuration
    api_key, model, prompt, max_tokens = load_global_config(config_path)

    # Find user and lv directories
    user_dir = find_user_directory(special_user_dir, user_id)
    if user_dir is None:
        raise FileNotFoundError(
            f"Could not find directory for user_id '{user_id}' under {special_user_dir}"
        )
    lv_dir = find_lv_directory(user_dir, lv_value)
    if lv_dir is None:
        raise FileNotFoundError(
            f"Could not find directory '{lv_value}' under {user_dir}"
        )
    data_path = os.path.join(lv_dir, 'data.json')

    # Extract analysis and live title from data.json
    ai_analysis, live_title = extract_analysis_and_title(data_path)
    cleaned_analysis = strip_html_tags(ai_analysis)

    # Call the Claude API to generate HTML
    raw_html = call_claude(api_key, model, prompt, cleaned_analysis, max_tokens)
    unwrapped_html = strip_wrapping(raw_html)

    # Determine output filename and path
    sanitized_title = sanitize_filename(live_title)
    output_filename = f"{lv_value}_{sanitized_title}_image.html"
    output_path = os.path.join(lv_dir, output_filename)

    # Write the HTML content to the file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(unwrapped_html)
    print(f"Generated HTML saved to: {output_path}")

def get_max_tokens_for_model(model: str, configured_max: int) -> int:
    if 'opus' in model.lower():
        return min(configured_max, 32000)
    elif 'sonnet' in model.lower():
        return min(configured_max, 64000)
    else:
        return min(configured_max, 8192)  # 他のモデル用のデフォルト


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: python Claude_imagehtml_generator.py <user_id> <lv_value>",
            file=sys.stderr,
        )
        sys.exit(1)
    user_id = sys.argv[1]
    lv_value = sys.argv[2]
    try:
        generate_html_file(lv_value, user_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()