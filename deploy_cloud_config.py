import sys
import os
import re
import subprocess

def main():
    if len(sys.argv) < 3:
        print("Usage: python deploy_cloud_config.py <Cloud_Chat_Webhook_URL> <Cloud_GitHub_Webhook_URL>")
        print("Example: python deploy_cloud_config.py https://n8n.up.railway.app/webhook/123/chat https://n8n.up.railway.app/webhook/github-webhook")
        sys.exit(1)

    chat_url = sys.argv[1].strip()
    github_url = sys.argv[2].strip()

    index_path = "index.html"
    if not os.path.exists(index_path):
        print(f"Error: {index_path} not found at the root of the repository.")
        sys.exit(1)

    print("Reading index.html...")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Replace the Chat Webhook URL in index.html
    # Matches: webhookUrl: "http://..." or "https://..."
    new_content = re.sub(
        r'webhookUrl:\s*["\'](https?://[^\s"\']+)["\']',
        f'webhookUrl: "{chat_url}"',
        content
    )

    # 2. Replace the GitHub Webhook URL in index.html step 1
    # Matches: <span id="webhook-url">http://...</span>
    new_content = re.sub(
        r'<span id="webhook-url">[^<]+</span>',
        f'<span id="webhook-url">{github_url}</span>',
        new_content
    )

    # 3. Replace the fetch URL in triggerSimulation function
    # Matches: fetch("http://localhost:5678/webhook/github-webhook",
    # Or fetch("https://...",
    new_content = re.sub(
        r'fetch\(\s*["\'](https?://[^\s"\']+/webhook/github-webhook)["\']',
        f'fetch("{github_url}"',
        new_content
    )

    print("Updating index.html with cloud URLs...")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Staging and committing changes to Git...")
    subprocess.run(["git", "add", index_path], check=True)
    res = subprocess.run(["git", "commit", "-m", "Deploy cloud configurations for GitHub Pages and n8n webhook"], capture_output=True, text=True)
    print(res.stdout or res.stderr)

    print("Pushing updates to GitHub...")
    res_push = subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True)
    print(res_push.stdout or res_push.stderr)

    print("\n--- Cloud Deployment Configurations Updated! ---")
    print(f"Your live website at GitHub Pages will update shortly.")
    print(f"Lecturer URL: https://levi2599.github.io/cyber-management-project/")
    print(f"Linked Chat Webhook: {chat_url}")
    print(f"Linked GitHub Webhook: {github_url}")

if __name__ == "__main__":
    main()
