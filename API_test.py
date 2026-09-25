import httpx
import asyncio

async def get_data(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        
        # FIX 1: Property access (no parentheses)
        status = response.status_code
        print(f"Status Code: {status}")
        
        # Raise error if 4xx or 5xx
        response.raise_for_status()
        
        # FIX 2: Return .text because arXiv is XML, not JSON
        return response.text

async def main():
    q = input("Enter your chat topic today: ")
    
    # arXiv prefers '+' for spaces in simple queries
    clean_q = q.replace(" ", "+")
    
    # We use 'all:' to search across title, abstract, and authors
    url = f"https://export.arxiv.org/api/query?search_query=all:{clean_q}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
    
    # FIX 3: Correctly await the coroutine
    data = await get_data(url)
    
    print("\n--- Raw XML Data Received ---")
    print(data[:500]) # Printing first 500 chars to verify
    with open("data.xml","w") as f:
      f.write(data)

if __name__ == "__main__":
    asyncio.run(main())