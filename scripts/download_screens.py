import urllib.request
import os

files = {
    "landing.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiNzJhMGQ5ZTIwMzgzOGQyNGUxMDVmYWQ0EgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "landing-dark.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiODJiMjkzYTIwMjA3YTI3ZmNjMTgxOTc2EgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "choose-brain.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiNWY1NTBlNmMwNjM5NGVlMjM1MGEwZDFmEgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "choose-brain-dark.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiODYxNTAzZTUwMjA3YTI3ZmNjMTgxOTc2EgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "workspace.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiNjVjNDJkMDgwOTI1YzIxNDdjMDk1NTJhEgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "workspace-dark.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiODIzNzI1MzIwMmE5ODBkY2FjMDc3ZWUyEgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "active-research.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiNDk3NjMyNTYwODhlYjgyZGE0MmIzMTZmEgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "active-research-dark.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiODIyNGUwOGQwODhlYmEwZjgxMjllNWIyEgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "account-settings.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2QwMjRmMTk5OGQwMzRjN2JhOWQ4MjIwODhiM2Y1ZTI3EgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "account-settings-dark.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1MmJiODI1OTQzMTAwMWE2MzIyYzUyMWQ3NGI4EgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086",
    "logo.svg": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzExODNmZjlmZDE0NjQ5NGI4NDUyMjU0NDhlNjc0MTNmEgsSBxDHru-5kxkYAZIBJAoKcHJvamVjdF9pZBIWQhQxMjI4NjY5MDUxMDQ2NzYxNDk1Mg&filename=&opi=89354086"
}

out_dir = "frontend/src/pages"
os.makedirs(out_dir, exist_ok=True)

for name, url in files.items():
    print(f"Downloading {name}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response, open(os.path.join(out_dir, name), 'wb') as out_file:
            data = response.read()
            out_file.write(data)
    except Exception as e:
        print(f"Error downloading {name}: {e}")
