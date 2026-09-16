#!/usr/bin/env python3
"""Debug scraper to see raw HTML response."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

async def main():
    url = "https://ctpb.euskalpilota.fr/resultats.php"
    
    # Full form data
    post_data = "InSel=&InCompet=20260102&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://ctpb.euskalpilota.fr",
        "Referer": "https://ctpb.euskalpilota.fr/resultats.php",
    }
    
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        print("📡 Getting session cookie...")
        await client.get(url)
        
        print("📡 POSTing form data...")
        response = await client.post(url, content=post_data)
        
        print(f"\n📊 Status Code: {response.status_code}")
        print(f"📊 Content-Type: {response.headers.get('content-type')}")
        print(f"📊 Content Length: {len(response.text)}")
        
        print("\n📄 First 2000 chars of HTML:")
        print("=" * 80)
        print(response.text[:2000])
        print("=" * 80)
        
        # Check if we got the results table
        if "<table" in response.text:
            print("\n✅ Found <table> tag in HTML")
        else:
            print("\n❌ No <table> tag found - site may have changed structure")
            
        if "resultats" in response.text.lower():
            print("✅ Found 'resultats' in HTML")
        else:
            print("❌ No 'resultats' in HTML - may have gotten error page")

if __name__ == "__main__":
    asyncio.run(main())
